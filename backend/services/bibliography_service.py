"""
Bibliography Service - Automatic Bibliography Generation
Generates formatted bibliographies from citations
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.database.models import Citation, Chapter
from backend.services.citation_service import CitationService
from backend.utils import get_logger

logger = get_logger(__name__)


class BibliographyService:
    """
    Service for generating bibliographies

    Provides:
    - Automatic bibliography generation from chapter citations
    - Multiple sorting options (alphabetical, chronological, appearance)
    - Citation grouping
    - Duplicate detection
    """

    def __init__(self, db: Session):
        """
        Initialize bibliography service

        Args:
            db: Database session
        """
        self.db = db
        self.citation_service = CitationService(db)

    def generate_bibliography(
        self,
        chapter: Chapter,
        style_name: str = "apa",
        sort_by: str = "author",
        include_in_text_markers: bool = False
    ) -> Dict[str, Any]:
        """
        Generate complete bibliography for a chapter

        Args:
            chapter: Chapter to generate bibliography for
            style_name: Citation style (apa, mla, chicago, vancouver)
            sort_by: Sorting method ('author', 'year', 'appearance')
            include_in_text_markers: Include in-text citation markers

        Returns:
            Dictionary with formatted bibliography
        """
        try:
            # Extract citations from chapter
            citations = self.citation_service.extract_citations_from_chapter(chapter)

            if not citations:
                return {
                    "bibliography": [],
                    "count": 0,
                    "style": style_name,
                    "message": "No citations found in chapter"
                }

            # Sort citations
            sorted_citations = self._sort_citations(citations, sort_by)

            # Format citations
            formatted_bibliography = []

            for i, citation in enumerate(sorted_citations, start=1):
                formatted = self.citation_service.format_citation(
                    citation,
                    style_name,
                    "bibliography"
                )

                entry = {
                    "index": i,
                    "citation_id": str(citation.id),
                    "formatted": formatted,
                    "citation": citation.to_dict() if hasattr(citation, 'to_dict') else {}
                }

                # Add in-text marker if needed
                if include_in_text_markers:
                    in_text = self.citation_service.format_citation(
                        citation,
                        style_name,
                        "in_text"
                    )
                    entry["in_text_marker"] = in_text

                formatted_bibliography.append(entry)

            return {
                "bibliography": formatted_bibliography,
                "count": len(formatted_bibliography),
                "style": style_name,
                "sort_by": sort_by
            }

        except Exception as e:
            logger.error(f"Failed to generate bibliography: {str(e)}")
            return {
                "bibliography": [],
                "count": 0,
                "error": str(e)
            }

    def _sort_citations(
        self,
        citations: List[Citation],
        sort_by: str
    ) -> List[Citation]:
        """
        Sort citations according to specified method

        Args:
            citations: List of citations to sort
            sort_by: Sorting method

        Returns:
            Sorted list of citations
        """
        try:
            if sort_by == "author":
                return sorted(
                    citations,
                    key=lambda c: (c.authors or "").lower()
                )
            elif sort_by == "year":
                return sorted(
                    citations,
                    key=lambda c: c.year or 0,
                    reverse=True
                )
            elif sort_by == "appearance":
                # Keep original order (order of appearance in text)
                return citations
            else:
                # Default to author sort
                return sorted(
                    citations,
                    key=lambda c: (c.authors or "").lower()
                )

        except Exception as e:
            logger.error(f"Failed to sort citations: {str(e)}")
            return citations

    def detect_duplicate_citations(
        self,
        citations: List[Citation]
    ) -> Dict[str, Any]:
        """
        Detect duplicate citations

        Args:
            citations: List of citations to check

        Returns:
            Dictionary with duplicate information
        """
        try:
            seen = {}
            duplicates = []

            for citation in citations:
                # Create a key based on authors, year, and title
                key = f"{(citation.authors or '').lower()}_{citation.year}_{(citation.title or '').lower()}"

                if key in seen:
                    duplicates.append({
                        "citation_id": str(citation.id),
                        "duplicate_of": str(seen[key].id),
                        "citation": citation.to_dict() if hasattr(citation, 'to_dict') else {}
                    })
                else:
                    seen[key] = citation

            return {
                "has_duplicates": len(duplicates) > 0,
                "duplicate_count": len(duplicates),
                "duplicates": duplicates
            }

        except Exception as e:
            logger.error(f"Failed to detect duplicates: {str(e)}")
            return {
                "has_duplicates": False,
                "duplicate_count": 0,
                "duplicates": []
            }

    def group_citations_by_year(
        self,
        citations: List[Citation]
    ) -> Dict[str, List[Citation]]:
        """
        Group citations by publication year

        Args:
            citations: List of citations

        Returns:
            Dictionary mapping years to citations
        """
        try:
            grouped = {}

            for citation in citations:
                year = citation.year or "Unknown"
                if year not in grouped:
                    grouped[year] = []
                grouped[year].append(citation)

            return grouped

        except Exception as e:
            logger.error(f"Failed to group citations: {str(e)}")
            return {}

    def generate_citation_summary(
        self,
        chapter: Chapter
    ) -> Dict[str, Any]:
        """
        Generate summary statistics about chapter citations

        Args:
            chapter: Chapter to analyze

        Returns:
            Dictionary with citation statistics
        """
        try:
            citations = self.citation_service.extract_citations_from_chapter(chapter)

            if not citations:
                return {
                    "total_citations": 0,
                    "year_range": None,
                    "average_year": None,
                    "journals": [],
                    "completeness": 0
                }

            # Calculate statistics
            years = [c.year for c in citations if c.year]
            journals = list(set([c.journal for c in citations if c.journal]))

            # Calculate completeness
            complete_count = sum(
                1 for c in citations
                if self.citation_service.validate_citation_completeness(c)["is_complete"]
            )

            return {
                "total_citations": len(citations),
                "year_range": {
                    "oldest": min(years) if years else None,
                    "newest": max(years) if years else None
                },
                "average_year": sum(years) / len(years) if years else None,
                "journals": journals,
                "journal_count": len(journals),
                "completeness": (complete_count / len(citations)) * 100 if citations else 0
            }

        except Exception as e:
            logger.error(f"Failed to generate citation summary: {str(e)}")
            return {
                "total_citations": 0,
                "error": str(e)
            }

    def format_bibliography_html(
        self,
        bibliography: List[Dict[str, Any]],
        style: str = "default"
    ) -> str:
        """
        Format bibliography as HTML

        Args:
            bibliography: Formatted bibliography entries
            style: HTML style (default, numbered, hanging)

        Returns:
            HTML string
        """
        try:
            if not bibliography:
                return "<p>No references found.</p>"

            html_parts = ['<div class="bibliography">']

            if style == "numbered":
                html_parts.append('<ol class="bibliography-list">')
                for entry in bibliography:
                    html_parts.append(f'<li>{entry["formatted"]}</li>')
                html_parts.append('</ol>')

            elif style == "hanging":
                html_parts.append('<div class="bibliography-list hanging-indent">')
                for entry in bibliography:
                    html_parts.append(
                        f'<p class="citation-entry">{entry["formatted"]}</p>'
                    )
                html_parts.append('</div>')

            else:  # default
                html_parts.append('<div class="bibliography-list">')
                for entry in bibliography:
                    html_parts.append(
                        f'<p class="citation-entry">{entry["formatted"]}</p>'
                    )
                html_parts.append('</div>')

            html_parts.append('</div>')

            return '\n'.join(html_parts)

        except Exception as e:
            logger.error(f"Failed to format bibliography as HTML: {str(e)}")
            return "<p>Error formatting bibliography.</p>"
