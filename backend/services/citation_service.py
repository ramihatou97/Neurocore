"""
Citation Service - Citation Management and Formatting
Handles citation extraction, formatting, and style application
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import re

from backend.database.models import Citation, CitationStyle, Chapter
from backend.utils import get_logger

logger = get_logger(__name__)


class CitationService:
    """
    Service for managing and formatting citations

    Provides:
    - Citation extraction from content
    - Multiple citation style formatting (APA, MLA, Chicago, Vancouver)
    - In-text citation generation
    - Bibliography formatting
    """

    def __init__(self, db: Session):
        """
        Initialize citation service

        Args:
            db: Database session
        """
        self.db = db

    def get_citation_style(self, style_name: str) -> Optional[CitationStyle]:
        """
        Get citation style by name

        Args:
            style_name: Citation style name (apa, mla, chicago, vancouver)

        Returns:
            CitationStyle object or None
        """
        try:
            style = self.db.query(CitationStyle).filter(
                CitationStyle.name == style_name.lower(),
                CitationStyle.is_active == True
            ).first()

            return style

        except Exception as e:
            logger.error(f"Failed to get citation style {style_name}: {str(e)}")
            return None

    def get_all_citation_styles(self) -> List[Dict[str, Any]]:
        """
        Get all available citation styles

        Returns:
            List of citation styles
        """
        try:
            styles = self.db.query(CitationStyle).filter(
                CitationStyle.is_active == True
            ).all()

            return [style.to_dict() for style in styles]

        except Exception as e:
            logger.error(f"Failed to get citation styles: {str(e)}")
            return []

    def extract_citations_from_chapter(self, chapter: Chapter) -> List[Citation]:
        """
        Extract citations from chapter content

        Looks for citation markers in content like [1], [Smith et al., 2020]

        Args:
            chapter: Chapter to extract citations from

        Returns:
            List of Citation objects
        """
        try:
            citations = []

            # Get all citations referenced in this chapter
            # In a real implementation, this would parse the content
            # and extract citation markers, then look them up in the database

            # For now, get citations associated with the chapter via relationships
            if hasattr(chapter, 'citations'):
                citations = chapter.citations

            return citations

        except Exception as e:
            logger.error(f"Failed to extract citations from chapter {chapter.id}: {str(e)}")
            return []

    def format_citation(
        self,
        citation: Citation,
        style_name: str = "apa",
        format_type: str = "bibliography"
    ) -> str:
        """
        Format a citation according to specified style

        Args:
            citation: Citation object
            style_name: Citation style (apa, mla, chicago, vancouver)
            format_type: 'bibliography' or 'in_text'

        Returns:
            Formatted citation string
        """
        try:
            style = self.get_citation_style(style_name)
            if not style:
                return self._format_citation_default(citation)

            if format_type == "in_text":
                return self._format_in_text_citation(citation, style)
            else:
                return self._format_bibliography_citation(citation, style)

        except Exception as e:
            logger.error(f"Failed to format citation: {str(e)}")
            return self._format_citation_default(citation)

    def _format_bibliography_citation(
        self,
        citation: Citation,
        style: CitationStyle
    ) -> str:
        """Format citation for bibliography"""
        try:
            template = style.format_template.get("bibliography", "")

            # Extract citation data
            data = {
                "authors": self._format_authors(
                    citation.authors,
                    style.format_template.get("author_separator", ", "),
                    style.format_template.get("et_al_threshold", 3)
                ),
                "year": citation.year or "",
                "title": citation.title or "",
                "journal": citation.journal or "",
                "volume": citation.volume or "",
                "issue": citation.issue or "",
                "pages": citation.pages or "",
                "doi": citation.doi or "",
                "url": citation.url or ""
            }

            # Replace placeholders in template
            formatted = template
            for key, value in data.items():
                formatted = formatted.replace(f"{{{key}}}", str(value))

            return formatted

        except Exception as e:
            logger.error(f"Failed to format bibliography citation: {str(e)}")
            return self._format_citation_default(citation)

    def _format_in_text_citation(
        self,
        citation: Citation,
        style: CitationStyle
    ) -> str:
        """Format citation for in-text reference"""
        try:
            in_text_template = style.format_template.get("in_text", {})

            # Determine number of authors
            authors_list = citation.authors.split(",") if citation.authors else []
            num_authors = len(authors_list)

            # Select appropriate template
            if num_authors == 1:
                template = in_text_template.get("one_author", "({author}, {year})")
                author = authors_list[0].strip()
            elif num_authors == 2:
                template = in_text_template.get("two_authors", "({author1} & {author2}, {year})")
                author = authors_list[0].strip()
                author2 = authors_list[1].strip()
            else:
                template = in_text_template.get("multiple", "({first_author} et al., {year})")
                author = authors_list[0].strip()

            # Replace placeholders
            formatted = template.replace("{author}", self._get_last_name(author))
            formatted = formatted.replace("{first_author}", self._get_last_name(author))
            formatted = formatted.replace("{year}", str(citation.year or ""))

            if num_authors == 2 and "{author2}" in formatted:
                formatted = formatted.replace("{author2}", self._get_last_name(author2))

            return formatted

        except Exception as e:
            logger.error(f"Failed to format in-text citation: {str(e)}")
            return f"({self._get_last_name(citation.authors.split(',')[0]) if citation.authors else 'Unknown'}, {citation.year or 'n.d.'})"

    def _format_authors(
        self,
        authors: str,
        separator: str = ", ",
        et_al_threshold: int = 3
    ) -> str:
        """
        Format author list according to style

        Args:
            authors: Comma-separated author names
            separator: Separator between authors
            et_al_threshold: Number of authors before using "et al."

        Returns:
            Formatted author string
        """
        if not authors:
            return "Unknown"

        authors_list = [a.strip() for a in authors.split(",")]

        if len(authors_list) > et_al_threshold:
            return f"{authors_list[0]} et al."
        elif len(authors_list) == 1:
            return authors_list[0]
        elif len(authors_list) == 2:
            return f"{authors_list[0]}{separator}{authors_list[1]}"
        else:
            last_author = authors_list[-1]
            other_authors = separator.join(authors_list[:-1])
            return f"{other_authors}{separator}{last_author}"

    def _get_last_name(self, full_name: str) -> str:
        """Extract last name from full name"""
        try:
            # Handle "Last, First" format
            if "," in full_name:
                return full_name.split(",")[0].strip()
            # Handle "First Last" format
            else:
                parts = full_name.strip().split()
                return parts[-1] if parts else full_name
        except:
            return full_name

    def _format_citation_default(self, citation: Citation) -> str:
        """Default citation format fallback"""
        authors = citation.authors or "Unknown"
        year = citation.year or "n.d."
        title = citation.title or "Untitled"
        journal = citation.journal or ""

        if journal:
            return f"{authors} ({year}). {title}. {journal}."
        else:
            return f"{authors} ({year}). {title}."

    def generate_numbered_citations(
        self,
        citations: List[Citation],
        style_name: str = "vancouver"
    ) -> Dict[str, Any]:
        """
        Generate numbered citations (Vancouver style)

        Args:
            citations: List of citations
            style_name: Citation style

        Returns:
            Dictionary with numbered citations
        """
        try:
            formatted_citations = []

            for i, citation in enumerate(citations, start=1):
                formatted = self.format_citation(citation, style_name, "bibliography")
                formatted_citations.append({
                    "number": i,
                    "citation": citation,
                    "formatted": f"{i}. {formatted}"
                })

            return {
                "citations": formatted_citations,
                "count": len(formatted_citations)
            }

        except Exception as e:
            logger.error(f"Failed to generate numbered citations: {str(e)}")
            return {"citations": [], "count": 0}

    def validate_citation_completeness(self, citation: Citation) -> Dict[str, Any]:
        """
        Check if citation has all required fields

        Args:
            citation: Citation to validate

        Returns:
            Validation result with missing fields
        """
        required_fields = ["authors", "year", "title"]
        recommended_fields = ["journal", "volume", "pages", "doi"]

        missing_required = []
        missing_recommended = []

        for field in required_fields:
            if not getattr(citation, field, None):
                missing_required.append(field)

        for field in recommended_fields:
            if not getattr(citation, field, None):
                missing_recommended.append(field)

        is_complete = len(missing_required) == 0

        return {
            "is_complete": is_complete,
            "is_recommended_complete": len(missing_recommended) == 0,
            "missing_required": missing_required,
            "missing_recommended": missing_recommended,
            "completeness_score": (
                (len(required_fields) - len(missing_required)) / len(required_fields)
            ) if required_fields else 1.0
        }
