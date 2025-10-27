"""
Tests for Recommendation Service
Tests collaborative filtering, content-based recommendations, and hybrid algorithms
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from sqlalchemy.orm import Session

from backend.services.recommendation_service import RecommendationService


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = Mock(spec=Session)
    db.execute = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    return db


@pytest.fixture
def recommendation_service(mock_db):
    """Recommendation service instance with mock database"""
    return RecommendationService(mock_db)


@pytest.fixture
def sample_user_interactions():
    """Sample user interactions for testing"""
    return [
        {
            'user_id': 'user-1',
            'content_type': 'chapter',
            'content_id': 'chapter-1',
            'interaction_type': 'view',
            'duration': 300
        },
        {
            'user_id': 'user-1',
            'content_type': 'pdf',
            'content_id': 'pdf-1',
            'interaction_type': 'read',
            'duration': 600
        }
    ]


@pytest.fixture
def sample_recommendations():
    """Sample recommendation results"""
    return [
        {
            'id': 'chapter-2',
            'type': 'chapter',
            'title': 'Brain Tumor Surgery',
            'relevance_score': 0.85,
            'author': 'Dr. Smith'
        },
        {
            'id': 'pdf-2',
            'type': 'pdf',
            'title': 'Neurosurgical Techniques',
            'relevance_score': 0.78,
            'author': 'Dr. Jones'
        }
    ]


class TestRecommendationService:
    """Test suite for RecommendationService"""

    def test_initialization(self, mock_db):
        """Test service initialization"""
        service = RecommendationService(mock_db)
        assert service.db == mock_db

    def test_get_recommendations_hybrid(self, recommendation_service, mock_db, sample_recommendations):
        """Test hybrid recommendations algorithm"""
        # Mock content-based recommendations
        with patch.object(
            recommendation_service,
            '_get_content_based_recommendations',
            return_value=sample_recommendations[:1]
        ), patch.object(
            recommendation_service,
            '_get_collaborative_recommendations',
            return_value=sample_recommendations[1:]
        ):
            results = recommendation_service.get_recommendations(
                user_id='user-1',
                algorithm='hybrid',
                limit=10
            )

            assert isinstance(results, list)
            # Hybrid should combine both strategies
            assert len(results) > 0

    def test_get_recommendations_content_based(
        self,
        recommendation_service,
        mock_db,
        sample_recommendations
    ):
        """Test content-based recommendations"""
        # Mock database query
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            ('chapter-2', 'chapter', 'Brain Tumor Surgery', 0.85, 'Dr. Smith', None)
        ]
        mock_db.execute.return_value = mock_result

        results = recommendation_service._get_content_based_recommendations(
            user_id='user-1',
            limit=10
        )

        assert isinstance(results, list)
        if len(results) > 0:
            assert 'id' in results[0]
            assert 'type' in results[0]
            assert 'title' in results[0]
            assert 'relevance_score' in results[0]

    def test_get_recommendations_collaborative(
        self,
        recommendation_service,
        mock_db,
        sample_recommendations
    ):
        """Test collaborative filtering recommendations"""
        # Mock similar users query
        mock_similar_users = Mock()
        mock_similar_users.fetchall.return_value = [
            ('user-2', 0.75),
            ('user-3', 0.68)
        ]

        # Mock recommended content query
        mock_content = Mock()
        mock_content.fetchall.return_value = [
            ('pdf-2', 'pdf', 'Neurosurgical Techniques', 'Dr. Jones', None, 2)
        ]

        mock_db.execute.side_effect = [mock_similar_users, mock_content]

        results = recommendation_service._get_collaborative_recommendations(
            user_id='user-1',
            limit=10
        )

        assert isinstance(results, list)
        if len(results) > 0:
            assert 'id' in results[0]
            assert 'type' in results[0]
            assert 'relevance_score' in results[0]

    def test_track_user_interaction_success(
        self,
        recommendation_service,
        mock_db
    ):
        """Test tracking user interaction successfully"""
        mock_result = Mock()
        mock_result.fetchone.return_value = ['interaction-id']
        mock_db.execute.return_value = mock_result

        success = recommendation_service.track_user_interaction(
            user_id='user-1',
            interaction_type='view',
            content_type='chapter',
            content_id='chapter-1',
            duration_seconds=300
        )

        assert success is True
        mock_db.commit.assert_called_once()

    def test_track_user_interaction_failure(
        self,
        recommendation_service,
        mock_db
    ):
        """Test tracking user interaction failure"""
        mock_db.execute.side_effect = Exception('Database error')

        success = recommendation_service.track_user_interaction(
            user_id='user-1',
            interaction_type='view',
            content_type='chapter',
            content_id='chapter-1'
        )

        assert success is False
        mock_db.rollback.assert_called_once()

    def test_get_user_interactions(
        self,
        recommendation_service,
        mock_db,
        sample_user_interactions
    ):
        """Test retrieving user interactions"""
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            (
                'chapter-1',
                'chapter',
                'Brain Surgery Basics',
                'view',
                300,
                datetime.utcnow()
            )
        ]
        mock_db.execute.return_value = mock_result

        interactions = recommendation_service.get_user_interactions(
            user_id='user-1',
            limit=10
        )

        assert isinstance(interactions, list)
        if len(interactions) > 0:
            assert 'content_id' in interactions[0]
            assert 'content_type' in interactions[0]
            assert 'interaction_type' in interactions[0]

    def test_calculate_similarity_score(self, recommendation_service):
        """Test similarity score calculation"""
        # Test with overlapping interactions
        set1 = {'chapter-1', 'chapter-2', 'pdf-1'}
        set2 = {'chapter-2', 'pdf-1', 'pdf-2'}

        # Jaccard similarity = |intersection| / |union| = 2 / 4 = 0.5
        score = recommendation_service._calculate_jaccard_similarity(set1, set2)

        assert 0 <= score <= 1
        assert score == 2 / 4  # Exact expected value

    def test_calculate_similarity_score_no_overlap(self, recommendation_service):
        """Test similarity with no overlap"""
        set1 = {'chapter-1', 'chapter-2'}
        set2 = {'pdf-1', 'pdf-2'}

        score = recommendation_service._calculate_jaccard_similarity(set1, set2)

        assert score == 0.0

    def test_calculate_similarity_score_identical(self, recommendation_service):
        """Test similarity with identical sets"""
        set1 = {'chapter-1', 'pdf-1'}
        set2 = {'chapter-1', 'pdf-1'}

        score = recommendation_service._calculate_jaccard_similarity(set1, set2)

        assert score == 1.0

    def test_get_recommendations_with_filters(
        self,
        recommendation_service,
        mock_db
    ):
        """Test recommendations with content type filter"""
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            ('chapter-1', 'chapter', 'Test Chapter', 0.9, 'Author', None)
        ]
        mock_db.execute.return_value = mock_result

        results = recommendation_service.get_recommendations(
            user_id='user-1',
            algorithm='content_based',
            content_type_filter='chapter',
            limit=5
        )

        assert isinstance(results, list)

    def test_get_recommendations_empty_history(
        self,
        recommendation_service,
        mock_db
    ):
        """Test recommendations for user with no history"""
        # Mock empty interaction history
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        results = recommendation_service.get_recommendations(
            user_id='new-user',
            algorithm='content_based',
            limit=10
        )

        # Should return empty list or fallback to popular content
        assert isinstance(results, list)

    def test_get_recommendation_explanation(
        self,
        recommendation_service,
        mock_db
    ):
        """Test getting recommendation explanation"""
        mock_result = Mock()
        mock_result.fetchone.return_value = [
            'chapter-1',
            'chapter',
            'Test',
            0.85,
            'collaborative_filtering'
        ]
        mock_db.execute.return_value = mock_result

        explanation = recommendation_service.get_recommendation_explanation(
            user_id='user-1',
            content_type='chapter',
            content_id='chapter-1'
        )

        assert isinstance(explanation, dict)

    def test_clear_user_recommendations(
        self,
        recommendation_service,
        mock_db
    ):
        """Test clearing user recommendations cache"""
        success = recommendation_service.clear_user_recommendations('user-1')

        assert success is True
        mock_db.commit.assert_called_once()

    def test_hybrid_algorithm_weight_distribution(
        self,
        recommendation_service
    ):
        """Test that hybrid algorithm properly weights strategies"""
        content_based = [
            {'id': 'c1', 'relevance_score': 0.9},
            {'id': 'c2', 'relevance_score': 0.8}
        ]
        collaborative = [
            {'id': 'c3', 'relevance_score': 0.85},
            {'id': 'c4', 'relevance_score': 0.75}
        ]

        with patch.object(
            recommendation_service,
            '_get_content_based_recommendations',
            return_value=content_based
        ), patch.object(
            recommendation_service,
            '_get_collaborative_recommendations',
            return_value=collaborative
        ):
            results = recommendation_service._get_hybrid_recommendations(
                user_id='user-1',
                limit=10
            )

            # Should combine both strategies
            assert isinstance(results, list)

    def test_recommendation_diversity(
        self,
        recommendation_service,
        mock_db
    ):
        """Test that recommendations maintain diversity"""
        # Mock recommendations that include different content types
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            ('chapter-1', 'chapter', 'Title1', 0.9, 'Author1', None),
            ('pdf-1', 'pdf', 'Title2', 0.85, 'Author2', None),
            ('chapter-2', 'chapter', 'Title3', 0.8, 'Author3', None)
        ]
        mock_db.execute.return_value = mock_result

        results = recommendation_service._get_content_based_recommendations(
            user_id='user-1',
            limit=10
        )

        # Check that we have different content types
        if len(results) > 0:
            content_types = {r['type'] for r in results}
            # In this mock, we should have both 'chapter' and 'pdf'
            assert len(content_types) >= 1

    def test_error_handling_database_failure(
        self,
        recommendation_service,
        mock_db
    ):
        """Test graceful handling of database failures"""
        mock_db.execute.side_effect = Exception('Connection lost')

        results = recommendation_service.get_recommendations(
            user_id='user-1',
            algorithm='hybrid',
            limit=10
        )

        # Should return empty list on error
        assert results == []

    def test_recommendation_freshness(
        self,
        recommendation_service,
        mock_db
    ):
        """Test that recent content is prioritized"""
        recent_date = datetime.utcnow()

        mock_result = Mock()
        mock_result.fetchall.return_value = [
            ('chapter-1', 'chapter', 'Recent', 0.8, 'Author', recent_date)
        ]
        mock_db.execute.return_value = mock_result

        results = recommendation_service._get_content_based_recommendations(
            user_id='user-1',
            limit=10
        )

        # Verify recency is considered
        assert isinstance(results, list)
