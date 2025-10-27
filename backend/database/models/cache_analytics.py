"""
CacheAnalytics model for tracking cache performance and cost savings
Supports hybrid smart caching with 40-65% cost reduction goal
"""

from sqlalchemy import String, Integer, ForeignKey, Numeric, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
import uuid
from datetime import datetime
from backend.database.base import Base, UUIDMixin


class CacheAnalytics(Base, UUIDMixin):
    """
    CacheAnalytics model for observability and cost tracking

    Tracks:
    - Cache hit/miss rates by type (hot/cold)
    - Cache hit/miss rates by category (embedding, query, synthesis, pattern)
    - Cost savings from cache usage
    - Time savings from cache usage
    - User-level cache performance
    """

    __tablename__ = "cache_analytics"

    # ==================== Cache Type & Category ====================

    cache_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Cache tier: 'hot' (in-memory) or 'cold' (Redis)"
    )

    cache_category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Category: 'embedding', 'template', 'structure', 'query', 'synthesis', 'pattern'"
    )

    # ==================== Operation ====================

    operation: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
        comment="Operation: 'hit', 'miss', 'set'"
    )

    # ==================== Key Information ====================

    key_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="SHA-256 hash of cache key (for privacy and deduplication)"
    )

    # ==================== Performance Metrics ====================

    cost_saved_usd: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4),
        nullable=True,
        comment="Cost saved by cache hit (in USD)"
    )

    time_saved_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Time saved by cache hit (in milliseconds)"
    )

    # ==================== Context (Optional Foreign Keys) ====================

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=True,
        index=True,
        comment="User who triggered this cache operation"
    )

    chapter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('chapters.id', ondelete='CASCADE'),
        nullable=True,
        index=True,
        comment="Chapter associated with this cache operation"
    )

    # ==================== Timestamp ====================

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
        comment="When this cache operation occurred"
    )

    # ==================== Relationships ====================

    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[user_id]
    )

    chapter: Mapped[Optional["Chapter"]] = relationship(
        "Chapter",
        foreign_keys=[chapter_id]
    )

    def __repr__(self) -> str:
        return f"<CacheAnalytics(type='{self.cache_type}', category='{self.cache_category}', operation='{self.operation}', cost_saved=${self.cost_saved_usd})>"

    def to_dict(self) -> dict:
        """Convert cache analytics to dictionary"""
        return {
            "id": str(self.id),
            "cache_type": self.cache_type,
            "cache_category": self.cache_category,
            "operation": self.operation,
            "key_hash": self.key_hash,
            "cost_saved_usd": float(self.cost_saved_usd) if self.cost_saved_usd else None,
            "time_saved_ms": self.time_saved_ms,
            "user_id": str(self.user_id) if self.user_id else None,
            "chapter_id": str(self.chapter_id) if self.chapter_id else None,
            "recorded_at": self.recorded_at.isoformat()
        }

    def is_hit(self) -> bool:
        """Check if this was a cache hit"""
        return self.operation == 'hit'

    def is_miss(self) -> bool:
        """Check if this was a cache miss"""
        return self.operation == 'miss'

    def is_hot_cache(self) -> bool:
        """Check if this was from hot (in-memory) cache"""
        return self.cache_type == 'hot'

    def is_cold_cache(self) -> bool:
        """Check if this was from cold (Redis) cache"""
        return self.cache_type == 'cold'
