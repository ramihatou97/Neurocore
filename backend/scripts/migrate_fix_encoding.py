#!/usr/bin/env python3
"""
Migration Script: Fix Text Encoding Issues in Existing Chapters
Re-extracts chapter text using new robust extraction with OCR fallback

This script:
1. Identifies chapters with corrupted text (>5% replacement characters)
2. Re-extracts text using multi-strategy approach (PyMuPDF → OCR)
3. Updates database with clean text
4. Preserves all other chapter data

Usage:
    python3 -m backend.scripts.migrate_fix_encoding [--dry-run] [--limit N]

Options:
    --dry-run: Show what would be done without making changes
    --limit N: Only process first N chapters (for testing)
"""

import sys
import argparse
from pathlib import Path
from typing import List, Tuple
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.database import get_db
from backend.database.models import PDFChapter, PDFBook
from backend.services.textbook_processor import TextbookProcessorService
from backend.utils import get_logger

logger = get_logger(__name__)


def has_encoding_issues(text: str, threshold: float = 0.05) -> bool:
    """
    Check if text has encoding issues

    Args:
        text: Text to check
        threshold: Minimum ratio of replacement chars to consider corrupted (default 5%)

    Returns:
        True if text has >threshold replacement characters
    """
    if not text or len(text) == 0:
        return False

    replacement_char = chr(0xfffd)  # U+FFFD
    replacement_count = text.count(replacement_char)
    ratio = replacement_count / len(text)

    return ratio > threshold


def find_corrupted_chapters(db_session, limit: int = None) -> List[Tuple[PDFChapter, PDFBook, float]]:
    """
    Find chapters with corrupted text

    Args:
        db_session: Database session
        limit: Maximum number of chapters to return (None = all)

    Returns:
        List of (chapter, book, corruption_ratio) tuples
    """
    logger.info("Scanning database for chapters with encoding issues...")

    query = db_session.query(PDFChapter, PDFBook).join(
        PDFBook, PDFChapter.book_id == PDFBook.id
    ).filter(
        PDFChapter.extracted_text.isnot(None),
        PDFChapter.extracted_text != ""
    )

    if limit:
        query = query.limit(limit * 3)  # Get 3x to account for filtering

    all_chapters = query.all()

    corrupted = []
    for chapter, book in all_chapters:
        if has_encoding_issues(chapter.extracted_text, threshold=0.05):
            replacement_char = chr(0xfffd)
            corruption_ratio = chapter.extracted_text.count(replacement_char) / len(chapter.extracted_text)
            corrupted.append((chapter, book, corruption_ratio))

    # Sort by corruption ratio (worst first)
    corrupted.sort(key=lambda x: x[2], reverse=True)

    if limit:
        corrupted = corrupted[:limit]

    logger.info(f"Found {len(corrupted)} chapters with encoding issues")

    return corrupted


def re_extract_chapter(
    processor: TextbookProcessorService,
    chapter: PDFChapter,
    book: PDFBook,
    dry_run: bool = False
) -> Tuple[bool, str, int]:
    """
    Re-extract chapter text using robust extraction

    Args:
        processor: TextbookProcessorService instance
        chapter: PDFChapter to re-extract
        book: PDFBook containing the chapter
        dry_run: If True, don't update database

    Returns:
        Tuple of (success, message, new_char_count)
    """
    try:
        # Check if PDF file exists
        if not Path(book.file_path).exists():
            return False, f"PDF file not found: {book.file_path}", 0

        logger.info(
            f"Re-extracting chapter: {chapter.chapter_title} "
            f"(pages {chapter.start_page}-{chapter.end_page}) "
            f"from {book.title}"
        )

        # Extract using new robust method
        result = processor.extract_chapter(
            pdf_path=book.file_path,
            start_page=chapter.start_page,
            end_page=chapter.end_page,
            title=chapter.chapter_title
        )

        new_text = result['extracted_text']
        new_char_count = len(new_text)

        # Check if new text is clean
        if has_encoding_issues(new_text, threshold=0.05):
            replacement_char = chr(0xfffd)
            ratio = new_text.count(replacement_char) / len(new_text) if len(new_text) > 0 else 0
            return False, f"Re-extraction still has encoding issues ({ratio*100:.1f}% corrupted)", 0

        # Update database (if not dry run)
        if not dry_run:
            old_char_count = len(chapter.extracted_text)
            chapter.extracted_text = new_text
            chapter.word_count = result['word_count']
            chapter.content_hash = result['content_hash']

            # Add metadata about migration
            if not hasattr(chapter, 'processing_metadata') or chapter.processing_metadata is None:
                chapter.processing_metadata = {}

            chapter.processing_metadata['text_re_extracted'] = {
                'timestamp': datetime.utcnow().isoformat(),
                'reason': 'encoding_fix_migration',
                'old_char_count': old_char_count,
                'new_char_count': new_char_count,
                'improvement': 'ocr_used' if 'ocr' in result.get('extraction_method', '') else 'pymupdf_fixed'
            }

        return True, f"Successfully re-extracted {new_char_count} characters", new_char_count

    except Exception as e:
        logger.error(f"Error re-extracting chapter {chapter.id}: {str(e)}", exc_info=True)
        return False, f"Error: {str(e)}", 0


def main():
    """Main migration function"""
    parser = argparse.ArgumentParser(
        description="Fix text encoding issues in existing chapters"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help="Only process first N chapters (for testing)"
    )

    args = parser.parse_args()

    logger.info("="*80)
    logger.info("TEXT ENCODING FIX MIGRATION")
    logger.info("="*80)
    logger.info(f"Mode: {'DRY RUN (no changes)' if args.dry_run else 'LIVE (will update database)'}")
    if args.limit:
        logger.info(f"Limit: {args.limit} chapters")
    logger.info("")

    # Get database session
    db = next(get_db())

    try:
        # Find corrupted chapters
        corrupted_chapters = find_corrupted_chapters(db, limit=args.limit)

        if not corrupted_chapters:
            logger.info("✅ No chapters with encoding issues found!")
            return

        # Display corruption summary
        logger.info("")
        logger.info("CORRUPTION SUMMARY:")
        logger.info("-" * 80)
        for i, (chapter, book, ratio) in enumerate(corrupted_chapters[:10], 1):
            logger.info(
                f"{i}. {chapter.chapter_title[:50]:<50} | "
                f"Corruption: {ratio*100:5.1f}% | "
                f"Book: {book.title[:30]}"
            )

        if len(corrupted_chapters) > 10:
            logger.info(f"... and {len(corrupted_chapters) - 10} more")

        logger.info("")
        logger.info(f"Total chapters to process: {len(corrupted_chapters)}")
        logger.info("")

        # Confirm before proceeding (unless dry-run)
        if not args.dry_run:
            response = input("Proceed with re-extraction? (yes/no): ")
            if response.lower() != 'yes':
                logger.info("Cancelled by user")
                return

        # Initialize processor
        processor = TextbookProcessorService(db)

        # Process each chapter
        logger.info("")
        logger.info("PROCESSING CHAPTERS:")
        logger.info("-" * 80)

        stats = {
            'total': len(corrupted_chapters),
            'success': 0,
            'failed': 0,
            'total_chars_extracted': 0
        }

        for i, (chapter, book, old_ratio) in enumerate(corrupted_chapters, 1):
            logger.info(
                f"\n[{i}/{stats['total']}] Processing: {chapter.chapter_title} "
                f"(corruption: {old_ratio*100:.1f}%)"
            )

            success, message, char_count = re_extract_chapter(
                processor, chapter, book, dry_run=args.dry_run
            )

            if success:
                stats['success'] += 1
                stats['total_chars_extracted'] += char_count
                logger.info(f"✅ {message}")
            else:
                stats['failed'] += 1
                logger.error(f"❌ {message}")

        # Commit changes (if not dry run)
        if not args.dry_run and stats['success'] > 0:
            logger.info("\nCommitting changes to database...")
            db.commit()
            logger.info("✅ Changes committed")

        # Print final statistics
        logger.info("")
        logger.info("="*80)
        logger.info("MIGRATION COMPLETE")
        logger.info("="*80)
        logger.info(f"Total chapters processed: {stats['total']}")
        logger.info(f"✅ Successfully re-extracted: {stats['success']}")
        logger.info(f"❌ Failed: {stats['failed']}")
        logger.info(f"📝 Total characters extracted: {stats['total_chars_extracted']:,}")

        if args.dry_run:
            logger.info("\n⚠️  DRY RUN MODE - No changes were made to the database")

    except KeyboardInterrupt:
        logger.info("\n\nMigration cancelled by user")
        db.rollback()

    except Exception as e:
        logger.error(f"\n\n❌ Migration failed: {str(e)}", exc_info=True)
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
