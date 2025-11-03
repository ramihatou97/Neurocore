"""
Textbook/Chapter Upload API Routes
Phase 5: Chapter-Level Vector Search Upload Infrastructure
"""

import io
import re
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Query, status, HTTPException
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid as uuid_module
from datetime import datetime

from backend.database import get_db, User
from backend.services.textbook_processor import TextbookProcessorService
from backend.services.chapter_embedding_service import (
    generate_chapter_embeddings,
    generate_chunk_embeddings,
    get_embedding_progress
)
from backend.services.chapter_vector_search_service import check_for_duplicates
from backend.services.title_extraction_tasks import extract_title_from_cover, batch_extract_titles
from backend.services.background_tasks import extract_images_task, analyze_images_task
from backend.utils import get_logger, get_current_active_user
from backend.database.models import PDFBook, PDFChapter, PDFChunk, PDF

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/textbooks", tags=["textbooks"])


# ==================== Response Models ====================

class ChapterResponse(BaseModel):
    """Response model for chapter information"""
    id: str
    book_id: Optional[str]
    book_title: Optional[str] = None  # Parent book title
    source_type: str
    chapter_number: Optional[int]
    chapter_title: str
    start_page: Optional[int]
    end_page: Optional[int]
    page_count: Optional[int]
    word_count: Optional[int]
    has_images: bool
    image_count: int
    has_embedding: bool
    is_duplicate: bool
    quality_score: float
    detection_method: Optional[str]
    detection_confidence: Optional[float]
    created_at: str

    # Content fields (Fix for Issue #1 - Chapter content not displaying)
    extracted_text: str = ""  # Full chapter text
    extracted_text_preview: Optional[str] = None  # First 500 chars preview

    # Embedding metadata
    embedding_model: Optional[str] = None
    embedding_generated_at: Optional[str] = None

    # Deduplication fields
    content_hash: Optional[str] = None
    duplicate_of_id: Optional[str] = None
    duplicate_group_id: Optional[str] = None
    preference_score: Optional[float] = 0.0

    # Additional metadata
    updated_at: Optional[str] = None
    chunks_count: Optional[int] = 0

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "book_id": "456e7890-e89b-12d3-a456-426614174000",
                "source_type": "textbook_chapter",
                "chapter_number": 5,
                "chapter_title": "Cerebrovascular Neurosurgery",
                "start_page": 120,
                "end_page": 165,
                "page_count": 45,
                "word_count": 12000,
                "has_images": True,
                "image_count": 8,
                "has_embedding": True,
                "is_duplicate": False,
                "quality_score": 0.85,
                "detection_method": "toc",
                "detection_confidence": 0.9,
                "created_at": "2025-10-31T12:00:00"
            }
        }


class BookResponse(BaseModel):
    """Response model for book information"""
    id: str
    title: str
    authors: Optional[List[str]]
    edition: Optional[str]
    publication_year: Optional[int]
    publisher: Optional[str]
    isbn: Optional[str]
    total_chapters: Optional[int]
    total_pages: Optional[int]
    file_size_bytes: Optional[int]
    processing_status: str
    uploaded_at: str
    created_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": "456e7890-e89b-12d3-a456-426614174000",
                "title": "Principles of Neurosurgery",
                "authors": ["Dr. Smith", "Dr. Johnson"],
                "edition": "5th Edition",
                "publication_year": 2023,
                "publisher": "Medical Publishing Inc.",
                "isbn": "978-1-234567-89-0",
                "total_chapters": 25,
                "total_pages": 850,
                "file_size_bytes": 52428800,
                "processing_status": "completed",
                "uploaded_at": "2025-10-31T12:00:00",
                "created_at": "2025-10-31T12:00:00"
            }
        }


class UploadResponse(BaseModel):
    """Response model for upload operations"""
    status: str
    message: str
    book_id: str
    chapters_created: int
    pdf_type: str
    total_pages: int
    embedding_tasks_queued: int

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "PDF uploaded and processed successfully",
                "book_id": "456e7890-e89b-12d3-a456-426614174000",
                "chapters_created": 25,
                "pdf_type": "textbook",
                "total_pages": 850,
                "embedding_tasks_queued": 25
            }
        }


class BatchUploadResponse(BaseModel):
    """Response model for batch upload operations"""
    status: str
    message: str
    total_files: int
    successful_uploads: int
    failed_uploads: int
    books_created: List[str]
    total_chapters_created: int
    total_embedding_tasks_queued: int
    failures: Optional[List[dict]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "completed",
                "message": "Batch upload completed with 8/10 successful uploads",
                "total_files": 10,
                "successful_uploads": 8,
                "failed_uploads": 2,
                "books_created": ["uuid1", "uuid2", "uuid3"],
                "total_chapters_created": 150,
                "total_embedding_tasks_queued": 150,
                "failures": [
                    {"filename": "corrupt.pdf", "error": "Invalid PDF format"}
                ]
            }
        }


class UploadProgressResponse(BaseModel):
    """Response model for upload progress"""
    book_id: str
    title: str
    processing_status: str
    total_chapters: int
    chapters_with_embeddings: int
    embedding_progress_percent: float
    estimated_completion_minutes: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "book_id": "456e7890-e89b-12d3-a456-426614174000",
                "title": "Principles of Neurosurgery",
                "processing_status": "processing",
                "total_chapters": 25,
                "chapters_with_embeddings": 12,
                "embedding_progress_percent": 48.0,
                "estimated_completion_minutes": 5
            }
        }


class LibraryStatsResponse(BaseModel):
    """Response model for library statistics"""
    total_books: int
    total_chapters: int
    total_chunks: int
    chapters_with_embeddings: int
    embedding_progress_percent: float
    unique_chapters: int
    duplicate_chapters: int
    total_storage_bytes: int
    storage_gb: float

    class Config:
        json_schema_extra = {
            "example": {
                "total_books": 50,
                "total_chapters": 1250,
                "total_chunks": 3500,
                "chapters_with_embeddings": 1100,
                "embedding_progress_percent": 88.0,
                "unique_chapters": 1050,
                "duplicate_chapters": 200,
                "total_storage_bytes": 5368709120,
                "storage_gb": 5.0
            }
        }


class TitleUpdateRequest(BaseModel):
    """Request model for updating book title"""
    title: str = Field(..., min_length=1, max_length=500, description="New book title")

    @validator('title')
    def validate_title(cls, v):
        """Validate title is not empty or generic placeholder"""
        if not v or not v.strip():
            raise ValueError('Title cannot be empty or whitespace')
        if v.strip() == "Untitled Book - Please Edit":
            raise ValueError('Please enter a meaningful title')
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Youmans Neurological Surgery Volume 1"
            }
        }


# ==================== Upload Routes ====================

@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a textbook or chapter PDF",
    description="""
    Upload a PDF (textbook, standalone chapter, or research paper) for chapter-level processing.

    The system will:
    1. Classify the PDF (textbook/chapter/paper)
    2. Detect and extract chapters (3-tier detection: TOC/Pattern/Heading)
    3. Create PDFBook and PDFChapter records
    4. Queue background tasks for:
       - Embedding generation (1536-dim text-embedding-3-large)
       - Chunk generation (for long chapters >4000 words)
       - Duplicate detection (>95% similarity threshold)

    Maximum file size: 100MB
    Supported formats: PDF
    """
)
async def upload_textbook(
    file: UploadFile = File(..., description="PDF file to upload (textbook/chapter/paper)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> UploadResponse:
    """
    Upload PDF and process into chapters with automatic embedding generation

    Workflow:
    1. Save file to storage
    2. Classify PDF type
    3. Detect chapters
    4. Extract chapter content
    5. Queue Celery tasks for embeddings

    Requires authentication.
    """
    logger.info(f"Textbook upload started by user {current_user.email}: {file.filename}")

    # Validate file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )

    # Save file to storage
    from backend.services.storage_service import StorageService
    storage = StorageService()

    try:
        file_content = await file.read()
        storage_result = storage.save_pdf(
            io.BytesIO(file_content),
            file.filename
        )
        file_path = storage_result["file_path"]
        original_filename = storage_result["original_filename"]

        logger.info(f"PDF saved to storage: {file_path} (original: {original_filename})")

    except Exception as e:
        logger.error(f"Failed to save PDF: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save PDF file: {str(e)}"
        )

    # Process PDF with TextbookProcessor
    processor = TextbookProcessorService(db)

    try:
        result = processor.process_pdf(
            file_path=file_path,
            uploaded_by=current_user.id,
            original_filename=original_filename
        )

        book_id = result['book_id']
        chapters_created = result['chapters_created']

        logger.info(
            f"PDF processed successfully: {chapters_created} chapters created "
            f"for book {book_id}"
        )

        # Get book record (used for both image extraction and title extraction)
        book = db.query(PDFBook).filter(
            PDFBook.id == uuid_module.UUID(book_id)
        ).first()

        # ========== IMAGE EXTRACTION INTEGRATION ==========
        # Create pdfs table entry to enable image extraction pipeline
        # (Fixes architecture gap where textbooks bypass image extraction)
        if book:
            try:
                # Create pdfs table record
                pdf_record = PDF(
                    id=uuid_module.uuid4(),
                    file_path=file_path,
                    filename=original_filename,
                    file_size_bytes=len(file_content),
                    indexing_status="pending",  # Valid status: will transition to extracting_images
                    text_extracted=True  # Text already extracted by textbook processor
                )
                db.add(pdf_record)
                db.flush()  # Get pdf_record.id without committing

                # Link book to pdf record (enables image lookup)
                book.pdf_id = pdf_record.id
                db.commit()

                logger.info(
                    f"Created pdfs record {pdf_record.id} for book {book_id}, "
                    f"queuing image extraction pipeline"
                )

                # Queue image extraction tasks
                # Chain: extract_images → analyze_images (Claude Vision)
                extract_images_task.delay(str(pdf_record.id))

                logger.info(
                    f"Queued image extraction pipeline for PDF {pdf_record.id} "
                    f"(book: {book.title})"
                )

            except Exception as e:
                logger.error(
                    f"Failed to queue image extraction for book {book_id}: {str(e)}",
                    exc_info=True
                )
                # Don't fail the entire upload if image extraction queueing fails
                # Book and chapters are already created, images can be extracted later

            # ========== END IMAGE EXTRACTION INTEGRATION ==========

        # Queue Celery tasks for embedding generation
        # Get all chapter IDs for this book
        chapters = db.query(PDFChapter).filter(
            PDFChapter.book_id == uuid_module.UUID(book_id)
        ).all()

        embedding_tasks_queued = 0
        for chapter in chapters:
            try:
                # Queue chapter embedding generation
                generate_chapter_embeddings.delay(str(chapter.id))
                embedding_tasks_queued += 1

                logger.debug(f"Queued embedding task for chapter {chapter.id}")

            except Exception as e:
                logger.error(f"Failed to queue embedding task for chapter {chapter.id}: {str(e)}")

        # Queue deduplication check for each chapter (runs after embeddings)
        for chapter in chapters:
            try:
                # Deduplication runs after embedding generation
                check_for_duplicates.delay(str(chapter.id))
                logger.debug(f"Queued deduplication task for chapter {chapter.id}")

            except Exception as e:
                logger.error(f"Failed to queue deduplication task for chapter {chapter.id}: {str(e)}")

        logger.info(
            f"Upload complete: {embedding_tasks_queued} embedding tasks queued "
            f"for book {book_id}"
        )

        # Auto-queue title extraction if book has UUID or generic title (Enhancement #2)
        # Note: book variable already fetched above for image extraction
        if book:
            title = book.title
            # Check if title is a UUID (8-4-4-4-12 pattern) or generic placeholder
            is_uuid_title = re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', title.lower())
            is_placeholder = title in [
                "Untitled Book - Please Edit",
                "Untitled Book",
                "Unknown",
                original_filename,  # Sometimes filename is used as title
            ]

            if is_uuid_title or is_placeholder:
                try:
                    extract_title_from_cover.delay(str(book_id), auto_apply_threshold=0.8)
                    logger.info(
                        f"Auto-queued title extraction for book {book_id} "
                        f"(current title: '{title}')"
                    )
                except Exception as e:
                    logger.error(f"Failed to queue title extraction for book {book_id}: {str(e)}")

        return UploadResponse(
            status="success",
            message=f"PDF uploaded and {chapters_created} chapters extracted. Background processing started.",
            book_id=book_id,
            chapters_created=chapters_created,
            pdf_type=result['pdf_type'],
            total_pages=result['total_pages'],
            embedding_tasks_queued=embedding_tasks_queued
        )

    except Exception as e:
        logger.error(f"PDF processing failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"PDF processing failed: {str(e)}"
        )


@router.post(
    "/batch-upload",
    response_model=BatchUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload multiple PDFs in batch",
    description="""
    Upload multiple PDF files in a single request for batch processing.

    Each PDF will be processed independently:
    - Successful uploads will be processed normally
    - Failed uploads will be reported but won't block others

    Maximum: 50 files per batch
    Maximum file size: 100MB per file
    """
)
async def batch_upload_textbooks(
    files: List[UploadFile] = File(..., description="List of PDF files to upload"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> BatchUploadResponse:
    """
    Upload multiple PDFs in batch

    Each file is processed independently.
    Returns summary of successes and failures.

    Requires authentication.
    """
    logger.info(f"Batch upload started by user {current_user.email}: {len(files)} files")

    if len(files) > 50:
        raise HTTPException(
            status_code=400,
            detail="Maximum 50 files per batch upload"
        )

    successful_uploads = 0
    failed_uploads = 0
    books_created = []
    total_chapters_created = 0
    total_embedding_tasks_queued = 0
    failures = []

    storage = StorageService()
    processor = TextbookProcessorService(db)

    for file in files:
        try:
            # Validate file
            if not file.filename.lower().endswith('.pdf'):
                raise ValueError("Only PDF files are supported")

            # Save file
            file_content = await file.read()
            storage_result = storage.save_pdf(io.BytesIO(file_content), file.filename)
            file_path = storage_result["file_path"]
            original_filename = storage_result["original_filename"]

            # Process PDF
            result = processor.process_pdf(
                file_path=file_path,
                uploaded_by=current_user.id,
                original_filename=original_filename
            )

            book_id = result['book_id']
            chapters_created = result['chapters_created']

            # Queue embedding tasks
            chapters = db.query(PDFChapter).filter(
                PDFChapter.book_id == uuid_module.UUID(book_id)
            ).all()

            for chapter in chapters:
                generate_chapter_embeddings.delay(str(chapter.id))
                check_for_duplicates.delay(str(chapter.id))

            successful_uploads += 1
            books_created.append(book_id)
            total_chapters_created += chapters_created
            total_embedding_tasks_queued += len(chapters)

            logger.info(f"Batch upload: {file.filename} processed successfully ({chapters_created} chapters)")

        except Exception as e:
            failed_uploads += 1
            failures.append({
                "filename": file.filename,
                "error": str(e)
            })
            logger.error(f"Batch upload: {file.filename} failed: {str(e)}")

    logger.info(
        f"Batch upload complete: {successful_uploads}/{len(files)} successful, "
        f"{total_chapters_created} total chapters, "
        f"{total_embedding_tasks_queued} embedding tasks queued"
    )

    return BatchUploadResponse(
        status="completed",
        message=f"Batch upload completed with {successful_uploads}/{len(files)} successful uploads",
        total_files=len(files),
        successful_uploads=successful_uploads,
        failed_uploads=failed_uploads,
        books_created=books_created,
        total_chapters_created=total_chapters_created,
        total_embedding_tasks_queued=total_embedding_tasks_queued,
        failures=failures if failures else None
    )


# ==================== Progress Monitoring Routes ====================

@router.get(
    "/upload-progress/{book_id}",
    response_model=UploadProgressResponse,
    summary="Get upload/processing progress for a book",
    description="""
    Get detailed progress information for a book upload.

    Returns:
    - Processing status
    - Chapter count
    - Embedding generation progress
    - Estimated completion time
    """
)
async def get_upload_progress(
    book_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> UploadProgressResponse:
    """
    Get upload and processing progress for a specific book

    Requires authentication.
    """
    try:
        book_uuid = uuid_module.UUID(book_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book ID format")

    # Get book
    book = db.query(PDFBook).filter(PDFBook.id == book_uuid).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Get chapter statistics
    total_chapters = db.query(PDFChapter).filter(
        PDFChapter.book_id == book_uuid
    ).count()

    chapters_with_embeddings = db.query(PDFChapter).filter(
        PDFChapter.book_id == book_uuid,
        PDFChapter.embedding.isnot(None)
    ).count()

    # Calculate progress
    if total_chapters > 0:
        progress_percent = (chapters_with_embeddings / total_chapters) * 100
    else:
        progress_percent = 0.0

    # Estimate completion time (rough estimate: 6 seconds per chapter)
    remaining_chapters = total_chapters - chapters_with_embeddings
    estimated_completion_minutes = max(1, (remaining_chapters * 6) // 60) if remaining_chapters > 0 else None

    return UploadProgressResponse(
        book_id=book_id,
        title=book.title,
        processing_status=book.processing_status,
        total_chapters=total_chapters,
        chapters_with_embeddings=chapters_with_embeddings,
        embedding_progress_percent=round(progress_percent, 2),
        estimated_completion_minutes=estimated_completion_minutes
    )


@router.get(
    "/library-stats",
    response_model=LibraryStatsResponse,
    summary="Get overall library statistics",
    description="""
    Get comprehensive statistics for the entire library.

    Returns:
    - Total books, chapters, and chunks
    - Embedding generation progress
    - Deduplication statistics
    - Storage usage
    """
)
async def get_library_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> LibraryStatsResponse:
    """
    Get comprehensive library statistics

    Requires authentication.
    """
    # Count totals
    total_books = db.query(PDFBook).count()
    total_chapters = db.query(PDFChapter).count()
    total_chunks = db.query(PDFChunk).count()

    # Embedding progress
    chapters_with_embeddings = db.query(PDFChapter).filter(
        PDFChapter.embedding.isnot(None)
    ).count()

    if total_chapters > 0:
        embedding_progress_percent = (chapters_with_embeddings / total_chapters) * 100
    else:
        embedding_progress_percent = 0.0

    # Deduplication stats
    unique_chapters = db.query(PDFChapter).filter(
        PDFChapter.is_duplicate == False
    ).count()

    duplicate_chapters = db.query(PDFChapter).filter(
        PDFChapter.is_duplicate == True
    ).count()

    # Storage usage
    total_storage_bytes = db.query(
        func.sum(PDFBook.file_size_bytes)
    ).scalar() or 0

    storage_gb = total_storage_bytes / (1024 * 1024 * 1024)

    logger.info(
        f"Library stats requested: {total_books} books, "
        f"{total_chapters} chapters, {embedding_progress_percent:.1f}% embedded"
    )

    return LibraryStatsResponse(
        total_books=total_books,
        total_chapters=total_chapters,
        total_chunks=total_chunks,
        chapters_with_embeddings=chapters_with_embeddings,
        embedding_progress_percent=round(embedding_progress_percent, 2),
        unique_chapters=unique_chapters,
        duplicate_chapters=duplicate_chapters,
        total_storage_bytes=int(total_storage_bytes),
        storage_gb=round(storage_gb, 2)
    )


# ==================== Book and Chapter Query Routes ====================

@router.get(
    "/books",
    response_model=List[BookResponse],
    summary="List all books",
    description="List all uploaded books with pagination"
)
async def list_books(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records"),
    processing_status: Optional[str] = Query(None, description="Filter by processing status"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[BookResponse]:
    """
    List books with pagination and filtering

    Requires authentication.
    """
    query = db.query(PDFBook)

    if processing_status:
        query = query.filter(PDFBook.processing_status == processing_status)

    books = query.order_by(PDFBook.uploaded_at.desc()).offset(skip).limit(limit).all()

    return [BookResponse(**book.to_dict()) for book in books]


@router.get(
    "/books/{book_id}",
    response_model=BookResponse,
    summary="Get book details",
    description="Get detailed information about a specific book"
)
async def get_book(
    book_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> BookResponse:
    """
    Get book by ID

    Requires authentication.
    """
    try:
        book_uuid = uuid_module.UUID(book_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book ID format")

    book = db.query(PDFBook).filter(PDFBook.id == book_uuid).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    return BookResponse(**book.to_dict())


@router.patch(
    "/books/{book_id}/title",
    response_model=BookResponse,
    summary="Update book title",
    description="""
    Update the title of a book with full audit trail.

    Features:
    - Preserves original title on first edit (audit trail)
    - Records user who edited and timestamp
    - Validates title (1-500 chars, not empty, not placeholder)
    - Returns updated book data

    Requires authentication.
    """
)
async def update_book_title(
    book_id: str,
    title_update: TitleUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> BookResponse:
    """
    Update book title with audit trail

    Security:
    - Requires authentication
    - Records user_id and timestamp
    - Preserves original title if first edit

    Validation:
    - Title length: 1-500 characters
    - No empty/whitespace-only titles
    - No generic placeholder titles
    """
    try:
        book_uuid = uuid_module.UUID(book_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book ID format")

    # Get book
    book = db.query(PDFBook).filter(PDFBook.id == book_uuid).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Preserve original title on first edit
    if book.original_title is None:
        book.original_title = book.title

    # Update title with audit trail
    book.title = title_update.title
    book.title_edited_at = datetime.utcnow()
    book.title_edited_by = current_user.id

    db.commit()
    db.refresh(book)

    logger.info(
        f"Book title updated: {book_id} | "
        f"Old: '{book.original_title}' | "
        f"New: '{book.title}' | "
        f"By: {current_user.email}"
    )

    return BookResponse(**book.to_dict())


@router.get(
    "/books/{book_id}/chapters",
    response_model=List[ChapterResponse],
    summary="Get all chapters from a book",
    description="Get all extracted chapters from a specific book"
)
async def get_book_chapters(
    book_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[ChapterResponse]:
    """
    Get all chapters from a book

    Requires authentication.
    """
    try:
        book_uuid = uuid_module.UUID(book_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book ID format")

    # Verify book exists
    book = db.query(PDFBook).filter(PDFBook.id == book_uuid).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Get chapters
    chapters = db.query(PDFChapter).filter(
        PDFChapter.book_id == book_uuid
    ).order_by(PDFChapter.chapter_number).all()

    return [ChapterResponse(**chapter.to_dict()) for chapter in chapters]


@router.get(
    "/chapters/{chapter_id}",
    response_model=ChapterResponse,
    summary="Get chapter details",
    description="Get detailed information about a specific chapter"
)
async def get_chapter(
    chapter_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> ChapterResponse:
    """
    Get chapter by ID

    Requires authentication.
    """
    try:
        chapter_uuid = uuid_module.UUID(chapter_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid chapter ID format")

    chapter = db.query(PDFChapter).filter(PDFChapter.id == chapter_uuid).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    return ChapterResponse(**chapter.to_dict())


@router.get(
    "/chapters/{chapter_id}/embedding",
    summary="Get chapter embedding vector",
    description="Get the full 1536-dimensional embedding vector for a chapter"
)
async def get_chapter_embedding(
    chapter_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get chapter embedding vector

    Returns the full 1536-dimensional vector as JSON array.
    Returns null if embedding hasn't been generated yet.

    Requires authentication.
    """
    try:
        chapter_uuid = uuid_module.UUID(chapter_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid chapter ID format")

    chapter = db.query(PDFChapter).filter(PDFChapter.id == chapter_uuid).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Convert pgvector to list
    embedding_vector = None
    if chapter.embedding is not None:
        embedding_vector = chapter.embedding.tolist() if hasattr(chapter.embedding, 'tolist') else list(chapter.embedding)

    return {
        "chapter_id": str(chapter.id),
        "chapter_title": chapter.chapter_title,
        "has_embedding": chapter.embedding is not None,
        "embedding_dimensions": len(embedding_vector) if embedding_vector else 0,
        "embedding": embedding_vector,
        "embedding_preview": embedding_vector[:20] if embedding_vector else None
    }


@router.get(
    "/chapters/{chapter_id}/similar",
    summary="Get similar chapters",
    description="Find chapters similar to this one using vector similarity"
)
async def get_similar_chapters(
    chapter_id: str,
    limit: int = Query(5, ge=1, le=20, description="Number of similar chapters to return"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get similar chapters using cosine similarity

    Requires authentication.
    """
    try:
        chapter_uuid = uuid_module.UUID(chapter_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid chapter ID format")

    chapter = db.query(PDFChapter).filter(PDFChapter.id == chapter_uuid).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    if chapter.embedding is None:
        raise HTTPException(status_code=400, detail="Chapter does not have an embedding yet")

    # Use vector search service to find similar chapters
    from backend.services.chapter_vector_search_service import ChapterVectorSearchService
    search_service = ChapterVectorSearchService(db)

    similar_chapters = search_service.find_similar_chapters(
        chapter_id=chapter_uuid,
        limit=limit,
        exclude_duplicates=False
    )

    return {
        "chapter_id": str(chapter.id),
        "chapter_title": chapter.chapter_title,
        "similar_chapters": [
            {
                "id": str(ch.id),
                "book_id": str(ch.book_id) if ch.book_id else None,
                "chapter_number": ch.chapter_number,
                "chapter_title": ch.chapter_title,
                "similarity_score": score,
                "is_duplicate": ch.is_duplicate
            }
            for ch, score in similar_chapters
        ]
    }


@router.delete(
    "/books/{book_id}",
    summary="Delete a book and all its chapters",
    description="Permanently delete a book and all associated chapters from the system"
)
async def delete_book(
    book_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete book and all its chapters

    This will:
    1. Delete all chapters belonging to this book
    2. Delete all chunks belonging to those chapters
    3. Delete the book record
    4. Delete the PDF file from storage (optional)

    Requires authentication.
    """
    try:
        book_uuid = uuid_module.UUID(book_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book ID format")

    book = db.query(PDFBook).filter(PDFBook.id == book_uuid).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Count chapters before deletion
    chapter_count = db.query(PDFChapter).filter(PDFChapter.book_id == book_uuid).count()

    # Delete all chunks for chapters in this book
    db.query(PDFChunk).filter(
        PDFChunk.chapter_id.in_(
            db.query(PDFChapter.id).filter(PDFChapter.book_id == book_uuid)
        )
    ).delete(synchronize_session=False)

    # Delete all chapters
    db.query(PDFChapter).filter(PDFChapter.book_id == book_uuid).delete(synchronize_session=False)

    # Delete book
    file_path = book.file_path
    db.delete(book)
    db.commit()

    # Optionally delete file from storage
    try:
        from backend.services.storage_service import StorageService
        storage = StorageService()
        storage.delete_pdf(file_path)
        logger.info(f"Deleted PDF file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to delete PDF file {file_path}: {str(e)}")

    logger.info(f"Deleted book {book_id} and {chapter_count} chapters")

    return {
        "status": "success",
        "message": f"Book deleted successfully",
        "book_id": book_id,
        "chapters_deleted": chapter_count
    }


@router.delete(
    "/chapters/{chapter_id}",
    summary="Delete a chapter",
    description="Permanently delete a chapter from the system"
)
async def delete_chapter(
    chapter_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a single chapter

    This will:
    1. Delete all chunks belonging to this chapter
    2. Delete the chapter record

    Requires authentication.
    """
    try:
        chapter_uuid = uuid_module.UUID(chapter_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid chapter ID format")

    chapter = db.query(PDFChapter).filter(PDFChapter.id == chapter_uuid).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Delete all chunks
    chunk_count = db.query(PDFChunk).filter(PDFChunk.chapter_id == chapter_uuid).delete(synchronize_session=False)

    # Delete chapter
    db.delete(chapter)
    db.commit()

    logger.info(f"Deleted chapter {chapter_id} and {chunk_count} chunks")

    return {
        "status": "success",
        "message": f"Chapter deleted successfully",
        "chapter_id": chapter_id,
        "chunks_deleted": chunk_count
    }


# ==================== AI Title Extraction (Enhancement #2) ====================


@router.post(
    "/books/{book_id}/extract-title",
    summary="Extract book title from cover page (async)",
    description="Trigger async AI-powered title extraction from PDF cover page using GPT-4o Vision"
)
async def trigger_title_extraction(
    book_id: str,
    auto_apply_threshold: float = Query(
        0.8,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for auto-applying title (0.0-1.0)"
    ),
    page_num: int = Query(
        0,
        ge=0,
        description="Page number to extract from (0 = cover page)"
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Trigger async title extraction for a specific book

    This endpoint:
    1. Validates the book exists
    2. Queues a background Celery task for title extraction
    3. Returns immediately with task_id for tracking

    The background task will:
    - Render the PDF cover page to high-quality image
    - Call GPT-4o Vision API to extract title
    - Auto-apply title if confidence >= threshold
    - Store suggestion for manual review if 0.5 <= confidence < threshold
    - Log failure if confidence < 0.5

    Args:
        book_id: UUID of book to process
        auto_apply_threshold: Confidence threshold for auto-apply (default 0.8)
        page_num: Page number to extract from (default 0 = cover)
        current_user: Authenticated user
        db: Database session

    Returns:
        {
            "status": "queued",
            "task_id": "celery-task-uuid",
            "book_id": "book-uuid",
            "message": "Title extraction task queued successfully"
        }

    Raises:
        400: Invalid book ID format
        404: Book not found
        401: Not authenticated

    Example:
        POST /textbooks/books/{book_id}/extract-title?auto_apply_threshold=0.85
    """
    # Validate book ID format
    try:
        book_uuid = uuid_module.UUID(book_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book ID format")

    # Verify book exists
    book = db.query(PDFBook).filter(PDFBook.id == book_uuid).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Queue title extraction task
    logger.info(
        f"Queueing title extraction for book {book_id} | "
        f"Threshold: {auto_apply_threshold} | Page: {page_num} | "
        f"User: {current_user.email}"
    )

    task = extract_title_from_cover.delay(
        str(book_id),
        auto_apply_threshold=auto_apply_threshold,
        page_num=page_num
    )

    return {
        "status": "queued",
        "task_id": task.id,
        "book_id": str(book_id),
        "message": "Title extraction task queued successfully",
        "estimated_time_seconds": 10,  # Typical completion time
        "auto_apply_threshold": auto_apply_threshold
    }


class BatchTitleExtractionRequest(BaseModel):
    """Request model for batch title extraction"""
    book_ids: List[str] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="List of book UUIDs to process (max 100)"
    )
    auto_apply_threshold: float = Field(
        0.8,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for auto-applying titles"
    )


@router.post(
    "/batch-extract-titles",
    summary="Batch extract titles from multiple books (async)",
    description="Trigger async batch title extraction for multiple books"
)
async def trigger_batch_title_extraction(
    request: BatchTitleExtractionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Trigger async batch title extraction for multiple books

    This endpoint:
    1. Validates all book IDs and checks they exist
    2. Queues a single background Celery task for batch processing
    3. Returns immediately with task_id for tracking

    The background task will:
    - Process each book sequentially
    - Extract titles from cover pages
    - Auto-apply or suggest titles based on confidence
    - Return comprehensive statistics

    Args:
        request: BatchTitleExtractionRequest with book_ids and threshold
        current_user: Authenticated user
        db: Database session

    Returns:
        {
            "status": "queued",
            "task_id": "celery-task-uuid",
            "total_books": 15,
            "message": "Batch title extraction task queued successfully"
        }

    Raises:
        400: Invalid book ID format
        404: One or more books not found
        422: Too many books (max 100)

    Example:
        POST /textbooks/batch-extract-titles
        {
            "book_ids": ["uuid1", "uuid2", "uuid3"],
            "auto_apply_threshold": 0.85
        }
    """
    # Validate all book IDs
    book_uuids = []
    for book_id in request.book_ids:
        try:
            book_uuids.append(uuid_module.UUID(book_id))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid book ID format: {book_id}"
            )

    # Verify all books exist
    existing_books = db.query(PDFBook).filter(
        PDFBook.id.in_(book_uuids)
    ).all()

    if len(existing_books) != len(book_uuids):
        found_ids = {str(book.id) for book in existing_books}
        missing_ids = [book_id for book_id in request.book_ids if book_id not in found_ids]
        raise HTTPException(
            status_code=404,
            detail=f"Books not found: {', '.join(missing_ids[:5])}"
        )

    # Queue batch extraction task
    logger.info(
        f"Queueing batch title extraction for {len(request.book_ids)} books | "
        f"Threshold: {request.auto_apply_threshold} | "
        f"User: {current_user.email}"
    )

    task = batch_extract_titles.delay(
        request.book_ids,
        auto_apply_threshold=request.auto_apply_threshold
    )

    return {
        "status": "queued",
        "task_id": task.id,
        "total_books": len(request.book_ids),
        "message": "Batch title extraction task queued successfully",
        "estimated_time_seconds": len(request.book_ids) * 10,  # ~10 sec per book
        "auto_apply_threshold": request.auto_apply_threshold
    }


@router.get(
    "/books/{book_id}/title-suggestion",
    summary="Get AI title suggestion (if available)",
    description="Get the AI-generated title suggestion stored in book metadata"
)
async def get_title_suggestion(
    book_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get AI-generated title suggestion for a book

    Returns the title suggestion stored in book's ai_metadata field
    (if title extraction task ran with medium confidence 0.5-0.8)

    Args:
        book_id: UUID of book
        current_user: Authenticated user
        db: Database session

    Returns:
        {
            "book_id": "uuid",
            "current_title": "Current Title",
            "has_suggestion": true,
            "suggestion": {
                "suggested_title": "AI Extracted Title",
                "confidence": 0.75,
                "reasoning": "Title visible but slightly obscured",
                "alternatives": ["Alt Title 1"],
                "language": "English",
                "subtitle": "Principles and Practice",
                "suggestion_date": "2025-11-02T00:35:00",
                "model": "gpt-4o"
            }
        }

    Raises:
        400: Invalid book ID format
        404: Book not found
        401: Not authenticated

    Example:
        GET /textbooks/books/{book_id}/title-suggestion
    """
    # Validate book ID
    try:
        book_uuid = uuid_module.UUID(book_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid book ID format")

    # Get book
    book = db.query(PDFBook).filter(PDFBook.id == book_uuid).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Check for title suggestion in ai_metadata
    has_suggestion = False
    suggestion = None

    if hasattr(book, 'ai_metadata') and book.ai_metadata:
        if 'title_suggestion' in book.ai_metadata:
            has_suggestion = True
            suggestion = book.ai_metadata['title_suggestion']

    return {
        "book_id": str(book_id),
        "current_title": book.title,
        "has_suggestion": has_suggestion,
        "suggestion": suggestion
    }
