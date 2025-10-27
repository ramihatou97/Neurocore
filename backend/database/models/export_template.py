"""
Export Template Model
Stores templates for PDF/DOCX/HTML export
"""

from sqlalchemy import Column, String, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from backend.database.base import Base


class ExportTemplate(Base):
    """
    Export Template Model - Templates for chapter export

    Stores reusable templates for exporting chapters to various formats
    """

    __tablename__ = "export_templates"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Template details
    name = Column(String(200), nullable=False)
    description = Column(Text)
    format = Column(String(20), nullable=False, index=True)  # pdf, docx, html

    # Template content
    template_content = Column(Text, nullable=False)
    styles = Column(JSONB, default={})
    required_variables = Column(JSONB, default=[])

    # Ownership and visibility
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    is_default = Column(Boolean, default=False)
    is_public = Column(Boolean, default=False, index=True)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    export_history = relationship("ExportHistory", back_populates="template")

    def __repr__(self):
        return f"<ExportTemplate(name='{self.name}', format='{self.format}')>"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "format": self.format,
            "template_content": self.template_content,
            "styles": self.styles,
            "required_variables": self.required_variables,
            "created_by": str(self.created_by) if self.created_by else None,
            "is_default": self.is_default,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CitationStyle(Base):
    """
    Citation Style Model - Citation formatting styles

    Stores citation formatting rules for different academic styles
    """

    __tablename__ = "citation_styles"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Style details
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text)
    format_template = Column(JSONB, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, index=True)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    export_history = relationship("ExportHistory", back_populates="citation_style")

    def __repr__(self):
        return f"<CitationStyle(name='{self.name}', display_name='{self.display_name}')>"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "format_template": self.format_template,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ExportHistory(Base):
    """
    Export History Model - Tracks chapter exports

    Records each export operation for auditing and analytics
    """

    __tablename__ = "export_history"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey("export_templates.id", ondelete="SET NULL"))
    citation_style_id = Column(UUID(as_uuid=True), ForeignKey("citation_styles.id", ondelete="SET NULL"))

    # Export details
    export_format = Column(String(20), nullable=False)
    file_name = Column(String(500), nullable=False)
    file_size = Column(String(50))
    file_path = Column(Text)

    # Options
    export_options = Column(JSONB, default={})

    # Status
    status = Column(String(50), default="pending", index=True)
    error_message = Column(Text)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    completed_at = Column(TIMESTAMP(timezone=True))

    # Relationships
    chapter = relationship("Chapter")
    user = relationship("User")
    template = relationship("ExportTemplate", back_populates="export_history")
    citation_style = relationship("CitationStyle", back_populates="export_history")

    def __repr__(self):
        return f"<ExportHistory(chapter_id={self.chapter_id}, format='{self.export_format}', status='{self.status}')>"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "chapter_id": str(self.chapter_id),
            "user_id": str(self.user_id),
            "template_id": str(self.template_id) if self.template_id else None,
            "citation_style_id": str(self.citation_style_id) if self.citation_style_id else None,
            "export_format": self.export_format,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "file_path": self.file_path,
            "export_options": self.export_options,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
