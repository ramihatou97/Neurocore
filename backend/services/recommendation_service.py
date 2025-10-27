"""
Recommendation Service
Handles content recommendations using collaborative filtering, content-based, and hybrid approaches
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_, desc
from uuid import UUID
import json

from backend.utils import get_logger

logger = get_logger(__name__)


class RecommendationService:
    """
    Service for content recommendations

    Handles:
    - Content-based recommendations (similarity)
    - Collaborative filtering (user behavior)
    - Hybrid recommendations
    - Recommendation tracking and feedback
    - Personalized suggestions
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== Main Recommendation Methods ====================

    def get_recommendations(
        self,
        user_id: str,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        algorithm: str = 'hybrid',
        limit: int = 10,
        min_score: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Get personalized recommendations for a user

        Args:
            user_id: User to get recommendations for
            source_type: Optional source content type (chapter, pdf)
            source_id: Optional source content ID
            algorithm: Algorithm to use (content_based, collaborative, hybrid)
            limit: Maximum number of recommendations
            min_score: Minimum relevance score threshold

        Returns:
            List of recommendation dictionaries
        """
        try:
            if algorithm == 'content_based':
                recommendations = self._get_content_based_recommendations(
                    user_id, source_type, source_id, limit, min_score
                )
            elif algorithm == 'collaborative':
                recommendations = self._get_collaborative_recommendations(
                    user_id, limit, min_score
                )
            elif algorithm == 'hybrid':
                recommendations = self._get_hybrid_recommendations(
                    user_id, source_type, source_id, limit, min_score
                )
            else:
                logger.warning(f"Unknown algorithm: {algorithm}, defaulting to hybrid")
                recommendations = self._get_hybrid_recommendations(
                    user_id, source_type, source_id, limit, min_score
                )

            # Store recommendations for tracking
            for rec in recommendations:
                self._store_recommendation(
                    user_id=user_id,
                    source_type=source_type or 'user_profile',
                    source_id=source_id or user_id,
                    recommended_type=rec['type'],
                    recommended_id=rec['id'],
                    relevance_score=rec['score'],
                    algorithm=algorithm,
                    reason=rec.get('reason')
                )

            return recommendations

        except Exception as e:
            logger.error(f"Failed to get recommendations: {str(e)}", exc_info=True)
            return []

    def _get_content_based_recommendations(
        self,
        user_id: str,
        source_type: Optional[str],
        source_id: Optional[str],
        limit: int,
        min_score: float
    ) -> List[Dict[str, Any]]:
        """
        Get recommendations based on content similarity

        Uses vector embeddings to find similar content
        """
        try:
            recommendations = []

            if source_type and source_id:
                # Get similar content to specific item
                similar = self._get_similar_content(
                    content_type=source_type,
                    content_id=source_id,
                    limit=limit * 2,  # Get more to filter later
                    min_similarity=min_score
                )
                recommendations.extend(similar)
            else:
                # Get recommendations based on user's recent interactions
                recent_interactions = self._get_user_recent_interactions(
                    user_id, limit=5
                )

                for interaction in recent_interactions:
                    similar = self._get_similar_content(
                        content_type=interaction['content_type'],
                        content_id=interaction['content_id'],
                        limit=limit,
                        min_similarity=min_score
                    )
                    recommendations.extend(similar)

            # Remove duplicates and sort by score
            seen = set()
            unique_recommendations = []
            for rec in sorted(recommendations, key=lambda x: x['score'], reverse=True):
                key = (rec['type'], rec['id'])
                if key not in seen:
                    seen.add(key)
                    unique_recommendations.append(rec)
                    if len(unique_recommendations) >= limit:
                        break

            return unique_recommendations

        except Exception as e:
            logger.error(f"Content-based recommendations failed: {str(e)}", exc_info=True)
            return []

    def _get_collaborative_recommendations(
        self,
        user_id: str,
        limit: int,
        min_score: float
    ) -> List[Dict[str, Any]]:
        """
        Get recommendations based on collaborative filtering

        Find similar users and recommend what they liked
        """
        try:
            # Find similar users based on interaction patterns
            similar_users = self._find_similar_users(user_id, limit=10)

            if not similar_users:
                # Fallback to popular content
                return self._get_popular_content_recommendations(limit)

            recommendations = []

            # Get content that similar users interacted with but this user hasn't
            for similar_user in similar_users:
                user_content = self._get_user_content_not_seen(
                    target_user_id=user_id,
                    source_user_id=similar_user['user_id'],
                    limit=limit
                )

                for content in user_content:
                    recommendations.append({
                        'id': content['content_id'],
                        'type': content['content_type'],
                        'title': content.get('title', 'Untitled'),
                        'score': content['interaction_score'] * similar_user['similarity'],
                        'reason': f'Users with similar interests viewed this',
                        'metadata': {
                            'similar_user_similarity': similar_user['similarity'],
                            'interaction_count': content['interaction_count']
                        }
                    })

            # Sort by score and limit
            recommendations.sort(key=lambda x: x['score'], reverse=True)
            return recommendations[:limit]

        except Exception as e:
            logger.error(f"Collaborative recommendations failed: {str(e)}", exc_info=True)
            return []

    def _get_hybrid_recommendations(
        self,
        user_id: str,
        source_type: Optional[str],
        source_id: Optional[str],
        limit: int,
        min_score: float
    ) -> List[Dict[str, Any]]:
        """
        Get hybrid recommendations combining content-based and collaborative filtering

        Weights: 60% content-based, 40% collaborative
        """
        try:
            # Get content-based recommendations
            content_based = self._get_content_based_recommendations(
                user_id, source_type, source_id, limit * 2, min_score
            )

            # Get collaborative recommendations
            collaborative = self._get_collaborative_recommendations(
                user_id, limit * 2, min_score
            )

            # Merge and re-score
            recommendations_dict = {}

            # Add content-based with 0.6 weight
            for rec in content_based:
                key = (rec['type'], rec['id'])
                recommendations_dict[key] = {
                    **rec,
                    'score': rec['score'] * 0.6,
                    'reason': f"Similar to your interests"
                }

            # Add collaborative with 0.4 weight
            for rec in collaborative:
                key = (rec['type'], rec['id'])
                if key in recommendations_dict:
                    # Boost score if recommended by both methods
                    recommendations_dict[key]['score'] += rec['score'] * 0.4
                    recommendations_dict[key]['reason'] = "Highly recommended (multiple signals)"
                else:
                    recommendations_dict[key] = {
                        **rec,
                        'score': rec['score'] * 0.4
                    }

            # Convert back to list and sort
            recommendations = list(recommendations_dict.values())
            recommendations.sort(key=lambda x: x['score'], reverse=True)

            return recommendations[:limit]

        except Exception as e:
            logger.error(f"Hybrid recommendations failed: {str(e)}", exc_info=True)
            return []

    # ==================== Helper Methods ====================

    def _get_similar_content(
        self,
        content_type: str,
        content_id: str,
        limit: int = 10,
        min_similarity: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Get similar content using vector similarity

        Uses PostgreSQL function for efficient vector search
        """
        try:
            # First check similarity cache
            cached = self._check_similarity_cache(content_type, content_id, limit)
            if cached:
                return cached

            # Use PostgreSQL function for vector similarity
            query = text("""
                SELECT
                    similar_type,
                    similar_id,
                    similarity_score
                FROM get_similar_content(
                    :content_type,
                    :content_id,
                    :limit,
                    :min_similarity
                )
            """)

            result = self.db.execute(query, {
                'content_type': content_type,
                'content_id': content_id,
                'limit': limit,
                'min_similarity': min_similarity
            })

            similar_content = []
            for row in result:
                # Get content details
                details = self._get_content_details(row[0], str(row[1]))
                if details:
                    similar_content.append({
                        'id': str(row[1]),
                        'type': row[0],
                        'title': details.get('title', 'Untitled'),
                        'score': float(row[2]),
                        'reason': f'{int(float(row[2]) * 100)}% similar',
                        'metadata': {
                            'similarity_score': float(row[2]),
                            'method': 'vector_cosine'
                        }
                    })

            # Cache results
            self._cache_similarity_results(content_type, content_id, similar_content)

            return similar_content

        except Exception as e:
            logger.error(f"Failed to get similar content: {str(e)}", exc_info=True)
            return []

    def _find_similar_users(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find users with similar interaction patterns

        Uses Jaccard similarity on content interactions
        """
        try:
            query = text("""
                WITH user_interactions AS (
                    SELECT content_type, content_id
                    FROM user_interactions
                    WHERE user_id = :user_id
                ),
                other_user_interactions AS (
                    SELECT
                        ui.user_id,
                        ui.content_type,
                        ui.content_id,
                        COUNT(*) as interaction_count
                    FROM user_interactions ui
                    WHERE ui.user_id != :user_id
                    GROUP BY ui.user_id, ui.content_type, ui.content_id
                ),
                similarity_scores AS (
                    SELECT
                        oui.user_id,
                        COUNT(DISTINCT CASE
                            WHEN EXISTS (
                                SELECT 1 FROM user_interactions uic
                                WHERE uic.content_type = oui.content_type
                                    AND uic.content_id = oui.content_id
                            ) THEN oui.content_id
                        END)::FLOAT / NULLIF(COUNT(DISTINCT oui.content_id), 0) as similarity
                    FROM other_user_interactions oui
                    GROUP BY oui.user_id
                    HAVING COUNT(DISTINCT oui.content_id) > 2
                )
                SELECT user_id, similarity
                FROM similarity_scores
                WHERE similarity > 0.1
                ORDER BY similarity DESC
                LIMIT :limit
            """)

            result = self.db.execute(query, {
                'user_id': user_id,
                'limit': limit
            })

            similar_users = []
            for row in result:
                similar_users.append({
                    'user_id': str(row[0]),
                    'similarity': float(row[1])
                })

            return similar_users

        except Exception as e:
            logger.error(f"Failed to find similar users: {str(e)}", exc_info=True)
            return []

    def _get_user_content_not_seen(
        self,
        target_user_id: str,
        source_user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get content that source user interacted with but target user hasn't
        """
        try:
            query = text("""
                SELECT
                    ui.content_type,
                    ui.content_id,
                    AVG(ui.interaction_score) as avg_score,
                    COUNT(*) as interaction_count
                FROM user_interactions ui
                WHERE ui.user_id = :source_user_id
                    AND NOT EXISTS (
                        SELECT 1 FROM user_interactions ui2
                        WHERE ui2.user_id = :target_user_id
                            AND ui2.content_type = ui.content_type
                            AND ui2.content_id = ui.content_id
                    )
                GROUP BY ui.content_type, ui.content_id
                ORDER BY avg_score DESC, interaction_count DESC
                LIMIT :limit
            """)

            result = self.db.execute(query, {
                'source_user_id': source_user_id,
                'target_user_id': target_user_id,
                'limit': limit
            })

            content_list = []
            for row in result:
                details = self._get_content_details(row[0], str(row[1]))
                content_list.append({
                    'content_type': row[0],
                    'content_id': str(row[1]),
                    'title': details.get('title', 'Untitled') if details else 'Untitled',
                    'interaction_score': float(row[2]),
                    'interaction_count': row[3]
                })

            return content_list

        except Exception as e:
            logger.error(f"Failed to get unseen content: {str(e)}", exc_info=True)
            return []

    def _get_user_recent_interactions(
        self,
        user_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get user's recent interactions for context
        """
        try:
            query = text("""
                SELECT DISTINCT
                    content_type,
                    content_id,
                    MAX(interaction_score) as max_score,
                    MAX(created_at) as last_interaction
                FROM user_interactions
                WHERE user_id = :user_id
                GROUP BY content_type, content_id
                ORDER BY last_interaction DESC
                LIMIT :limit
            """)

            result = self.db.execute(query, {
                'user_id': user_id,
                'limit': limit
            })

            interactions = []
            for row in result:
                interactions.append({
                    'content_type': row[0],
                    'content_id': str(row[1]),
                    'score': float(row[2]),
                    'timestamp': row[3]
                })

            return interactions

        except Exception as e:
            logger.error(f"Failed to get user interactions: {str(e)}", exc_info=True)
            return []

    def _get_popular_content_recommendations(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get popular content as fallback recommendations
        """
        try:
            query = text("""
                SELECT
                    content_type,
                    content_id,
                    content_title,
                    total_interactions,
                    unique_viewers,
                    avg_interaction_score
                FROM popular_content_view
                WHERE total_interactions > 0
                ORDER BY total_interactions DESC, unique_viewers DESC
                LIMIT :limit
            """)

            result = self.db.execute(query, {'limit': limit})

            popular = []
            for row in result:
                popular.append({
                    'id': str(row[1]),
                    'type': row[0],
                    'title': row[2],
                    'score': float(row[5]) if row[5] else 0.5,
                    'reason': f'Popular ({row[3]} views)',
                    'metadata': {
                        'total_interactions': row[3],
                        'unique_viewers': row[4]
                    }
                })

            return popular

        except Exception as e:
            logger.error(f"Failed to get popular content: {str(e)}", exc_info=True)
            return []

    def _get_content_details(
        self,
        content_type: str,
        content_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get content details (title, author, etc.)
        """
        try:
            if content_type == 'chapter':
                query = text("""
                    SELECT id, title, author_id, created_at
                    FROM chapters
                    WHERE id = :content_id
                """)
            elif content_type == 'pdf':
                query = text("""
                    SELECT id, title, uploaded_by, upload_date
                    FROM pdfs
                    WHERE id = :content_id
                """)
            else:
                return None

            result = self.db.execute(query, {'content_id': content_id})
            row = result.fetchone()

            if row:
                return {
                    'id': str(row[0]),
                    'title': row[1],
                    'author_id': str(row[2]) if row[2] else None,
                    'created_at': row[3].isoformat() if row[3] else None
                }

            return None

        except Exception as e:
            logger.error(f"Failed to get content details: {str(e)}", exc_info=True)
            return None

    # ==================== Recommendation Storage & Tracking ====================

    def _store_recommendation(
        self,
        user_id: str,
        source_type: str,
        source_id: str,
        recommended_type: str,
        recommended_id: str,
        relevance_score: float,
        algorithm: str,
        reason: Optional[str] = None
    ) -> bool:
        """
        Store recommendation for tracking and analysis
        """
        try:
            expires_at = datetime.now() + timedelta(days=7)

            query = text("""
                INSERT INTO recommendations (
                    user_id, source_type, source_id,
                    recommended_type, recommended_id,
                    relevance_score, algorithm,
                    recommendation_reason, expires_at
                )
                VALUES (
                    :user_id, :source_type, :source_id,
                    :recommended_type, :recommended_id,
                    :relevance_score, :algorithm,
                    :reason, :expires_at
                )
            """)

            self.db.execute(query, {
                'user_id': user_id,
                'source_type': source_type,
                'source_id': source_id,
                'recommended_type': recommended_type,
                'recommended_id': recommended_id,
                'relevance_score': relevance_score,
                'algorithm': algorithm,
                'reason': reason,
                'expires_at': expires_at
            })

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to store recommendation: {str(e)}", exc_info=True)
            return False

    def track_recommendation_click(
        self,
        recommendation_id: str,
        user_id: str
    ) -> bool:
        """
        Track when a user clicks on a recommendation
        """
        try:
            query = text("""
                UPDATE recommendations
                SET was_clicked = TRUE, clicked_at = NOW()
                WHERE id = :recommendation_id AND user_id = :user_id
            """)

            self.db.execute(query, {
                'recommendation_id': recommendation_id,
                'user_id': user_id
            })

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to track click: {str(e)}", exc_info=True)
            return False

    def submit_recommendation_feedback(
        self,
        recommendation_id: str,
        user_id: str,
        was_helpful: bool,
        feedback_text: Optional[str] = None
    ) -> bool:
        """
        Submit feedback on recommendation quality
        """
        try:
            query = text("""
                UPDATE recommendations
                SET was_helpful = :was_helpful, feedback_text = :feedback_text
                WHERE id = :recommendation_id AND user_id = :user_id
            """)

            self.db.execute(query, {
                'recommendation_id': recommendation_id,
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

    # ==================== User Interaction Tracking ====================

    def track_user_interaction(
        self,
        user_id: str,
        interaction_type: str,
        content_type: str,
        content_id: str,
        duration_seconds: Optional[int] = None,
        interaction_score: float = 1.0,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Track user interaction for recommendation training

        Interaction types: view, read, search, create, edit, export, share
        """
        try:
            metadata_json = json.dumps(metadata or {})

            query = text("""
                INSERT INTO user_interactions (
                    user_id, interaction_type, content_type, content_id,
                    duration_seconds, interaction_score, session_id, metadata
                )
                VALUES (
                    :user_id, :interaction_type, :content_type, :content_id,
                    :duration_seconds, :interaction_score, :session_id, :metadata::jsonb
                )
            """)

            self.db.execute(query, {
                'user_id': user_id,
                'interaction_type': interaction_type,
                'content_type': content_type,
                'content_id': content_id,
                'duration_seconds': duration_seconds,
                'interaction_score': interaction_score,
                'session_id': session_id,
                'metadata': metadata_json
            })

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to track interaction: {str(e)}", exc_info=True)
            return False

    # ==================== Caching Methods ====================

    def _check_similarity_cache(
        self,
        content_type: str,
        content_id: str,
        limit: int
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Check if similarity results are cached
        """
        try:
            query = text("""
                SELECT
                    content_type_b,
                    content_id_b,
                    similarity_score
                FROM similarity_cache
                WHERE content_type_a = :content_type
                    AND content_id_a = :content_id
                    AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY similarity_score DESC
                LIMIT :limit
            """)

            result = self.db.execute(query, {
                'content_type': content_type,
                'content_id': content_id,
                'limit': limit
            })

            cached_results = []
            for row in result:
                details = self._get_content_details(row[0], str(row[1]))
                if details:
                    cached_results.append({
                        'id': str(row[1]),
                        'type': row[0],
                        'title': details.get('title', 'Untitled'),
                        'score': float(row[2]),
                        'reason': f'{int(float(row[2]) * 100)}% similar',
                        'metadata': {'cached': True}
                    })

            return cached_results if cached_results else None

        except Exception as e:
            logger.error(f"Failed to check cache: {str(e)}", exc_info=True)
            return None

    def _cache_similarity_results(
        self,
        content_type: str,
        content_id: str,
        similar_content: List[Dict[str, Any]]
    ) -> None:
        """
        Cache similarity results for performance
        """
        try:
            expires_at = datetime.now() + timedelta(hours=24)

            for item in similar_content:
                query = text("""
                    INSERT INTO similarity_cache (
                        content_type_a, content_id_a,
                        content_type_b, content_id_b,
                        similarity_score, expires_at
                    )
                    VALUES (
                        :content_type_a, :content_id_a,
                        :content_type_b, :content_id_b,
                        :similarity_score, :expires_at
                    )
                    ON CONFLICT (content_type_a, content_id_a, content_type_b, content_id_b)
                    DO UPDATE SET
                        similarity_score = EXCLUDED.similarity_score,
                        calculated_at = NOW(),
                        expires_at = EXCLUDED.expires_at
                """)

                self.db.execute(query, {
                    'content_type_a': content_type,
                    'content_id_a': content_id,
                    'content_type_b': item['type'],
                    'content_id_b': item['id'],
                    'similarity_score': item['score'],
                    'expires_at': expires_at
                })

            self.db.commit()

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to cache similarity: {str(e)}", exc_info=True)
