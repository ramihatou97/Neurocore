#!/usr/bin/env python3
"""
Cleanup script to delete all test PDFs from database
Phase 0 of vector search implementation - Clean slate for true library

This script:
1. Counts existing PDFs, images, and citations
2. Deletes all PDFs (CASCADE deletes images and citations)
3. Optionally cleans up physical PDF files in /data/pdfs
4. Verifies cleanup completed successfully

Usage:
    # From backend directory
    python -m scripts.cleanup_test_pdfs

    # With file cleanup
    python -m scripts.cleanup_test_pdfs --delete-files

    # Dry run (no actual deletion)
    python -m scripts.cleanup_test_pdfs --dry-run
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Add backend to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import db, PDF, Image, Citation
from sqlalchemy import func

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def count_records(session):
    """Count PDFs, images, and citations before cleanup"""
    pdf_count = session.query(func.count(PDF.id)).scalar()
    image_count = session.query(func.count(Image.id)).scalar()
    citation_count = session.query(func.count(Citation.id)).scalar()

    return {
        "pdfs": pdf_count,
        "images": image_count,
        "citations": citation_count
    }


def get_pdf_file_paths(session):
    """Get all PDF file paths for optional file deletion"""
    pdfs = session.query(PDF).all()
    return [pdf.file_path for pdf in pdfs if pdf.file_path]


def delete_all_pdfs(session, dry_run=False):
    """
    Delete all PDFs from database

    CASCADE deletes will automatically delete:
    - Related images (ForeignKey with ondelete='CASCADE')
    - Related citations (ForeignKey with ondelete='CASCADE')

    Args:
        session: SQLAlchemy session
        dry_run: If True, don't actually delete (just simulate)

    Returns:
        int: Number of PDFs deleted
    """
    pdf_count = session.query(func.count(PDF.id)).scalar()

    if dry_run:
        logger.info(f"DRY RUN: Would delete {pdf_count} PDFs")
        return pdf_count

    # Delete all PDFs (CASCADE will handle images and citations)
    deleted = session.query(PDF).delete(synchronize_session=False)
    session.commit()

    logger.info(f"✅ Deleted {deleted} PDFs from database")
    return deleted


def delete_pdf_files(file_paths, dry_run=False):
    """
    Delete physical PDF files from storage

    Args:
        file_paths: List of file paths to delete
        dry_run: If True, don't actually delete

    Returns:
        dict: Statistics about deleted files
    """
    stats = {
        "total": len(file_paths),
        "deleted": 0,
        "not_found": 0,
        "errors": 0
    }

    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                if dry_run:
                    logger.info(f"DRY RUN: Would delete {file_path}")
                    stats["deleted"] += 1
                else:
                    os.remove(file_path)
                    logger.debug(f"Deleted file: {file_path}")
                    stats["deleted"] += 1
            else:
                logger.debug(f"File not found (already deleted?): {file_path}")
                stats["not_found"] += 1
        except Exception as e:
            logger.error(f"Error deleting {file_path}: {str(e)}")
            stats["errors"] += 1

    return stats


def cleanup_test_pdfs(delete_files=False, dry_run=False):
    """
    Main cleanup function

    Args:
        delete_files: If True, also delete physical PDF files
        dry_run: If True, simulate without actually deleting

    Returns:
        bool: True if cleanup successful, False otherwise
    """
    logger.info("=" * 70)
    logger.info("Phase 0: Cleanup Test PDFs - Clean Slate for True Library")
    logger.info("=" * 70)

    if dry_run:
        logger.warning("DRY RUN MODE: No actual changes will be made")

    try:
        with db.session_scope() as session:
            # Step 1: Count existing records
            logger.info("\n📊 Current Database State:")
            logger.info("-" * 70)
            before_counts = count_records(session)
            logger.info(f"  PDFs:      {before_counts['pdfs']}")
            logger.info(f"  Images:    {before_counts['images']}")
            logger.info(f"  Citations: {before_counts['citations']}")
            logger.info("-" * 70)

            if before_counts['pdfs'] == 0:
                logger.info("\n✅ Database is already clean (0 PDFs)")
                return True

            # Step 2: Get file paths if needed
            file_paths = []
            if delete_files:
                logger.info("\n📁 Collecting PDF file paths for deletion...")
                file_paths = get_pdf_file_paths(session)
                logger.info(f"  Found {len(file_paths)} file paths")

            # Step 3: Delete PDFs from database
            logger.info("\n🗑️  Deleting PDFs from database...")
            logger.info("  (CASCADE delete will remove images and citations)")
            deleted_count = delete_all_pdfs(session, dry_run=dry_run)

            # Step 4: Verify deletion
            if not dry_run:
                logger.info("\n🔍 Verifying cleanup...")
                after_counts = count_records(session)
                logger.info(f"  PDFs:      {after_counts['pdfs']} (was {before_counts['pdfs']})")
                logger.info(f"  Images:    {after_counts['images']} (was {before_counts['images']})")
                logger.info(f"  Citations: {after_counts['citations']} (was {before_counts['citations']})")

                if after_counts['pdfs'] == 0 and after_counts['images'] == 0 and after_counts['citations'] == 0:
                    logger.info("\n✅ Database cleanup successful: 0 PDFs, 0 Images, 0 Citations")
                else:
                    logger.error("\n❌ Database cleanup incomplete!")
                    logger.error(f"  Still have {after_counts['pdfs']} PDFs, {after_counts['images']} images, {after_counts['citations']} citations")
                    return False

        # Step 5: Delete physical files if requested
        if delete_files and file_paths:
            logger.info("\n🗑️  Deleting physical PDF files...")
            file_stats = delete_pdf_files(file_paths, dry_run=dry_run)
            logger.info(f"  Total files:   {file_stats['total']}")
            logger.info(f"  Deleted:       {file_stats['deleted']}")
            logger.info(f"  Not found:     {file_stats['not_found']}")
            logger.info(f"  Errors:        {file_stats['errors']}")

            if file_stats['errors'] > 0:
                logger.warning(f"\n⚠️  File cleanup completed with {file_stats['errors']} errors")
            else:
                logger.info("\n✅ File cleanup successful")

        # Final summary
        logger.info("\n" + "=" * 70)
        if dry_run:
            logger.info("DRY RUN COMPLETED: No changes were made")
        else:
            logger.info("CLEANUP COMPLETED SUCCESSFULLY")
            logger.info(f"  Deleted {deleted_count} PDFs from database")
            logger.info(f"  Deleted {before_counts['images']} images (CASCADE)")
            logger.info(f"  Deleted {before_counts['citations']} citations (CASCADE)")
            if delete_files:
                logger.info(f"  Deleted {file_stats['deleted']} physical files")
            logger.info("\n🎉 Database is now clean and ready for true library upload")
        logger.info("=" * 70)

        return True

    except Exception as e:
        logger.error(f"\n❌ Cleanup failed: {str(e)}", exc_info=True)
        return False


def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(
        description="Cleanup test PDFs to prepare for true library upload",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Database cleanup only (keep physical files)
  python -m scripts.cleanup_test_pdfs

  # Database AND file cleanup
  python -m scripts.cleanup_test_pdfs --delete-files

  # Dry run (see what would be deleted without actually deleting)
  python -m scripts.cleanup_test_pdfs --dry-run --delete-files
        """
    )

    parser.add_argument(
        '--delete-files',
        action='store_true',
        help='Also delete physical PDF files from /data/pdfs'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate cleanup without actually deleting (useful for testing)'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Confirm if not dry run
    if not args.dry_run:
        logger.warning("\n⚠️  WARNING: This will DELETE ALL PDFs from the database!")
        if args.delete_files:
            logger.warning("⚠️  WARNING: This will also DELETE physical PDF files!")
        logger.warning("\nThis action CANNOT be undone.")

        response = input("\nType 'DELETE ALL' to confirm: ")
        if response != "DELETE ALL":
            logger.info("Cleanup cancelled")
            return 1

    # Run cleanup
    success = cleanup_test_pdfs(
        delete_files=args.delete_files,
        dry_run=args.dry_run
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
