"""
Chapter model for generated neurosurgery chapters
Core of Process B: User-Requested Chapter Generation (14-stage workflow)
"""

from sqlalchemy import String, Float, Boolean, ForeignKey, Text, ARRAY
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional, Dict, Any
import uuid
from backend.database.base import Base, UUIDMixin, TimestampMixin


class Chapter(Base, UUIDMixin, TimestampMixin):
    """
    Chapter model tracking the complete 14-stage workflow

    Process B Stages:
    - Stage 1: Authentication & Authorization
    - Stage 2: Context Intelligence (stored in stage_2_context)
    - Stage 3: Internal Research (stored in stage_3_internal_research)
    - Stage 4: External Research (stored in stage_4_external_research)
    - Stage 5: Primary Synthesis (stored in stage_5_synthesis_metadata)
    - Stage 6: Smart Gap Detection (stored in stage_6_gaps_detected)
    - Stage 7: Decision Point
    - Stage 8: Document Integration (stored in stage_8_integration_log)
    - Stage 9: Secondary Enrichment
    - Stage 10: Summary
    - Stages 11-14: Alive Chapter features

    The chapter evolves through versions, with each significant change creating a new version.
    """

    __tablename__ = "chapters"

    # Basic Information
    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Chapter title"
    )

    chapter_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Type: surgical_disease, pure_anatomy, surgical_technique"
    )

    # Content (JSONB for flexibility)
    # Structure: [{"section_num": 1, "title": "Introduction", "content": "...", "word_count": 500, "images": [image_ids]}]
    sections: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of section objects with content"
    )

    # Metadata about structure
    structure_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Total sections, words, section types distribution"
    )

    # ==================== Workflow Stage Tracking ====================

    # Stage 2: Context Intelligence
    stage_2_context: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Medical entities extracted, chapter type reasoning"
    )

    # Stage 3: Internal Research (Vector Search)
    stage_3_internal_research: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Sources from indexed library, relevance scores, cached queries"
    )

    # Stage 4: External Research (PubMed, Scholar, arXiv)
    stage_4_external_research: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="External research results, PubMed papers, Scholar articles"
    )

    # Stage 5: Primary Synthesis (Main content generation)
    stage_5_synthesis_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="AI provider used, tokens consumed, cost, quality scores, generation time"
    )

    # Stage 6: Smart Gap Detection
    stage_6_gaps_detected: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Detected gaps: coverage, user demand, literature currency, semantic completeness"
    )

    # Stage 8: Document Integration (if user provided documents)
    stage_8_integration_log: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Documents integrated, conflicts resolved, nuance merge results"
    )

    # ==================== Quality Scores ====================

    depth_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Depth of content coverage (0.0 - 1.0)"
    )

    coverage_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Topic coverage completeness (0.0 - 1.0)"
    )

    currency_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Recency of literature cited (0.0 - 1.0)"
    )

    evidence_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Strength of evidence-based content (0.0 - 1.0)"
    )

    # ==================== Version Control ====================

    version: Mapped[str] = mapped_column(
        String(20),
        default='1.0',
        nullable=False,
        comment="Semantic version: 1.0, 1.1, 1.2, etc."
    )

    is_current_version: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether this is the latest version"
    )

    parent_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('chapters.id', ondelete='SET NULL'),
        nullable=True,
        comment="Parent version for version history"
    )

    # ==================== Status ====================

    generation_status: Mapped[str] = mapped_column(
        String(50),
        default='draft',
        nullable=False,
        index=True,
        comment="Status: draft, in_progress, completed, failed"
    )

    # ==================== Foreign Keys ====================

    author_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="User who requested this chapter"
    )

    # ==================== Relationships ====================

    author: Mapped["User"] = relationship(
        "User",
        back_populates="chapters"
    )

    # Self-referential relationship for version history
    # Note: 'versions' represents child versions of this chapter
    # 'parent_version' represents the parent version of this chapter

    parent_version: Mapped[Optional["Chapter"]] = relationship(
        "Chapter",
        remote_side="Chapter.id",
        foreign_keys=[parent_version_id],
        back_populates="versions",
        post_update=True
    )

    versions: Mapped[List["Chapter"]] = relationship(
        "Chapter",
        foreign_keys="Chapter.parent_version_id",
        back_populates="parent_version",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Chapter(id={self.id}, title='{self.title[:50]}...', version='{self.version}', status='{self.generation_status}')>"

    def to_dict(self, include_content: bool = True) -> dict:
        """Convert chapter to dictionary

        Args:
            include_content: Whether to include full section content (can be large)
        """
        data = {
            "id": str(self.id),
            "title": self.title,
            "chapter_type": self.chapter_type,
            "version": self.version,
            "is_current_version": self.is_current_version,
            "generation_status": self.generation_status,
            "author_id": str(self.author_id),
            "parent_version_id": str(self.parent_version_id) if self.parent_version_id else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

        # Quality scores
        if self.depth_score is not None:
            data["quality_scores"] = {
                "depth": self.depth_score,
                "coverage": self.coverage_score,
                "currency": self.currency_score,
                "evidence": self.evidence_score
            }

        # Structure metadata
        if self.structure_metadata:
            data["structure_metadata"] = self.structure_metadata

        # Content (optional, can be large)
        if include_content and self.sections:
            data["sections"] = self.sections
            # Calculate stats
            total_words = sum(s.get("word_count", 0) for s in self.sections if isinstance(self.sections, list))
            data["total_words"] = total_words
            data["total_sections"] = len(self.sections) if isinstance(self.sections, list) else 0

        # Workflow stage data (summary only)
        data["workflow_stages"] = {
            "context_intelligence": self.stage_2_context is not None,
            "internal_research": self.stage_3_internal_research is not None,
            "external_research": self.stage_4_external_research is not None,
            "synthesis": self.stage_5_synthesis_metadata is not None,
            "gaps_detected": self.stage_6_gaps_detected is not None,
            "documents_integrated": self.stage_8_integration_log is not None
        }

        return data

    def get_word_count(self) -> int:
        """Calculate total word count across all sections"""
        if not self.sections or not isinstance(self.sections, list):
            return 0
        return sum(section.get("word_count", 0) for section in self.sections)

    def get_section_count(self) -> int:
        """Get total number of sections"""
        if not self.sections or not isinstance(self.sections, list):
            return 0
        return len(self.sections)

    def is_completed(self) -> bool:
        """Check if chapter generation is completed"""
        return self.generation_status == 'completed'

    def has_gaps(self) -> bool:
        """Check if any gaps were detected"""
        if not self.stage_6_gaps_detected:
            return False
        gaps = self.stage_6_gaps_detected.get("gaps", [])
        return len(gaps) > 0
