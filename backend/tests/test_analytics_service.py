"""
Tests for Analytics Service
Tests event tracking, querying, and aggregation functionality
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session

from backend.services.analytics_service import AnalyticsService, AnalyticsEvent


@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def analytics_service(mock_db):
    """Analytics service instance"""
    return AnalyticsService(mock_db)


@pytest.fixture
def sample_event():
    """Sample analytics event"""
    return AnalyticsEvent(
        event_type='search',
        event_category='search',
        user_id='user-123',
        resource_type='chapter',
        resource_id='chapter-456',
        metadata={'query': 'test search'},
        duration_ms=150,
        success=True
    )


class TestAnalyticsEventModel:
    """Tests for AnalyticsEvent model"""

    def test_event_initialization(self, sample_event):
        """Test event initialization with all fields"""
        assert sample_event.event_type == 'search'
        assert sample_event.event_category == 'search'
        assert sample_event.user_id == 'user-123'
        assert sample_event.resource_type == 'chapter'
        assert sample_event.resource_id == 'chapter-456'
        assert sample_event.metadata == {'query': 'test search'}
        assert sample_event.duration_ms == 150
        assert sample_event.success is True

    def test_event_optional_fields(self):
        """Test event with minimal required fields"""
        event = AnalyticsEvent(
            event_type='login',
            event_category='user'
        )

        assert event.event_type == 'login'
        assert event.event_category == 'user'
        assert event.user_id is None
        assert event.metadata == {}
        assert event.success is True


class TestEventTracking:
    """Tests for event tracking functionality"""

    def test_track_event_success(self, analytics_service, mock_db):
        """Test successful event tracking"""
        # Mock database execute to return event ID
        mock_result = Mock()
        mock_result.fetchone.return_value = ['event-uuid-123']
        mock_db.execute.return_value = mock_result

        result = analytics_service.track_event(
            event_type='chapter_create',
            event_category='content',
            user_id='user-123',
            resource_type='chapter',
            resource_id='chapter-456'
        )

        assert result['success'] is True
        assert result['event_id'] == 'event-uuid-123'
        assert result['event_type'] == 'chapter_create'
        mock_db.commit.assert_called_once()

    def test_track_event_with_metadata(self, analytics_service, mock_db):
        """Test event tracking with metadata"""
        mock_result = Mock()
        mock_result.fetchone.return_value = ['event-uuid-123']
        mock_db.execute.return_value = mock_result

        result = analytics_service.track_event(
            event_type='search',
            event_category='search',
            user_id='user-123',
            metadata={
                'query': 'brain tumor',
                'results_count': 15,
                'filters': ['recent']
            }
        )

        assert result['success'] is True
        mock_db.execute.assert_called_once()

    def test_track_event_with_duration(self, analytics_service, mock_db):
        """Test event tracking with duration"""
        mock_result = Mock()
        mock_result.fetchone.return_value = ['event-uuid-123']
        mock_db.execute.return_value = mock_result

        result = analytics_service.track_event(
            event_type='export',
            event_category='export',
            duration_ms=2500
        )

        assert result['success'] is True
        assert result['event_type'] == 'export'

    def test_track_event_failure(self, analytics_service, mock_db):
        """Test event tracking with error"""
        mock_result = Mock()
        mock_result.fetchone.return_value = ['event-uuid-123']
        mock_db.execute.return_value = mock_result

        result = analytics_service.track_event(
            event_type='pdf_upload',
            event_category='content',
            success=False,
            error_message='File too large'
        )

        assert result['success'] is True
        assert result['event_type'] == 'pdf_upload'

    def test_track_event_database_error(self, analytics_service, mock_db):
        """Test event tracking with database error"""
        mock_db.execute.side_effect = Exception('Database connection error')

        result = analytics_service.track_event(
            event_type='search',
            event_category='search'
        )

        assert result['success'] is False
        assert 'error' in result
        mock_db.rollback.assert_called_once()


class TestEventQuerying:
    """Tests for event querying functionality"""

    def test_get_events_all(self, analytics_service, mock_db):
        """Test getting all events"""
        # Mock database result
        mock_db.execute.return_value = [
            ('id1', 'search', 'search', 'user1', 'chapter', 'ch1', {}, None, None, None, 100, True, None, datetime.now()),
            ('id2', 'export', 'export', 'user2', 'chapter', 'ch2', {}, None, None, None, 200, True, None, datetime.now())
        ]

        events = analytics_service.get_events(limit=10)

        assert len(events) == 2
        assert events[0]['event_type'] == 'search'
        assert events[1]['event_type'] == 'export'

    def test_get_events_filtered_by_type(self, analytics_service, mock_db):
        """Test getting events filtered by type"""
        mock_db.execute.return_value = [
            ('id1', 'search', 'search', 'user1', None, None, {}, None, None, None, 100, True, None, datetime.now())
        ]

        events = analytics_service.get_events(event_type='search', limit=10)

        assert len(events) == 1
        assert events[0]['event_type'] == 'search'

    def test_get_events_filtered_by_user(self, analytics_service, mock_db):
        """Test getting events filtered by user"""
        mock_db.execute.return_value = [
            ('id1', 'search', 'search', 'user-123', None, None, {}, None, None, None, 100, True, None, datetime.now())
        ]

        events = analytics_service.get_events(user_id='user-123', limit=10)

        assert len(events) == 1
        assert events[0]['user_id'] == 'user-123'

    def test_get_events_filtered_by_date_range(self, analytics_service, mock_db):
        """Test getting events filtered by date range"""
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()

        mock_db.execute.return_value = []

        events = analytics_service.get_events(
            start_date=start_date,
            end_date=end_date,
            limit=10
        )

        assert isinstance(events, list)

    def test_get_event_count(self, analytics_service, mock_db):
        """Test getting event count"""
        mock_result = Mock()
        mock_result.fetchone.return_value = [42]
        mock_db.execute.return_value = mock_result

        count = analytics_service.get_event_count(event_type='search')

        assert count == 42

    def test_get_event_count_with_filters(self, analytics_service, mock_db):
        """Test getting event count with multiple filters"""
        mock_result = Mock()
        mock_result.fetchone.return_value = [10]
        mock_db.execute.return_value = mock_result

        count = analytics_service.get_event_count(
            event_type='export',
            user_id='user-123',
            success=True
        )

        assert count == 10


class TestAggregation:
    """Tests for aggregation functionality"""

    def test_get_daily_aggregates(self, analytics_service, mock_db):
        """Test getting daily aggregates"""
        mock_db.execute.return_value = [
            ('id1', datetime.now(), datetime.now(), 'event_count', 'search', None, 150, {}, datetime.now(), datetime.now())
        ]

        aggregates = analytics_service.get_daily_aggregates(
            metric_type='event_count',
            metric_category='search',
            limit=30
        )

        assert len(aggregates) == 1
        assert aggregates[0]['metric_type'] == 'event_count'
        assert aggregates[0]['value'] == 150.0

    def test_calculate_aggregates_for_date(self, analytics_service, mock_db):
        """Test calculating aggregates for specific date"""
        target_date = date.today() - timedelta(days=1)

        result = analytics_service.calculate_aggregates_for_date(target_date)

        assert result['success'] is True
        assert result['date'] == target_date.isoformat()
        mock_db.commit.assert_called_once()

    def test_calculate_aggregates_error(self, analytics_service, mock_db):
        """Test aggregate calculation with error"""
        mock_db.execute.side_effect = Exception('Calculation error')

        result = analytics_service.calculate_aggregates_for_date(date.today())

        assert result['success'] is False
        assert 'error' in result
        mock_db.rollback.assert_called_once()


class TestAnalyticsQueries:
    """Tests for analytics query methods"""

    def test_get_user_activity_summary(self, analytics_service, mock_db):
        """Test getting user activity summary"""
        mock_result = Mock()
        mock_result.fetchone.return_value = (
            100,  # total_events
            10,   # active_days
            30,   # searches
            5,    # exports
            2,    # chapters_created
            1,    # pdfs_uploaded
            150.5,  # avg_duration_ms
            datetime.now()  # last_activity
        )
        mock_db.execute.return_value = mock_result

        summary = analytics_service.get_user_activity_summary(
            user_id='user-123'
        )

        assert summary['user_id'] == 'user-123'
        assert summary['total_events'] == 100
        assert summary['active_days'] == 10
        assert summary['searches'] == 30
        assert summary['exports'] == 5

    def test_get_popular_content(self, analytics_service, mock_db):
        """Test getting popular content"""
        mock_db.execute.return_value = [
            ('chapter', 'ch-123', 150, 50, datetime.now()),
            ('chapter', 'ch-456', 100, 30, datetime.now())
        ]

        popular = analytics_service.get_popular_content(
            resource_type='chapter',
            limit=10
        )

        assert len(popular) == 2
        assert popular[0]['view_count'] == 150
        assert popular[0]['unique_viewers'] == 50

    def test_get_event_timeline(self, analytics_service, mock_db):
        """Test getting event timeline"""
        mock_db.execute.return_value = [
            (datetime.now(), 50, 10),
            (datetime.now() - timedelta(days=1), 45, 8)
        ]

        timeline = analytics_service.get_event_timeline(
            event_type='search',
            interval='1 day'
        )

        assert len(timeline) == 2
        assert timeline[0]['event_count'] == 50
        assert timeline[0]['unique_users'] == 10

    def test_get_system_health_metrics(self, analytics_service, mock_db):
        """Test getting system health metrics"""
        mock_result = Mock()
        mock_result.fetchone.return_value = (
            1000,    # total_events
            125.5,   # avg_response_time_ms
            250.0,   # p95_response_time_ms
            500.0,   # p99_response_time_ms
            99.5,    # success_rate
            50,      # active_users
            75,      # total_sessions
            5        # error_count
        )
        mock_db.execute.return_value = mock_result

        health = analytics_service.get_system_health_metrics()

        assert health['total_events'] == 1000
        assert health['avg_response_time_ms'] == 125.5
        assert health['success_rate'] == 99.5
        assert health['error_count'] == 5


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_get_events_empty_result(self, analytics_service, mock_db):
        """Test getting events with no results"""
        mock_db.execute.return_value = []

        events = analytics_service.get_events(event_type='nonexistent')

        assert events == []

    def test_get_event_count_error(self, analytics_service, mock_db):
        """Test event count with database error"""
        mock_db.execute.side_effect = Exception('Database error')

        count = analytics_service.get_event_count()

        assert count == 0

    def test_get_popular_content_no_views(self, analytics_service, mock_db):
        """Test getting popular content with no views"""
        mock_db.execute.return_value = []

        popular = analytics_service.get_popular_content()

        assert popular == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
