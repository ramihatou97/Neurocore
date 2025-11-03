"""
PDF API routes for upload, extraction, and management
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db, User
from backend.services.pdf_service import PDFService
from backend.utils import get_logger, get_current_active_user
from backend.database.models import PDF, Image

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/pdfs", tags=["pdfs"])


# ==================== Response Models ====================

class PDFResponse(BaseModel):
    """Response model for PDF information"""
    id: str
    filename: str
    file_size_bytes: int
    total_pages: int
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    publication_year: Optional[int] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    indexing_status: str
    text_extracted: bool
    images_extracted: bool
    embeddings_generated: bool
    total_images: Optional[int] = None
    total_words: Optional[int] = None
    total_text_length: Optional[int] = None
    created_at: str
    last_indexed_at: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "filename": "neurosurgery_paper.pdf",
                "file_size_bytes": 2048000,
                "total_pages": 15,
                "title": "Advanced Neurosurgical Techniques",
                "authors": ["Dr. Smith", "Dr. Johnson"],
                "publication_year": 2023,
                "journal": "Journal of Neurosurgery",
                "doi": "10.1234/jns.2023.001",
                "pmid": "12345678",
                "indexing_status": "completed",
                "text_extracted": True,
                "images_extracted": True,
                "embeddings_generated": False,
                "total_images": 8,
                "total_words": 5000,
                "total_text_length": 30000,
                "created_at": "2025-10-27T12:00:00",
                "last_indexed_at": "2025-10-27T12:05:00"
            }
        }


class ImageResponse(BaseModel):
    """Response model for image information"""
    id: str
    pdf_id: str
    page_number: int
    image_index_on_page: int
    file_path: str
    thumbnail_path: Optional[str]
    width: int
    height: int
    format: str
    file_size_bytes: int
    ai_description: Optional[str]
    image_type: Optional[str]
    quality_score: Optional[float]

    class Config:
        json_schema_extra = {
            "example": {
                "id": "img-123e4567-e89b-12d3-a456-426614174000",
                "pdf_id": "123e4567-e89b-12d3-a456-426614174000",
                "page_number": 5,
                "image_index_on_page": 0,
                "file_path": "/storage/images/2025/10/27/img123.png",
                "thumbnail_path": "/storage/thumbnails/2025/10/27/img123_thumb.jpg",
                "width": 1920,
                "height": 1080,
                "format": "PNG",
                "file_size_bytes": 256000,
                "ai_description": "Anatomical diagram of cerebral cortex",
                "image_type": "anatomical_diagram",
                "quality_score": 0.92
            }
        }


class ExtractionResponse(BaseModel):
    """Response model for extraction operations"""
    pdf_id: str
    status: str
    message: str
    statistics: dict

    class Config:
        json_schema_extra = {
            "example": {
                "pdf_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "completed",
                "message": "Text extraction completed successfully",
                "statistics": {
                    "total_pages": 15,
                    "total_words": 5000,
                    "total_text_length": 30000
                }
            }
        }


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    details: Optional[dict] = None


# ==================== Health Check (must be before dynamic routes) ====================

@router.get(
    "/health",
    response_model=MessageResponse,
    summary="PDF service health check",
    description="Health check endpoint - no authentication required"
)
async def pdf_health_check() -> MessageResponse:
    """
    Health check endpoint for PDF service

    No authentication required.
    """
    return MessageResponse(message="PDF service is healthy")


# ==================== Statistics ====================

@router.get(
    "/stats",
    response_model=dict,
    summary="Get PDF statistics",
    description="Get aggregate statistics about PDFs in the system"
)
async def get_pdf_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get PDF statistics

    Returns:
    - total: Total number of PDFs
    - processing: PDFs currently being processed
    - completed: PDFs successfully indexed
    - failed: PDFs that failed processing
    """
    pdf_service = PDFService(db)

    # Get counts by status
    total = db.query(PDF).count()
    processing = db.query(PDF).filter(PDF.indexing_status == 'processing').count()
    completed = db.query(PDF).filter(PDF.indexing_status == 'completed').count()
    failed = db.query(PDF).filter(PDF.indexing_status == 'failed').count()
    pending = db.query(PDF).filter(PDF.indexing_status == 'pending').count()

    return {
        "total": total,
        "processing": processing,
        "completed": completed,
        "failed": failed,
        "pending": pending
    }


# ==================== PDF Routes ====================

@router.post(
    "/upload",
    response_model=PDFResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF file",
    description="""
    Upload a PDF file for processing.

    The PDF will be:
    1. Validated (size, format)
    2. Stored in the file system
    3. Metadata extracted (title, authors, DOI, etc.)
    4. Optionally text/images can be extracted immediately

    Maximum file size: 100MB
    """
)
async def upload_pdf(
    file: UploadFile = File(..., description="PDF file to upload"),
    extract_immediately: bool = Query(False, description="Extract text and images immediately"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> PDFResponse:
    """
    Upload PDF file and create database record

    Requires authentication.
    """
    pdf_service = PDFService(db)

    try:
        pdf = await pdf_service.upload_pdf(file, extract_immediately)

        logger.info(f"PDF uploaded by user {current_user.email}: {pdf.filename}")

        return PDFResponse(**pdf.to_dict())

    except Exception as e:
        logger.error(f"PDF upload failed: {str(e)}", exc_info=True)
        raise


@router.get(
    "",
    response_model=List[PDFResponse],
    summary="List all PDFs",
    description="""
    List all uploaded PDFs with pagination and filtering.

    Supports filtering by indexing status.
    """
)
async def list_pdfs(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records"),
    indexing_status: Optional[str] = Query(None, description="Filter by indexing status"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[PDFResponse]:
    """
    List PDFs with pagination

    Requires authentication.
    """
    pdf_service = PDFService(db)

    pdfs = pdf_service.list_pdfs(skip, limit, indexing_status)

    return [PDFResponse(**pdf.to_dict()) for pdf in pdfs]


@router.get(
    "/{pdf_id}",
    response_model=PDFResponse,
    summary="Get PDF details",
    description="Get detailed information about a specific PDF"
)
async def get_pdf(
    pdf_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> PDFResponse:
    """
    Get PDF by ID

    Requires authentication.
    """
    pdf_service = PDFService(db)

    pdf = pdf_service.get_pdf(pdf_id)

    return PDFResponse(**pdf.to_dict())


@router.delete(
    "/{pdf_id}",
    response_model=MessageResponse,
    summary="Delete a PDF",
    description="""
    Delete a PDF and all associated data:
    - PDF file from storage
    - All extracted images
    - All database records
    """
)
async def delete_pdf(
    pdf_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> MessageResponse:
    """
    Delete PDF and all associated data

    Requires authentication.
    """
    pdf_service = PDFService(db)

    result = pdf_service.delete_pdf(pdf_id)

    logger.info(f"PDF deleted by user {current_user.email}: {pdf_id}")

    return MessageResponse(
        message=f"PDF deleted successfully",
        details=result
    )


# ==================== Extraction Routes ====================

@router.post(
    "/{pdf_id}/extract-text",
    response_model=ExtractionResponse,
    summary="Extract text from PDF",
    description="""
    Extract text from all pages of a PDF with layout preservation.

    This will:
    1. Extract text page by page
    2. Calculate word count and text length
    3. Update PDF status
    """
)
async def extract_text(
    pdf_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> ExtractionResponse:
    """
    Extract text from PDF

    Requires authentication.
    """
    pdf_service = PDFService(db)

    result = pdf_service.extract_text(pdf_id)

    logger.info(f"Text extraction requested by user {current_user.email}: {pdf_id}")

    return ExtractionResponse(
        pdf_id=result["pdf_id"],
        status=result["status"],
        message="Text extraction completed successfully",
        statistics={
            "total_pages": result["total_pages"],
            "total_words": result["total_words"],
            "total_text_length": result["total_text_length"]
        }
    )


@router.post(
    "/{pdf_id}/extract-images",
    response_model=ExtractionResponse,
    summary="Extract images from PDF",
    description="""
    Extract all images from a PDF.

    For each image:
    1. Extract image data
    2. Save full-size image
    3. Generate thumbnail
    4. Store metadata (page, position, size)
    """
)
async def extract_images(
    pdf_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> ExtractionResponse:
    """
    Extract images from PDF

    Requires authentication.
    """
    pdf_service = PDFService(db)

    result = pdf_service.extract_images(pdf_id)

    logger.info(f"Image extraction requested by user {current_user.email}: {pdf_id}")

    return ExtractionResponse(
        pdf_id=result["pdf_id"],
        status=result["status"],
        message="Image extraction completed successfully",
        statistics={
            "total_images": result["total_images"],
            "successful_extractions": result["successful_extractions"]
        }
    )


@router.get(
    "/{pdf_id}/images",
    response_model=List[ImageResponse],
    summary="Get all images from PDF",
    description="Get all extracted images from a specific PDF, ordered by page number"
)
async def get_pdf_images(
    pdf_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[ImageResponse]:
    """
    Get all images from a PDF

    Requires authentication.
    """
    pdf_service = PDFService(db)

    images = pdf_service.get_pdf_images(pdf_id)

    return [ImageResponse(**img.to_dict()) for img in images]


@router.post(
    "/{pdf_id}/process",
    summary="Start background PDF processing",
    description="""
    Start asynchronous processing pipeline for a PDF:
    1. Extract text
    2. Extract images
    3. Analyze images with Claude Vision
    4. Generate embeddings
    5. Extract citations

    Returns task ID for status tracking.
    """
)
async def start_pdf_processing(
    pdf_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Start background processing for a PDF

    Returns task ID for tracking progress via /api/v1/tasks/{task_id}
    """
    from backend.services.background_tasks import start_pdf_processing
    from backend.services.task_service import TaskService

    logger.info(f"Starting background processing for PDF: {pdf_id}")

    # Check PDF exists
    pdf_service = PDFService(db)
    pdf = pdf_service.get_pdf(pdf_id)

    # Start background task
    task_info = start_pdf_processing(pdf_id)

    # Create task tracking record
    task_service = TaskService(db)
    task = task_service.create_task(
        task_id=task_info["task_id"],
        task_type="pdf_processing",
        user=current_user,
        entity_id=pdf_id,
        entity_type="pdf",
        total_steps=5  # text, images, analysis, embeddings, citations
    )

    return {
        "message": "PDF processing started",
        "pdf_id": pdf_id,
        "task_id": task_info["task_id"],
        "status": "queued",
        "track_progress_at": f"/api/v1/tasks/{task_info['task_id']}"
    }
