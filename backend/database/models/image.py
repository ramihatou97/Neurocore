"""
Image model for extracted images from PDFs with AI analysis
Part of Process A: Background PDF Indexation - Images are first-class citizens
"""

from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, Text, ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
import uuid
from pgvector.sqlalchemy import Vector
from backend.database.base import Base, UUIDMixin, TimestampMixin


class Image(Base, UUIDMixin, TimestampMixin):
    """
    Image model with comprehensive AI analysis

    Images receive extensive processing (95% complete vs 40% for text):
    1. Extract from PDF
    2. Analyze with Claude Vision API
    3. Perform OCR (EasyOCR + Tesseract)
    4. Generate vector embedding
    5. Detect duplicates
    6. Store with rich metadata (24 fields)

    This contrasts with basic text extraction, making images first-class citizens.
    """

    __tablename__ = "images"

    # ==================== Source Information ====================

    pdf_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('pdfs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="Source PDF containing this image"
    )

    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Page number where image appears"
    )

    image_index_on_page: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Index of image on the page (0-based)"
    )

    # ==================== Storage ====================

    file_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        unique=True,
        comment="Full path to stored image file"
    )

    thumbnail_path: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        comment="Path to thumbnail version for quick loading"
    )

    # ==================== Image Properties ====================

    width: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Image width in pixels"
    )

    height: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Image height in pixels"
    )

    format: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Image format: PNG, JPEG, etc."
    )

    file_size_bytes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="File size in bytes"
    )

    # ==================== AI Analysis (Claude Vision) ====================

    ai_description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Claude Vision's detailed description of the image"
    )

    image_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Type: anatomical_diagram, surgical_photo, mri, ct, flowchart, graph, table"
    )

    anatomical_structures: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="List of anatomical structures identified in image"
    )

    clinical_context: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Clinical context and significance of the image"
    )

    quality_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Image quality score from Claude Vision (0.0 - 1.0)"
    )

    confidence_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="AI confidence in analysis (0.0 - 1.0)"
    )

    # ==================== OCR Results ====================

    ocr_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Text extracted from image via OCR (EasyOCR + Tesseract)"
    )

    contains_text: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether image contains extractable text"
    )

    # ==================== Vector Embedding for Semantic Search ====================

    embedding: Mapped[Optional[List[float]]] = mapped_column(
        Vector(1536),  # OpenAI ada-002 embedding dimension
        nullable=True,
        comment="Vector embedding for semantic image search"
    )

    # ==================== Metadata ====================

    caption: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Caption or figure text extracted from PDF"
    )

    figure_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Figure number (e.g., 'Figure 3.2')"
    )

    # ==================== Deduplication ====================

    is_duplicate: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Whether this is a duplicate of another image"
    )

    duplicate_of_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('images.id', ondelete='SET NULL'),
        nullable=True,
        comment="ID of original image if this is a duplicate"
    )

    # ==================== Relationships ====================

    pdf: Mapped["PDF"] = relationship(
        "PDF",
        back_populates="images"
    )

    # Self-referential for duplicates
    original_image: Mapped[Optional["Image"]] = relationship(
        "Image",
        remote_side="Image.id",
        foreign_keys=[duplicate_of_id],
        post_update=True
    )

    # AI Provider Metrics
    ai_metrics: Mapped[List["AIProviderMetric"]] = relationship(
        "AIProviderMetric",
        back_populates="image",
        foreign_keys="AIProviderMetric.image_id",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Image(id={self.id}, type='{self.image_type}', pdf_id={self.pdf_id}, page={self.page_number})>"

    def to_dict(self) -> dict:
        """Convert image to dictionary"""
        return {
            "id": str(self.id),
            "pdf_id": str(self.pdf_id),
            "page_number": self.page_number,
            "image_index_on_page": self.image_index_on_page,  # Keep for API compatibility (0-based)
            "image_number": self.image_index_on_page + 1,  # Human-readable: 1-based numbering
            "image_label": f"Image {self.image_index_on_page + 1} on Page {self.page_number}",  # Full context label
            "file_path": self.file_path,
            "thumbnail_path": self.thumbnail_path,
            "dimensions": {
                "width": self.width,
                "height": self.height
            },
            "format": self.format,
            "file_size_bytes": self.file_size_bytes,
            "ai_analysis": {
                "description": self.ai_description,
                "image_type": self.image_type,
                "anatomical_structures": self.anatomical_structures,
                "clinical_context": self.clinical_context,
                "quality_score": self.quality_score,
                "quality_percentage": round(self.quality_score * 100) if self.quality_score is not None else None,  # User-friendly percentage
                "confidence_score": self.confidence_score,
                "confidence_percentage": round(self.confidence_score * 100) if self.confidence_score is not None else None  # User-friendly percentage
            },
            "ocr": {
                "text": self.ocr_text,
                "contains_text": self.contains_text
            },
            "metadata": {
                "caption": self.caption,
                "figure_number": self.figure_number
            },
            "is_duplicate": self.is_duplicate,
            "duplicate_of_id": str(self.duplicate_of_id) if self.duplicate_of_id else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    def has_embedding(self) -> bool:
        """Check if image has vector embedding"""
        return self.embedding is not None and len(self.embedding) > 0

    def is_high_quality(self) -> bool:
        """Check if image meets high quality threshold"""
        return self.quality_score is not None and self.quality_score >= 0.7
