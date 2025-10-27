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

        pdf.extraction_status = "processing"
        pdf.processing_started_at = time.time()
        self.db_session.commit()

        # Execute pipeline as chain
        workflow = chain(
            extract_text_task.s(pdf_id),
            extract_images_task.s(pdf_id),
            analyze_images_task.s(pdf_id),
            generate_embeddings_task.s(pdf_id),
            extract_citations_task.s(pdf_id)
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
                pdf.extraction_status = "failed"
                pdf.extraction_error = str(e)
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

        # Get PDF
        pdf = self.db_session.query(PDF).filter(PDF.id == pdf_id).first()
        if not pdf:
            raise ValueError(f"PDF not found: {pdf_id}")

        # Extract text (synchronous method from PDFService)
        result = pdf_service._extract_text_from_pdf(pdf.file_path)

        # Update PDF
        pdf.extracted_text = result["text"]
        pdf.page_count = result["page_count"]
        self.db_session.commit()

        logger.info(f"Text extraction complete for {pdf_id}: {result['page_count']} pages")

        return {
            "pdf_id": pdf_id,
            "page_count": result["page_count"],
            "text_length": len(result["text"]),
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

        # Get PDF
        pdf = self.db_session.query(PDF).filter(PDF.id == pdf_id).first()
        if not pdf:
            raise ValueError(f"PDF not found: {pdf_id}")

        # Extract images (synchronous method from PDFService)
        images = pdf_service._extract_images_from_pdf(pdf.file_path, str(pdf.id))

        # Store images in database
        for img_data in images:
            image = Image(
                pdf_id=pdf.id,
                page_number=img_data["page"],
                file_path=img_data["path"],
                thumbnail_path=img_data["thumbnail"],
                width=img_data["width"],
                height=img_data["height"]
            )
            self.db_session.add(image)

        self.db_session.commit()

        logger.info(f"Image extraction complete for {pdf_id}: {len(images)} images")

        return {
            "pdf_id": pdf_id,
            "image_count": len(images),
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
                image.description = self._build_description(analysis["analysis"])
                image.analysis_metadata = analysis["analysis"]
                image.analysis_confidence = analysis.get("confidence_score", 0.0)

        self.db_session.commit()

        logger.info(f"Image analysis complete for {pdf_id}: {len(analyses)} images")

        return {
            "pdf_id": pdf_id,
            "image_count": len(analyses),
            "analyzed_count": sum(1 for a in analyses if a.get("analysis")),
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
            Image.description.isnot(None)
        ).all()

        image_count = 0
        for image in images:
            try:
                asyncio.run(
                    embedding_service.generate_image_embeddings(
                        str(image.id),
                        image.description
                    )
                )
                image_count += 1
            except Exception as img_error:
                logger.error(f"Failed to generate embedding for image {image.id}: {str(img_error)}")

        logger.info(f"Embedding generation complete for {pdf_id}: {image_count} images")

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
def finalize_pdf_processing(self, results: List[Dict[str, Any]], pdf_id: str) -> Dict[str, Any]:
    """
    Finalize PDF processing after all stages complete

    Args:
        results: Results from all processing stages
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
        pdf.extraction_status = "completed"
        pdf.processing_completed_at = time.time()

        # Calculate processing time
        if pdf.processing_started_at:
            processing_time = pdf.processing_completed_at - pdf.processing_started_at
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
        return summary

    except Exception as e:
        logger.error(f"Failed to finalize PDF processing: {str(e)}", exc_info=True)

        # Update PDF status to failed
        try:
            pdf = self.db_session.query(PDF).filter(PDF.id == pdf_id).first()
            if pdf:
                pdf.extraction_status = "failed"
                pdf.extraction_error = str(e)
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
