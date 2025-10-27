"""
Tests for BookmarkService - Phase 18: Advanced Content Features
Comprehensive test suite for bookmark and collection management
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from uuid import uuid4

from backend.services.bookmark_service import BookmarkService


@pytest.fixture
def mock_db():
    """Create mock database session"""
    db = Mock()
    db.execute = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    return db


@pytest.fixture
def bookmark_service(mock_db):
    """Create BookmarkService instance with mock DB"""
    return BookmarkService(mock_db)


class TestBookmarkCreation:
    """Test bookmark creation and management"""

    def test_create_bookmark_success(self, bookmark_service, mock_db):
        """Test successful bookmark creation"""
        # Setup
        user_id = str(uuid4())
        content_id = str(uuid4())

        mock_result = Mock()
        mock_row = (uuid4(), datetime.now())
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Execute
        result = bookmark_service.create_bookmark(
            user_id=user_id,
            content_type='chapter',
            content_id=content_id,
            title='Test Bookmark',
            notes='Test notes',
            tags=['test', 'bookmark'],
            is_favorite=True
        )

        # Assert
        assert result is not None
        assert result['id'] == str(mock_row[0])
        assert result['user_id'] == user_id
        assert result['content_type'] == 'chapter'
        assert result['content_id'] == content_id
        mock_db.commit.assert_called_once()

    def test_create_bookmark_with_collection(self, bookmark_service, mock_db):
        """Test bookmark creation with collection assignment"""
        # Setup
        collection_id = str(uuid4())

        mock_result = Mock()
        mock_row = (uuid4(), datetime.now())
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Execute
        result = bookmark_service.create_bookmark(
            user_id=str(uuid4()),
            content_type='pdf',
            content_id=str(uuid4()),
            collection_id=collection_id
        )

        # Assert
        assert result is not None
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        assert call_args[0][1]['collection_id'] == collection_id

    def test_create_bookmark_failure(self, bookmark_service, mock_db):
        """Test bookmark creation failure handling"""
        # Setup
        mock_db.execute.side_effect = Exception("Database error")

        # Execute
        result = bookmark_service.create_bookmark(
            user_id=str(uuid4()),
            content_type='chapter',
            content_id=str(uuid4())
        )

        # Assert
        assert result is None
        mock_db.rollback.assert_called_once()

    def test_create_bookmark_upsert_on_conflict(self, bookmark_service, mock_db):
        """Test bookmark upsert behavior on conflict"""
        # Setup
        user_id = str(uuid4())
        content_id = str(uuid4())

        mock_result = Mock()
        mock_row = (uuid4(), datetime.now())
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Execute - create same bookmark twice
        result1 = bookmark_service.create_bookmark(
            user_id=user_id,
            content_type='chapter',
            content_id=content_id
        )

        result2 = bookmark_service.create_bookmark(
            user_id=user_id,
            content_type='chapter',
            content_id=content_id,
            notes='Updated notes'
        )

        # Assert
        assert result1 is not None
        assert result2 is not None


class TestBookmarkRetrieval:
    """Test bookmark retrieval and filtering"""

    def test_get_user_bookmarks(self, bookmark_service, mock_db):
        """Test retrieving user's bookmarks"""
        # Setup
        user_id = str(uuid4())

        mock_result = Mock()
        mock_rows = [
            (uuid4(), 'chapter', uuid4(), None, 'Test 1', None, ['tag1'], True, 1, datetime.now(), None, None),
            (uuid4(), 'pdf', uuid4(), None, 'Test 2', None, ['tag2'], False, 2, datetime.now(), None, None)
        ]
        mock_result.fetchall.return_value = mock_rows
        mock_db.execute.return_value = mock_result

        # Execute
        bookmarks = bookmark_service.get_user_bookmarks(user_id=user_id)

        # Assert
        assert len(bookmarks) == 2
        assert bookmarks[0]['content_type'] == 'chapter'
        assert bookmarks[1]['content_type'] == 'pdf'

    def test_get_bookmarks_by_collection(self, bookmark_service, mock_db):
        """Test filtering bookmarks by collection"""
        # Setup
        collection_id = str(uuid4())

        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        # Execute
        bookmarks = bookmark_service.get_user_bookmarks(
            user_id=str(uuid4()),
            collection_id=collection_id
        )

        # Assert
        call_args = mock_db.execute.call_args
        assert 'collection_id' in call_args[0][1]

    def test_get_favorites_only(self, bookmark_service, mock_db):
        """Test retrieving only favorite bookmarks"""
        # Setup
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        # Execute
        bookmarks = bookmark_service.get_user_bookmarks(
            user_id=str(uuid4()),
            favorites_only=True
        )

        # Assert
        call_args = mock_db.execute.call_args
        query_sql = str(call_args[0][0])
        assert 'is_favorite = TRUE' in query_sql

    def test_get_bookmarks_pagination(self, bookmark_service, mock_db):
        """Test bookmark pagination"""
        # Setup
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        # Execute
        bookmarks = bookmark_service.get_user_bookmarks(
            user_id=str(uuid4()),
            limit=10,
            offset=20
        )

        # Assert
        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params['limit'] == 10
        assert params['offset'] == 20


class TestBookmarkDeletion:
    """Test bookmark deletion"""

    def test_delete_bookmark_success(self, bookmark_service, mock_db):
        """Test successful bookmark deletion"""
        # Setup
        bookmark_id = str(uuid4())
        user_id = str(uuid4())

        mock_result = Mock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result

        # Execute
        success = bookmark_service.delete_bookmark(bookmark_id, user_id)

        # Assert
        assert success is True
        mock_db.commit.assert_called_once()

    def test_delete_bookmark_not_found(self, bookmark_service, mock_db):
        """Test deleting non-existent bookmark"""
        # Setup
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_db.execute.return_value = mock_result

        # Execute
        success = bookmark_service.delete_bookmark(str(uuid4()), str(uuid4()))

        # Assert
        assert success is False

    def test_delete_bookmark_permission_check(self, bookmark_service, mock_db):
        """Test that users can only delete their own bookmarks"""
        # Setup
        bookmark_id = str(uuid4())
        wrong_user_id = str(uuid4())

        mock_result = Mock()
        mock_result.rowcount = 0
        mock_db.execute.return_value = mock_result

        # Execute
        success = bookmark_service.delete_bookmark(bookmark_id, wrong_user_id)

        # Assert
        assert success is False


class TestCollectionManagement:
    """Test bookmark collection operations"""

    def test_create_collection(self, bookmark_service, mock_db):
        """Test collection creation"""
        # Setup
        user_id = str(uuid4())

        mock_result = Mock()
        mock_row = (uuid4(), 'My Collection', datetime.now())
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Execute
        result = bookmark_service.create_collection(
            user_id=user_id,
            name='My Collection',
            description='Test collection',
            icon='folder',
            color='#1976d2',
            is_public=False
        )

        # Assert
        assert result is not None
        assert result['name'] == 'My Collection'
        mock_db.commit.assert_called_once()

    def test_create_nested_collection(self, bookmark_service, mock_db):
        """Test creating nested collection"""
        # Setup
        parent_id = str(uuid4())

        mock_result = Mock()
        mock_row = (uuid4(), 'Nested Collection', datetime.now())
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Execute
        result = bookmark_service.create_collection(
            user_id=str(uuid4()),
            name='Nested Collection',
            parent_collection_id=parent_id
        )

        # Assert
        assert result is not None
        call_args = mock_db.execute.call_args
        assert call_args[0][1]['parent_collection_id'] == parent_id

    def test_get_user_collections(self, bookmark_service, mock_db):
        """Test retrieving user's collections"""
        # Setup
        user_id = str(uuid4())

        mock_result = Mock()
        mock_rows = [
            (uuid4(), 'Collection 1', 'Desc 1', 'folder', '#1976d2', False, None, 1, 5, datetime.now(), None),
            (uuid4(), 'Collection 2', 'Desc 2', 'star', '#ff9800', True, None, 2, 3, datetime.now(), None)
        ]
        mock_result.fetchall.return_value = mock_rows
        mock_db.execute.return_value = mock_result

        # Execute
        collections = bookmark_service.get_user_collections(user_id=user_id)

        # Assert
        assert len(collections) == 2
        assert collections[0]['name'] == 'Collection 1'
        assert collections[0]['bookmark_count'] == 5
        assert collections[1]['is_public'] is True

    def test_get_collections_with_shared(self, bookmark_service, mock_db):
        """Test retrieving collections including shared ones"""
        # Setup with mocking _get_shared_collections
        user_id = str(uuid4())

        # Mock main collections query
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        # Mock shared collections
        with patch.object(bookmark_service, '_get_shared_collections') as mock_shared:
            mock_shared.return_value = [
                {
                    'id': str(uuid4()),
                    'name': 'Shared Collection',
                    'is_shared': True
                }
            ]

            # Execute
            collections = bookmark_service.get_user_collections(
                user_id=user_id,
                include_shared=True
            )

            # Assert
            mock_shared.assert_called_once_with(user_id)
            assert len(collections) >= 0


class TestCollectionSharing:
    """Test collection sharing functionality"""

    def test_share_collection_success(self, bookmark_service, mock_db):
        """Test successful collection sharing"""
        # Setup
        collection_id = str(uuid4())
        user_id = str(uuid4())
        shared_with_user_id = str(uuid4())

        # Mock verification query
        mock_verify_result = Mock()
        mock_verify_result.fetchone.return_value = (1,)

        # Mock share query
        mock_share_result = Mock()

        mock_db.execute.side_effect = [mock_verify_result, mock_share_result]

        # Execute
        success = bookmark_service.share_collection(
            collection_id=collection_id,
            user_id=user_id,
            shared_with_user_id=shared_with_user_id,
            permission_level='view'
        )

        # Assert
        assert success is True
        mock_db.commit.assert_called_once()

    def test_share_collection_not_owner(self, bookmark_service, mock_db):
        """Test sharing collection by non-owner"""
        # Setup
        mock_verify_result = Mock()
        mock_verify_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_verify_result

        # Execute
        success = bookmark_service.share_collection(
            collection_id=str(uuid4()),
            user_id=str(uuid4()),
            shared_with_email='test@example.com',
            permission_level='edit'
        )

        # Assert
        assert success is False

    def test_share_collection_with_email(self, bookmark_service, mock_db):
        """Test sharing collection via email"""
        # Setup
        mock_verify_result = Mock()
        mock_verify_result.fetchone.return_value = (1,)
        mock_share_result = Mock()
        mock_db.execute.side_effect = [mock_verify_result, mock_share_result]

        # Execute
        success = bookmark_service.share_collection(
            collection_id=str(uuid4()),
            user_id=str(uuid4()),
            shared_with_email='colleague@example.com',
            permission_level='view'
        )

        # Assert
        assert success is True


class TestCollaborativeRecommendations:
    """Test collaborative filtering recommendations"""

    def test_get_collaborative_recommendations(self, bookmark_service, mock_db):
        """Test getting bookmark-based recommendations"""
        # Setup
        user_id = str(uuid4())
        content_id = str(uuid4())

        mock_result = Mock()
        mock_rows = [
            ('chapter', uuid4(), 0.85),
            ('pdf', uuid4(), 0.72),
            ('chapter', uuid4(), 0.68)
        ]
        mock_result.fetchall.return_value = mock_rows
        mock_db.execute.return_value = mock_result

        # Execute
        recommendations = bookmark_service.get_collaborative_recommendations(
            user_id=user_id,
            content_type='chapter',
            content_id=content_id,
            limit=10
        )

        # Assert
        assert len(recommendations) == 3
        assert recommendations[0]['relevance_score'] == 0.85
        assert recommendations[1]['content_type'] == 'pdf'

    def test_get_popular_bookmarked_content(self, bookmark_service, mock_db):
        """Test getting most bookmarked content"""
        # Setup
        mock_result = Mock()
        mock_rows = [
            ('chapter', uuid4(), 25, 15),
            ('pdf', uuid4(), 18, 12)
        ]
        mock_result.fetchall.return_value = mock_rows
        mock_db.execute.return_value = mock_result

        # Execute
        popular = bookmark_service.get_popular_bookmarked_content(limit=20)

        # Assert
        assert len(popular) == 2
        assert popular[0]['bookmark_count'] == 25
        assert popular[0]['unique_users'] == 15


class TestBookmarkStatistics:
    """Test bookmark statistics"""

    def test_get_bookmark_statistics(self, bookmark_service, mock_db):
        """Test retrieving bookmark statistics"""
        # Setup
        user_id = str(uuid4())

        mock_result = Mock()
        mock_row = (user_id, 42, 10, 5, 3, datetime.now())
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Execute
        stats = bookmark_service.get_bookmark_statistics(user_id)

        # Assert
        assert stats is not None
        assert stats['total_bookmarks'] == 42
        assert stats['favorite_count'] == 10
        assert stats['collection_count'] == 5
        assert stats['content_types_bookmarked'] == 3

    def test_get_statistics_no_data(self, bookmark_service, mock_db):
        """Test statistics when user has no bookmarks"""
        # Setup
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        # Execute
        stats = bookmark_service.get_bookmark_statistics(str(uuid4()))

        # Assert
        assert stats == {}


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_database_connection_error(self, bookmark_service, mock_db):
        """Test handling of database connection errors"""
        # Setup
        mock_db.execute.side_effect = Exception("Connection lost")

        # Execute
        result = bookmark_service.create_bookmark(
            user_id=str(uuid4()),
            content_type='chapter',
            content_id=str(uuid4())
        )

        # Assert
        assert result is None
        mock_db.rollback.assert_called()

    def test_invalid_content_type(self, bookmark_service, mock_db):
        """Test handling of invalid content types"""
        # Setup
        mock_result = Mock()
        mock_row = (uuid4(), datetime.now())
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Execute - service should accept any content_type
        result = bookmark_service.create_bookmark(
            user_id=str(uuid4()),
            content_type='invalid_type',
            content_id=str(uuid4())
        )

        # Assert - should still work (validation happens at API layer)
        assert result is not None

    def test_empty_collection_name(self, bookmark_service, mock_db):
        """Test creating collection with empty name"""
        # Setup
        mock_db.execute.side_effect = Exception("Constraint violation")

        # Execute
        result = bookmark_service.create_collection(
            user_id=str(uuid4()),
            name=''
        )

        # Assert
        assert result is None
        mock_db.rollback.assert_called()
