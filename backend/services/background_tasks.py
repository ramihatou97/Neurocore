"""
Background Tasks for PDF Processing
Celery tasks for asynchronous PDF indexing, image analysis, and embedding generation
"""

from celery import Task, chain, group
from typing import Dict, Any, List
from pathlib import Path
import time

from backend.services.celery_app import celery_app
from backend.database.connection import db
from backend.database.models import PDF, Image
from backend.services.pdf_service import PDFService
from backend.services.image_analysis_service import ImageAnalysisService
from backend.services.embedding_service import EmbeddingService
from backend.services.task_service import TaskService
from backend.utils import get_logger
from backend.utils.websocket_emitter import emitter
from backend.utils.events import EventType

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
    name="backend.services.background_tasks.process_pdf_async",
    max_retries=3,
    default_retry_delay=300
)
def process_pdf_async(self, pdf_id: str) -> Dict[str, Any]:
    """
    Main orchestration task for PDF processing pipeline

    Workflow:
    1. Extract text
    2. Extract images
    3. Analyze images (Claude Vision)
    4. Generate embeddings
    5. Extract citations

    Args:
        pdf_id: PDF document ID

    Returns:
        Processing summary
    """
    logger.info(f"Starting async PDF processing for: {pdf_id}")

    try:
        # Update PDF status
        pdf = self.db_session.query(PDF).filter(PDF.id == pdf_id).first()
        if not pdf:
            raise ValueError(f"PDF not found: {pdf_id}")

        pdf.indexing_status = "processing"
        pdf.processing_started_at = time.time()
        self.db_session.commit()

        # Execute pipeline as chain
        # Use .si() (immutable signature) to prevent Celery from passing previous results as arguments
        workflow = chain(
            extract_text_task.si(pdf_id),
            extract_images_task.si(pdf_id),
            analyze_images_task.si(pdf_id),
            generate_embeddings_task.si(pdf_id),
            extract_citations_task.si(pdf_id),
            finalize_pdf_processing.si(pdf_id)
        )

        result = workflow.apply_async()

        logger.info(f"PDF processing pipeline started for {pdf_id}: task_id={result.id}")

        return {
            "pdf_id": pdf_id,
            "status": "pipeline_started",
            "task_id": result.id
        }

    except Exception as e:
        logger.error(f"Failed to start PDF processing pipeline: {str(e)}", exc_info=True)

        # Update PDF status to failed
        try:
            pdf = self.db_session.query(PDF).filter(PDF.id == pdf_id).first()
            if pdf:
                pdf.indexing_status = "failed"
                self.db_session.commit()
        except Exception as db_error:
            logger.error(f"Failed to update PDF status: {str(db_error)}")

        # Retry with exponential backoff
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="backend.services.background_tasks.extract_text_task"
)
def extract_text_task(self, pdf_id: str) -> Dict[str, Any]:
    """
    Extract text from PDF

    Args:
        pdf_id: PDF document ID

    Returns:
        Extraction summary
    """
    logger.info(f"Extracting text from PDF: {pdf_id}")

    try:
        pdf_service = PDFService(self.db_session)

        # Extract text using PDFService high-level method
        result = pdf_service.extract_text(pdf_id)

        logger.info(f"Text extraction complete for {pdf_id}: {result.get('total_pages', 0)} pages, {result.get('total_words', 0)} words")

        # Emit WebSocket event
        import asyncio
        asyncio.run(emitter.emit_pdf_processing_event(
            pdf_id,
            EventType.PDF_TEXT_EXTRACTED,
            "text_extraction",
            f"Extracted text from {result.get('total_pages', 0)} pages",
            progress=20
        ))

        return {
            "pdf_id": pdf_id,
            "page_count": result.get("total_pages", 0),
            "text_length": result.get("total_text_length", 0),
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Text extraction failed for {pdf_id}: {str(e)}", exc_info=True)
        raise


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="backend.services.background_tasks.extract_images_task"
)
def extract_images_task(self, pdf_id: str) -> Dict[str, Any]:
    """
    Extract images from PDF

    Args:
        pdf_id: PDF document ID

    Returns:
        Extraction summary
    """
    logger.info(f"Extracting images from PDF: {pdf_id}")

    try:
        pdf_service = PDFService(self.db_session)

        # Extract images using PDFService high-level method
        result = pdf_service.extract_images(pdf_id)

        logger.info(f"Image extraction complete for {pdf_id}: {result.get('total_images', 0)} images")

        # Emit WebSocket event
        import asyncio
        asyncio.run(emitter.emit_pdf_processing_event(
            pdf_id,
            EventType.PDF_IMAGES_EXTRACTED,
            "image_extraction",
            f"Extracted {result.get('total_images', 0)} images",
            progress=40
        ))

        return {
            "pdf_id": pdf_id,
            "image_count": result.get('total_images', 0),
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Image extraction failed for {pdf_id}: {str(e)}", exc_info=True)
        raise


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="backend.services.background_tasks.analyze_images_task"
)
def analyze_images_task(self, pdf_id: str) -> Dict[str, Any]:
    """
    Analyze images using Claude Vision (95% complete analysis)

    Args:
        pdf_id: PDF document ID

    Returns:
        Analysis summary
    """
    logger.info(f"Analyzing images for PDF: {pdf_id}")

    try:
        # Get all images for this PDF
        images = self.db_session.query(Image).filter(Image.pdf_id == pdf_id).all()

        if not images:
            logger.info(f"No images found for PDF {pdf_id}")
            return {
                "pdf_id": pdf_id,
                "image_count": 0,
                "status": "no_images"
            }

        # Get PDF for context
        pdf = self.db_session.query(PDF).filter(PDF.id == pdf_id).first()

        # Analyze images
        image_service = ImageAnalysisService()

        # Build context
        context = {
            "pdf_title": pdf.title if pdf else "Unknown",
            "pdf_id": pdf_id
        }

        # Analyze images in batch (async operation)
        import asyncio
        image_paths = [img.file_path for img in images]
        analyses = asyncio.run(
            image_service.analyze_images_batch(image_paths, context)
        )

        # Update image records with analysis
        for image, analysis in zip(images, analyses):
            if analysis.get("analysis"):
                image.ai_description = self._build_description(analysis["analysis"])
                image.analysis_metadata = analysis["analysis"]
                image.analysis_confidence = analysis.get("confidence_score", 0.0)

        self.db_session.commit()

        logger.info(f"Image analysis complete for {pdf_id}: {len(analyses)} images")

        # Emit WebSocket event
        analyzed_count = sum(1 for a in analyses if a.get("analysis"))
        asyncio.run(emitter.emit_pdf_processing_event(
            pdf_id,
            EventType.PDF_IMAGES_ANALYZED,
            "image_analysis",
            f"Analyzed {analyzed_count} images with Claude Vision",
            progress=60
        ))

        return {
            "pdf_id": pdf_id,
            "image_count": len(analyses),
            "analyzed_count": analyzed_count,
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Image analysis failed for {pdf_id}: {str(e)}", exc_info=True)
        raise

    def _build_description(self, analysis: Dict[str, Any]) -> str:
        """Build human-readable description from analysis"""
        parts = []

        image_type = analysis.get("image_type", "Unknown")
        modality = analysis.get("modality", "")
        parts.append(f"{image_type}")

        if modality:
            parts.append(f"({modality})")

        structures = analysis.get("anatomical_structures", [])
        if structures:
            parts.append(f"showing {', '.join(structures[:3])}")

        pathology = analysis.get("pathology")
        if pathology:
            parts.append(f"with {pathology}")

        return " ".join(parts)


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="backend.services.background_tasks.generate_embeddings_task"
)
def generate_embeddings_task(self, pdf_id: str) -> Dict[str, Any]:
    """
    Generate vector embeddings for PDF and its images

    Args:
        pdf_id: PDF document ID

    Returns:
        Embedding generation summary
    """
    logger.info(f"Generating embeddings for PDF: {pdf_id}")

    try:
        embedding_service = EmbeddingService(self.db_session)

        # Generate PDF embeddings
        import asyncio
        pdf_result = asyncio.run(
            embedding_service.generate_pdf_embeddings(pdf_id)
        )

        # Generate image embeddings
        images = self.db_session.query(Image).filter(
            Image.pdf_id == pdf_id,
            Image.ai_description.isnot(None)
        ).all()

        image_count = 0
        for image in images:
            try:
                asyncio.run(
                    embedding_service.generate_image_embeddings(
                        str(image.id),
                        image.ai_description
                    )
                )
                image_count += 1
            except Exception as img_error:
                logger.error(f"Failed to generate embedding for image {image.id}: {str(img_error)}")

        logger.info(f"Embedding generation complete for {pdf_id}: {image_count} images")

        # Update PDF record
        pdf = self.db_session.query(PDF).filter(PDF.id == pdf_id).first()
        if pdf:
            pdf.embeddings_generated = True
            self.db_session.commit()

        # Emit WebSocket event
        asyncio.run(emitter.emit_pdf_processing_event(
            pdf_id,
            EventType.PDF_EMBEDDINGS_GENERATED,
            "embedding_generation",
            f"Generated embeddings for PDF and {image_count} images",
            progress=80
        ))

        return {
            "pdf_id": pdf_id,
            "pdf_embedding": "completed",
            "image_embeddings": image_count,
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Embedding generation failed for {pdf_id}: {str(e)}", exc_info=True)
        raise


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="backend.services.background_tasks.extract_citations_task"
)
def extract_citations_task(self, pdf_id: str) -> Dict[str, Any]:
    """
    Extract citations from PDF text

    Args:
        pdf_id: PDF document ID

    Returns:
        Citation extraction summary
    """
    logger.info(f"Extracting citations from PDF: {pdf_id}")

    try:
        pdf_service = PDFService(self.db_session)

        # Get PDF
        pdf = self.db_session.query(PDF).filter(PDF.id == pdf_id).first()
        if not pdf:
            raise ValueError(f"PDF not found: {pdf_id}")

        if not pdf.extracted_text:
            logger.warning(f"No extracted text for PDF {pdf_id}")
            return {
                "pdf_id": pdf_id,
                "citation_count": 0,
                "status": "no_text"
            }

        # Extract citations (synchronous method from PDFService)
        citations = pdf_service._extract_citations_from_text(pdf.extracted_text)

        # Update PDF
        pdf.citations = citations
        self.db_session.commit()

        logger.info(f"Citation extraction complete for {pdf_id}: {len(citations)} citations")

        # Emit WebSocket event
        import asyncio
        asyncio.run(emitter.emit_pdf_processing_event(
            pdf_id,
            EventType.PDF_PROCESSING_COMPLETED,  # Using generic completed event
            "citation_extraction",
            f"Extracted {len(citations)} citations",
            progress=90
        ))

        return {
            "pdf_id": pdf_id,
            "citation_count": len(citations),
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Citation extraction failed for {pdf_id}: {str(e)}", exc_info=True)
        raise


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="backend.services.background_tasks.finalize_pdf_processing"
)
def finalize_pdf_processing(self, pdf_id: str) -> Dict[str, Any]:
    """
    Finalize PDF processing after all stages complete

    Args:
        pdf_id: PDF document ID

    Returns:
        Final processing summary
    """
    logger.info(f"Finalizing PDF processing for: {pdf_id}")

    try:
        # Get PDF
        pdf = self.db_session.query(PDF).filter(PDF.id == pdf_id).first()
        if not pdf:
            raise ValueError(f"PDF not found: {pdf_id}")

        # Update status
        pdf.indexing_status = "completed"
        pdf.processing_completed_at = time.time()

        # Calculate processing time
        if pdf.processing_started_at:
            processing_time = float(pdf.processing_completed_at) - float(pdf.processing_started_at)
            logger.info(f"PDF {pdf_id} processed in {processing_time:.2f} seconds")

        self.db_session.commit()

        # Build summary
        summary = {
            "pdf_id": pdf_id,
            "status": "completed",
            "stages": {
                "text_extraction": "completed",
                "image_extraction": "completed",
                "image_analysis": "completed",
                "embeddings": "completed",
                "citations": "completed"
            }
        }

        logger.info(f"PDF processing finalized for {pdf_id}")

        # Emit final WebSocket event
        import asyncio
        asyncio.run(emitter.emit_pdf_processing_event(
            pdf_id,
            EventType.PDF_PROCESSING_COMPLETED,
            "finalization",
            "PDF processing completed successfully",
            progress=100
        ))

        return summary

    except Exception as e:
        logger.error(f"Failed to finalize PDF processing: {str(e)}", exc_info=True)

        # Update PDF status to failed
        try:
            pdf = self.db_session.query(PDF).filter(PDF.id == pdf_id).first()
            if pdf:
                pdf.indexing_status = "failed"
                self.db_session.commit()
        except Exception as db_error:
            logger.error(f"Failed to update PDF status: {str(db_error)}")

        raise


# Helper function to start PDF processing
def start_pdf_processing(pdf_id: str) -> Dict[str, Any]:
    """
    Start asynchronous PDF processing pipeline

    Args:
        pdf_id: PDF document ID

    Returns:
        Task information
    """
    task = process_pdf_async.apply_async(args=[pdf_id])

    return {
        "pdf_id": pdf_id,
        "task_id": task.id,
        "status": "queued"
    }
