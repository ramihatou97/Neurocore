"""
Storage service for managing file uploads and storage
Handles PDF files, extracted images, and thumbnails
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, BinaryIO
from PIL import Image
import uuid

from backend.config import settings
from backend.utils import get_logger

logger = get_logger(__name__)


class StorageService:
    """
    Handles file storage operations for PDFs and images

    Directory structure:
    - storage/pdfs/YYYY/MM/DD/{uuid}.pdf
    - storage/images/YYYY/MM/DD/{uuid}.{ext}
    - storage/thumbnails/YYYY/MM/DD/{uuid}_thumb.{ext}
    """

    def __init__(self):
        """Initialize storage service and create base directories"""
        self.base_storage_path = Path(settings.STORAGE_BASE_PATH)
        self.pdf_storage_path = self.base_storage_path / "pdfs"
        self.image_storage_path = self.base_storage_path / "images"
        self.thumbnail_storage_path = self.base_storage_path / "thumbnails"

        # Create base directories if they don't exist
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create storage directories if they don't exist"""
        for path in [self.pdf_storage_path, self.image_storage_path, self.thumbnail_storage_path]:
            path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {path}")

    def _get_date_path(self, base_path: Path) -> Path:
        """
        Get date-based subdirectory path (YYYY/MM/DD)

        Args:
            base_path: Base storage path

        Returns:
            Path with date subdirectories
        """
        now = datetime.utcnow()
        date_path = base_path / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
        date_path.mkdir(parents=True, exist_ok=True)
        return date_path

    def save_pdf(self, file_content: BinaryIO, filename: str, pdf_id: Optional[uuid.UUID] = None) -> dict:
        """
        Save uploaded PDF file to storage

        Args:
            file_content: File content as binary stream
            filename: Original filename
            pdf_id: Optional PDF ID (generates new UUID if not provided)

        Returns:
            dict with file_path, file_size_bytes, storage_id
        """
        # Generate storage ID if not provided
        storage_id = pdf_id or uuid.uuid4()

        # Get date-based directory
        date_path = self._get_date_path(self.pdf_storage_path)

        # Create file path with UUID
        file_extension = Path(filename).suffix.lower()
        if file_extension != '.pdf':
            raise ValueError(f"Invalid file extension: {file_extension}. Must be .pdf")

        file_path = date_path / f"{storage_id}.pdf"

        # Save file
        try:
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(file_content, f)

            # Get file size
            file_size = os.path.getsize(file_path)

            logger.info(f"PDF saved: {file_path} ({file_size} bytes)")

            return {
                "file_path": str(file_path),
                "file_size_bytes": file_size,
                "storage_id": str(storage_id)
            }

        except Exception as e:
            logger.error(f"Failed to save PDF: {str(e)}", exc_info=True)
            # Clean up partial file if it exists
            if file_path.exists():
                file_path.unlink()
            raise

    def save_image(
        self,
        image_content: bytes,
        image_format: str,
        image_id: Optional[uuid.UUID] = None,
        create_thumbnail: bool = True,
        thumbnail_size: tuple = (300, 300)
    ) -> dict:
        """
        Save extracted image to storage with optional thumbnail

        Args:
            image_content: Image content as bytes
            image_format: Image format (PNG, JPEG, etc.)
            image_id: Optional image ID (generates new UUID if not provided)
            create_thumbnail: Whether to create thumbnail
            thumbnail_size: Thumbnail dimensions (width, height)

        Returns:
            dict with image_path, thumbnail_path, file_size_bytes, storage_id
        """
        # Generate storage ID if not provided
        storage_id = image_id or uuid.uuid4()

        # Get date-based directory
        date_path = self._get_date_path(self.image_storage_path)

        # Determine file extension
        extension = f".{image_format.lower()}"
        if extension not in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
            extension = '.png'  # Default to PNG

        image_path = date_path / f"{storage_id}{extension}"

        # Save image
        try:
            with open(image_path, 'wb') as f:
                f.write(image_content)

            file_size = os.path.getsize(image_path)

            result = {
                "image_path": str(image_path),
                "file_size_bytes": file_size,
                "storage_id": str(storage_id),
                "thumbnail_path": None
            }

            # Create thumbnail if requested
            if create_thumbnail:
                thumbnail_path = self._create_thumbnail(
                    image_path,
                    storage_id,
                    thumbnail_size
                )
                result["thumbnail_path"] = str(thumbnail_path) if thumbnail_path else None

            logger.info(f"Image saved: {image_path} ({file_size} bytes)")

            return result

        except Exception as e:
            logger.error(f"Failed to save image: {str(e)}", exc_info=True)
            # Clean up partial files
            if image_path.exists():
                image_path.unlink()
            raise

    def _create_thumbnail(
        self,
        image_path: Path,
        storage_id: uuid.UUID,
        size: tuple
    ) -> Optional[Path]:
        """
        Create thumbnail for an image

        Args:
            image_path: Path to original image
            storage_id: Storage ID for naming
            size: Thumbnail size (width, height)

        Returns:
            Path to thumbnail or None if creation failed
        """
        try:
            # Get date-based directory for thumbnails
            date_path = self._get_date_path(self.thumbnail_storage_path)

            # Open image and create thumbnail
            with Image.open(image_path) as img:
                # Convert to RGB if necessary (for PNG with transparency)
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background

                # Create thumbnail
                img.thumbnail(size, Image.Resampling.LANCZOS)

                # Save thumbnail
                thumbnail_path = date_path / f"{storage_id}_thumb.jpg"
                img.save(thumbnail_path, 'JPEG', quality=85, optimize=True)

                logger.debug(f"Thumbnail created: {thumbnail_path}")
                return thumbnail_path

        except Exception as e:
            logger.warning(f"Failed to create thumbnail: {str(e)}")
            return None

    def delete_pdf(self, file_path: str) -> bool:
        """
        Delete PDF file from storage

        Args:
            file_path: Path to PDF file

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info(f"PDF deleted: {file_path}")
                return True
            else:
                logger.warning(f"PDF not found for deletion: {file_path}")
                return False
        except Exception as e:
            logger.error(f"Failed to delete PDF: {str(e)}", exc_info=True)
            return False

    def delete_image(self, image_path: str, thumbnail_path: Optional[str] = None) -> bool:
        """
        Delete image and its thumbnail from storage

        Args:
            image_path: Path to image file
            thumbnail_path: Optional path to thumbnail

        Returns:
            True if deleted successfully, False otherwise
        """
        success = True

        # Delete main image
        try:
            path = Path(image_path)
            if path.exists():
                path.unlink()
                logger.debug(f"Image deleted: {image_path}")
            else:
                logger.warning(f"Image not found for deletion: {image_path}")
                success = False
        except Exception as e:
            logger.error(f"Failed to delete image: {str(e)}", exc_info=True)
            success = False

        # Delete thumbnail if provided
        if thumbnail_path:
            try:
                thumb_path = Path(thumbnail_path)
                if thumb_path.exists():
                    thumb_path.unlink()
                    logger.debug(f"Thumbnail deleted: {thumbnail_path}")
            except Exception as e:
                logger.error(f"Failed to delete thumbnail: {str(e)}", exc_info=True)
                success = False

        return success

    def get_storage_stats(self) -> dict:
        """
        Get storage statistics

        Returns:
            dict with total_pdfs, total_images, total_size_bytes
        """
        stats = {
            "total_pdfs": 0,
            "total_images": 0,
            "total_thumbnails": 0,
            "total_size_bytes": 0
        }

        try:
            # Count PDFs
            for pdf_file in self.pdf_storage_path.rglob("*.pdf"):
                stats["total_pdfs"] += 1
                stats["total_size_bytes"] += pdf_file.stat().st_size

            # Count images
            for img_file in self.image_storage_path.rglob("*"):
                if img_file.is_file():
                    stats["total_images"] += 1
                    stats["total_size_bytes"] += img_file.stat().st_size

            # Count thumbnails
            for thumb_file in self.thumbnail_storage_path.rglob("*"):
                if thumb_file.is_file():
                    stats["total_thumbnails"] += 1
                    stats["total_size_bytes"] += thumb_file.stat().st_size

        except Exception as e:
            logger.error(f"Failed to get storage stats: {str(e)}", exc_info=True)

        return stats
