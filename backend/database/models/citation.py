"""
Citation model for extracted references from PDFs
Part of Process A: Background PDF Indexation - Citation Network Building
"""

from sqlalchemy import String, Integer, Float, ForeignKey, Text, ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
import uuid
from backend.database.base import Base, UUIDMixin, TimestampMixin


class Citation(Base, UUIDMixin, TimestampMixin):
    """
    Citation model tracking bibliographic references

    Extracted from PDFs to build a citation network:
    - Track which papers cite which papers
    - Calculate citation counts
    - Determine relevance scores
    - Enable literature network analysis
    """

    __tablename__ = "citations"

    # ==================== Source Information ====================

    pdf_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('pdfs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="PDF that contains this citation"
    )

    # ==================== Cited Work Metadata ====================

    cited_title: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Title of the cited work"
    )

    cited_authors: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="List of authors of cited work"
    )

    cited_journal: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Journal or publication venue"
    )

    cited_year: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        comment="Publication year of cited work"
    )

    cited_doi: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="DOI of cited work"
    )

    cited_pmid: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="PubMed ID of cited work"
    )

    # ==================== Context Information ====================

    citation_context: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Surrounding text where citation appears (for context)"
    )

    page_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Page number where citation appears"
    )

    # ==================== Network Analysis ====================

    citation_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of times this work has been cited across all PDFs"
    )

    relevance_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Relevance score based on citation frequency and recency (0.0 - 1.0)"
    )

    # ==================== Relationships ====================

    pdf: Mapped["PDF"] = relationship(
        "PDF",
        back_populates="citations"
    )

    def __repr__(self) -> str:
        title_preview = self.cited_title[:50] if self.cited_title else "Unknown"
        return f"<Citation(id={self.id}, title='{title_preview}...', year={self.cited_year})>"

    def to_dict(self) -> dict:
        """Convert citation to dictionary"""
        return {
            "id": str(self.id),
            "pdf_id": str(self.pdf_id),
            "cited_work": {
                "title": self.cited_title,
                "authors": self.cited_authors,
                "journal": self.cited_journal,
                "year": self.cited_year,
                "doi": self.cited_doi,
                "pmid": self.cited_pmid
            },
            "context": {
                "citation_context": self.citation_context,
                "page_number": self.page_number
            },
            "network_analysis": {
                "citation_count": self.citation_count,
                "relevance_score": self.relevance_score
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    def has_doi_or_pmid(self) -> bool:
        """Check if citation has identifiable DOI or PMID"""
        return bool(self.cited_doi or self.cited_pmid)

    def is_recent(self, years_threshold: int = 5) -> bool:
        """Check if citation is recent (within threshold years)"""
        if not self.cited_year:
            return False
        from datetime import datetime
        current_year = datetime.utcnow().year
        return (current_year - self.cited_year) <= years_threshold
