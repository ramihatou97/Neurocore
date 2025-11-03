"""
SQLAlchemy model for pdf_chunks table
Fine-grained chunks for long chapters (>4000 words)
Part of Chapter-Level Vector Search (Migration 006)
"""

from sqlalchemy import String, Integer, ForeignKey, Text, ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
import uuid
from pgvector.sqlalchemy import Vector
from backend.database.base import Base, UUIDMixin, TimestampMixin


class PDFChunk(Base, UUIDMixin, TimestampMixin):
    """
    Fine-grained chunks for long chapters (>4000 words)
    Enables precise retrieval within large chapters

    Chunking Strategy:
    - Chunk size: ~1024 tokens (~4096 chars)
    - Overlap: 128 tokens (~512 chars)
    - Respects paragraph boundaries
    - Preserves context with headings

    Use case: When chapter-level embedding is too coarse,
    chunk-level search provides precise section retrieval
    """

    __tablename__ = "pdf_chunks"

    # ==================== Hierarchy ====================

    chapter_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('pdf_chapters.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="Parent chapter containing this chunk"
    )

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="0-based index of chunk within chapter"
    )

    # ==================== Content ====================

    chunk_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Chunk text content"
    )

    token_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Approximate token count"
    )

    start_char_offset: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Character offset from chapter start"
    )

    end_char_offset: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Character offset from chapter start"
    )

    # ==================== Context Preservation ====================

    preceding_heading: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Section heading before this chunk (for context)"
    )

    contains_headings: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Headings within this chunk (structure awareness)"
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

    # ==================== Relationships ====================

    chapter: Mapped["PDFChapter"] = relationship(
        "PDFChapter",
        back_populates="chunks"
    )

    def __repr__(self) -> str:
        return f"<PDFChunk(id={self.id}, chapter_id={self.chapter_id}, index={self.chunk_index}, tokens={self.token_count})>"

    def to_dict(self) -> dict:
        """Convert PDFChunk to dictionary"""
        return {
            "id": str(self.id),
            "chapter_id": str(self.chapter_id),
            "chunk_index": self.chunk_index,
            "chunk_text": self.chunk_text,
            "token_count": self.token_count,
            "start_char_offset": self.start_char_offset,
            "end_char_offset": self.end_char_offset,
            "preceding_heading": self.preceding_heading,
            "contains_headings": self.contains_headings,
            "embedding_model": self.embedding_model,
            "has_embedding": self.embedding is not None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    def has_embedding(self) -> bool:
        """Check if chunk has embedding generated"""
        return self.embedding is not None

    def get_context(self) -> str:
        """
        Get chunk with context (preceding heading)
        Useful for displaying chunk in search results
        """
        if self.preceding_heading:
            return f"[{self.preceding_heading}]\n\n{self.chunk_text}"
        return self.chunk_text

    def get_chapter_title(self) -> Optional[str]:
        """Get parent chapter title"""
        return self.chapter.chapter_title if self.chapter else None
