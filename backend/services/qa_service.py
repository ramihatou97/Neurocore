"""
Question Answering Service
Handles Q&A over the knowledge base using RAG (Retrieval-Augmented Generation)
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from openai import OpenAI  # Fixed: Migrated to openai>=1.0.0 client pattern
import json

from backend.config import settings
from backend.utils import get_logger

logger = get_logger(__name__)


class QuestionAnsweringService:
    """
    Service for Q&A over knowledge base

    Handles:
    - RAG-based question answering
    - Context retrieval from embeddings
    - Answer generation with citations
    - Conversation history
    - Answer quality assessment
    """

    def __init__(self, db: Session):
        self.db = db
        # Fixed: Initialize OpenAI client (openai>=1.0.0 pattern)
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # ==================== Q&A Methods ====================

    def ask_question(
        self,
        user_id: str,
        question: str,
        session_id: Optional[str] = None,
        max_context_docs: int = 5
    ) -> Dict[str, Any]:
        """
        Answer a question using RAG over knowledge base

        Args:
            user_id: User asking the question
            question: Question text
            session_id: Optional session ID for conversation tracking
            max_context_docs: Maximum context documents to retrieve

        Returns:
            Dict with answer, sources, and metadata
        """
        try:
            start_time = datetime.now()

            # Step 1: Retrieve relevant context
            context_docs = self._retrieve_context(question, max_context_docs)

            if not context_docs:
                return {
                    'answer': "I couldn't find relevant information in the knowledge base to answer this question.",
                    'confidence': 0.0,
                    'sources': [],
                    'question': question
                }

            # Step 2: Generate answer using context
            answer, confidence = self._generate_answer(question, context_docs)

            response_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Step 3: Store in history
            qa_id = self._store_qa_history(
                user_id=user_id,
                question=question,
                answer=answer,
                context_docs=context_docs,
                confidence=confidence,
                response_time_ms=response_time,
                session_id=session_id
            )

            return {
                'id': qa_id,
                'question': question,
                'answer': answer,
                'confidence': confidence,
                'sources': context_docs,
                'response_time_ms': response_time,
                'session_id': session_id,
                'answered_at': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Q&A failed: {str(e)}", exc_info=True)
            return {
                'error': str(e),
                'question': question
            }

    def _retrieve_context(
        self,
        question: str,
        max_docs: int
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context documents using vector search
        """
        try:
            # Generate embedding for question
            question_embedding = self._generate_question_embedding(question)

            if not question_embedding:
                return []

            # Search for similar content in chapters
            query = text("""
                SELECT
                    c.id,
                    c.title,
                    c.content,
                    1 - (ce.embedding <=> :question_embedding::vector) as similarity
                FROM chapters c
                JOIN chapter_embeddings ce ON ce.chapter_id = c.id
                WHERE 1 - (ce.embedding <=> :question_embedding::vector) > 0.5
                ORDER BY similarity DESC
                LIMIT :max_docs
            """)

            result = self.db.execute(query, {
                'question_embedding': str(question_embedding),
                'max_docs': max_docs
            })

            context_docs = []
            for row in result:
                # Truncate content for context window
                content = row[2][:1000] if row[2] else ""

                context_docs.append({
                    'id': str(row[0]),
                    'type': 'chapter',
                    'title': row[1],
                    'content': content,
                    'similarity': float(row[3])
                })

            logger.info(f"Retrieved {len(context_docs)} context documents")
            return context_docs

        except Exception as e:
            logger.error(f"Context retrieval failed: {str(e)}", exc_info=True)
            return []

    def _generate_question_embedding(self, question: str) -> Optional[List[float]]:
        """
        Generate embedding for question using OpenAI
        """
        try:
            # Fixed: Use new client.embeddings.create() API (openai>=1.0.0)
            response = self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=question
            )

            # Fixed: Response is now an object, not dict
            return response.data[0].embedding

        except Exception as e:
            logger.error(f"Question embedding failed: {str(e)}", exc_info=True)
            return None

    def _generate_answer(
        self,
        question: str,
        context_docs: List[Dict[str, Any]]
    ) -> tuple[str, float]:
        """
        Generate answer using GPT-4 with retrieved context
        """
        try:
            # Build context from documents
            context_text = "\n\n---\n\n".join([
                f"Document: {doc['title']}\n{doc['content']}"
                for doc in context_docs
            ])

            prompt = f"""You are a neurosurgical expert assistant. Answer the following question based on the provided context from the knowledge base.

Context from knowledge base:
{context_text}

Question: {question}

Instructions:
1. Provide a clear, accurate answer based on the context
2. If the context doesn't contain enough information, say so
3. Use medical terminology appropriately
4. Be concise but comprehensive
5. Cite which documents you're referencing when relevant

Answer:"""

            # Fixed: Use new client.chat.completions.create() API (openai>=1.0.0)
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful neurosurgical knowledge base assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=500
            )

            # Fixed: Response is now an object, not dict
            answer = response.choices[0].message.content.strip()

            # Estimate confidence based on context similarity
            avg_similarity = sum(doc['similarity'] for doc in context_docs) / len(context_docs)
            confidence = min(0.95, avg_similarity)

            return answer, confidence

        except Exception as e:
            logger.error(f"Answer generation failed: {str(e)}", exc_info=True)
            return "I encountered an error generating the answer.", 0.0

    # ==================== History Management ====================

    def _store_qa_history(
        self,
        user_id: str,
        question: str,
        answer: str,
        context_docs: List[Dict[str, Any]],
        confidence: float,
        response_time_ms: int,
        session_id: Optional[str]
    ) -> Optional[str]:
        """
        Store Q&A interaction in history
        """
        try:
            # Prepare context documents for storage
            context_data = [
                {'id': doc['id'], 'type': doc['type'], 'title': doc['title'], 'similarity': doc['similarity']}
                for doc in context_docs
            ]

            query = text("""
                INSERT INTO qa_history (
                    user_id, question, answer, context_documents,
                    confidence_score, response_time_ms, session_id, model_used
                )
                VALUES (
                    :user_id, :question, :answer, :context_docs::jsonb,
                    :confidence, :response_time_ms, :session_id, 'gpt-4'
                )
                RETURNING id
            """)

            result = self.db.execute(query, {
                'user_id': user_id,
                'question': question,
                'answer': answer,
                'context_docs': json.dumps(context_data),
                'confidence': confidence,
                'response_time_ms': response_time_ms,
                'session_id': session_id
            })

            self.db.commit()

            row = result.fetchone()
            return str(row[0]) if row else None

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to store Q&A history: {str(e)}", exc_info=True)
            return None

    def get_conversation_history(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for user
        """
        try:
            conditions = ["user_id = :user_id"]
            params = {'user_id': user_id, 'limit': limit}

            if session_id:
                conditions.append("session_id = :session_id")
                params['session_id'] = session_id

            where_clause = " AND ".join(conditions)

            query = text(f"""
                SELECT
                    id, question, answer, confidence_score,
                    context_documents, was_helpful, created_at
                FROM qa_history
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit
            """)

            result = self.db.execute(query, params)

            history = []
            for row in result:
                history.append({
                    'id': str(row[0]),
                    'question': row[1],
                    'answer': row[2],
                    'confidence': float(row[3]) if row[3] else None,
                    'sources': row[4] if row[4] else [],
                    'was_helpful': row[5],
                    'asked_at': row[6].isoformat() if row[6] else None
                })

            return history

        except Exception as e:
            logger.error(f"Failed to get conversation history: {str(e)}", exc_info=True)
            return []

    def submit_feedback(
        self,
        qa_id: str,
        user_id: str,
        was_helpful: bool,
        feedback_text: Optional[str] = None
    ) -> bool:
        """
        Submit feedback on Q&A answer quality
        """
        try:
            query = text("""
                UPDATE qa_history
                SET was_helpful = :was_helpful, feedback_text = :feedback_text
                WHERE id = :qa_id AND user_id = :user_id
            """)

            self.db.execute(query, {
                'qa_id': qa_id,
                'user_id': user_id,
                'was_helpful': was_helpful,
                'feedback_text': feedback_text
            })

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to submit feedback: {str(e)}", exc_info=True)
            return False

    # ==================== Analytics ====================

    def get_qa_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get Q&A usage statistics
        """
        try:
            conditions = []
            params = {}

            if user_id:
                conditions.append("user_id = :user_id")
                params['user_id'] = user_id

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = text(f"""
                SELECT
                    COUNT(*) as total_questions,
                    AVG(confidence_score) as avg_confidence,
                    AVG(response_time_ms) as avg_response_time_ms,
                    COUNT(CASE WHEN was_helpful = TRUE THEN 1 END) as helpful_count,
                    COUNT(CASE WHEN was_helpful = FALSE THEN 1 END) as not_helpful_count
                FROM qa_history
                {where_clause}
            """)

            result = self.db.execute(query, params)
            row = result.fetchone()

            return {
                'total_questions': row[0] or 0,
                'avg_confidence': float(row[1]) if row[1] else 0.0,
                'avg_response_time_ms': float(row[2]) if row[2] else 0,
                'helpful_count': row[3] or 0,
                'not_helpful_count': row[4] or 0,
                'helpfulness_rate': (row[3] / row[0] * 100) if row[0] > 0 else 0
            }

        except Exception as e:
            logger.error(f"Failed to get Q&A statistics: {str(e)}", exc_info=True)
            return {}
