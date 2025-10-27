"""
Tests for Metrics Service
Tests dashboard metrics calculation, retrieval, and trend analysis
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from sqlalchemy.orm import Session

from backend.services.metrics_service import MetricsService


@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def metrics_service(mock_db):
    """Metrics service instance"""
    return MetricsService(mock_db)


@pytest.fixture
def sample_metric():
    """Sample metric data"""
    return {
        'id': 'metric-123',
        'metric_key': 'total_users',
        'metric_name': 'Total Users',
        'metric_description': 'Total number of registered users',
        'metric_value': 150,
        'metric_unit': 'users',
        'metric_category': 'users',
        'previous_value': 140,
        'change_percentage': 7.14,
        'trend': 'up',
        'metadata': {},
        'last_calculated_at': datetime.now().isoformat(),
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }


class TestMetricUpdate:
    """Tests for metric update functionality"""

    def test_update_all_metrics(self, metrics_service, mock_db):
        """Test updating all dashboard metrics"""
        # Mock execute and fetchone for getting count
        mock_result = Mock()
        mock_result.fetchone.return_value = [6]

        # Mock execute to return mock_result for count query
        def execute_side_effect(query, *args, **kwargs):
            if 'COUNT' in str(query):
                return mock_result
            return Mock()

        mock_db.execute.side_effect = execute_side_effect

        result = metrics_service.update_all_metrics()

        assert result['success'] is True
        assert result['metrics_updated'] == 6
        assert 'updated_at' in result
        mock_db.commit.assert_called_once()

    def test_update_all_metrics_error(self, metrics_service, mock_db):
        """Test updating metrics with database error"""
        mock_db.execute.side_effect = Exception('Database error')

        result = metrics_service.update_all_metrics()

        assert result['success'] is False
        assert 'error' in result
        mock_db.rollback.assert_called_once()

    def test_update_specific_metric(self, metrics_service, mock_db):
        """Test updating a specific metric"""
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result

        result = metrics_service.update_specific_metric(
            metric_key='total_users',
            metric_value=150,
            previous_value=140
        )

        assert result['success'] is True
        assert result['metric_value'] == 150
        assert result['change_percentage'] is not None
        assert result['trend'] == 'up'
        mock_db.commit.assert_called_once()

    def test_update_specific_metric_not_found(self, metrics_service, mock_db):
        """Test updating non-existent metric"""
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_db.execute.return_value = mock_result

        result = metrics_service.update_specific_metric(
            metric_key='nonexistent',
            metric_value=100
        )

        assert result['success'] is False
        assert 'not found' in result['error']

    def test_update_metric_with_trend_calculation(self, metrics_service, mock_db):
        """Test metric update with trend calculation"""
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result

        # Test upward trend
        result_up = metrics_service.update_specific_metric(
            metric_key='searches',
            metric_value=200,
            previous_value=150
        )
        assert result_up['trend'] == 'up'
        assert result_up['change_percentage'] > 0

        # Test downward trend
        result_down = metrics_service.update_specific_metric(
            metric_key='errors',
            metric_value=5,
            previous_value=10
        )
        assert result_down['trend'] == 'down'
        assert result_down['change_percentage'] < 0

        # Test stable
        result_stable = metrics_service.update_specific_metric(
            metric_key='stable_metric',
            metric_value=100,
            previous_value=100
        )
        assert result_stable['trend'] == 'stable'
        assert result_stable['change_percentage'] == 0


class TestMetricCreation:
    """Tests for custom metric creation"""

    def test_create_custom_metric(self, metrics_service, mock_db):
        """Test creating a new custom metric"""
        mock_result = Mock()
        mock_result.fetchone.return_value = ['metric-uuid-123']
        mock_db.execute.return_value = mock_result

        result = metrics_service.create_custom_metric(
            metric_key='custom_metric',
            metric_name='Custom Metric',
            metric_value=100,
            metric_category='custom',
            metric_description='A custom metric',
            metric_unit='units'
        )

        assert result['success'] is True
        assert result['metric_id'] == 'metric-uuid-123'
        assert result['metric_key'] == 'custom_metric'
        mock_db.commit.assert_called_once()

    def test_create_custom_metric_with_metadata(self, metrics_service, mock_db):
        """Test creating custom metric with metadata"""
        mock_result = Mock()
        mock_result.fetchone.return_value = ['metric-uuid-123']
        mock_db.execute.return_value = mock_result

        result = metrics_service.create_custom_metric(
            metric_key='advanced_metric',
            metric_name='Advanced Metric',
            metric_value=250,
            metric_category='custom',
            metadata={
                'source': 'external_api',
                'calculation': 'complex',
                'tags': ['important', 'monitored']
            }
        )

        assert result['success'] is True
        mock_db.commit.assert_called_once()

    def test_create_custom_metric_error(self, metrics_service, mock_db):
        """Test metric creation with error"""
        mock_db.execute.side_effect = Exception('Duplicate key error')

        result = metrics_service.create_custom_metric(
            metric_key='duplicate',
            metric_name='Duplicate',
            metric_value=0,
            metric_category='test'
        )

        assert result['success'] is False
        assert 'error' in result
        mock_db.rollback.assert_called_once()


class TestMetricRetrieval:
    """Tests for metric retrieval functionality"""

    def test_get_metric(self, metrics_service, mock_db):
        """Test getting a specific metric"""
        mock_result = Mock()
        mock_result.fetchone.return_value = (
            'metric-123',
            'total_users',
            'Total Users',
            'Total registered users',
            150,
            'users',
            'users',
            140,
            7.14,
            'up',
            {},
            datetime.now(),
            datetime.now(),
            datetime.now()
        )
        mock_db.execute.return_value = mock_result

        metric = metrics_service.get_metric('total_users')

        assert metric is not None
        assert metric['metric_key'] == 'total_users'
        assert metric['metric_value'] == 150.0
        assert metric['trend'] == 'up'

    def test_get_metric_not_found(self, metrics_service, mock_db):
        """Test getting non-existent metric"""
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        metric = metrics_service.get_metric('nonexistent')

        assert metric is None

    def test_get_all_metrics(self, metrics_service, mock_db):
        """Test getting all metrics"""
        mock_db.execute.return_value = [
            ('id1', 'total_users', 'Total Users', 'Desc', 150, 'users', 'users', 140, 7.14, 'up', {}, datetime.now(), datetime.now(), datetime.now()),
            ('id2', 'total_chapters', 'Total Chapters', 'Desc', 50, 'chapters', 'content', 45, 11.11, 'up', {}, datetime.now(), datetime.now(), datetime.now())
        ]

        metrics = metrics_service.get_all_metrics()

        assert len(metrics) == 2
        assert metrics[0]['metric_key'] == 'total_users'
        assert metrics[1]['metric_key'] == 'total_chapters'

    def test_get_all_metrics_filtered_by_category(self, metrics_service, mock_db):
        """Test getting metrics filtered by category"""
        mock_db.execute.return_value = [
            ('id1', 'total_users', 'Total Users', 'Desc', 150, 'users', 'users', 140, 7.14, 'up', {}, datetime.now(), datetime.now(), datetime.now())
        ]

        metrics = metrics_service.get_all_metrics(category='users')

        assert len(metrics) == 1
        assert metrics[0]['metric_category'] == 'users'

    def test_get_metrics_by_category(self, metrics_service, mock_db):
        """Test getting metrics grouped by category"""
        mock_db.execute.return_value = [
            ('id1', 'total_users', 'Total Users', 'Desc', 150, 'users', 'users', 140, 7.14, 'up', {}, datetime.now(), datetime.now(), datetime.now()),
            ('id2', 'total_chapters', 'Total Chapters', 'Desc', 50, 'chapters', 'content', 45, 11.11, 'up', {}, datetime.now(), datetime.now(), datetime.now())
        ]

        by_category = metrics_service.get_metrics_by_category()

        assert 'users' in by_category
        assert 'content' in by_category
        assert len(by_category['users']) == 1
        assert len(by_category['content']) == 1

    def test_get_metric_count(self, metrics_service, mock_db):
        """Test getting total metric count"""
        mock_result = Mock()
        mock_result.fetchone.return_value = [6]
        mock_db.execute.return_value = mock_result

        count = metrics_service.get_metric_count()

        assert count == 6


class TestDashboardSummary:
    """Tests for dashboard summary functionality"""

    def test_get_dashboard_summary(self, metrics_service, mock_db):
        """Test getting complete dashboard summary"""
        # Mock get_all_metrics
        mock_db.execute.return_value = [
            ('id1', 'metric1', 'Metric 1', 'Desc', 100, 'units', 'users', 90, 11.11, 'up', {}, datetime.now(), datetime.now(), datetime.now()),
            ('id2', 'metric2', 'Metric 2', 'Desc', 50, 'units', 'content', 45, 11.11, 'up', {}, datetime.now(), datetime.now(), datetime.now())
        ]

        # Mock timestamp query
        def execute_side_effect(query, *args, **kwargs):
            if 'MIN' in str(query) or 'MAX' in str(query):
                mock_result = Mock()
                mock_result.fetchone.return_value = (datetime.now(), datetime.now())
                return mock_result
            return [
                ('id1', 'metric1', 'Metric 1', 'Desc', 100, 'units', 'users', 90, 11.11, 'up', {}, datetime.now(), datetime.now(), datetime.now()),
                ('id2', 'metric2', 'Metric 2', 'Desc', 50, 'units', 'content', 45, 11.11, 'up', {}, datetime.now(), datetime.now(), datetime.now())
            ]

        mock_db.execute.side_effect = execute_side_effect

        summary = metrics_service.get_dashboard_summary()

        assert summary['success'] is True
        assert 'summary' in summary
        assert 'metrics_by_category' in summary
        assert summary['summary']['total_metrics'] == 2

    def test_get_key_metrics(self, metrics_service, mock_db):
        """Test getting key metrics"""
        mock_result = Mock()
        mock_result.fetchone.return_value = (
            'id', 'total_users', 'Total Users', 'Desc', 150, 'users', 'users',
            140, 7.14, 'up', {}, datetime.now(), datetime.now(), datetime.now()
        )
        mock_db.execute.return_value = mock_result

        key_metrics = metrics_service.get_key_metrics()

        assert key_metrics['success'] is True
        assert 'key_metrics' in key_metrics


class TestTrendAnalysis:
    """Tests for trend analysis functionality"""

    def test_calculate_metric_trends(self, metrics_service, mock_db):
        """Test calculating trends for a metric"""
        mock_result = Mock()
        mock_result.fetchone.return_value = (
            'id', 'total_users', 'Total Users', 'Desc', 150, 'users', 'users',
            140, 7.14, 'up', {}, datetime.now(), datetime.now(), datetime.now()
        )
        mock_db.execute.return_value = mock_result

        trends = metrics_service.calculate_metric_trends(
            metric_key='total_users',
            lookback_days=7
        )

        assert trends['success'] is True
        assert trends['metric_key'] == 'total_users'
        assert trends['current_value'] == 150.0
        assert trends['trend'] == 'up'

    def test_calculate_metric_trends_not_found(self, metrics_service, mock_db):
        """Test trend calculation for non-existent metric"""
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        trends = metrics_service.calculate_metric_trends(
            metric_key='nonexistent'
        )

        assert trends['success'] is False
        assert 'not found' in trends['error']

    def test_get_trending_metrics(self, metrics_service, mock_db):
        """Test getting top trending metrics"""
        def execute_side_effect(query, *args, **kwargs):
            if 'trend = \'up\'' in str(query):
                # Return trending up metrics
                return [
                    ('searches', 'Total Searches', 200, 150, 33.33, 'up'),
                    ('exports', 'Total Exports', 50, 40, 25.0, 'up')
                ]
            elif 'trend = \'down\'' in str(query):
                # Return trending down metrics
                return [
                    ('errors', 'Error Count', 5, 10, -50.0, 'down')
                ]
            return []

        mock_db.execute.side_effect = execute_side_effect

        trending = metrics_service.get_trending_metrics(limit=5)

        assert trending['success'] is True
        assert len(trending['trending_up']) == 2
        assert len(trending['trending_down']) == 1
        assert trending['trending_up'][0]['metric_key'] == 'searches'


class TestUtilityMethods:
    """Tests for utility methods"""

    def test_delete_metric(self, metrics_service, mock_db):
        """Test deleting a metric"""
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result

        result = metrics_service.delete_metric('custom_metric')

        assert result['success'] is True
        assert result['metric_key'] == 'custom_metric'
        mock_db.commit.assert_called_once()

    def test_delete_metric_not_found(self, metrics_service, mock_db):
        """Test deleting non-existent metric"""
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_db.execute.return_value = mock_result

        result = metrics_service.delete_metric('nonexistent')

        assert result['success'] is False
        assert 'not found' in result['error']

    def test_reset_all_metrics(self, metrics_service, mock_db):
        """Test resetting all metrics"""
        mock_result = Mock()
        mock_result.rowcount = 6
        mock_db.execute.return_value = mock_result

        result = metrics_service.reset_all_metrics()

        assert result['success'] is True
        assert result['metrics_reset'] == 6
        mock_db.commit.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
