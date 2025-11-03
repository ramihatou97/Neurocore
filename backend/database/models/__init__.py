"""
Database models package
Exports all SQLAlchemy models for the Neurosurgery Knowledge Base
"""

from backend.database.base import Base, TimestampMixin, UUIDMixin
from backend.database.models.user import User
from backend.database.models.pdf import PDF
from backend.database.models.chapter import Chapter
from backend.database.models.chapter_version import ChapterVersion
from backend.database.models.image import Image
from backend.database.models.citation import Citation
from backend.database.models.cache_analytics import CacheAnalytics
from backend.database.models.task import Task
from backend.database.models.export_template import ExportTemplate, CitationStyle, ExportHistory
from backend.database.models.ai_provider_metric import AIProviderMetric

# Chapter-level vector search models (Phase 2)
from backend.database.models.pdf_book import PDFBook
from backend.database.models.pdf_chapter import PDFChapter
from backend.database.models.pdf_chunk import PDFChunk

__all__ = [
    # Base classes
    "Base",
    "TimestampMixin",
    "UUIDMixin",

    # Models
    "User",
    "PDF",
    "Chapter",
    "ChapterVersion",
    "Image",
    "Citation",
    "CacheAnalytics",
    "Task",
    "ExportTemplate",
    "CitationStyle",
    "ExportHistory",
    "AIProviderMetric",

    # Chapter-level vector search models
    "PDFBook",
    "PDFChapter",
    "PDFChunk",
]
