"""
API routes package
"""

from backend.api import auth_routes, pdf_routes, chapter_routes

__all__ = [
    "auth_routes",
    "pdf_routes",
    "chapter_routes",
]
