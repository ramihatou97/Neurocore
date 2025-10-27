"""
Tests for Version Service
Tests version creation, retrieval, comparison, and rollback
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from sqlalchemy.orm import Session

from backend.services.version_service import VersionService
from backend.database.models import Chapter, ChapterVersion, User


@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def version_service(mock_db):
    """Version service instance"""
    return VersionService(mock_db)


@pytest.fixture
def sample_chapter():
    """Sample chapter for testing"""
    return Chapter(
        id="chapter-123",
        title="Test Chapter",
        content="This is test content for the chapter.",
        author_id="user-123",
        generation_status="completed",
        version="1.0",
        created_at=datetime.utcnow()
    )


@pytest.fixture
def sample_version():
    """Sample version for testing"""
    return ChapterVersion(
        id="version-123",
        chapter_id="chapter-123",
        version_number=1,
        title="Test Chapter",
        content="This is test content for the chapter.",
        summary="Test summary",
        word_count=8,
        character_count=39,
        change_size=0,
        changed_by="user-123",
        change_description="Initial version",
        change_type="initial",
        created_at=datetime.utcnow()
    )


class TestVersionService:
    """Test suite for VersionService"""

    def test_create_version(self, version_service, mock_db, sample_chapter):
        """Test creating a version"""
        # Mock next version number
        mock_db.query().filter().scalar.return_value = None  # No existing versions

        # Mock version creation
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        version = version_service.create_version(
            chapter=sample_chapter,
            changed_by="user-123",
            change_description="Test version"
        )

        assert mock_db.add.called
        assert mock_db.commit.called

    def test_get_version_history(self, version_service, mock_db, sample_version):
        """Test getting version history"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [sample_version]

        mock_db.query.return_value = mock_query

        history = version_service.get_version_history("chapter-123")

        assert len(history) == 1
        assert history[0]["version_number"] == 1

    def test_get_specific_version(self, version_service, mock_db, sample_version):
        """Test getting a specific version"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_version

        mock_db.query.return_value = mock_query

        version = version_service.get_version("chapter-123", 1)

        assert version is not None
        assert version.version_number == 1

    def test_get_version_statistics(self, version_service, mock_db):
        """Test getting version statistics"""
        mock_stats = Mock()
        mock_stats.total_versions = 5
        mock_stats.unique_contributors = 2
        mock_stats.avg_word_count = 500.0
        mock_stats.first_version_date = datetime.utcnow()
        mock_stats.last_version_date = datetime.utcnow()
        mock_stats.total_content_size = 2500
        mock_stats.latest_version_number = 5

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_stats

        mock_db.query.return_value = mock_query

        stats = version_service.get_version_statistics("chapter-123")

        assert stats["total_versions"] == 5
        assert stats["unique_contributors"] == 2

    def test_rollback_to_version(self, version_service, mock_db, sample_chapter, sample_version):
        """Test rolling back to a previous version"""
        # Mock chapter query
        chapter_query = Mock()
        chapter_query.filter.return_value = chapter_query
        chapter_query.first.return_value = sample_chapter

        # Mock version query
        version_query = Mock()
        version_query.filter.return_value = version_query
        version_query.first.return_value = sample_version

        def query_side_effect(model):
            if model == Chapter:
                return chapter_query
            elif model == ChapterVersion:
                return version_query
            return Mock()

        mock_db.query.side_effect = query_side_effect

        # Mock version creation
        with patch.object(version_service, 'create_version') as mock_create:
            mock_create.return_value = sample_version

            chapter, new_version = version_service.rollback_to_version(
                chapter_id="chapter-123",
                version_number=1,
                user_id="user-123",
                reason="Rolling back for testing"
            )

            assert mock_create.call_count == 2  # Pre-rollback + post-rollback
            assert mock_db.commit.called

    def test_rollback_to_nonexistent_version(self, version_service, mock_db, sample_chapter):
        """Test rollback fails when version doesn't exist"""
        # Mock chapter query
        chapter_query = Mock()
        chapter_query.filter.return_value = chapter_query
        chapter_query.first.return_value = sample_chapter

        # Mock version query (returns None - version not found)
        version_query = Mock()
        version_query.filter.return_value = version_query
        version_query.first.return_value = None

        def query_side_effect(model):
            if model == Chapter:
                return chapter_query
            elif model == ChapterVersion:
                return version_query
            return Mock()

        mock_db.query.side_effect = query_side_effect

        with pytest.raises(ValueError, match="not found"):
            version_service.rollback_to_version(
                chapter_id="chapter-123",
                version_number=99,
                user_id="user-123"
            )

    def test_delete_old_versions(self, version_service, mock_db, sample_version):
        """Test deleting old versions"""
        versions_to_delete = [sample_version]

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = versions_to_delete

        mock_db.query.return_value = mock_query
        mock_db.delete = Mock()
        mock_db.commit = Mock()

        count = version_service.delete_old_versions("chapter-123", keep_count=10)

        assert count == 1
        assert mock_db.delete.called
        assert mock_db.commit.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
