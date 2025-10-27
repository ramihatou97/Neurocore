"""
PDF model for uploaded research papers and textbooks
Part of Process A: Background PDF Indexation
"""

from sqlalchemy import String, Integer, BigInteger, Boolean, DateTime, Text, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from datetime import datetime
from backend.database.base import Base, UUIDMixin, TimestampMixin


class PDF(Base, UUIDMixin, TimestampMixin):
    """
    PDF model tracking uploaded research papers

    Process A (Background Indexation) workflow:
    1. Upload PDF → status: 'pending'
    2. Extract text → text_extracted: True
    3. Extract images → images_extracted: True
    4. Generate embeddings → embeddings_generated: True
    5. Complete → status: 'completed'
    """

    __tablename__ = "pdfs"

    # File information
    filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Original uploaded filename"
    )

    file_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        unique=True,
        comment="Full path to stored PDF file"
    )

    file_size_bytes: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        comment="File size in bytes"
    )

    total_pages: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Total number of pages in PDF"
    )

    # Metadata extracted from PDF
    title: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Paper/book title from metadata"
    )

    authors: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="List of author names"
    )

    publication_year: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        comment="Year of publication"
    )

    journal: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Journal or publisher name"
    )

    doi: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
        comment="Digital Object Identifier"
    )

    pmid: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        unique=True,
        index=True,
        comment="PubMed ID"
    )

    # Processing status flags
    indexing_status: Mapped[str] = mapped_column(
        String(50),
        default='pending',
        nullable=False,
        index=True,
        comment="Status: pending, processing, completed, failed"
    )

    text_extracted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether text extraction completed"
    )

    images_extracted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether image extraction completed"
    )

    embeddings_generated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether vector embeddings generated"
    )

    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
        comment="When PDF was uploaded"
    )

    indexed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="When indexing completed"
    )

    # Relationships
    images: Mapped[List["Image"]] = relationship(
        "Image",
        back_populates="pdf",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    citations: Mapped[List["Citation"]] = relationship(
        "Citation",
        back_populates="pdf",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<PDF(id={self.id}, filename='{self.filename}', status='{self.indexing_status}')>"

    def to_dict(self) -> dict:
        """Convert PDF to dictionary"""
        return {
            "id": str(self.id),
            "filename": self.filename,
            "file_size_bytes": self.file_size_bytes,
            "total_pages": self.total_pages,
            "title": self.title,
            "authors": self.authors,
            "publication_year": self.publication_year,
            "journal": self.journal,
            "doi": self.doi,
            "pmid": self.pmid,
            "indexing_status": self.indexing_status,
            "text_extracted": self.text_extracted,
            "images_extracted": self.images_extracted,
            "embeddings_generated": self.embeddings_generated,
            "uploaded_at": self.uploaded_at.isoformat(),
            "indexed_at": self.indexed_at.isoformat() if self.indexed_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "total_images": len(self.images) if self.images else 0,
            "total_citations": len(self.citations) if self.citations else 0
        }

    def is_fully_indexed(self) -> bool:
        """Check if PDF indexing is complete"""
        return (
            self.indexing_status == 'completed' and
            self.text_extracted and
            self.images_extracted and
            self.embeddings_generated
        )
