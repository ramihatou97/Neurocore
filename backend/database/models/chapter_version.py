"""
Chapter Version Model
Stores historical snapshots of chapter content for version tracking
"""

from sqlalchemy import Column, String, Integer, Text, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from backend.database.base import Base


class ChapterVersion(Base):
    """
    Chapter Version Model - Historical snapshots of chapters

    Stores complete snapshots of chapter content at different points in time,
    enabling version tracking, comparison, and rollback functionality.
    """

    __tablename__ = "chapter_versions"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    changed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)

    # Version tracking
    version_number = Column(Integer, nullable=False)

    # Content snapshot
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text)

    # Version metadata (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    version_metadata = Column(JSONB, default={})
    word_count = Column(Integer)
    character_count = Column(Integer)
    change_size = Column(Integer, default=0)  # Net characters added/removed

    # Change attribution
    change_description = Column(Text)
    change_type = Column(String(50), default="update", index=True)  # update, rollback, major_edit, initial

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    chapter = relationship("Chapter", back_populates="version_history")
    user = relationship("User", foreign_keys=[changed_by])

    # Constraints
    __table_args__ = (
        UniqueConstraint("chapter_id", "version_number", name="unique_chapter_version"),
        CheckConstraint("version_number > 0", name="positive_version_number"),
    )

    def __repr__(self):
        return f"<ChapterVersion(chapter_id={self.chapter_id}, version={self.version_number}, changed_by={self.changed_by})>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "chapter_id": str(self.chapter_id),
            "version_number": self.version_number,
            "title": self.title,
            "content": self.content,
            "summary": self.summary,
            "metadata": self.version_metadata,
            "word_count": self.word_count,
            "character_count": self.character_count,
            "change_size": self.change_size,
            "changed_by": str(self.changed_by) if self.changed_by else None,
            "change_description": self.change_description,
            "change_type": self.change_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def to_summary_dict(self):
        """Convert to summary dictionary (without full content)"""
        return {
            "id": str(self.id),
            "chapter_id": str(self.chapter_id),
            "version_number": self.version_number,
            "title": self.title,
            "summary": self.summary,
            "word_count": self.word_count,
            "character_count": self.character_count,
            "change_size": self.change_size,
            "changed_by": str(self.changed_by) if self.changed_by else None,
            "change_description": self.change_description,
            "change_type": self.change_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
