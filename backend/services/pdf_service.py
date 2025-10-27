"""
PDF processing service for text and image extraction
Uses PyMuPDF (fitz) for high-quality extraction with layout preservation
"""

import fitz  # PyMuPDF
import io
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, BinaryIO
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile

from backend.database.models import PDF, Image
from backend.services.storage_service import StorageService
from backend.config import settings
from backend.utils import get_logger

logger = get_logger(__name__)


class PDFService:
    """
    Service for PDF processing and extraction

    Handles:
    - PDF upload and validation
    - Metadata extraction (title, authors, DOI, etc.)
    - Text extraction with layout preservation
    - Image extraction with position and metadata
    - Progress tracking in database
    """

    def __init__(self, db_session: Session):
        """
        Initialize PDF service

        Args:
            db_session: Database session
        """
        self.db = db_session
        self.storage = StorageService()

    async def upload_pdf(
        self,
        file: UploadFile,
        extract_immediately: bool = False
    ) -> PDF:
        """
        Upload and save PDF file

        Args:
            file: Uploaded PDF file
            extract_immediately: Whether to extract text/images immediately

        Returns:
            Created PDF database record

        Raises:
            HTTPException: If validation fails or upload error occurs
        """
        # Validate file
        self._validate_pdf_file(file)

        # Read file content
        file_content = await file.read()
        file_size_mb = len(file_content) / (1024 * 1024)

        # Check file size
        if file_size_mb > settings.MAX_PDF_SIZE_MB:
            raise HTTPException(
                status_code=400,
                detail=f"PDF file too large: {file_size_mb:.2f}MB (max: {settings.MAX_PDF_SIZE_MB}MB)"
            )

        # Save file to storage
        try:
            storage_result = self.storage.save_pdf(
                io.BytesIO(file_content),
                file.filename
            )
        except Exception as e:
            logger.error(f"Failed to save PDF: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Failed to save PDF file"
            )

        # Extract metadata from PDF
        metadata = self._extract_pdf_metadata(file_content)

        # Create PDF record
        pdf = PDF(
            filename=file.filename,
            file_path=storage_result["file_path"],
            file_size_bytes=storage_result["file_size_bytes"],
            total_pages=metadata.get("page_count", 0),
            title=metadata.get("title"),
            authors=metadata.get("authors"),
            publication_year=metadata.get("year"),
            journal=metadata.get("journal"),
            doi=metadata.get("doi"),
            pmid=metadata.get("pmid"),
            indexing_status="uploaded",
            text_extracted=False,
            images_extracted=False,
            embeddings_generated=False
        )

        self.db.add(pdf)
        self.db.commit()
        self.db.refresh(pdf)

        logger.info(f"PDF uploaded: {pdf.filename} (ID: {pdf.id}, Size: {file_size_mb:.2f}MB)")

        # Extract immediately if requested
        if extract_immediately:
            self.extract_text(pdf.id)
            self.extract_images(pdf.id)

        return pdf

    def _validate_pdf_file(self, file: UploadFile) -> None:
        """
        Validate uploaded PDF file

        Args:
            file: Uploaded file

        Raises:
            HTTPException: If validation fails
        """
        # Check filename
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="No filename provided"
            )

        # Check file extension
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in settings.ALLOWED_PDF_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file_extension}. Allowed: {settings.ALLOWED_PDF_EXTENSIONS}"
            )

        # Check content type
        if file.content_type and file.content_type not in ['application/pdf', 'application/x-pdf']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid content type: {file.content_type}. Must be application/pdf"
            )

    def _extract_pdf_metadata(self, file_content: bytes) -> Dict[str, Any]:
        """
        Extract metadata from PDF file

        Args:
            file_content: PDF file content as bytes

        Returns:
            Dictionary with metadata (title, authors, year, doi, etc.)
        """
        metadata = {}

        try:
            doc = fitz.open(stream=file_content, filetype="pdf")

            # Get page count
            metadata["page_count"] = len(doc)

            # Get PDF metadata
            pdf_meta = doc.metadata
            if pdf_meta:
                metadata["title"] = pdf_meta.get("title") or None
                metadata["author"] = pdf_meta.get("author") or None

                # Parse authors (comma-separated)
                if metadata.get("author"):
                    authors = [a.strip() for a in metadata["author"].split(",")]
                    metadata["authors"] = authors if authors else None

                # Try to extract year from creation date
                creation_date = pdf_meta.get("creationDate")
                if creation_date:
                    # PyMuPDF format: D:YYYYMMDDHHmmSS
                    year_match = re.search(r'D:(\d{4})', creation_date)
                    if year_match:
                        metadata["year"] = int(year_match.group(1))

            # Try to extract DOI and PMID from first page text
            if len(doc) > 0:
                first_page_text = doc[0].get_text()

                # DOI pattern
                doi_match = re.search(r'10\.\d{4,}/[^\s]+', first_page_text)
                if doi_match:
                    metadata["doi"] = doi_match.group(0)

                # PMID pattern
                pmid_match = re.search(r'PMID:\s*(\d+)', first_page_text, re.IGNORECASE)
                if pmid_match:
                    metadata["pmid"] = pmid_match.group(1)

                # Try to extract journal name (common patterns)
                # This is a simple heuristic - can be improved
                journal_patterns = [
                    r'(?:Published in|Journal of|International Journal of)\s+([A-Za-z\s&]+)',
                    r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+\d{4}',  # Journal Name YYYY
                ]
                for pattern in journal_patterns:
                    journal_match = re.search(pattern, first_page_text, re.MULTILINE)
                    if journal_match:
                        metadata["journal"] = journal_match.group(1).strip()
                        break

            doc.close()

        except Exception as e:
            logger.error(f"Failed to extract PDF metadata: {str(e)}", exc_info=True)

        return metadata

    def extract_text(self, pdf_id: str) -> Dict[str, Any]:
        """
        Extract text from PDF with layout preservation

        Args:
            pdf_id: PDF ID

        Returns:
            Dictionary with extraction statistics

        Raises:
            HTTPException: If PDF not found or extraction fails
        """
        # Get PDF record
        pdf = self.db.query(PDF).filter(PDF.id == pdf_id).first()
        if not pdf:
            raise HTTPException(status_code=404, detail="PDF not found")

        # Update status
        pdf.indexing_status = "extracting_text"
        self.db.commit()

        try:
            # Open PDF
            doc = fitz.open(pdf.file_path)

            total_text_length = 0
            total_words = 0

            # Extract text page by page
            for page_num in range(len(doc)):
                page = doc[page_num]

                # Get text with layout preservation
                text = page.get_text("text")  # Simple text extraction
                # For better layout: page.get_text("blocks") or page.get_text("dict")

                if text:
                    total_text_length += len(text)
                    total_words += len(text.split())

                    # Store page text in JSONB (can be indexed/searched later)
                    # For now, we'll just track statistics
                    # In a full implementation, store page text in separate table

            doc.close()

            # Update PDF record
            pdf.text_extracted = True
            pdf.total_text_length = total_text_length
            pdf.total_words = total_words
            pdf.indexing_status = "text_extracted"
            pdf.last_indexed_at = datetime.utcnow()

            self.db.commit()

            logger.info(
                f"Text extracted from PDF {pdf.id}: "
                f"{total_words} words, {total_text_length} characters"
            )

            return {
                "pdf_id": str(pdf.id),
                "total_pages": pdf.total_pages,
                "total_words": total_words,
                "total_text_length": total_text_length,
                "status": "completed"
            }

        except Exception as e:
            logger.error(f"Text extraction failed: {str(e)}", exc_info=True)
            pdf.indexing_status = "text_extraction_failed"
            self.db.commit()
            raise HTTPException(
                status_code=500,
                detail=f"Text extraction failed: {str(e)}"
            )

    def extract_images(self, pdf_id: str) -> Dict[str, Any]:
        """
        Extract all images from PDF with metadata

        Args:
            pdf_id: PDF ID

        Returns:
            Dictionary with extraction statistics

        Raises:
            HTTPException: If PDF not found or extraction fails
        """
        # Get PDF record
        pdf = self.db.query(PDF).filter(PDF.id == pdf_id).first()
        if not pdf:
            raise HTTPException(status_code=404, detail="PDF not found")

        # Update status
        pdf.indexing_status = "extracting_images"
        self.db.commit()

        try:
            doc = fitz.open(pdf.file_path)

            total_images = 0
            successful_extractions = 0

            # Extract images page by page
            for page_num in range(len(doc)):
                page = doc[page_num]

                # Get image list from page
                image_list = page.get_images(full=True)

                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]  # Image reference number
                        base_image = doc.extract_image(xref)

                        if not base_image:
                            continue

                        image_bytes = base_image["image"]
                        image_format = base_image["ext"]  # png, jpeg, etc.
                        width = base_image.get("width", 0)
                        height = base_image.get("height", 0)

                        # Save image to storage
                        storage_result = self.storage.save_image(
                            image_bytes,
                            image_format,
                            create_thumbnail=True
                        )

                        # Create Image record
                        image_record = Image(
                            pdf_id=pdf.id,
                            page_number=page_num + 1,  # 1-indexed
                            image_index_on_page=img_index,
                            file_path=storage_result["image_path"],
                            thumbnail_path=storage_result["thumbnail_path"],
                            width=width,
                            height=height,
                            format=image_format.upper(),
                            file_size_bytes=storage_result["file_size_bytes"],
                            # AI analysis will be done in Phase 4
                            ai_description=None,
                            image_type=None,
                            quality_score=None,
                            is_duplicate=False
                        )

                        self.db.add(image_record)
                        successful_extractions += 1

                    except Exception as e:
                        logger.warning(
                            f"Failed to extract image {img_index} from page {page_num + 1}: {str(e)}"
                        )
                        continue

                total_images += len(image_list)

            doc.close()

            # Update PDF record
            pdf.images_extracted = True
            pdf.total_images = total_images
            pdf.indexing_status = "images_extracted"
            pdf.last_indexed_at = datetime.utcnow()

            self.db.commit()

            logger.info(
                f"Images extracted from PDF {pdf.id}: "
                f"{successful_extractions}/{total_images} successful"
            )

            return {
                "pdf_id": str(pdf.id),
                "total_images": total_images,
                "successful_extractions": successful_extractions,
                "status": "completed"
            }

        except Exception as e:
            logger.error(f"Image extraction failed: {str(e)}", exc_info=True)
            pdf.indexing_status = "image_extraction_failed"
            self.db.commit()
            raise HTTPException(
                status_code=500,
                detail=f"Image extraction failed: {str(e)}"
            )

    def get_pdf(self, pdf_id: str) -> PDF:
        """
        Get PDF by ID

        Args:
            pdf_id: PDF ID

        Returns:
            PDF record

        Raises:
            HTTPException: If PDF not found
        """
        pdf = self.db.query(PDF).filter(PDF.id == pdf_id).first()
        if not pdf:
            raise HTTPException(status_code=404, detail="PDF not found")
        return pdf

    def list_pdfs(
        self,
        skip: int = 0,
        limit: int = 100,
        indexing_status: Optional[str] = None
    ) -> List[PDF]:
        """
        List PDFs with pagination and filtering

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            indexing_status: Filter by indexing status

        Returns:
            List of PDF records
        """
        query = self.db.query(PDF)

        if indexing_status:
            query = query.filter(PDF.indexing_status == indexing_status)

        query = query.order_by(PDF.created_at.desc())
        query = query.offset(skip).limit(limit)

        return query.all()

    def delete_pdf(self, pdf_id: str) -> Dict[str, Any]:
        """
        Delete PDF and all associated data

        Args:
            pdf_id: PDF ID

        Returns:
            Dictionary with deletion statistics

        Raises:
            HTTPException: If PDF not found
        """
        # Get PDF record
        pdf = self.db.query(PDF).filter(PDF.id == pdf_id).first()
        if not pdf:
            raise HTTPException(status_code=404, detail="PDF not found")

        # Delete associated images
        images = self.db.query(Image).filter(Image.pdf_id == pdf_id).all()
        deleted_images = 0

        for image in images:
            # Delete image files from storage
            self.storage.delete_image(image.file_path, image.thumbnail_path)
            # Delete image record
            self.db.delete(image)
            deleted_images += 1

        # Delete PDF file from storage
        self.storage.delete_pdf(pdf.file_path)

        # Delete PDF record
        self.db.delete(pdf)
        self.db.commit()

        logger.info(f"PDF deleted: {pdf_id} ({deleted_images} images)")

        return {
            "pdf_id": pdf_id,
            "deleted_images": deleted_images,
            "status": "deleted"
        }

    def get_pdf_images(self, pdf_id: str) -> List[Image]:
        """
        Get all images from a PDF

        Args:
            pdf_id: PDF ID

        Returns:
            List of Image records

        Raises:
            HTTPException: If PDF not found
        """
        # Verify PDF exists
        pdf = self.db.query(PDF).filter(PDF.id == pdf_id).first()
        if not pdf:
            raise HTTPException(status_code=404, detail="PDF not found")

        # Get images
        images = self.db.query(Image).filter(Image.pdf_id == pdf_id).order_by(
            Image.page_number, Image.image_index_on_page
        ).all()

        return images
