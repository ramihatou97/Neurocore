"""
SQLAlchemy model for pdf_books table
Full textbooks with multiple chapters
Part of Chapter-Level Vector Search (Migration 006)
"""

from sqlalchemy import String, Integer, BigInteger, Text, ARRAY, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from backend.database.base import Base, UUIDMixin, TimestampMixin


class PDFBook(Base, UUIDMixin, TimestampMixin):
    """
    Full textbook with multiple chapters
    Book-level metadata for hierarchical organization

    Hierarchy: Book → Chapter (PRIMARY) → Chunk
    Processing: Upload → Classify → Detect Chapters → Extract → Generate Embeddings
    """

    __tablename__ = "pdf_books"

    # ==================== Book Metadata ====================

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Book title (from metadata or TOC)"
    )

    authors: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="List of author names"
    )

    edition: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Edition information (e.g., '5th Edition')"
    )

    publication_year: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        comment="Year of publication"
    )

    publisher: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Publisher name"
    )

    isbn: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        unique=True,
        index=True,
        comment="ISBN (unique identifier)"
    )

    # ==================== File Information ====================

    total_chapters: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of chapters detected and extracted"
    )

    total_pages: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Total number of pages in PDF"
    )

    file_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full path to stored PDF file"
    )

    file_size_bytes: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        comment="File size in bytes"
    )

    # ==================== Upload Tracking ====================

    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        comment="User who uploaded this book"
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="When book was uploaded"
    )

    # ==================== Processing Status ====================

    processing_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default='pending',
        index=True,
        comment="Status: pending, processing, completed, failed"
    )

    processing_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="When background processing started"
    )

    processing_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="When background processing completed"
    )

    processing_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if processing failed"
    )

    # ==================== Flexible Metadata ====================

    book_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional metadata (TOC structure, classification info, etc.)"
    )

    # ==================== Title Editing (Migration 011) ====================

    title_edited_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Timestamp when title was manually edited"
    )

    title_edited_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        comment="User who edited the title"
    )

    original_title: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Original title before editing (for audit trail)"
    )

    # ==================== Image Extraction (Migration 012) ====================

    pdf_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('pdfs.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
        comment="Link to pdfs table for image extraction pipeline (Migration 012)"
    )

    # ==================== Relationships ====================

    chapters: Mapped[List["PDFChapter"]] = relationship(
        "PDFChapter",
        back_populates="book",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="PDFChapter.chapter_number"
    )

    def __repr__(self) -> str:
        return f"<PDFBook(id={self.id}, title='{self.title}', chapters={self.total_chapters}, status='{self.processing_status}')>"

    def to_dict(self) -> dict:
        """Convert PDFBook to dictionary"""
        return {
            "id": str(self.id),
            "title": self.title,
            "authors": self.authors,
            "edition": self.edition,
            "publication_year": self.publication_year,
            "publisher": self.publisher,
            "isbn": self.isbn,
            "total_chapters": self.total_chapters,
            "total_pages": self.total_pages,
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
            "uploaded_by": str(self.uploaded_by) if self.uploaded_by else None,
            "uploaded_at": self.uploaded_at.isoformat(),
            "processing_status": self.processing_status,
            "processing_started_at": self.processing_started_at.isoformat() if self.processing_started_at else None,
            "processing_completed_at": self.processing_completed_at.isoformat() if self.processing_completed_at else None,
            "processing_error": self.processing_error,
            "book_metadata": self.book_metadata,
            # Title editing fields (Migration 011)
            "title_edited_at": self.title_edited_at.isoformat() if self.title_edited_at else None,
            "title_edited_by": str(self.title_edited_by) if self.title_edited_by else None,
            "original_title": self.original_title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "chapters_count": len(self.chapters) if self.chapters else 0
        }

    def is_processing_complete(self) -> bool:
        """Check if book processing is complete"""
        return self.processing_status == 'completed'

    def get_embedded_chapters_count(self) -> int:
        """Get count of chapters with embeddings generated"""
        if not self.chapters:
            return 0
        return sum(1 for chapter in self.chapters if chapter.embedding is not None)
