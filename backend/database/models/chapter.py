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

    # References/Citations
    references: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of reference objects (citations from all sources)"
    )

    # Metadata about structure
    structure_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Total sections, words, section types distribution"
    )

    # ==================== Workflow Stage Tracking ====================

    # Stage 1: Input Validation & Analysis
    stage_1_input: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Topic validation, chapter type analysis, confidence scores"
    )

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

    # Stage 10: Medical Fact-Checking
    stage_10_fact_check: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Fact-checking results: accuracy scores, verified claims, critical issues"
    )

    # Stage 11: Formatting & Structure
    stage_11_formatting: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Markdown validation results, table of contents, formatting statistics, structure validation"
    )

    # Stage 12: Quality Review & Refinement
    stage_12_review: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="AI-powered quality review: contradictions, readability issues, flow problems, improvement suggestions"
    )

    # ==================== Phase 2 Week 5: Comprehensive Gap Analysis ====================

    gap_analysis: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Phase 2 Week 5: Comprehensive gap analysis with identified gaps, severity distribution, recommendations, and completeness score"
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

    # ==================== Fact-Checking Status ====================

    fact_checked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether fact-checking has been performed (Stage 10)"
    )

    fact_check_passed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether fact-checking passed quality thresholds"
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

    # ==================== Granular Version History ====================
    # Relationship to chapter_versions table for granular edit history
    # This captures every edit/change with full content snapshots
    version_history: Mapped[List["ChapterVersion"]] = relationship(
        "ChapterVersion",
        back_populates="chapter",
        cascade="all, delete-orphan",
        order_by="desc(ChapterVersion.version_number)"
    )

    # ==================== AI Provider Metrics ====================
    # Relationship to AI provider metrics for performance tracking
    ai_metrics: Mapped[List["AIProviderMetric"]] = relationship(
        "AIProviderMetric",
        back_populates="chapter",
        foreign_keys="AIProviderMetric.chapter_id",
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
                "evidence": self.evidence_score,
                "overall": self.overall_quality_score,
                "rating": self.get_quality_rating()
            }

        # Generation confidence (Phase 22 Part 4)
        confidence = self.generation_confidence
        if confidence > 0:
            data["generation_confidence"] = {
                "overall": confidence,
                "rating": self.get_confidence_rating(),
                "breakdown": self.get_confidence_breakdown()
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

        # Phase 2 Week 5: Gap Analysis summary
        if self.gap_analysis:
            data["gap_analysis_summary"] = {
                "total_gaps": self.gap_analysis.get("total_gaps", 0),
                "critical_gaps": self.gap_analysis.get("severity_distribution", {}).get("critical", 0),
                "completeness_score": self.gap_analysis.get("overall_completeness_score", 0.0),
                "requires_revision": self.gap_analysis.get("requires_revision", False),
                "analyzed_at": self.gap_analysis.get("analyzed_at")
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

    def has_gap_analysis(self) -> bool:
        """Check if Phase 2 gap analysis has been performed"""
        return self.gap_analysis is not None

    def requires_gap_revision(self) -> bool:
        """Check if gap analysis indicates revision is required"""
        if not self.gap_analysis:
            return False
        return self.gap_analysis.get("requires_revision", False)

    def get_gap_completeness_score(self) -> float:
        """Get gap analysis completeness score (0-1)"""
        if not self.gap_analysis:
            return 1.0  # No analysis = assume complete
        return self.gap_analysis.get("overall_completeness_score", 1.0)

    @property
    def overall_quality_score(self) -> float:
        """
        Compute overall quality score from four dimensions

        Returns average of:
        - Depth score (0-1): Content depth and detail
        - Coverage score (0-1): Topic coverage completeness
        - Evidence score (0-1): Strength of evidence-based content
        - Currency score (0-1): Recency of literature cited

        Returns:
            Overall quality score (0.0 - 1.0), or 0.0 if no scores available
        """
        scores = []

        if self.depth_score is not None:
            scores.append(self.depth_score)
        if self.coverage_score is not None:
            scores.append(self.coverage_score)
        if self.evidence_score is not None:
            scores.append(self.evidence_score)
        if self.currency_score is not None:
            scores.append(self.currency_score)

        if not scores:
            return 0.0

        return sum(scores) / len(scores)

    def get_quality_rating(self) -> str:
        """
        Get quality rating as human-readable string

        Returns:
            "Excellent" (90-100%), "Good" (75-89%), "Fair" (60-74%), or "Needs Improvement" (<60%)
        """
        score = self.overall_quality_score
        percentage = score * 100

        if percentage >= 90:
            return "Excellent"
        elif percentage >= 75:
            return "Good"
        elif percentage >= 60:
            return "Fair"
        else:
            return "Needs Improvement"

    @property
    def generation_confidence(self) -> float:
        """
        Compute overall generation confidence from three stages

        Weighted combination:
        - Stage 1 (Analysis): 20% weight - Confidence in topic analysis and classification
        - Stage 2 (Research Context): 30% weight - Confidence in available research quality
        - Stage 10 (Fact-Check): 50% weight - Accuracy of medical claims verification

        Returns:
            Generation confidence score (0.0 - 1.0), or 0.0 if no data available
        """
        confidences = []
        weights = []

        # Stage 1: Analysis confidence (20% weight)
        if self.stage_1_input:
            analysis = self.stage_1_input.get("analysis", {})
            analysis_confidence = analysis.get("analysis_confidence")
            if analysis_confidence is not None:
                confidences.append(float(analysis_confidence))
                weights.append(0.2)

        # Stage 2: Research context confidence (30% weight)
        if self.stage_2_context:
            context = self.stage_2_context.get("context", {})
            confidence_assessment = context.get("confidence_assessment", {})
            context_confidence = confidence_assessment.get("overall_confidence")
            if context_confidence is not None:
                confidences.append(float(context_confidence))
                weights.append(0.3)

        # Stage 10: Fact-check accuracy (50% weight)
        if self.stage_10_fact_check:
            fact_check_data = self.stage_10_fact_check.get("fact_check_data", {})
            fact_check_accuracy = fact_check_data.get("overall_accuracy")
            if fact_check_accuracy is not None:
                confidences.append(float(fact_check_accuracy))
                weights.append(0.5)

        # If no confidence data available, return 0.0
        if not confidences:
            return 0.0

        # Calculate weighted average
        total_weight = sum(weights)
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(c * w for c, w in zip(confidences, weights))
        return weighted_sum / total_weight

    def get_confidence_breakdown(self) -> dict:
        """
        Get detailed breakdown of confidence scores

        Returns:
            Dictionary with individual confidence scores and their contributions
        """
        breakdown = {
            "overall": self.generation_confidence,
            "components": {}
        }

        # Stage 1: Analysis confidence
        if self.stage_1_input:
            analysis = self.stage_1_input.get("analysis", {})
            analysis_confidence = analysis.get("analysis_confidence")
            if analysis_confidence is not None:
                breakdown["components"]["analysis"] = {
                    "score": float(analysis_confidence),
                    "weight": 0.2,
                    "contribution": float(analysis_confidence) * 0.2,
                    "description": "Topic analysis and classification confidence"
                }

        # Stage 2: Research context confidence
        if self.stage_2_context:
            context = self.stage_2_context.get("context", {})
            confidence_assessment = context.get("confidence_assessment", {})
            context_confidence = confidence_assessment.get("overall_confidence")
            evidence_quality = confidence_assessment.get("evidence_quality", "unknown")
            if context_confidence is not None:
                breakdown["components"]["research"] = {
                    "score": float(context_confidence),
                    "weight": 0.3,
                    "contribution": float(context_confidence) * 0.3,
                    "description": f"Research availability and quality ({evidence_quality})"
                }

        # Stage 10: Fact-check accuracy
        if self.stage_10_fact_check:
            fact_check_data = self.stage_10_fact_check.get("fact_check_data", {})
            fact_check_accuracy = fact_check_data.get("overall_accuracy")
            verified_count = len([c for c in fact_check_data.get("claims", []) if c.get("verified", False)])
            total_claims = len(fact_check_data.get("claims", []))
            if fact_check_accuracy is not None:
                breakdown["components"]["fact_check"] = {
                    "score": float(fact_check_accuracy),
                    "weight": 0.5,
                    "contribution": float(fact_check_accuracy) * 0.5,
                    "description": f"Medical accuracy ({verified_count}/{total_claims} claims verified)"
                }

        return breakdown

    def get_confidence_rating(self) -> str:
        """
        Get confidence rating as human-readable string

        Returns:
            "Very High" (90-100%), "High" (75-89%), "Moderate" (60-74%), or "Low" (<60%)
        """
        score = self.generation_confidence
        percentage = score * 100

        if percentage >= 90:
            return "Very High"
        elif percentage >= 75:
            return "High"
        elif percentage >= 60:
            return "Moderate"
        else:
            return "Low"
