"""
Chapter Embedding Service
Celery tasks for generating embeddings for chapters and chunks
Part of Chapter-Level Vector Search (Phase 3)
"""

import asyncio
from celery import Task
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import re

from backend.services.celery_app import celery_app
from backend.database.connection import db
from backend.database.models import PDFChapter, PDFChunk
from backend.services.ai_provider_service import AIProviderService
from backend.utils import get_logger

logger = get_logger(__name__)


class DatabaseTask(Task):
    """
    Base task class that provides database session management

    Ensures proper session cleanup after task execution
    """
    _db_session = None

    @property
    def db_session(self):
        if self._db_session is None:
            self._db_session = db.get_session()
        return self._db_session

    def after_return(self, *args, **kwargs):
        if self._db_session is not None:
            self._db_session.close()
            self._db_session = None


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="backend.services.chapter_embedding_service.generate_chapter_embeddings",
    max_retries=3,
    default_retry_delay=60
)
def generate_chapter_embeddings(self, chapter_id: str) -> Dict[str, Any]:
    """
    Generate embedding for a single chapter
    Runs automatically after chapter extraction

    CRITICAL: Uses text-embedding-3-large with dimensions=1536 (pgvector limit: 2000)

    Args:
        chapter_id: UUID of PDFChapter

    Returns:
        Dict with status, embedding_dimensions, and processing info
    """
    logger.info(f"Generating embeddings for chapter: {chapter_id}")

    try:
        # Get chapter from database
        chapter = self.db_session.query(PDFChapter).filter(
            PDFChapter.id == uuid.UUID(chapter_id)
        ).first()

        if not chapter:
            raise ValueError(f"Chapter not found: {chapter_id}")

        # Skip if already embedded
        if chapter.embedding is not None:
            logger.info(f"Chapter {chapter_id} already has embedding, skipping")
            return {
                "status": "skipped",
                "reason": "embedding_exists",
                "chapter_id": chapter_id
            }

        if not chapter.extracted_text:
            raise ValueError(f"Chapter {chapter_id} has no extracted text")

        # Truncate to 8k tokens (~24k characters to be safe)
        # text-embedding-3-large supports 8191 tokens max
        # Conservative estimate: 1 token ≈ 3 characters
        max_chars = 24000
        text = chapter.extracted_text[:max_chars]
        if len(chapter.extracted_text) > max_chars:
            logger.warning(f"Truncated chapter text from {len(chapter.extracted_text)} to {len(text)} characters to fit token limit")

        # Generate embedding with CORRECT dimensions parameter
        ai_service = AIProviderService()
        result = asyncio.run(ai_service.generate_embedding(text))

        # Store embedding
        chapter.embedding = result["embedding"]
        chapter.embedding_model = result["model"]
        chapter.embedding_generated_at = datetime.utcnow()

        self.db_session.commit()

        logger.info(
            f"Chapter {chapter_id} embedding generated: "
            f"{result['dimensions']} dims, {result['tokens_used']} tokens, "
            f"${result['cost_usd']:.6f}"
        )

        # If long chapter, generate chunks
        if chapter.word_count and chapter.word_count > 4000:
            logger.info(f"Chapter {chapter_id} is long ({chapter.word_count} words), generating chunks")
            # Queue chunk embedding task
            generate_chunk_embeddings.delay(chapter_id)

        return {
            "status": "success",
            "chapter_id": chapter_id,
            "embedding_dimensions": result["dimensions"],
            "tokens_used": result["tokens_used"],
            "cost_usd": result["cost_usd"],
            "chunks_queued": chapter.word_count > 4000 if chapter.word_count else False
        }

    except Exception as e:
        logger.error(f"Error generating chapter embedding: {str(e)}", exc_info=True)

        # Retry if not max retries yet
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying chapter embedding generation (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))  # Exponential backoff

        raise


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="backend.services.chapter_embedding_service.generate_chunk_embeddings",
    max_retries=3,
    default_retry_delay=60
)
def generate_chunk_embeddings(self, chapter_id: str) -> Dict[str, Any]:
    """
    Generate embeddings for chunks of a long chapter (>4000 words)
    Enables precise retrieval within large chapters

    Args:
        chapter_id: UUID of PDFChapter

    Returns:
        Dict with status and chunk processing info
    """
    logger.info(f"Generating chunk embeddings for chapter: {chapter_id}")

    try:
        # Get chapter from database
        chapter = self.db_session.query(PDFChapter).filter(
            PDFChapter.id == uuid.UUID(chapter_id)
        ).first()

        if not chapter:
            raise ValueError(f"Chapter not found: {chapter_id}")

        if not chapter.extracted_text:
            raise ValueError(f"Chapter {chapter_id} has no extracted text")

        # Check if chunks already exist
        existing_chunks = self.db_session.query(PDFChunk).filter(
            PDFChunk.chapter_id == uuid.UUID(chapter_id)
        ).count()

        if existing_chunks > 0:
            logger.info(f"Chapter {chapter_id} already has {existing_chunks} chunks, skipping")
            return {
                "status": "skipped",
                "reason": "chunks_exist",
                "chapter_id": chapter_id,
                "existing_chunks": existing_chunks
            }

        # Intelligent chunking with boundary respect
        chunks = intelligent_chunk(
            chapter.extracted_text,
            chunk_size=1024,  # ~1024 tokens
            overlap=128,      # 128 tokens overlap
            respect_boundaries=True
        )

        logger.info(f"Created {len(chunks)} chunks for chapter {chapter_id}")

        # Generate embeddings for each chunk
        ai_service = AIProviderService()
        total_cost = 0.0
        chunks_created = 0

        for i, chunk_data in enumerate(chunks):
            try:
                # Generate embedding
                result = asyncio.run(ai_service.generate_embedding(chunk_data['text']))

                # Create PDFChunk record
                chunk = PDFChunk(
                    chapter_id=uuid.UUID(chapter_id),
                    chunk_index=i,
                    chunk_text=chunk_data['text'],
                    token_count=chunk_data['token_count'],
                    start_char_offset=chunk_data['start_offset'],
                    end_char_offset=chunk_data['end_offset'],
                    preceding_heading=chunk_data['preceding_heading'],
                    contains_headings=chunk_data['contains_headings'],
                    embedding=result["embedding"],
                    embedding_model=result["model"]
                )

                self.db_session.add(chunk)
                total_cost += result["cost_usd"]
                chunks_created += 1

                # Commit in batches of 10 to avoid memory issues
                if (i + 1) % 10 == 0:
                    self.db_session.commit()
                    logger.info(f"Committed batch of 10 chunks ({i + 1}/{len(chunks)})")

            except Exception as e:
                logger.error(f"Error generating embedding for chunk {i}: {str(e)}")
                continue

        # Final commit
        self.db_session.commit()

        logger.info(
            f"Chapter {chapter_id}: Created {chunks_created} chunks, "
            f"total cost: ${total_cost:.6f}"
        )

        return {
            "status": "success",
            "chapter_id": chapter_id,
            "chunks_created": chunks_created,
            "total_chunks": len(chunks),
            "total_cost_usd": total_cost
        }

    except Exception as e:
        logger.error(f"Error generating chunk embeddings: {str(e)}", exc_info=True)

        # Retry if not max retries yet
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying chunk embedding generation (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

        raise


def intelligent_chunk(
    text: str,
    chunk_size: int = 1024,
    overlap: int = 128,
    respect_boundaries: bool = True
) -> List[Dict[str, Any]]:
    """
    Intelligently chunk text with boundary respect

    Features:
    - Respects paragraph boundaries (double newlines)
    - Respects sentence boundaries (periods, question marks, exclamation marks)
    - Preserves section headings for context
    - Handles medical term coherence
    - Maintains overlap for continuity

    Args:
        text: Input text to chunk
        chunk_size: Target chunk size in tokens (~4 chars per token)
        overlap: Overlap size in tokens
        respect_boundaries: Whether to respect paragraph/sentence boundaries

    Returns:
        List of chunk dictionaries with text, offsets, and metadata
    """
    # Approximate: 1 token ~= 4 characters
    chunk_size_chars = chunk_size * 4
    overlap_chars = overlap * 4

    chunks = []

    # Extract section headings (lines that are all caps or start with numbers)
    headings_pattern = r'^([A-Z][A-Z\s]+|[\dIVX]+\.?\s+[^\n]+)$'
    lines = text.split('\n')
    headings = {}

    for i, line in enumerate(lines):
        if re.match(headings_pattern, line.strip()):
            headings[i] = line.strip()

    # Split into paragraphs first
    paragraphs = text.split('\n\n')

    current_chunk = ""
    current_offset = 0
    preceding_heading = None
    contains_headings = []

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        # Check if this paragraph is a heading
        is_heading = any(heading in paragraph for heading in headings.values())

        if is_heading:
            # Save current heading as context
            preceding_heading = paragraph
            contains_headings = []

        # If adding this paragraph would exceed chunk size, start new chunk
        if len(current_chunk) + len(paragraph) > chunk_size_chars and current_chunk:
            # Save current chunk
            chunks.append({
                'text': current_chunk.strip(),
                'token_count': len(current_chunk) // 4,  # Approximate
                'start_offset': current_offset,
                'end_offset': current_offset + len(current_chunk),
                'preceding_heading': preceding_heading,
                'contains_headings': contains_headings.copy() if contains_headings else None
            })

            # Start new chunk with overlap
            if respect_boundaries:
                # Take last sentence(s) for overlap
                overlap_text = get_last_sentences(current_chunk, overlap_chars)
                current_offset += len(current_chunk) - len(overlap_text)
                current_chunk = overlap_text + "\n\n" + paragraph
            else:
                # Simple character overlap
                current_offset += chunk_size_chars - overlap_chars
                current_chunk = current_chunk[-overlap_chars:] + "\n\n" + paragraph

            contains_headings = []

        else:
            # Add paragraph to current chunk
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
                current_offset = text.find(paragraph)

        # Track headings in current chunk
        if is_heading and paragraph not in contains_headings:
            contains_headings.append(paragraph)

    # Add final chunk
    if current_chunk:
        chunks.append({
            'text': current_chunk.strip(),
            'token_count': len(current_chunk) // 4,
            'start_offset': current_offset,
            'end_offset': current_offset + len(current_chunk),
            'preceding_heading': preceding_heading,
            'contains_headings': contains_headings if contains_headings else None
        })

    return chunks


def get_last_sentences(text: str, max_length: int) -> str:
    """
    Get last complete sentences from text up to max_length

    Args:
        text: Input text
        max_length: Maximum length in characters

    Returns:
        Last complete sentences
    """
    # Split on sentence boundaries
    sentence_endings = r'[.!?]\s+'
    sentences = re.split(sentence_endings, text)

    # Build from end
    result = ""
    for sentence in reversed(sentences):
        if len(result) + len(sentence) > max_length:
            break
        result = sentence + ". " + result

    return result.strip()


def get_embedding_progress() -> Dict[str, Any]:
    """
    Get embedding generation progress for all chapters

    Returns:
        Dict with total_chapters, embedded_chapters, progress_percent
    """
    session = db.get_session()

    try:
        total_chapters = session.query(PDFChapter).count()
        embedded_chapters = session.query(PDFChapter).filter(
            PDFChapter.embedding.isnot(None)
        ).count()

        progress_percent = (embedded_chapters / total_chapters * 100) if total_chapters > 0 else 0

        return {
            "total_chapters": total_chapters,
            "embedded_chapters": embedded_chapters,
            "pending_chapters": total_chapters - embedded_chapters,
            "progress_percent": round(progress_percent, 2)
        }

    finally:
        session.close()
