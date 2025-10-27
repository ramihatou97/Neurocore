"""
Tests for Export Service
Tests citation management, bibliography generation, and export functionality
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from sqlalchemy.orm import Session

from backend.services.export_service import ExportService
from backend.services.citation_service import CitationService
from backend.services.bibliography_service import BibliographyService
from backend.database.models import Chapter, Citation, CitationStyle, ExportTemplate


@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def export_service(mock_db):
    """Export service instance"""
    return ExportService(mock_db)


@pytest.fixture
def citation_service(mock_db):
    """Citation service instance"""
    return CitationService(mock_db)


@pytest.fixture
def bibliography_service(mock_db):
    """Bibliography service instance"""
    return BibliographyService(mock_db)


@pytest.fixture
def sample_citation():
    """Sample citation"""
    return Citation(
        id="citation-123",
        authors="Smith, J., Jones, K.",
        year=2024,
        title="Test Article",
        journal="Test Journal",
        volume="10",
        issue="2",
        pages="100-110",
        doi="10.1234/test"
    )


@pytest.fixture
def sample_chapter():
    """Sample chapter"""
    chapter = Chapter(
        id="chapter-123",
        title="Test Chapter",
        content="Test content for the chapter.",
        author_id="user-123",
        created_at=datetime.utcnow()
    )
    chapter.author = Mock()
    chapter.author.name = "Test Author"
    return chapter


@pytest.fixture
def sample_citation_style():
    """Sample citation style (APA)"""
    return CitationStyle(
        id="style-123",
        name="apa",
        display_name="APA 7th Edition",
        format_template={
            "in_text": {
                "one_author": "({author}, {year})",
                "two_authors": "({author1} & {author2}, {year})",
                "multiple": "({first_author} et al., {year})"
            },
            "bibliography": "{authors}. ({year}). {title}. {journal}, {volume}({issue}), {pages}.",
            "author_separator": ", & ",
            "et_al_threshold": 3
        },
        is_active=True
    )


@pytest.fixture
def sample_template():
    """Sample export template"""
    return ExportTemplate(
        id="template-123",
        name="Test Template",
        format="html",
        template_content="<html><body><h1>{{ title }}</h1><div>{{ content }}</div></body></html>",
        styles={"font_family": "Arial"},
        is_default=True,
        is_public=True
    )


class TestCitationService:
    """Tests for CitationService"""

    def test_format_citation_apa(self, citation_service, mock_db, sample_citation, sample_citation_style):
        """Test APA citation formatting"""
        mock_db.query().filter().first.return_value = sample_citation_style

        formatted = citation_service.format_citation(sample_citation, "apa", "bibliography")

        assert "Smith, J., Jones, K." in formatted or "Smith" in formatted
        assert "2024" in formatted
        assert "Test Article" in formatted

    def test_format_in_text_citation(self, citation_service, mock_db, sample_citation, sample_citation_style):
        """Test in-text citation formatting"""
        mock_db.query().filter().first.return_value = sample_citation_style

        formatted = citation_service.format_citation(sample_citation, "apa", "in_text")

        assert "2024" in formatted

    def test_get_all_citation_styles(self, citation_service, mock_db, sample_citation_style):
        """Test getting all citation styles"""
        mock_db.query().filter().all.return_value = [sample_citation_style]

        styles = citation_service.get_all_citation_styles()

        assert len(styles) == 1
        assert styles[0]["name"] == "apa"


class TestBibliographyService:
    """Tests for BibliographyService"""

    def test_generate_bibliography(self, bibliography_service, mock_db, sample_chapter):
        """Test bibliography generation"""
        # Mock citations
        sample_chapter.citations = []

        result = bibliography_service.generate_bibliography(sample_chapter, "apa")

        assert "bibliography" in result
        assert "count" in result

    def test_sort_citations_by_author(self, bibliography_service):
        """Test sorting citations by author"""
        citations = [
            Mock(authors="Zeta, A.", year=2024),
            Mock(authors="Alpha, B.", year=2024),
            Mock(authors="Beta, C.", year=2024)
        ]

        sorted_citations = bibliography_service._sort_citations(citations, "author")

        assert sorted_citations[0].authors == "Alpha, B."
        assert sorted_citations[-1].authors == "Zeta, A."

    def test_detect_duplicate_citations(self, bibliography_service):
        """Test duplicate detection"""
        citations = [
            Mock(id="1", authors="Smith, J.", year=2024, title="Test"),
            Mock(id="2", authors="Smith, J.", year=2024, title="Test"),
            Mock(id="3", authors="Jones, K.", year=2024, title="Other")
        ]

        result = bibliography_service.detect_duplicate_citations(citations)

        assert result["has_duplicates"] == True
        assert result["duplicate_count"] > 0


class TestExportService:
    """Tests for ExportService"""

    def test_export_chapter_html(self, export_service, mock_db, sample_chapter, sample_template):
        """Test HTML export"""
        # Mock database queries
        chapter_query = Mock()
        chapter_query.filter().first.return_value = sample_chapter

        template_query = Mock()
        template_query.filter().first.return_value = sample_template

        def query_side_effect(model):
            if model == Chapter:
                return chapter_query
            elif model == ExportTemplate:
                return template_query
            return Mock()

        mock_db.query.side_effect = query_side_effect

        result = export_service.export_chapter(
            chapter_id="chapter-123",
            user_id="user-123",
            export_format="html"
        )

        assert result["success"] == True
        assert result["format"] == "html"
        assert "file_name" in result

    def test_prepare_chapter_content(self, export_service, sample_chapter):
        """Test content preparation"""
        content_data = export_service._prepare_chapter_content(
            sample_chapter,
            "apa",
            {"include_bibliography": True}
        )

        assert "title" in content_data
        assert "author_name" in content_data
        assert "content" in content_data

    def test_export_unsupported_format(self, export_service, mock_db, sample_chapter):
        """Test export with unsupported format"""
        chapter_query = Mock()
        chapter_query.filter().first.return_value = sample_chapter

        mock_db.query.return_value = chapter_query

        result = export_service.export_chapter(
            chapter_id="chapter-123",
            user_id="user-123",
            export_format="invalid"
        )

        assert result["success"] == False
        assert "error" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
