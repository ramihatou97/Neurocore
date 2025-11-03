"""
Title Extraction Celery Tasks
Background tasks for async AI-powered book title extraction from PDF cover pages
Part of Enhancement #2: AI Title Extraction
"""

from celery import Task
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid as uuid_module

from backend.services.celery_app import celery_app
from backend.database import get_db
from backend.database.models import PDFBook
from backend.services.title_extraction_service import TitleExtractionService
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
            self._db_session = next(get_db())
        return self._db_session

    def after_return(self, *args, **kwargs):
        if self._db_session is not None:
            self._db_session.close()
            self._db_session = None


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="backend.services.title_extraction_tasks.extract_title_from_cover",
    max_retries=2,
    default_retry_delay=30,
    soft_time_limit=90,
    time_limit=120
)
def extract_title_from_cover(
    self,
    book_id: str,
    auto_apply_threshold: float = 0.8,
    page_num: int = 0
) -> Dict[str, Any]:
    """
    Extract book title from PDF cover page using GPT-4o Vision

    This task:
    1. Renders PDF cover page to high-quality image
    2. Calls GPT-4o Vision API to extract title with confidence
    3. Auto-applies title if confidence >= threshold
    4. Stores metadata for manual review if 0.5 <= confidence < threshold
    5. Logs failure if confidence < 0.5

    Args:
        book_id: UUID of PDFBook to process
        auto_apply_threshold: Confidence threshold for auto-apply (default 0.8)
        page_num: Page number to extract from (default 0 = cover page)

    Returns:
        Dict with extraction results:
        {
            "book_id": "uuid",
            "status": "auto_applied" | "needs_review" | "failed",
            "title": "Extracted Title" or None,
            "confidence": 0.95,
            "original_title": "Previous Title",
            "metadata": {...}
        }

    Raises:
        ValueError: If book not found
        Exception: If extraction fails (will retry up to 2 times)

    Example:
        >>> extract_title_from_cover.delay("book-uuid-here")
    """
    logger.info(f"Starting title extraction for book: {book_id}")

    try:
        # Get book from database
        book = self.db_session.query(PDFBook).filter(
            PDFBook.id == uuid_module.UUID(book_id)
        ).first()

        if not book:
            logger.error(f"Book not found: {book_id}")
            raise ValueError(f"Book not found: {book_id}")

        # Initialize extraction service
        service = TitleExtractionService()

        # Extract title from cover page
        logger.info(f"Extracting title from: {book.file_path}")
        title, confidence, metadata = service.extract_title_from_pdf(
            book.file_path,
            page_num=page_num
        )

        # Store original title for audit trail
        original_title = book.title

        # Decision logic based on confidence
        if title and confidence >= auto_apply_threshold:
            # HIGH CONFIDENCE: Auto-apply title
            logger.info(
                f"Auto-applying title for book {book_id}: "
                f"'{original_title}' → '{title}' (confidence {confidence:.2f})"
            )

            # Preserve original title on first edit
            if book.original_title is None:
                book.original_title = original_title

            # Update title with AI extraction metadata
            book.title = title
            book.title_edited_at = datetime.utcnow()
            book.title_edited_by = None  # AI extraction, not user edit

            # Store AI extraction metadata in JSONB field (if it exists)
            if hasattr(book, 'ai_metadata') and book.ai_metadata:
                book.ai_metadata['title_extraction'] = {
                    'extracted_title': title,
                    'confidence': confidence,
                    'extraction_date': datetime.utcnow().isoformat(),
                    'model': metadata.get('model', 'gpt-4o'),
                    'reasoning': metadata.get('reasoning', ''),
                    'alternatives': metadata.get('alternatives', []),
                    'language': metadata.get('language', 'Unknown'),
                    'subtitle': metadata.get('subtitle'),
                    'auto_applied': True
                }

            self.db_session.commit()

            return {
                "book_id": book_id,
                "status": "auto_applied",
                "title": title,
                "confidence": confidence,
                "original_title": original_title,
                "metadata": metadata
            }

        elif title and confidence >= 0.5:
            # MEDIUM CONFIDENCE: Store for manual review
            logger.info(
                f"Title suggestion for book {book_id}: "
                f"'{title}' (confidence {confidence:.2f}) - needs manual review"
            )

            # Store suggestion in metadata for later review
            if hasattr(book, 'ai_metadata'):
                if book.ai_metadata is None:
                    book.ai_metadata = {}

                book.ai_metadata['title_suggestion'] = {
                    'suggested_title': title,
                    'confidence': confidence,
                    'suggestion_date': datetime.utcnow().isoformat(),
                    'model': metadata.get('model', 'gpt-4o'),
                    'reasoning': metadata.get('reasoning', ''),
                    'alternatives': metadata.get('alternatives', []),
                    'language': metadata.get('language', 'Unknown'),
                    'subtitle': metadata.get('subtitle'),
                    'needs_review': True
                }

                self.db_session.commit()

            return {
                "book_id": book_id,
                "status": "needs_review",
                "suggested_title": title,
                "confidence": confidence,
                "current_title": original_title,
                "metadata": metadata
            }

        else:
            # LOW CONFIDENCE: Extraction failed
            logger.warning(
                f"Title extraction failed for book {book_id}: "
                f"{metadata.get('error', 'Low confidence')} (confidence {confidence:.2f})"
            )

            return {
                "book_id": book_id,
                "status": "failed",
                "reason": metadata.get("error") or "Low confidence",
                "confidence": confidence,
                "current_title": original_title,
                "metadata": metadata
            }

    except ValueError as e:
        # Don't retry for ValueError (book not found)
        logger.error(f"ValueError in title extraction for {book_id}: {str(e)}")
        raise

    except Exception as e:
        # Retry for other exceptions (API errors, network issues, etc.)
        logger.error(
            f"Error extracting title for book {book_id}: {str(e)}",
            exc_info=True
        )

        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="backend.services.title_extraction_tasks.batch_extract_titles",
    max_retries=1,
    default_retry_delay=60,
    soft_time_limit=1500,  # 25 minutes
    time_limit=1800  # 30 minutes
)
def batch_extract_titles(
    self,
    book_ids: List[str],
    auto_apply_threshold: float = 0.8
) -> Dict[str, Any]:
    """
    Batch process multiple books for title extraction

    This task:
    1. Iterates through list of book IDs
    2. Extracts title from each book's cover page
    3. Auto-applies or suggests titles based on confidence
    4. Returns processing statistics

    Args:
        book_ids: List of PDFBook UUIDs to process
        auto_apply_threshold: Confidence threshold for auto-apply (default 0.8)

    Returns:
        Dict with processing statistics:
        {
            "total_books": 15,
            "processed": 15,
            "auto_applied": 12,
            "manual_review": 2,
            "failed": 1,
            "results": [...]
        }

    Example:
        >>> batch_extract_titles.delay(["uuid1", "uuid2", "uuid3"])
    """
    logger.info(f"Starting batch title extraction for {len(book_ids)} books")

    results = {
        "total_books": len(book_ids),
        "processed": 0,
        "auto_applied": 0,
        "manual_review": 0,
        "failed": 0,
        "results": []
    }

    service = TitleExtractionService()

    for book_id in book_ids:
        try:
            # Get book from database
            book = self.db_session.query(PDFBook).filter(
                PDFBook.id == uuid_module.UUID(book_id)
            ).first()

            if not book:
                results["failed"] += 1
                results["results"].append({
                    "book_id": book_id,
                    "status": "error",
                    "message": "Book not found"
                })
                continue

            # Extract title
            title, confidence, metadata = service.extract_title_from_pdf(
                book.file_path,
                page_num=0
            )

            results["processed"] += 1
            original_title = book.title

            if title and confidence >= auto_apply_threshold:
                # Auto-apply high-confidence titles
                if book.original_title is None:
                    book.original_title = original_title

                book.title = title
                book.title_edited_at = datetime.utcnow()
                book.title_edited_by = None  # AI extraction

                self.db_session.commit()

                results["auto_applied"] += 1
                results["results"].append({
                    "book_id": book_id,
                    "status": "auto_applied",
                    "title": title,
                    "confidence": confidence,
                    "previous_title": original_title
                })

                logger.info(
                    f"Auto-applied title for book {book_id}: "
                    f"'{original_title}' → '{title}' (confidence {confidence:.2f})"
                )

            elif title and confidence >= 0.5:
                # Medium confidence - manual review
                results["manual_review"] += 1
                results["results"].append({
                    "book_id": book_id,
                    "status": "needs_review",
                    "suggested_title": title,
                    "confidence": confidence,
                    "alternatives": metadata.get("alternatives", []),
                    "current_title": original_title
                })

                logger.info(
                    f"Title suggestion for book {book_id}: "
                    f"'{title}' (confidence {confidence:.2f})"
                )

            else:
                # Low confidence or extraction failed
                results["failed"] += 1
                results["results"].append({
                    "book_id": book_id,
                    "status": "failed",
                    "reason": metadata.get("error") or "Low confidence",
                    "confidence": confidence,
                    "current_title": original_title
                })

                logger.warning(
                    f"Title extraction failed for book {book_id}: "
                    f"{metadata.get('error', 'Low confidence')} "
                    f"(confidence {confidence:.2f})"
                )

        except Exception as e:
            results["failed"] += 1
            results["results"].append({
                "book_id": book_id,
                "status": "error",
                "message": str(e)
            })
            logger.error(f"Error processing book {book_id}: {str(e)}", exc_info=True)

    logger.info(
        f"Batch title extraction complete: "
        f"{results['processed']}/{results['total_books']} processed, "
        f"{results['auto_applied']} auto-applied, "
        f"{results['manual_review']} need review, "
        f"{results['failed']} failed"
    )

    return results
