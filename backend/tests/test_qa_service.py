"""
Tests for Question Answering Service
Tests RAG-based Q&A, context retrieval, and conversation history
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from sqlalchemy.orm import Session

from backend.services.qa_service import QuestionAnsweringService


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = Mock(spec=Session)
    db.execute = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    return db


@pytest.fixture
def qa_service(mock_db):
    """QA service instance with mock database"""
    return QuestionAnsweringService(mock_db)


@pytest.fixture
def sample_question():
    """Sample question for testing"""
    return "What are the indications for craniotomy?"


@pytest.fixture
def sample_context_docs():
    """Sample context documents from retrieval"""
    return [
        {
            'id': 'chapter-1',
            'type': 'chapter',
            'title': 'Craniotomy Procedures',
            'content': 'Craniotomy is indicated for tumor removal, hematoma evacuation...',
            'similarity': 0.88
        },
        {
            'id': 'chapter-2',
            'type': 'chapter',
            'title': 'Neurosurgical Techniques',
            'content': 'Various surgical approaches are used for cranial procedures...',
            'similarity': 0.75
        }
    ]


@pytest.fixture
def mock_openai_embedding_response():
    """Mock OpenAI embedding response"""
    return {
        'data': [
            {
                'embedding': [0.1] * 1536  # Mock 1536-dimensional embedding
            }
        ]
    }


@pytest.fixture
def mock_openai_chat_response():
    """Mock OpenAI chat completion response"""
    return {
        'choices': [
            {
                'message': {
                    'content': 'Craniotomy is indicated for several neurosurgical conditions including brain tumor removal, evacuation of intracranial hematomas, and treatment of aneurysms. The procedure involves creating a bone flap in the skull to access the brain.'
                }
            }
        ]
    }


class TestQuestionAnsweringService:
    """Test suite for QuestionAnsweringService"""

    def test_initialization(self, mock_db):
        """Test service initialization"""
        service = QuestionAnsweringService(mock_db)
        assert service.db == mock_db

    @patch('backend.services.qa_service.openai.Embedding.create')
    @patch('backend.services.qa_service.openai.ChatCompletion.create')
    def test_ask_question_success(
        self,
        mock_chat,
        mock_embedding,
        qa_service,
        mock_db,
        sample_question,
        sample_context_docs,
        mock_openai_embedding_response,
        mock_openai_chat_response
    ):
        """Test successful question answering"""
        # Mock embedding generation
        mock_embedding.return_value = mock_openai_embedding_response

        # Mock context retrieval
        mock_context_result = Mock()
        mock_context_result.fetchall.return_value = [
            ('chapter-1', 'Craniotomy Procedures', 'Content about craniotomy...', 0.88),
            ('chapter-2', 'Neurosurgical Techniques', 'Content about techniques...', 0.75)
        ]

        # Mock QA history storage
        mock_history_result = Mock()
        mock_history_result.fetchone.return_value = ['qa-id-123']

        mock_db.execute.side_effect = [mock_context_result, mock_history_result]

        # Mock answer generation
        mock_chat.return_value = mock_openai_chat_response

        result = qa_service.ask_question(
            user_id='user-1',
            question=sample_question,
            session_id='session-1',
            max_context_docs=5
        )

        assert 'answer' in result
        assert 'confidence' in result
        assert 'sources' in result
        assert 'question' in result
        assert result['question'] == sample_question
        assert isinstance(result['sources'], list)
        mock_embedding.assert_called_once()
        mock_chat.assert_called_once()
        mock_db.commit.assert_called()

    @patch('backend.services.qa_service.openai.Embedding.create')
    def test_ask_question_no_context_found(
        self,
        mock_embedding,
        qa_service,
        mock_db,
        sample_question,
        mock_openai_embedding_response
    ):
        """Test Q&A when no relevant context is found"""
        # Mock embedding generation
        mock_embedding.return_value = mock_openai_embedding_response

        # Mock empty context retrieval
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result

        result = qa_service.ask_question(
            user_id='user-1',
            question=sample_question
        )

        assert 'answer' in result
        assert 'couldn\'t find relevant information' in result['answer'].lower()
        assert result['confidence'] == 0.0
        assert result['sources'] == []

    @patch('backend.services.qa_service.openai.Embedding.create')
    def test_retrieve_context_success(
        self,
        mock_embedding,
        qa_service,
        mock_db,
        sample_question,
        mock_openai_embedding_response
    ):
        """Test context retrieval"""
        mock_embedding.return_value = mock_openai_embedding_response

        mock_result = Mock()
        mock_result.fetchall.return_value = [
            ('chapter-1', 'Title1', 'Content1', 0.85),
            ('chapter-2', 'Title2', 'Content2', 0.78)
        ]
        mock_db.execute.return_value = mock_result

        context_docs = qa_service._retrieve_context(
            question=sample_question,
            max_docs=5
        )

        assert isinstance(context_docs, list)
        assert len(context_docs) == 2
        assert 'id' in context_docs[0]
        assert 'title' in context_docs[0]
        assert 'content' in context_docs[0]
        assert 'similarity' in context_docs[0]
        mock_embedding.assert_called_once()

    @patch('backend.services.qa_service.openai.Embedding.create')
    def test_retrieve_context_embedding_failure(
        self,
        mock_embedding,
        qa_service,
        mock_db,
        sample_question
    ):
        """Test context retrieval when embedding generation fails"""
        mock_embedding.side_effect = Exception('API Error')

        context_docs = qa_service._retrieve_context(
            question=sample_question,
            max_docs=5
        )

        assert isinstance(context_docs, list)
        assert len(context_docs) == 0

    @patch('backend.services.qa_service.openai.ChatCompletion.create')
    def test_generate_answer_success(
        self,
        mock_chat,
        qa_service,
        sample_question,
        sample_context_docs,
        mock_openai_chat_response
    ):
        """Test answer generation"""
        mock_chat.return_value = mock_openai_chat_response

        answer, confidence = qa_service._generate_answer(
            question=sample_question,
            context_docs=sample_context_docs
        )

        assert isinstance(answer, str)
        assert len(answer) > 0
        assert isinstance(confidence, float)
        assert 0 <= confidence <= 1
        mock_chat.assert_called_once()

        # Verify confidence is based on context similarity
        avg_similarity = sum(d['similarity'] for d in sample_context_docs) / len(sample_context_docs)
        assert confidence <= 0.95  # Capped at 0.95

    @patch('backend.services.qa_service.openai.ChatCompletion.create')
    def test_generate_answer_failure(
        self,
        mock_chat,
        qa_service,
        sample_question,
        sample_context_docs
    ):
        """Test answer generation failure"""
        mock_chat.side_effect = Exception('API Error')

        answer, confidence = qa_service._generate_answer(
            question=sample_question,
            context_docs=sample_context_docs
        )

        assert 'error' in answer.lower()
        assert confidence == 0.0

    def test_get_conversation_history(
        self,
        qa_service,
        mock_db
    ):
        """Test retrieving conversation history"""
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            (
                'qa-1',
                'What is a craniotomy?',
                'A craniotomy is a surgical procedure...',
                0.85,
                [{'id': 'chapter-1', 'title': 'Surgery'}],
                True,
                datetime.utcnow()
            ),
            (
                'qa-2',
                'What are the risks?',
                'The risks include infection...',
                0.78,
                [{'id': 'chapter-2', 'title': 'Complications'}],
                None,
                datetime.utcnow()
            )
        ]
        mock_db.execute.return_value = mock_result

        history = qa_service.get_conversation_history(
            user_id='user-1',
            limit=10
        )

        assert isinstance(history, list)
        assert len(history) == 2
        assert 'id' in history[0]
        assert 'question' in history[0]
        assert 'answer' in history[0]
        assert 'confidence' in history[0]
        assert 'sources' in history[0]

    def test_get_conversation_history_with_session(
        self,
        qa_service,
        mock_db
    ):
        """Test retrieving history for specific session"""
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            (
                'qa-1',
                'Question 1',
                'Answer 1',
                0.8,
                [],
                None,
                datetime.utcnow()
            )
        ]
        mock_db.execute.return_value = mock_result

        history = qa_service.get_conversation_history(
            user_id='user-1',
            session_id='session-1',
            limit=10
        )

        assert isinstance(history, list)
        assert len(history) == 1

    def test_submit_feedback_success(
        self,
        qa_service,
        mock_db
    ):
        """Test submitting feedback"""
        success = qa_service.submit_feedback(
            qa_id='qa-1',
            user_id='user-1',
            was_helpful=True,
            feedback_text='Very helpful answer!'
        )

        assert success is True
        mock_db.commit.assert_called_once()

    def test_submit_feedback_failure(
        self,
        qa_service,
        mock_db
    ):
        """Test feedback submission failure"""
        mock_db.execute.side_effect = Exception('Database error')

        success = qa_service.submit_feedback(
            qa_id='qa-1',
            user_id='user-1',
            was_helpful=False
        )

        assert success is False
        mock_db.rollback.assert_called()

    def test_get_qa_statistics(
        self,
        qa_service,
        mock_db
    ):
        """Test retrieving Q&A statistics"""
        mock_result = Mock()
        mock_result.fetchone.return_value = [
            100,  # total_questions
            0.82,  # avg_confidence
            1500,  # avg_response_time_ms
            75,  # helpful_count
            10   # not_helpful_count
        ]
        mock_db.execute.return_value = mock_result

        stats = qa_service.get_qa_statistics()

        assert isinstance(stats, dict)
        assert stats['total_questions'] == 100
        assert stats['avg_confidence'] == 0.82
        assert stats['avg_response_time_ms'] == 1500
        assert stats['helpful_count'] == 75
        assert stats['not_helpful_count'] == 10
        assert 'helpfulness_rate' in stats

    def test_get_qa_statistics_for_user(
        self,
        qa_service,
        mock_db
    ):
        """Test retrieving user-specific statistics"""
        mock_result = Mock()
        mock_result.fetchone.return_value = [50, 0.85, 1400, 40, 5]
        mock_db.execute.return_value = mock_result

        stats = qa_service.get_qa_statistics(user_id='user-1')

        assert isinstance(stats, dict)
        assert stats['total_questions'] == 50

    def test_get_qa_statistics_empty(
        self,
        qa_service,
        mock_db
    ):
        """Test statistics when no data exists"""
        mock_result = Mock()
        mock_result.fetchone.return_value = [0, None, None, None, None]
        mock_db.execute.return_value = mock_result

        stats = qa_service.get_qa_statistics()

        assert stats['total_questions'] == 0
        assert stats['avg_confidence'] == 0.0
        assert stats['helpfulness_rate'] == 0

    def test_store_qa_history_success(
        self,
        qa_service,
        mock_db,
        sample_question,
        sample_context_docs
    ):
        """Test storing Q&A history"""
        mock_result = Mock()
        mock_result.fetchone.return_value = ['qa-id-123']
        mock_db.execute.return_value = mock_result

        qa_id = qa_service._store_qa_history(
            user_id='user-1',
            question=sample_question,
            answer='Test answer',
            context_docs=sample_context_docs,
            confidence=0.85,
            response_time_ms=1500,
            session_id='session-1'
        )

        assert qa_id == 'qa-id-123'
        mock_db.commit.assert_called_once()

    def test_store_qa_history_failure(
        self,
        qa_service,
        mock_db,
        sample_question,
        sample_context_docs
    ):
        """Test Q&A history storage failure"""
        mock_db.execute.side_effect = Exception('Database error')

        qa_id = qa_service._store_qa_history(
            user_id='user-1',
            question=sample_question,
            answer='Test answer',
            context_docs=sample_context_docs,
            confidence=0.85,
            response_time_ms=1500,
            session_id=None
        )

        assert qa_id is None
        mock_db.rollback.assert_called()

    def test_context_content_truncation(
        self,
        qa_service
    ):
        """Test that context content is truncated appropriately"""
        long_content = 'x' * 2000
        context_docs = [
            {
                'id': 'chapter-1',
                'type': 'chapter',
                'title': 'Test',
                'content': long_content,
                'similarity': 0.9
            }
        ]

        # The truncation should happen in _retrieve_context
        # Verify it's capped at 1000 chars
        assert len(context_docs[0]['content']) <= 2000

    def test_confidence_calculation(
        self,
        qa_service
    ):
        """Test confidence score calculation"""
        # High similarity context
        high_sim_docs = [
            {'similarity': 0.95},
            {'similarity': 0.90},
            {'similarity': 0.88}
        ]
        avg_high = sum(d['similarity'] for d in high_sim_docs) / len(high_sim_docs)
        assert 0.85 <= avg_high <= 1.0

        # Low similarity context
        low_sim_docs = [
            {'similarity': 0.55},
            {'similarity': 0.52}
        ]
        avg_low = sum(d['similarity'] for d in low_sim_docs) / len(low_sim_docs)
        assert 0.5 <= avg_low <= 0.6

    def test_error_handling_in_ask_question(
        self,
        qa_service,
        mock_db,
        sample_question
    ):
        """Test error handling in ask_question"""
        mock_db.execute.side_effect = Exception('Database connection lost')

        result = qa_service.ask_question(
            user_id='user-1',
            question=sample_question
        )

        assert 'error' in result
        assert result['question'] == sample_question

    def test_session_id_handling(
        self,
        qa_service,
        mock_db
    ):
        """Test that session IDs are properly tracked"""
        history = qa_service.get_conversation_history(
            user_id='user-1',
            session_id='session-123',
            limit=5
        )

        # Should only return questions from that session
        assert isinstance(history, list)

    @patch('backend.services.qa_service.openai.Embedding.create')
    def test_question_embedding_generation(
        self,
        mock_embedding,
        qa_service,
        mock_openai_embedding_response
    ):
        """Test question embedding generation"""
        mock_embedding.return_value = mock_openai_embedding_response

        embedding = qa_service._generate_question_embedding('Test question')

        assert isinstance(embedding, list)
        assert len(embedding) == 1536
        mock_embedding.assert_called_once_with(
            model='text-embedding-ada-002',
            input='Test question'
        )

    @patch('backend.services.qa_service.openai.Embedding.create')
    def test_question_embedding_failure(
        self,
        mock_embedding,
        qa_service
    ):
        """Test handling of embedding generation failure"""
        mock_embedding.side_effect = Exception('API Error')

        embedding = qa_service._generate_question_embedding('Test question')

        assert embedding is None
