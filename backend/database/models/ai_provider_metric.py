"""
AI Provider Metrics Model
Tracks performance, quality, and costs for all AI provider calls
"""

from sqlalchemy import Column, String, Boolean, Integer, DECIMAL, Text, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from backend.database.base import Base


class AIProviderMetric(Base):
    """
    Tracks AI provider performance and accuracy metrics

    Records every AI provider call with:
    - Performance: response time, success/failure
    - Quality: quality scores, confidence scores
    - Cost: tokens used, USD cost
    - Errors: parse failures, validation failures
    - Fallback: was this a fallback provider?
    """

    __tablename__ = "ai_provider_metrics"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Provider Information
    provider = Column(String(50), nullable=False, index=True)
    model = Column(String(100), nullable=False)
    task_type = Column(String(100), nullable=False, index=True)

    # Request Details
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=True, index=True)
    image_id = Column(UUID(as_uuid=True), ForeignKey("images.id", ondelete="CASCADE"), nullable=True, index=True)
    request_timestamp = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, index=True)

    # Performance Metrics
    success = Column(Boolean, nullable=False, index=True)
    response_time_ms = Column(Integer, nullable=True)

    # Quality Metrics
    quality_score = Column(DECIMAL(4, 3), nullable=True)
    confidence_score = Column(DECIMAL(4, 3), nullable=True)

    # Token & Cost Tracking
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    cost_usd = Column(DECIMAL(10, 6), nullable=True)

    # Output Quality
    json_parse_success = Column(Boolean, nullable=True)
    output_validated = Column(Boolean, nullable=True)

    # Error Tracking
    error_type = Column(String(100), nullable=True, index=True)
    error_message = Column(Text, nullable=True)

    # Fallback Tracking
    was_fallback = Column(Boolean, default=False)
    original_provider = Column(String(50), nullable=True)
    fallback_reason = Column(String(200), nullable=True)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    # Relationships
    chapter = relationship("Chapter", back_populates="ai_metrics", foreign_keys=[chapter_id])
    image = relationship("Image", back_populates="ai_metrics", foreign_keys=[image_id])

    def __repr__(self):
        return (
            f"<AIProviderMetric(provider={self.provider}, task={self.task_type}, "
            f"success={self.success}, quality={self.quality_score})>"
        )

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "provider": self.provider,
            "model": self.model,
            "task_type": self.task_type,
            "chapter_id": str(self.chapter_id) if self.chapter_id else None,
            "image_id": str(self.image_id) if self.image_id else None,
            "request_timestamp": self.request_timestamp.isoformat() if self.request_timestamp else None,
            "success": self.success,
            "response_time_ms": self.response_time_ms,
            "quality_score": float(self.quality_score) if self.quality_score else None,
            "confidence_score": float(self.confidence_score) if self.confidence_score else None,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": float(self.cost_usd) if self.cost_usd else None,
            "json_parse_success": self.json_parse_success,
            "output_validated": self.output_validated,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "was_fallback": self.was_fallback,
            "original_provider": self.original_provider,
            "fallback_reason": self.fallback_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
