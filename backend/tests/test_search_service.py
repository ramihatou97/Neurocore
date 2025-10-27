"""
Tests for Search Service
Tests hybrid search, semantic search, and keyword search functionality
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.services.search_service import SearchService
from backend.database.models import PDF, Chapter, Image, User


@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def search_service(mock_db):
    """Search service instance with mock database"""
    return SearchService(mock_db)


@pytest.fixture
def sample_pdf():
    """Sample PDF for testing"""
    return PDF(
        id="pdf-123",
        title="Brain Tumor Classification",
        authors="Dr. Smith, Dr. Jones",
        year=2024,
        journal="Neurosurgery Journal",
        extracted_text="This paper discusses brain tumor classification methods...",
        extraction_status="completed",
        embedding=[0.1] * 1536,  # Mock embedding vector
        created_at=datetime.utcnow()
    )


@pytest.fixture
def sample_chapter():
    """Sample chapter for testing"""
    return Chapter(
        id="chapter-456",
        title="Surgical Techniques for Brain Tumors",
        summary="Comprehensive guide to surgical approaches...",
        content="Detailed content about surgical techniques...",
        generation_status="completed",
        embedding=[0.2] * 1536,
        author_id="user-789",
        created_at=datetime.utcnow()
    )


class TestSearchService:
    """Test suite for SearchService"""

    def test_initialization(self, mock_db):
        """Test service initialization"""
        service = SearchService(mock_db)
        assert service.db == mock_db

    @pytest.mark.asyncio
    async def test_keyword_search_pdfs(self, search_service, mock_db, sample_pdf):
        """Test keyword search for PDFs"""
        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_pdf]

        mock_db.query.return_value = mock_query

        results = await search_service._search_pdfs_keyword(
            query="brain tumor",
            filters={},
            max_results=10
        )

        assert len(results) > 0
        assert results[0]["type"] == "pdf"
        assert "title" in results[0]

    @pytest.mark.asyncio
    async def test_semantic_search_requires_embeddings(self, search_service, mock_db):
        """Test semantic search requires query embeddings"""
        with patch.object(search_service, '_generate_query_embedding', return_value=None):
            results = await search_service._semantic_search(
                query="brain tumor",
                filters={},
                max_results=10,
                offset=0
            )

            # Should return empty results if embedding generation fails
            assert results == []

    @pytest.mark.asyncio
    async def test_hybrid_search_combines_results(self, search_service):
        """Test hybrid search combines keyword and semantic results"""
        keyword_results = [
            {"id": "pdf-1", "title": "Paper 1", "keyword_score": 0.8, "type": "pdf"},
            {"id": "pdf-2", "title": "Paper 2", "keyword_score": 0.6, "type": "pdf"},
        ]

        semantic_results = [
            {"id": "pdf-1", "title": "Paper 1", "semantic_score": 0.9, "type": "pdf"},
            {"id": "pdf-3", "title": "Paper 3", "semantic_score": 0.7, "type": "pdf"},
        ]

        with patch.object(search_service, '_keyword_search', return_value=keyword_results), \
             patch.object(search_service, '_semantic_search', return_value=semantic_results):

            results = await search_service._hybrid_search(
                query="brain tumor",
                filters={},
                max_results=10,
                offset=0
            )

            # Should have merged results
            assert len(results) > 0
            # pdf-1 should be ranked highest (appears in both)
            assert results[0]["id"] == "pdf-1"

    @pytest.mark.asyncio
    async def test_search_all_hybrid_mode(self, search_service):
        """Test search_all with hybrid mode"""
        with patch.object(search_service, '_hybrid_search', return_value=[]):
            result = await search_service.search_all(
                query="brain tumor",
                search_type="hybrid",
                filters={},
                max_results=20,
                offset=0
            )

            assert "query" in result
            assert "search_type" in result
            assert result["search_type"] == "hybrid"
            assert "results" in result

    @pytest.mark.asyncio
    async def test_search_all_keyword_mode(self, search_service):
        """Test search_all with keyword mode"""
        with patch.object(search_service, '_keyword_search', return_value=[]):
            result = await search_service.search_all(
                query="brain tumor",
                search_type="keyword",
                filters={},
                max_results=20,
                offset=0
            )

            assert result["search_type"] == "keyword"

    @pytest.mark.asyncio
    async def test_search_all_semantic_mode(self, search_service):
        """Test search_all with semantic mode"""
        with patch.object(search_service, '_semantic_search', return_value=[]):
            result = await search_service.search_all(
                query="brain tumor",
                search_type="semantic",
                filters={},
                max_results=20,
                offset=0
            )

            assert result["search_type"] == "semantic"

    @pytest.mark.asyncio
    async def test_search_suggestions(self, search_service, mock_db, sample_pdf, sample_chapter):
        """Test search suggestions"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_pdf]

        mock_db.query.return_value = mock_query

        suggestions = await search_service.get_search_suggestions(
            partial_query="brain",
            max_suggestions=10
        )

        assert isinstance(suggestions, list)

    @pytest.mark.asyncio
    async def test_find_related_content_pdf(self, search_service, mock_db, sample_pdf):
        """Test finding related content for a PDF"""
        # Mock PDF query
        mock_db.query.return_value.filter.return_value.first.return_value = sample_pdf

        # Mock related content query
        mock_result = Mock()
        mock_result.id = "pdf-related"
        mock_result.title = "Related Paper"
        mock_result.similarity = 0.85

        mock_db.execute.return_value.fetchall.return_value = [(mock_result,)]

        with patch.object(search_service, '_get_similar_content', return_value=[]):
            related = await search_service.find_related_content(
                content_id="pdf-123",
                content_type="pdf",
                max_results=5
            )

            assert isinstance(related, list)

    @pytest.mark.asyncio
    async def test_find_related_content_chapter(self, search_service, mock_db, sample_chapter):
        """Test finding related content for a chapter"""
        # Mock chapter query
        mock_db.query.return_value.filter.return_value.first.return_value = sample_chapter

        with patch.object(search_service, '_get_similar_content', return_value=[]):
            related = await search_service.find_related_content(
                content_id="chapter-456",
                content_type="chapter",
                max_results=5
            )

            assert isinstance(related, list)

    @pytest.mark.asyncio
    async def test_find_related_content_no_embedding(self, search_service, mock_db):
        """Test finding related content fails when source has no embedding"""
        pdf_no_embedding = PDF(
            id="pdf-123",
            title="Test",
            embedding=None,  # No embedding
            extraction_status="completed"
        )

        mock_db.query.return_value.filter.return_value.first.return_value = pdf_no_embedding

        with pytest.raises(ValueError, match="does not have embeddings"):
            await search_service.find_related_content(
                content_id="pdf-123",
                content_type="pdf",
                max_results=5
            )

    @pytest.mark.asyncio
    async def test_find_related_content_not_found(self, search_service, mock_db):
        """Test finding related content fails when source not found"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="not found"):
            await search_service.find_related_content(
                content_id="nonexistent",
                content_type="pdf",
                max_results=5
            )

    def test_merge_and_rerank(self, search_service):
        """Test merging and reranking results"""
        keyword_results = [
            {"id": "1", "keyword_score": 0.8, "created_at": datetime.utcnow().isoformat()},
            {"id": "2", "keyword_score": 0.6, "created_at": datetime.utcnow().isoformat()},
        ]

        semantic_results = [
            {"id": "1", "semantic_score": 0.9},
            {"id": "3", "semantic_score": 0.7},
        ]

        merged = search_service._merge_and_rerank(keyword_results, semantic_results)

        # Should have 3 unique results
        assert len(merged) == 3

        # All results should have final_score
        for result in merged:
            assert "final_score" in result
            assert 0 <= result["final_score"] <= 1

        # Results should be sorted by final_score
        scores = [r["final_score"] for r in merged]
        assert scores == sorted(scores, reverse=True)

    def test_calculate_recency_score(self, search_service):
        """Test recency score calculation"""
        # Recent content (< 30 days)
        recent_date = datetime.utcnow() - timedelta(days=15)
        recent_score = search_service._calculate_recency_score(recent_date.isoformat())
        assert recent_score == 1.0

        # Medium age (90 days)
        medium_date = datetime.utcnow() - timedelta(days=90)
        medium_score = search_service._calculate_recency_score(medium_date.isoformat())
        assert 0.5 <= medium_score <= 1.0

        # Old content (> 365 days)
        old_date = datetime.utcnow() - timedelta(days=400)
        old_score = search_service._calculate_recency_score(old_date.isoformat())
        assert old_score == 0.2

        # Invalid date
        invalid_score = search_service._calculate_recency_score("invalid-date")
        assert invalid_score == 0.5  # Default

    def test_format_pdf_result(self, search_service, sample_pdf):
        """Test formatting PDF result"""
        result = search_service._format_pdf_result(sample_pdf, score=0.85)

        assert result["id"] == sample_pdf.id
        assert result["type"] == "pdf"
        assert result["title"] == sample_pdf.title
        assert result["authors"] == sample_pdf.authors
        assert result["score"] == 0.85

    def test_format_chapter_result(self, search_service, sample_chapter):
        """Test formatting chapter result"""
        result = search_service._format_chapter_result(sample_chapter, score=0.75)

        assert result["id"] == sample_chapter.id
        assert result["type"] == "chapter"
        assert result["title"] == sample_chapter.title
        assert result["score"] == 0.75

    @pytest.mark.asyncio
    async def test_apply_filters_content_type(self, search_service):
        """Test applying content type filter"""
        results = [
            {"type": "pdf", "id": "1"},
            {"type": "chapter", "id": "2"},
            {"type": "pdf", "id": "3"},
        ]

        filtered = search_service._apply_filters(results, {"content_type": "pdf"})

        assert len(filtered) == 2
        assert all(r["type"] == "pdf" for r in filtered)

    @pytest.mark.asyncio
    async def test_apply_filters_date_range(self, search_service):
        """Test applying date range filter"""
        now = datetime.utcnow()
        results = [
            {"created_at": (now - timedelta(days=5)).isoformat()},
            {"created_at": (now - timedelta(days=50)).isoformat()},
            {"created_at": (now - timedelta(days=400)).isoformat()},
        ]

        cutoff = (now - timedelta(days=30)).isoformat()
        filtered = search_service._apply_filters(
            results,
            {"created_after": cutoff}
        )

        assert len(filtered) == 1

    @pytest.mark.asyncio
    async def test_empty_query_returns_error(self, search_service):
        """Test that empty query returns appropriate response"""
        result = await search_service.search_all(
            query="",
            search_type="hybrid",
            filters={},
            max_results=20,
            offset=0
        )

        assert result["total"] == 0
        assert result["results"] == []


class TestSearchIntegration:
    """Integration tests for search functionality"""

    @pytest.mark.asyncio
    async def test_full_hybrid_search_flow(self, search_service):
        """Test complete hybrid search flow"""
        with patch.object(search_service, '_keyword_search', return_value=[
            {"id": "1", "title": "Test", "keyword_score": 0.8, "type": "pdf",
             "created_at": datetime.utcnow().isoformat()}
        ]), \
             patch.object(search_service, '_semantic_search', return_value=[
            {"id": "1", "title": "Test", "semantic_score": 0.9, "type": "pdf"}
        ]):

            result = await search_service.search_all(
                query="brain tumor",
                search_type="hybrid",
                filters={"content_type": "pdf"},
                max_results=20,
                offset=0
            )

            assert result["total"] > 0
            assert len(result["results"]) > 0
            assert result["results"][0]["type"] == "pdf"

    @pytest.mark.asyncio
    async def test_pagination(self, search_service):
        """Test search pagination"""
        mock_results = [{"id": str(i), "score": 0.8} for i in range(50)]

        with patch.object(search_service, '_hybrid_search', return_value=mock_results):
            # First page
            page1 = await search_service.search_all(
                query="test",
                search_type="hybrid",
                filters={},
                max_results=20,
                offset=0
            )

            # Second page
            page2 = await search_service.search_all(
                query="test",
                search_type="hybrid",
                filters={},
                max_results=20,
                offset=20
            )

            assert len(page1["results"]) == 20
            assert len(page2["results"]) == 20
            assert page1["results"][0]["id"] != page2["results"][0]["id"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
