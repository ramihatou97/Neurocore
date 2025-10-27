"""
Database package
Provides database models, connection management, and session handling
"""

from backend.database.base import Base, TimestampMixin, UUIDMixin
from backend.database.connection import db, get_db, DatabaseConnection
from backend.database.models import (
    User,
    PDF,
    Chapter,
    Image,
    Citation,
    CacheAnalytics
)

__all__ = [
    # Base classes
    "Base",
    "TimestampMixin",
    "UUIDMixin",

    # Connection
    "db",
    "get_db",
    "DatabaseConnection",

    # Models
    "User",
    "PDF",
    "Chapter",
    "Image",
    "Citation",
    "CacheAnalytics",
]
