"""
SQLAlchemy model for pdf_chapters table
PRIMARY SEARCH UNIT for chapter-level vector search
Part of Chapter-Level Vector Search (Migration 006)
"""

from sqlalchemy import String, Integer, Boolean, Float, ForeignKey, Text, ARRAY, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from datetime import datetime
import uuid
from pgvector.sqlalchemy import Vector
from backend.database.base import Base, UUIDMixin, TimestampMixin


class PDFChapter(Base, UUIDMixin, TimestampMixin):
    """
    Chapter-level content - PRIMARY SEARCH UNIT

    Supports three source types:
    - textbook_chapter: Chapter from a multi-chapter textbook
    - standalone_chapter: Single chapter uploaded independently
    - research_paper: Research paper treated as a chapter

    Granularity: 20-80 pages per chapter (optimal for vector search)
    Processing: Extract → Hash → Embed → Deduplicate → Search
    """

    __tablename__ = "pdf_chapters"

    # ==================== Hierarchy ====================

    book_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('pdf_books.id', ondelete='CASCADE'),
        nullable=True,
        index=True,
        comment="Parent book (NULL for standalone chapters/papers)"
    )

    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type: textbook_chapter, standalone_chapter, research_paper"
    )

    # ==================== Chapter Identification ====================

    chapter_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Chapter number within book (NULL for standalone)"
    )

    chapter_title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Chapter title (from TOC, heading, or filename)"
    )

    start_page: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Starting page number"
    )

    end_page: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Ending page number"
    )

    page_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Total pages in chapter"
    )

    # ==================== Content ====================

    extracted_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full extracted text from chapter"
    )

    word_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Word count for sizing chunks"
    )

    has_images: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether chapter contains images"
    )

    image_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of images in chapter"
    )

    # ==================== Vector Search (1536-dim text-embedding-3-large) ====================

    embedding: Mapped[Optional[List[float]]] = mapped_column(
        Vector(1536),
        nullable=True,
        comment="1536-dim vector (text-embedding-3-large with dimensions=1536)"
    )

    embedding_model: Mapped[str] = mapped_column(
        String(100),
        default='text-embedding-3-large',
        nullable=False,
        comment="Embedding model used"
    )

    embedding_generated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="When embedding was generated"
    )

    # ==================== Deduplication (Mark-Not-Delete Strategy) ====================

    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="SHA-256 hash of normalized text for deduplication"
    )

    is_duplicate: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="TRUE if duplicate exists with higher preference_score"
    )

    duplicate_of_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('pdf_chapters.id', ondelete='SET NULL'),
        nullable=True,
        comment="Points to preferred version if this is duplicate"
    )

    duplicate_group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="UUID grouping all duplicates together"
    )

    preference_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Ranking for duplicates (higher = preferred). Standalone > textbook chapter"
    )

    # ==================== Chapter Detection Metadata ====================

    detection_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Confidence in chapter detection (0.0-1.0): TOC=0.9, pattern=0.8, heading=0.6"
    )

    detection_method: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Detection method: toc, pattern, heading, manual"
    )

    quality_score: Mapped[float] = mapped_column(
        Float,
        default=0.5,
        nullable=False,
        comment="Quality score (0.0-1.0) for ranking"
    )

    # ==================== Relationships ====================

    book: Mapped[Optional["PDFBook"]] = relationship(
        "PDFBook",
        back_populates="chapters"
    )

    chunks: Mapped[List["PDFChunk"]] = relationship(
        "PDFChunk",
        back_populates="chapter",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="PDFChunk.chunk_index"
    )

    def __repr__(self) -> str:
        return f"<PDFChapter(id={self.id}, title='{self.chapter_title[:50]}...', source='{self.source_type}', is_duplicate={self.is_duplicate})>"

    def to_dict(self) -> dict:
        """Convert PDFChapter to dictionary"""
        return {
            "id": str(self.id),
            "book_id": str(self.book_id) if self.book_id else None,
            "book_title": self.get_book_title(),  # Include parent book title
            "source_type": self.source_type,
            "chapter_number": self.chapter_number,
            "chapter_title": self.chapter_title,
            "start_page": self.start_page,
            "end_page": self.end_page,
            "page_count": self.page_count,
            "word_count": self.word_count,
            "has_images": self.has_images,
            "image_count": self.image_count,
            # Content fields (Issue #1 fix - add actual chapter text)
            "extracted_text": self.extracted_text,  # Full chapter text for display
            "extracted_text_preview": self.extracted_text[:500] + "..." if len(self.extracted_text) > 500 else self.extracted_text,  # Preview for search results
            # Embedding fields
            "embedding_model": self.embedding_model,
            "embedding_generated_at": self.embedding_generated_at.isoformat() if self.embedding_generated_at else None,
            "has_embedding": self.embedding is not None,
            # Deduplication fields
            "content_hash": self.content_hash,
            "is_duplicate": self.is_duplicate,
            "duplicate_of_id": str(self.duplicate_of_id) if self.duplicate_of_id else None,
            "duplicate_group_id": str(self.duplicate_group_id) if self.duplicate_group_id else None,
            "preference_score": self.preference_score,
            # Quality fields
            "detection_confidence": self.detection_confidence,
            "detection_method": self.detection_method,
            "quality_score": self.quality_score,
            # Timestamps
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "chunks_count": len(self.chunks) if self.chunks else 0
        }

    def has_embedding(self) -> bool:
        """Check if chapter has embedding generated"""
        return self.embedding is not None

    def is_long_chapter(self) -> bool:
        """Check if chapter needs chunking (>4000 words)"""
        return self.word_count is not None and self.word_count > 4000

    def get_book_title(self) -> Optional[str]:
        """Get parent book title if exists"""
        return self.book.title if self.book else None
