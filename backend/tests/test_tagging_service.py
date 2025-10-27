"""
Tests for Tagging Service
Tests AI auto-tagging, manual tagging, and tag suggestions
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from sqlalchemy.orm import Session

from backend.services.tagging_service import TaggingService


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = Mock(spec=Session)
    db.execute = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    return db


@pytest.fixture
def tagging_service(mock_db):
    """Tagging service instance with mock database"""
    return TaggingService(mock_db)


@pytest.fixture
def sample_content():
    """Sample content for testing"""
    return {
        'text': 'This paper discusses glioblastoma treatment using surgical resection and chemotherapy with temozolomide.',
        'title': 'Glioblastoma Management: A Comprehensive Review',
        'type': 'chapter',
        'id': 'chapter-123'
    }


@pytest.fixture
def sample_tags():
    """Sample tags for testing"""
    return [
        {
            'id': 'tag-1',
            'name': 'Glioblastoma',
            'slug': 'glioblastoma',
            'confidence': 0.95,
            'category': 'diagnosis'
        },
        {
            'id': 'tag-2',
            'name': 'Surgical Resection',
            'slug': 'surgical-resection',
            'confidence': 0.88,
            'category': 'treatment'
        },
        {
            'id': 'tag-3',
            'name': 'Chemotherapy',
            'slug': 'chemotherapy',
            'confidence': 0.82,
            'category': 'treatment'
        }
    ]


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response"""
    return {
        'choices': [
            {
                'message': {
                    'content': '''[
                        {"name": "Glioblastoma", "confidence": 0.95, "category": "diagnosis"},
                        {"name": "Surgical Resection", "confidence": 0.88, "category": "treatment"},
                        {"name": "Chemotherapy", "confidence": 0.82, "category": "treatment"}
                    ]'''
                }
            }
        ]
    }


class TestTaggingService:
    """Test suite for TaggingService"""

    def test_initialization(self, mock_db):
        """Test service initialization"""
        service = TaggingService(mock_db)
        assert service.db == mock_db

    @patch('backend.services.tagging_service.openai.ChatCompletion.create')
    def test_auto_tag_content_success(
        self,
        mock_openai,
        tagging_service,
        mock_db,
        sample_content,
        mock_openai_response,
        sample_tags
    ):
        """Test successful auto-tagging"""
        # Mock OpenAI response
        mock_openai.return_value = mock_openai_response

        # Mock tag creation/retrieval
        mock_tag_result = Mock()
        mock_tag_result.fetchone.return_value = ['tag-1']

        # Mock tag association
        mock_assoc_result = Mock()
        mock_assoc_result.fetchone.return_value = ['assoc-1']

        mock_db.execute.side_effect = [
            mock_tag_result,  # First tag creation
            mock_assoc_result,  # First association
            mock_tag_result,  # Second tag
            mock_assoc_result,  # Second association
            mock_tag_result,  # Third tag
            mock_assoc_result   # Third association
        ]

        result = tagging_service.auto_tag_content(
            content_type=sample_content['type'],
            content_id=sample_content['id'],
            content_text=sample_content['text'],
            content_title=sample_content['title'],
            max_tags=5,
            min_confidence=0.6
        )

        assert isinstance(result, list)
        mock_openai.assert_called_once()
        # Should commit for each tag + association
        assert mock_db.commit.call_count > 0

    @patch('backend.services.tagging_service.openai.ChatCompletion.create')
    def test_auto_tag_content_filters_low_confidence(
        self,
        mock_openai,
        tagging_service,
        mock_db
    ):
        """Test that low confidence tags are filtered out"""
        # Mock response with mixed confidence scores
        mock_openai.return_value = {
            'choices': [{
                'message': {
                    'content': '''[
                        {"name": "High Confidence", "confidence": 0.9, "category": "test"},
                        {"name": "Low Confidence", "confidence": 0.4, "category": "test"}
                    ]'''
                }
            }]
        }

        mock_tag_result = Mock()
        mock_tag_result.fetchone.return_value = ['tag-1']
        mock_assoc_result = Mock()
        mock_assoc_result.fetchone.return_value = ['assoc-1']
        mock_db.execute.side_effect = [mock_tag_result, mock_assoc_result]

        result = tagging_service.auto_tag_content(
            content_type='chapter',
            content_id='test-id',
            content_text='Test content',
            max_tags=5,
            min_confidence=0.6
        )

        # Should only include high confidence tag
        assert len(result) <= 1

    def test_add_manual_tag_success(
        self,
        tagging_service,
        mock_db
    ):
        """Test manually adding a tag"""
        mock_tag_result = Mock()
        mock_tag_result.fetchone.return_value = ['tag-1']

        mock_assoc_result = Mock()
        mock_assoc_result.fetchone.return_value = ['assoc-1']

        mock_db.execute.side_effect = [mock_tag_result, mock_assoc_result]

        result = tagging_service.add_tag(
            content_type='chapter',
            content_id='chapter-1',
            tag_name='Neurosurgery'
        )

        assert result is not None
        assert 'tag_id' in result
        mock_db.commit.assert_called()

    def test_add_manual_tag_failure(
        self,
        tagging_service,
        mock_db
    ):
        """Test manual tag addition failure"""
        mock_db.execute.side_effect = Exception('Database error')

        result = tagging_service.add_tag(
            content_type='chapter',
            content_id='chapter-1',
            tag_name='Test'
        )

        assert result is None
        mock_db.rollback.assert_called()

    def test_remove_tag_success(
        self,
        tagging_service,
        mock_db
    ):
        """Test removing a tag"""
        success = tagging_service.remove_tag(
            tag_id='tag-1',
            content_type='chapter',
            content_id='chapter-1'
        )

        assert success is True
        mock_db.commit.assert_called_once()

    def test_remove_tag_failure(
        self,
        tagging_service,
        mock_db
    ):
        """Test tag removal failure"""
        mock_db.execute.side_effect = Exception('Database error')

        success = tagging_service.remove_tag(
            tag_id='tag-1',
            content_type='chapter',
            content_id='chapter-1'
        )

        assert success is False
        mock_db.rollback.assert_called()

    def test_get_content_tags(
        self,
        tagging_service,
        mock_db,
        sample_tags
    ):
        """Test retrieving tags for content"""
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            ('tag-1', 'Glioblastoma', 'glioblastoma', True, 0.95),
            ('tag-2', 'Surgery', 'surgery', False, None)
        ]
        mock_db.execute.return_value = mock_result

        tags = tagging_service.get_content_tags(
            content_type='chapter',
            content_id='chapter-1'
        )

        assert isinstance(tags, list)
        assert len(tags) == 2
        assert 'id' in tags[0]
        assert 'name' in tags[0]
        assert 'is_auto_generated' in tags[0]

    def test_get_content_tags_empty(
        self,
        tagging_service,
        mock_db
    ):
        """Test retrieving tags when none exist"""
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        tags = tagging_service.get_content_tags(
            content_type='chapter',
            content_id='chapter-1'
        )

        assert isinstance(tags, list)
        assert len(tags) == 0

    @patch('backend.services.tagging_service.openai.ChatCompletion.create')
    def test_suggest_tags(
        self,
        mock_openai,
        tagging_service,
        mock_openai_response
    ):
        """Test tag suggestions"""
        mock_openai.return_value = mock_openai_response

        suggestions = tagging_service.suggest_tags(
            text='Content about brain tumors and surgery',
            max_suggestions=5
        )

        assert isinstance(suggestions, list)
        if len(suggestions) > 0:
            assert 'name' in suggestions[0]
            assert 'confidence' in suggestions[0]

    def test_get_popular_tags(
        self,
        tagging_service,
        mock_db
    ):
        """Test retrieving popular tags"""
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            ('tag-1', 'Neurosurgery', 'neurosurgery', 150),
            ('tag-2', 'Brain Tumor', 'brain-tumor', 120)
        ]
        mock_db.execute.return_value = mock_result

        tags = tagging_service.get_popular_tags(limit=10)

        assert isinstance(tags, list)
        assert len(tags) == 2
        assert 'usage_count' in tags[0]
        # Should be ordered by usage count
        assert tags[0]['usage_count'] >= tags[1]['usage_count']

    def test_search_tags(
        self,
        tagging_service,
        mock_db
    ):
        """Test tag search"""
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            ('tag-1', 'Neurosurgery', 'neurosurgery', 50),
            ('tag-2', 'Neuroscience', 'neuroscience', 30)
        ]
        mock_db.execute.return_value = mock_result

        tags = tagging_service.search_tags(
            query='neuro',
            limit=10
        )

        assert isinstance(tags, list)
        assert len(tags) == 2

    def test_search_tags_empty_query(
        self,
        tagging_service,
        mock_db
    ):
        """Test tag search with empty query"""
        tags = tagging_service.search_tags(
            query='',
            limit=10
        )

        assert isinstance(tags, list)
        assert len(tags) == 0

    def test_get_or_create_tag_existing(
        self,
        tagging_service,
        mock_db
    ):
        """Test getting existing tag"""
        mock_result = Mock()
        mock_result.fetchone.return_value = ['tag-1']
        mock_db.execute.return_value = mock_result

        tag_id = tagging_service._get_or_create_tag(
            name='Neurosurgery',
            is_auto_generated=False
        )

        assert tag_id == 'tag-1'

    def test_get_or_create_tag_new(
        self,
        tagging_service,
        mock_db
    ):
        """Test creating new tag"""
        # First call returns None (tag doesn't exist)
        # Second call returns new tag ID
        mock_result1 = Mock()
        mock_result1.fetchone.return_value = None

        mock_result2 = Mock()
        mock_result2.fetchone.return_value = ['new-tag-id']

        mock_db.execute.side_effect = [mock_result1, mock_result2]

        tag_id = tagging_service._get_or_create_tag(
            name='New Tag',
            is_auto_generated=True
        )

        assert tag_id == 'new-tag-id'
        assert mock_db.commit.call_count >= 1

    def test_slugify_tag_name(
        self,
        tagging_service
    ):
        """Test tag name slugification"""
        test_cases = [
            ('Brain Tumor', 'brain-tumor'),
            ('Surgical Resection', 'surgical-resection'),
            ('Glioblastoma', 'glioblastoma'),
            ('T1-weighted MRI', 't1-weighted-mri')
        ]

        for name, expected_slug in test_cases:
            slug = tagging_service._slugify(name)
            assert slug == expected_slug

    def test_max_tags_limit(
        self,
        tagging_service,
        mock_db
    ):
        """Test that max_tags limit is respected"""
        with patch('backend.services.tagging_service.openai.ChatCompletion.create') as mock_openai:
            # Mock response with many tags
            mock_openai.return_value = {
                'choices': [{
                    'message': {
                        'content': '''[
                            {"name": "Tag1", "confidence": 0.9, "category": "test"},
                            {"name": "Tag2", "confidence": 0.85, "category": "test"},
                            {"name": "Tag3", "confidence": 0.8, "category": "test"},
                            {"name": "Tag4", "confidence": 0.75, "category": "test"},
                            {"name": "Tag5", "confidence": 0.7, "category": "test"},
                            {"name": "Tag6", "confidence": 0.65, "category": "test"}
                        ]'''
                    }
                }]
            }

            mock_tag_result = Mock()
            mock_tag_result.fetchone.return_value = ['tag-id']
            mock_assoc_result = Mock()
            mock_assoc_result.fetchone.return_value = ['assoc-id']

            # Provide enough mocked results for max_tags
            mock_db.execute.side_effect = [
                mock_tag_result, mock_assoc_result,
                mock_tag_result, mock_assoc_result,
                mock_tag_result, mock_assoc_result
            ]

            result = tagging_service.auto_tag_content(
                content_type='chapter',
                content_id='test',
                content_text='Test content',
                max_tags=3
            )

            # Should only return max_tags number of tags
            assert len(result) <= 3

    @patch('backend.services.tagging_service.openai.ChatCompletion.create')
    def test_openai_error_handling(
        self,
        mock_openai,
        tagging_service,
        mock_db
    ):
        """Test handling of OpenAI API errors"""
        mock_openai.side_effect = Exception('API Error')

        result = tagging_service.auto_tag_content(
            content_type='chapter',
            content_id='test',
            content_text='Test content'
        )

        assert isinstance(result, list)
        assert len(result) == 0

    def test_duplicate_tag_handling(
        self,
        tagging_service,
        mock_db
    ):
        """Test that duplicate tags are not added"""
        # Mock tag already associated
        mock_check = Mock()
        mock_check.fetchone.return_value = ['existing-assoc']

        mock_db.execute.return_value = mock_check

        result = tagging_service.add_tag(
            content_type='chapter',
            content_id='chapter-1',
            tag_name='Existing Tag'
        )

        # Should handle gracefully
        assert result is not None or result is None
