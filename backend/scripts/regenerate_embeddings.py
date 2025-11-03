#!/usr/bin/env python3
"""
Regenerate Embeddings Script
Regenerates embeddings for chapters that had corrupted text fixed

This script:
1. Identifies chapters that were re-extracted (have text_re_extracted metadata)
2. Deletes old embeddings generated from corrupted text
3. Triggers Celery tasks to regenerate chapter and chunk embeddings
4. Monitors progress and reports results

Usage:
    python3 -m backend.scripts.regenerate_embeddings [--chapter-ids UUID1,UUID2,...]

Options:
    --chapter-ids: Comma-separated list of chapter UUIDs to regenerate (optional)
                  If not provided, will find all chapters with re-extracted text
"""

import sys
import argparse
import time
from pathlib import Path
from typing import List
from datetime import datetime
import uuid as uuid_module

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.database import get_db
from backend.database.models import PDFChapter, PDFChunk
from backend.services.chapter_embedding_service import (
    generate_chapter_embeddings,
    generate_chunk_embeddings
)
from backend.utils import get_logger

logger = get_logger(__name__)


def find_chapters_needing_regeneration(db_session) -> List[PDFChapter]:
    """
    Find chapters that had text re-extracted and need embedding regeneration

    Returns:
        List of PDFChapter objects with re-extracted text
    """
    logger.info("Searching for chapters with re-extracted text...")

    # Query all chapters
    all_chapters = db_session.query(PDFChapter).all()

    chapters_to_regenerate = []
    for chapter in all_chapters:
        # Check if chapter has processing_metadata with text_re_extracted flag
        if hasattr(chapter, 'processing_metadata') and chapter.processing_metadata:
            if 'text_re_extracted' in chapter.processing_metadata:
                chapters_to_regenerate.append(chapter)
                logger.debug(
                    f"Found chapter needing regeneration: {chapter.chapter_title} "
                    f"(ID: {chapter.id})"
                )

    logger.info(f"Found {len(chapters_to_regenerate)} chapters needing embedding regeneration")

    return chapters_to_regenerate


def delete_old_embeddings(db_session, chapter: PDFChapter):
    """
    Delete old embeddings for chapter and its chunks

    Args:
        db_session: Database session
        chapter: PDFChapter to clear embeddings for
    """
    logger.info(f"Deleting old embeddings for chapter: {chapter.chapter_title}")

    # Clear chapter embedding
    chapter.embedding = None
    chapter.embedding_model = None
    chapter.embedding_generated_at = None

    # Clear chunk embeddings
    chunks = db_session.query(PDFChunk).filter(
        PDFChunk.chapter_id == chapter.id
    ).all()

    for chunk in chunks:
        chunk.embedding = None
        chunk.embedding_model = None

    db_session.commit()

    logger.info(f"Cleared embeddings for chapter and {len(chunks)} chunks")


def trigger_embedding_generation(chapter_id: str) -> dict:
    """
    Trigger Celery tasks to regenerate embeddings

    Args:
        chapter_id: UUID of chapter to regenerate

    Returns:
        Dict with task IDs
    """
    logger.info(f"Triggering embedding generation for chapter: {chapter_id}")

    # Trigger chapter embedding generation
    chapter_task = generate_chapter_embeddings.delay(chapter_id)

    # Trigger chunk embedding generation
    chunk_task = generate_chunk_embeddings.delay(chapter_id)

    return {
        "chapter_id": chapter_id,
        "chapter_task_id": chapter_task.id,
        "chunk_task_id": chunk_task.id
    }


def verify_embeddings_generated(db_session, chapter_id: str) -> dict:
    """
    Verify that embeddings were successfully generated

    Args:
        db_session: Database session
        chapter_id: UUID of chapter to verify

    Returns:
        Dict with verification results
    """
    chapter = db_session.query(PDFChapter).filter(
        PDFChapter.id == uuid_module.UUID(chapter_id)
    ).first()

    if not chapter:
        return {"success": False, "error": "Chapter not found"}

    # Check chapter embedding
    chapter_has_embedding = chapter.embedding is not None

    # Check chunk embeddings
    chunks = db_session.query(PDFChunk).filter(
        PDFChunk.chapter_id == uuid_module.UUID(chapter_id)
    ).all()

    chunks_with_embeddings = sum(1 for c in chunks if c.embedding is not None)
    total_chunks = len(chunks)

    success = chapter_has_embedding and (chunks_with_embeddings == total_chunks)

    return {
        "success": success,
        "chapter_has_embedding": chapter_has_embedding,
        "chunks_with_embeddings": chunks_with_embeddings,
        "total_chunks": total_chunks,
        "embedding_model": chapter.embedding_model,
        "generated_at": chapter.embedding_generated_at.isoformat() if chapter.embedding_generated_at else None
    }


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Regenerate embeddings for chapters with fixed text"
    )
    parser.add_argument(
        '--chapter-ids',
        type=str,
        help="Comma-separated list of chapter UUIDs to regenerate"
    )
    parser.add_argument(
        '--no-verify',
        action='store_true',
        help="Skip verification step (faster but no status check)"
    )

    args = parser.parse_args()

    logger.info("="*80)
    logger.info("EMBEDDING REGENERATION SCRIPT")
    logger.info("="*80)
    logger.info("")

    # Get database session
    db = next(get_db())

    try:
        # Get chapters to process
        if args.chapter_ids:
            # Use provided chapter IDs
            chapter_ids = [id.strip() for id in args.chapter_ids.split(',')]
            chapters = []
            for chapter_id in chapter_ids:
                chapter = db.query(PDFChapter).filter(
                    PDFChapter.id == uuid_module.UUID(chapter_id)
                ).first()
                if chapter:
                    chapters.append(chapter)
                else:
                    logger.warning(f"Chapter not found: {chapter_id}")
        else:
            # Auto-detect chapters needing regeneration
            chapters = find_chapters_needing_regeneration(db)

        if not chapters:
            logger.info("✅ No chapters found needing embedding regeneration")
            return

        logger.info("")
        logger.info("CHAPTERS TO PROCESS:")
        logger.info("-" * 80)
        for i, chapter in enumerate(chapters, 1):
            logger.info(
                f"{i}. {chapter.chapter_title[:60]:<60} | "
                f"ID: {str(chapter.id)[:8]}..."
            )

        logger.info("")
        logger.info(f"Total chapters: {len(chapters)}")
        logger.info("")

        # Confirm before proceeding
        response = input("Proceed with embedding regeneration? (yes/no): ")
        if response.lower() != 'yes':
            logger.info("Cancelled by user")
            return

        logger.info("")
        logger.info("PROCESSING:")
        logger.info("-" * 80)

        task_info = []

        for i, chapter in enumerate(chapters, 1):
            logger.info(f"\n[{i}/{len(chapters)}] Processing: {chapter.chapter_title}")

            # Step 1: Delete old embeddings
            delete_old_embeddings(db, chapter)

            # Step 2: Trigger new embedding generation
            tasks = trigger_embedding_generation(str(chapter.id))
            task_info.append(tasks)

            logger.info(
                f"✅ Queued tasks - Chapter: {tasks['chapter_task_id'][:8]}..., "
                f"Chunks: {tasks['chunk_task_id'][:8]}..."
            )

        logger.info("")
        logger.info("="*80)
        logger.info("EMBEDDING GENERATION QUEUED")
        logger.info("="*80)
        logger.info(f"Total chapters queued: {len(chapters)}")
        logger.info("")
        logger.info("Celery tasks are now processing in the background.")
        logger.info("This may take 5-10 minutes per chapter.")
        logger.info("")

        if not args.no_verify:
            logger.info("Waiting 30 seconds before verification check...")
            time.sleep(30)

            logger.info("")
            logger.info("VERIFICATION:")
            logger.info("-" * 80)

            for i, task in enumerate(task_info, 1):
                chapter_id = task["chapter_id"]
                result = verify_embeddings_generated(db, chapter_id)

                chapter = db.query(PDFChapter).filter(
                    PDFChapter.id == uuid_module.UUID(chapter_id)
                ).first()

                status = "✅" if result["success"] else "⏳"
                logger.info(
                    f"{status} {chapter.chapter_title[:50]:<50} | "
                    f"Chapter: {result['chapter_has_embedding']}, "
                    f"Chunks: {result['chunks_with_embeddings']}/{result['total_chunks']}"
                )

            logger.info("")
            logger.info("Note: ⏳ indicates tasks may still be processing. Check again in a few minutes.")

        logger.info("")
        logger.info("="*80)
        logger.info("COMPLETE")
        logger.info("="*80)

    except KeyboardInterrupt:
        logger.info("\n\nCancelled by user")

    except Exception as e:
        logger.error(f"\n\n❌ Error: {str(e)}", exc_info=True)
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
