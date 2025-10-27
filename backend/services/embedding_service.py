"""
Embedding Service for Vector Search
Generates and manages vector embeddings for semantic search
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.services.ai_provider_service import AIProviderService, AITask
from backend.database.models import PDF, Image, Chapter
from backend.utils import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """
    Service for generating and managing vector embeddings

    Embeddings are used for:
    - Semantic search across PDFs
    - Image similarity search
    - Chapter recommendation
    - Related content discovery
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        self.ai_service = AIProviderService()

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text

        Args:
            text: Input text (will be truncated to 8k tokens if needed)

        Returns:
            1536-dimension embedding vector
        """
        try:
            result = await self.ai_service.generate_embedding(text)
            return result["embedding"]
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}", exc_info=True)
            raise

    async def generate_pdf_embeddings(
        self,
        pdf_id: str,
        chunk_size: int = 512,
        overlap: int = 50
    ) -> Dict[str, Any]:
        """
        Generate embeddings for a PDF document

        Args:
            pdf_id: PDF document ID
            chunk_size: Token chunk size for embeddings
            overlap: Token overlap between chunks

        Returns:
            Dictionary with embedding information
        """
        logger.info(f"Generating embeddings for PDF: {pdf_id}")

        # Get PDF from database
        pdf = self.db.query(PDF).filter(PDF.id == pdf_id).first()
        if not pdf:
            raise ValueError(f"PDF not found: {pdf_id}")

        if not pdf.extracted_text:
            raise ValueError(f"PDF has no extracted text: {pdf_id}")

        # Chunk text
        chunks = self._chunk_text(pdf.extracted_text, chunk_size, overlap)
        logger.info(f"Created {len(chunks)} text chunks for PDF {pdf_id}")

        # Generate embedding for full text (first 8k tokens)
        truncated_text = self._truncate_to_tokens(pdf.extracted_text, 8000)
        full_embedding = await self.generate_embedding(truncated_text)

        # Store full-text embedding
        pdf.embedding = full_embedding
        self.db.commit()

        logger.info(f"Generated embeddings for PDF {pdf_id}")

        return {
            "pdf_id": pdf_id,
            "full_embedding_dim": len(full_embedding),
            "num_chunks": len(chunks),
            "status": "completed"
        }

    async def generate_image_embeddings(
        self,
        image_id: str,
        description: str
    ) -> Dict[str, Any]:
        """
        Generate embedding for image description

        Args:
            image_id: Image ID
            description: Image description/analysis from Claude Vision

        Returns:
            Dictionary with embedding information
        """
        logger.info(f"Generating embedding for image: {image_id}")

        # Get image from database
        image = self.db.query(Image).filter(Image.id == image_id).first()
        if not image:
            raise ValueError(f"Image not found: {image_id}")

        # Generate embedding
        embedding = await self.generate_embedding(description)

        # Store embedding
        image.embedding = embedding
        self.db.commit()

        logger.info(f"Generated embedding for image {image_id}")

        return {
            "image_id": image_id,
            "embedding_dim": len(embedding),
            "status": "completed"
        }

    async def generate_chapter_embeddings(
        self,
        chapter_id: str
    ) -> Dict[str, Any]:
        """
        Generate embeddings for chapter content

        Args:
            chapter_id: Chapter ID

        Returns:
            Dictionary with embedding information
        """
        logger.info(f"Generating embeddings for chapter: {chapter_id}")

        # Get chapter from database
        chapter = self.db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter:
            raise ValueError(f"Chapter not found: {chapter_id}")

        if not chapter.sections:
            raise ValueError(f"Chapter has no content: {chapter_id}")

        # Build full chapter text
        chapter_text = self._build_chapter_text(chapter)

        # Generate embedding
        truncated_text = self._truncate_to_tokens(chapter_text, 8000)
        embedding = await self.generate_embedding(truncated_text)

        # Store embedding
        chapter.embedding = embedding
        self.db.commit()

        logger.info(f"Generated embedding for chapter {chapter_id}")

        return {
            "chapter_id": chapter_id,
            "embedding_dim": len(embedding),
            "status": "completed"
        }

    def _chunk_text(
        self,
        text: str,
        chunk_size: int = 512,
        overlap: int = 50
    ) -> List[str]:
        """
        Split text into overlapping chunks

        Args:
            text: Input text
            chunk_size: Approximate token size per chunk
            overlap: Token overlap between chunks

        Returns:
            List of text chunks
        """
        # Simple word-based chunking (approximation of tokens)
        words = text.split()
        chunks = []

        # Approximate 1 token = 0.75 words
        words_per_chunk = int(chunk_size * 0.75)
        words_overlap = int(overlap * 0.75)

        i = 0
        while i < len(words):
            chunk_words = words[i:i + words_per_chunk]
            chunks.append(" ".join(chunk_words))
            i += words_per_chunk - words_overlap

            if i >= len(words):
                break

        return chunks

    def _truncate_to_tokens(
        self,
        text: str,
        max_tokens: int = 8000
    ) -> str:
        """
        Truncate text to maximum token count

        Args:
            text: Input text
            max_tokens: Maximum tokens

        Returns:
            Truncated text
        """
        # Approximate 1 token = 0.75 words
        max_words = int(max_tokens * 0.75)
        words = text.split()

        if len(words) <= max_words:
            return text

        return " ".join(words[:max_words])

    def _build_chapter_text(self, chapter: Chapter) -> str:
        """
        Build full chapter text from sections

        Args:
            chapter: Chapter object

        Returns:
            Concatenated chapter text
        """
        parts = [f"Title: {chapter.title}"]

        if chapter.sections:
            for section in chapter.sections:
                title = section.get("title", "")
                content = section.get("content", "")
                parts.append(f"\n\n## {title}\n\n{content}")

        return "\n".join(parts)

    async def update_all_pdf_embeddings(
        self,
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """
        Regenerate embeddings for all PDFs (batch processing)

        Args:
            batch_size: Number of PDFs to process concurrently

        Returns:
            Summary statistics
        """
        logger.info("Starting batch embedding generation for all PDFs")

        # Get all PDFs without embeddings
        pdfs = self.db.query(PDF).filter(
            PDF.embedding.is_(None),
            PDF.extraction_status == "completed"
        ).all()

        logger.info(f"Found {len(pdfs)} PDFs without embeddings")

        success_count = 0
        error_count = 0

        # Process in batches
        for i in range(0, len(pdfs), batch_size):
            batch = pdfs[i:i + batch_size]

            for pdf in batch:
                try:
                    await self.generate_pdf_embeddings(str(pdf.id))
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to generate embeddings for PDF {pdf.id}: {str(e)}")
                    error_count += 1

        logger.info(f"Batch embedding complete: {success_count} success, {error_count} errors")

        return {
            "total_processed": len(pdfs),
            "success": success_count,
            "errors": error_count
        }

    async def find_similar_pdfs(
        self,
        query: str,
        max_results: int = 10,
        min_similarity: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Find PDFs similar to query using vector search

        Args:
            query: Search query
            max_results: Maximum number of results
            min_similarity: Minimum cosine similarity (0.0-1.0)

        Returns:
            List of similar PDFs with similarity scores
        """
        # Generate query embedding
        query_embedding = await self.generate_embedding(query)

        # Vector similarity search using pgvector
        # Note: This requires pgvector extension and proper indexing
        from sqlalchemy import text

        sql = text("""
            SELECT
                id,
                title,
                authors,
                year,
                journal,
                1 - (embedding <=> :query_embedding) as similarity
            FROM pdfs
            WHERE embedding IS NOT NULL
              AND 1 - (embedding <=> :query_embedding) >= :min_similarity
            ORDER BY embedding <=> :query_embedding
            LIMIT :max_results
        """)

        result = self.db.execute(
            sql,
            {
                "query_embedding": query_embedding,
                "min_similarity": min_similarity,
                "max_results": max_results
            }
        )

        pdfs = []
        for row in result:
            pdfs.append({
                "id": str(row.id),
                "title": row.title,
                "authors": row.authors,
                "year": row.year,
                "journal": row.journal,
                "similarity": float(row.similarity)
            })

        logger.info(f"Found {len(pdfs)} similar PDFs for query: '{query[:50]}...'")
        return pdfs

    async def find_similar_images(
        self,
        query: str,
        max_results: int = 10,
        min_similarity: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Find images similar to query using vector search

        Args:
            query: Search query (description)
            max_results: Maximum number of results
            min_similarity: Minimum cosine similarity

        Returns:
            List of similar images with similarity scores
        """
        # Generate query embedding
        query_embedding = await self.generate_embedding(query)

        # Vector similarity search
        from sqlalchemy import text

        sql = text("""
            SELECT
                id,
                file_path,
                description,
                1 - (embedding <=> :query_embedding) as similarity
            FROM images
            WHERE embedding IS NOT NULL
              AND 1 - (embedding <=> :query_embedding) >= :min_similarity
            ORDER BY embedding <=> :query_embedding
            LIMIT :max_results
        """)

        result = self.db.execute(
            sql,
            {
                "query_embedding": query_embedding,
                "min_similarity": min_similarity,
                "max_results": max_results
            }
        )

        images = []
        for row in result:
            images.append({
                "id": str(row.id),
                "file_path": row.file_path,
                "description": row.description,
                "similarity": float(row.similarity)
            })

        logger.info(f"Found {len(images)} similar images for query: '{query[:50]}...'")
        return images
