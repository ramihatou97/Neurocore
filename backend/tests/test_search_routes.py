"""
Tests for Search API Routes
Tests all search endpoints and their responses
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from datetime import datetime

from backend.main import app
from backend.database.models import User


@pytest.fixture
def client():
    """Test client"""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    return User(
        id="user-123",
        email="test@example.com",
        name="Test User",
        role="researcher"
    )


@pytest.fixture
def auth_headers():
    """Authentication headers"""
    return {"Authorization": "Bearer mock-token"}


class TestUnifiedSearch:
    """Tests for /search endpoint"""

    @patch('backend.api.search_routes.get_current_user')
    @patch('backend.api.search_routes.SearchService')
    def test_unified_search_success(self, mock_search_service, mock_get_user, client, mock_user, auth_headers):
        """Test successful unified search"""
        mock_get_user.return_value = mock_user

        # Mock search service response
        mock_service_instance = Mock()
        mock_service_instance.search_all.return_value = {
            "query": "brain tumor",
            "search_type": "hybrid",
            "total": 1,
            "results": [
                {
                    "id": "pdf-123",
                    "type": "pdf",
                    "title": "Brain Tumor Classification",
                    "score": 0.85
                }
            ],
            "filters_applied": {}
        }
        mock_search_service.return_value = mock_service_instance

        response = client.post(
            "/api/v1/search",
            json={
                "query": "brain tumor",
                "search_type": "hybrid",
                "max_results": 20
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "brain tumor"
        assert data["search_type"] == "hybrid"
        assert len(data["results"]) == 1

    @patch('backend.api.search_routes.get_current_user')
    def test_unified_search_empty_query(self, mock_get_user, client, mock_user, auth_headers):
        """Test search with empty query"""
        mock_get_user.return_value = mock_user

        response = client.post(
            "/api/v1/search",
            json={
                "query": "",
                "search_type": "hybrid"
            },
            headers=auth_headers
        )

        # Should fail validation
        assert response.status_code == 422

    @patch('backend.api.search_routes.get_current_user')
    @patch('backend.api.search_routes.SearchService')
    def test_unified_search_with_filters(self, mock_search_service, mock_get_user, client, mock_user, auth_headers):
        """Test search with filters"""
        mock_get_user.return_value = mock_user

        mock_service_instance = Mock()
        mock_service_instance.search_all.return_value = {
            "query": "brain",
            "search_type": "keyword",
            "total": 0,
            "results": [],
            "filters_applied": {"content_type": "pdf"}
        }
        mock_search_service.return_value = mock_service_instance

        response = client.post(
            "/api/v1/search",
            json={
                "query": "brain",
                "search_type": "keyword",
                "filters": {"content_type": "pdf"},
                "max_results": 10
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["filters_applied"]["content_type"] == "pdf"

    @patch('backend.api.search_routes.get_current_user')
    @patch('backend.api.search_routes.SearchService')
    def test_unified_search_pagination(self, mock_search_service, mock_get_user, client, mock_user, auth_headers):
        """Test search with pagination"""
        mock_get_user.return_value = mock_user

        mock_service_instance = Mock()
        mock_service_instance.search_all.return_value = {
            "query": "test",
            "search_type": "hybrid",
            "total": 50,
            "results": [{"id": str(i)} for i in range(20)],
            "filters_applied": {}
        }
        mock_search_service.return_value = mock_service_instance

        response = client.post(
            "/api/v1/search",
            json={
                "query": "test",
                "search_type": "hybrid",
                "max_results": 20,
                "offset": 20
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 50

    def test_unified_search_unauthorized(self, client):
        """Test search without authentication"""
        response = client.post(
            "/api/v1/search",
            json={"query": "test", "search_type": "hybrid"}
        )

        assert response.status_code == 401


class TestSearchSuggestions:
    """Tests for /search/suggestions endpoint"""

    @patch('backend.api.search_routes.get_current_user')
    @patch('backend.api.search_routes.SearchService')
    def test_get_suggestions_success(self, mock_search_service, mock_get_user, client, mock_user, auth_headers):
        """Test successful suggestions retrieval"""
        mock_get_user.return_value = mock_user

        mock_service_instance = Mock()
        mock_service_instance.get_search_suggestions.return_value = [
            "brain tumor classification",
            "brain tumor types",
            "brain tumor surgery"
        ]
        mock_search_service.return_value = mock_service_instance

        response = client.get(
            "/api/v1/search/suggestions?q=brain",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "brain"
        assert len(data["suggestions"]) == 3
        assert data["count"] == 3

    @patch('backend.api.search_routes.get_current_user')
    @patch('backend.api.search_routes.SearchService')
    def test_get_suggestions_no_results(self, mock_search_service, mock_get_user, client, mock_user, auth_headers):
        """Test suggestions with no results"""
        mock_get_user.return_value = mock_user

        mock_service_instance = Mock()
        mock_service_instance.get_search_suggestions.return_value = []
        mock_search_service.return_value = mock_service_instance

        response = client.get(
            "/api/v1/search/suggestions?q=xyz123",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["suggestions"]) == 0

    def test_get_suggestions_unauthorized(self, client):
        """Test suggestions without authentication"""
        response = client.get("/api/v1/search/suggestions?q=brain")
        assert response.status_code == 401


class TestRelatedContent:
    """Tests for /search/related endpoint"""

    @patch('backend.api.search_routes.get_current_user')
    @patch('backend.api.search_routes.SearchService')
    def test_find_related_content_success(self, mock_search_service, mock_get_user, client, mock_user, auth_headers):
        """Test successful related content search"""
        mock_get_user.return_value = mock_user

        mock_service_instance = Mock()
        mock_service_instance.find_related_content.return_value = [
            {"id": "pdf-456", "title": "Related Paper 1", "similarity": 0.85},
            {"id": "pdf-789", "title": "Related Paper 2", "similarity": 0.75}
        ]
        mock_search_service.return_value = mock_service_instance

        response = client.post(
            "/api/v1/search/related",
            json={
                "content_id": "pdf-123",
                "content_type": "pdf",
                "max_results": 5
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["source_id"] == "pdf-123"
        assert data["source_type"] == "pdf"
        assert len(data["related"]) == 2
        assert data["count"] == 2

    @patch('backend.api.search_routes.get_current_user')
    @patch('backend.api.search_routes.SearchService')
    def test_find_related_content_not_found(self, mock_search_service, mock_get_user, client, mock_user, auth_headers):
        """Test related content for non-existent source"""
        mock_get_user.return_value = mock_user

        mock_service_instance = Mock()
        mock_service_instance.find_related_content.side_effect = ValueError("Content not found")
        mock_search_service.return_value = mock_service_instance

        response = client.post(
            "/api/v1/search/related",
            json={
                "content_id": "nonexistent",
                "content_type": "pdf",
                "max_results": 5
            },
            headers=auth_headers
        )

        assert response.status_code == 400

    def test_find_related_content_invalid_type(self, client, auth_headers):
        """Test related content with invalid content type"""
        response = client.post(
            "/api/v1/search/related",
            json={
                "content_id": "123",
                "content_type": "invalid",
                "max_results": 5
            },
            headers=auth_headers
        )

        assert response.status_code == 422  # Validation error


class TestSemanticSearch:
    """Tests for semantic search endpoints"""

    @patch('backend.api.search_routes.get_current_user')
    @patch('backend.api.search_routes.EmbeddingService')
    def test_search_pdfs_semantic(self, mock_embedding_service, mock_get_user, client, mock_user, auth_headers):
        """Test semantic PDF search"""
        mock_get_user.return_value = mock_user

        mock_service_instance = Mock()
        mock_service_instance.find_similar_pdfs.return_value = [
            {"id": "pdf-123", "title": "Test PDF", "similarity": 0.85}
        ]
        mock_embedding_service.return_value = mock_service_instance

        response = client.get(
            "/api/v1/search/semantic/pdfs?q=brain tumor&max_results=10&min_similarity=0.7",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "brain tumor"
        assert len(data["results"]) == 1
        assert data["min_similarity"] == 0.7

    @patch('backend.api.search_routes.get_current_user')
    @patch('backend.api.search_routes.EmbeddingService')
    def test_search_images_semantic(self, mock_embedding_service, mock_get_user, client, mock_user, auth_headers):
        """Test semantic image search"""
        mock_get_user.return_value = mock_user

        mock_service_instance = Mock()
        mock_service_instance.find_similar_images.return_value = [
            {"id": "img-123", "description": "Brain MRI", "similarity": 0.80}
        ]
        mock_embedding_service.return_value = mock_service_instance

        response = client.get(
            "/api/v1/search/semantic/images?q=mri scan",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "mri scan"
        assert len(data["results"]) == 1


class TestEmbeddingManagement:
    """Tests for embedding generation endpoints"""

    @patch('backend.api.search_routes.get_current_user')
    @patch('backend.api.search_routes.EmbeddingService')
    @patch('backend.api.search_routes.get_db')
    def test_generate_embeddings_pdf(self, mock_get_db, mock_embedding_service, mock_get_user, client, mock_user, auth_headers):
        """Test generating embeddings for PDF"""
        mock_get_user.return_value = mock_user

        # Mock database
        from backend.database.models import PDF
        mock_pdf = PDF(id="pdf-123", title="Test", embedding=None)
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_pdf
        mock_get_db.return_value = mock_db

        # Mock embedding service
        mock_service_instance = Mock()
        mock_service_instance.generate_pdf_embeddings.return_value = {
            "success": True,
            "embedding_dimension": 1536
        }
        mock_embedding_service.return_value = mock_service_instance

        response = client.post(
            "/api/v1/embeddings/generate",
            json={
                "entity_type": "pdf",
                "entity_id": "pdf-123",
                "force_regenerate": False
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["entity_id"] == "pdf-123"
        assert data["status"] == "generated"

    @patch('backend.api.search_routes.get_current_user')
    @patch('backend.api.search_routes.get_db')
    def test_generate_embeddings_already_exists(self, mock_get_db, mock_get_user, client, mock_user, auth_headers):
        """Test generating embeddings when already exist"""
        mock_get_user.return_value = mock_user

        # Mock database with PDF that has embeddings
        from backend.database.models import PDF
        mock_pdf = PDF(id="pdf-123", title="Test", embedding=[0.1] * 1536)
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_pdf
        mock_get_db.return_value = mock_db

        response = client.post(
            "/api/v1/embeddings/generate",
            json={
                "entity_type": "pdf",
                "entity_id": "pdf-123",
                "force_regenerate": False
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "already_exists"

    @patch('backend.api.search_routes.get_current_user')
    @patch('backend.api.search_routes.get_db')
    def test_generate_embeddings_not_found(self, mock_get_db, mock_get_user, client, mock_user, auth_headers):
        """Test generating embeddings for non-existent entity"""
        mock_get_user.return_value = mock_user

        # Mock database returning None
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_get_db.return_value = mock_db

        response = client.post(
            "/api/v1/embeddings/generate",
            json={
                "entity_type": "pdf",
                "entity_id": "nonexistent",
                "force_regenerate": False
            },
            headers=auth_headers
        )

        assert response.status_code == 404

    @patch('backend.api.search_routes.get_current_user')
    @patch('backend.api.search_routes.EmbeddingService')
    def test_batch_generate_pdf_embeddings(self, mock_embedding_service, mock_get_user, client, mock_user, auth_headers):
        """Test batch embedding generation"""
        mock_get_user.return_value = mock_user

        mock_service_instance = Mock()
        mock_service_instance.update_all_pdf_embeddings.return_value = {
            "total_processed": 10,
            "success": 8,
            "errors": 2
        }
        mock_embedding_service.return_value = mock_service_instance

        response = client.post(
            "/api/v1/embeddings/batch/pdfs?batch_size=10",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["total_processed"] == 10
        assert data["success"] == 8


class TestSearchStatistics:
    """Tests for /search/stats endpoint"""

    @patch('backend.api.search_routes.get_current_user')
    @patch('backend.api.search_routes.get_db')
    def test_get_search_statistics(self, mock_get_db, mock_get_user, client, mock_user, auth_headers):
        """Test retrieving search statistics"""
        mock_get_user.return_value = mock_user

        # Mock database queries
        mock_db = Mock()

        # Mock count queries
        mock_query = Mock()
        mock_query.scalar.side_effect = [100, 80, 50, 40, 20, 15]  # totals and embeddings
        mock_query.filter.return_value = mock_query
        mock_db.query.return_value = mock_query

        mock_get_db.return_value = mock_db

        response = client.get(
            "/api/v1/search/stats",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "pdfs" in data
        assert "chapters" in data
        assert "images" in data

        # Check structure
        for entity_type in ["pdfs", "chapters", "images"]:
            assert "total" in data[entity_type]
            assert "with_embeddings" in data[entity_type]
            assert "coverage" in data[entity_type]


class TestSearchHealthCheck:
    """Tests for /health endpoint"""

    def test_health_check(self, client):
        """Test search service health check"""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "search"
        assert "features" in data
        assert "unified_search" in data["features"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
