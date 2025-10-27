"""
Suggestion Service
Handles related content suggestions, reading lists, and content discovery
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_, desc
from collections import Counter
import random

from backend.utils import get_logger

logger = get_logger(__name__)


class SuggestionService:
    """
    Service for content suggestions and discovery

    Handles:
    - Related content suggestions
    - Citation-based suggestions
    - Tag-based suggestions
    - User behavior-based suggestions
    - Reading list generation
    - Topic clustering
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== Main Suggestion Methods ====================

    def get_related_content(
        self,
        content_type: str,
        content_id: str,
        suggestion_types: List[str] = ['similar', 'tags', 'citations'],
        limit: int = 10
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get related content using multiple suggestion strategies

        Args:
            content_type: Type of source content (chapter, pdf)
            content_id: ID of source content
            suggestion_types: Types of suggestions to generate
            limit: Maximum suggestions per type

        Returns:
            Dict with suggestions grouped by type
        """
        try:
            suggestions = {}

            if 'similar' in suggestion_types:
                suggestions['similar'] = self._get_similar_content_suggestions(
                    content_type, content_id, limit
                )

            if 'tags' in suggestion_types:
                suggestions['by_tags'] = self._get_tag_based_suggestions(
                    content_type, content_id, limit
                )

            if 'citations' in suggestion_types:
                suggestions['by_citations'] = self._get_citation_based_suggestions(
                    content_type, content_id, limit
                )

            if 'authors' in suggestion_types:
                suggestions['by_author'] = self._get_author_based_suggestions(
                    content_type, content_id, limit
                )

            # Merge and rank all suggestions
            suggestions['recommended'] = self._merge_and_rank_suggestions(
                suggestions, limit
            )

            return suggestions

        except Exception as e:
            logger.error(f"Failed to get related content: {str(e)}", exc_info=True)
            return {}

    def suggest_next_reading(
        self,
        user_id: str,
        current_content_type: Optional[str] = None,
        current_content_id: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Suggest what the user should read next

        Based on:
        - Current reading context
        - User's reading history
        - Popular content
        - Incomplete reading sessions
        """
        try:
            suggestions = []

            # Context-based suggestions if currently reading something
            if current_content_type and current_content_id:
                context_suggestions = self._get_contextual_next_reading(
                    user_id, current_content_type, current_content_id, limit
                )
                suggestions.extend(context_suggestions)

            # Get user's reading patterns
            if len(suggestions) < limit:
                pattern_suggestions = self._get_pattern_based_suggestions(
                    user_id, limit - len(suggestions)
                )
                suggestions.extend(pattern_suggestions)

            # Get incomplete readings
            if len(suggestions) < limit:
                incomplete = self._get_incomplete_readings(
                    user_id, limit - len(suggestions)
                )
                suggestions.extend(incomplete)

            # Fill with trending content
            if len(suggestions) < limit:
                trending = self._get_trending_content(limit - len(suggestions))
                suggestions.extend(trending)

            # Remove duplicates and limit
            seen = set()
            unique_suggestions = []
            for suggestion in suggestions:
                key = (suggestion['type'], suggestion['id'])
                if key not in seen:
                    seen.add(key)
                    unique_suggestions.append(suggestion)
                    if len(unique_suggestions) >= limit:
                        break

            return unique_suggestions

        except Exception as e:
            logger.error(f"Next reading suggestion failed: {str(e)}", exc_info=True)
            return []

    def generate_reading_list(
        self,
        user_id: str,
        topic: Optional[str] = None,
        difficulty_level: Optional[str] = None,
        estimated_time_minutes: Optional[int] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Generate a curated reading list

        Args:
            user_id: User to generate list for
            topic: Optional topic filter
            difficulty_level: Optional difficulty (beginner, intermediate, advanced)
            estimated_time_minutes: Target reading time
            limit: Number of items in list

        Returns:
            Dict with reading list and metadata
        """
        try:
            # Get content matching criteria
            content_items = self._find_content_for_reading_list(
                user_id, topic, difficulty_level, limit * 2
            )

            # Order items intelligently
            ordered_list = self._order_reading_list(content_items, limit)

            # Calculate metadata
            total_word_count = sum(item.get('word_count', 0) for item in ordered_list)
            estimated_minutes = total_word_count / 200  # Average reading speed

            return {
                'title': self._generate_reading_list_title(topic, difficulty_level),
                'items': ordered_list,
                'total_items': len(ordered_list),
                'total_word_count': total_word_count,
                'estimated_minutes': int(estimated_minutes),
                'topic': topic,
                'difficulty_level': difficulty_level,
                'generated_at': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Reading list generation failed: {str(e)}", exc_info=True)
            return {}

    # ==================== Suggestion Strategy Methods ====================

    def _get_similar_content_suggestions(
        self,
        content_type: str,
        content_id: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Get suggestions based on content similarity (vectors)
        """
        try:
            query = text("""
                SELECT
                    similar_type,
                    similar_id,
                    similarity_score
                FROM get_similar_content(
                    :content_type,
                    :content_id,
                    :limit,
                    0.5
                )
            """)

            result = self.db.execute(query, {
                'content_type': content_type,
                'content_id': content_id,
                'limit': limit
            })

            suggestions = []
            for row in result:
                details = self._get_content_details(row[0], str(row[1]))
                if details:
                    suggestions.append({
                        'id': str(row[1]),
                        'type': row[0],
                        'title': details['title'],
                        'reason': f'{int(float(row[2]) * 100)}% content similarity',
                        'score': float(row[2]),
                        'metadata': details
                    })

            return suggestions

        except Exception as e:
            logger.error(f"Similar content suggestions failed: {str(e)}", exc_info=True)
            return []

    def _get_tag_based_suggestions(
        self,
        content_type: str,
        content_id: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Get suggestions based on shared tags
        """
        try:
            # Get tags for source content
            source_tags = self._get_content_tags(content_type, content_id)
            if not source_tags:
                return []

            tag_ids = [tag['id'] for tag in source_tags]

            # Find content with similar tags
            if content_type == 'chapter':
                query = text("""
                    SELECT
                        c.id,
                        c.title,
                        COUNT(ct.tag_id) as shared_tags,
                        ARRAY_AGG(t.name) as tag_names
                    FROM chapters c
                    JOIN chapter_tags ct ON ct.chapter_id = c.id
                    JOIN tags t ON t.id = ct.tag_id
                    WHERE ct.tag_id = ANY(:tag_ids)
                        AND c.id != :content_id
                    GROUP BY c.id, c.title
                    ORDER BY shared_tags DESC
                    LIMIT :limit
                """)
            else:  # pdf
                query = text("""
                    SELECT
                        p.id,
                        p.title,
                        COUNT(pt.tag_id) as shared_tags,
                        ARRAY_AGG(t.name) as tag_names
                    FROM pdfs p
                    JOIN pdf_tags pt ON pt.pdf_id = p.id
                    JOIN tags t ON t.id = pt.tag_id
                    WHERE pt.tag_id = ANY(:tag_ids)
                        AND p.id != :content_id
                    GROUP BY p.id, p.title
                    ORDER BY shared_tags DESC
                    LIMIT :limit
                """)

            result = self.db.execute(query, {
                'tag_ids': tag_ids,
                'content_id': content_id,
                'limit': limit
            })

            suggestions = []
            for row in result:
                suggestions.append({
                    'id': str(row[0]),
                    'type': content_type,
                    'title': row[1],
                    'reason': f'Shares {row[2]} tags: {", ".join(row[3][:3])}',
                    'score': float(row[2]) / len(tag_ids),
                    'metadata': {'shared_tags': row[2], 'tag_names': row[3]}
                })

            return suggestions

        except Exception as e:
            logger.error(f"Tag-based suggestions failed: {str(e)}", exc_info=True)
            return []

    def _get_citation_based_suggestions(
        self,
        content_type: str,
        content_id: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Get suggestions based on shared citations

        For chapters that cite similar sources
        """
        try:
            if content_type != 'chapter':
                return []

            query = text("""
                SELECT
                    c2.id,
                    c2.title,
                    COUNT(DISTINCT cit.id) as shared_citations
                FROM chapters c1
                JOIN citations cit1 ON cit1.id = ANY(
                    SELECT unnest(citations) FROM chapters WHERE id = :content_id
                )
                JOIN citations cit ON cit.doi = cit1.doi OR cit.title = cit1.title
                JOIN chapters c2 ON c2.id != :content_id
                    AND cit.id = ANY(SELECT unnest(c2.citations))
                WHERE c1.id = :content_id
                GROUP BY c2.id, c2.title
                HAVING COUNT(DISTINCT cit.id) > 0
                ORDER BY shared_citations DESC
                LIMIT :limit
            """)

            result = self.db.execute(query, {
                'content_id': content_id,
                'limit': limit
            })

            suggestions = []
            for row in result:
                suggestions.append({
                    'id': str(row[0]),
                    'type': 'chapter',
                    'title': row[1],
                    'reason': f'Cites {row[2]} similar sources',
                    'score': float(row[2]) / 10.0,  # Normalize to 0-1
                    'metadata': {'shared_citations': row[2]}
                })

            return suggestions

        except Exception as e:
            logger.error(f"Citation-based suggestions failed: {str(e)}", exc_info=True)
            return []

    def _get_author_based_suggestions(
        self,
        content_type: str,
        content_id: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Get suggestions from same author
        """
        try:
            if content_type == 'chapter':
                query = text("""
                    SELECT
                        c2.id,
                        c2.title,
                        c2.created_at,
                        u.full_name as author_name
                    FROM chapters c1
                    JOIN chapters c2 ON c2.author_id = c1.author_id
                    JOIN users u ON u.id = c1.author_id
                    WHERE c1.id = :content_id
                        AND c2.id != :content_id
                    ORDER BY c2.created_at DESC
                    LIMIT :limit
                """)
            else:  # pdf
                query = text("""
                    SELECT
                        p2.id,
                        p2.title,
                        p2.upload_date as created_at,
                        p1.author as author_name
                    FROM pdfs p1
                    JOIN pdfs p2 ON p2.author = p1.author
                    WHERE p1.id = :content_id
                        AND p2.id != :content_id
                    ORDER BY p2.upload_date DESC
                    LIMIT :limit
                """)

            result = self.db.execute(query, {
                'content_id': content_id,
                'limit': limit
            })

            suggestions = []
            for row in result:
                suggestions.append({
                    'id': str(row[0]),
                    'type': content_type,
                    'title': row[1],
                    'reason': f'By same author: {row[3]}' if row[3] else 'By same author',
                    'score': 0.8,  # Fixed high score for same author
                    'metadata': {
                        'created_at': row[2].isoformat() if row[2] else None,
                        'author': row[3]
                    }
                })

            return suggestions

        except Exception as e:
            logger.error(f"Author-based suggestions failed: {str(e)}", exc_info=True)
            return []

    # ==================== Next Reading Methods ====================

    def _get_contextual_next_reading(
        self,
        user_id: str,
        current_type: str,
        current_id: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Get contextual suggestions based on what user is currently reading
        """
        try:
            # Get related content
            related = self.get_related_content(
                current_type, current_id,
                suggestion_types=['similar', 'tags'],
                limit=limit
            )

            suggestions = []

            # Prioritize recommendations
            if 'recommended' in related:
                for item in related['recommended'][:limit]:
                    suggestions.append({
                        'id': item['id'],
                        'type': item['type'],
                        'title': item['title'],
                        'reason': f"Related to current reading: {item.get('reason', '')}",
                        'score': item.get('score', 0.5)
                    })

            return suggestions

        except Exception as e:
            logger.error(f"Contextual suggestions failed: {str(e)}", exc_info=True)
            return []

    def _get_pattern_based_suggestions(
        self,
        user_id: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Get suggestions based on user's reading patterns
        """
        try:
            # Find user's most interacted tags
            query = text("""
                WITH user_tags AS (
                    SELECT
                        t.id,
                        t.name,
                        COUNT(DISTINCT ui.content_id) as interaction_count
                    FROM user_interactions ui
                    LEFT JOIN chapter_tags ct ON ct.chapter_id = ui.content_id
                        AND ui.content_type = 'chapter'
                    LEFT JOIN pdf_tags pt ON pt.pdf_id = ui.content_id
                        AND ui.content_type = 'pdf'
                    LEFT JOIN tags t ON t.id = COALESCE(ct.tag_id, pt.tag_id)
                    WHERE ui.user_id = :user_id
                        AND t.id IS NOT NULL
                    GROUP BY t.id, t.name
                    ORDER BY interaction_count DESC
                    LIMIT 5
                )
                SELECT
                    c.id,
                    'chapter' as type,
                    c.title,
                    COUNT(DISTINCT ct.tag_id) as matching_tags
                FROM chapters c
                JOIN chapter_tags ct ON ct.chapter_id = c.id
                WHERE ct.tag_id IN (SELECT id FROM user_tags)
                    AND c.id NOT IN (
                        SELECT content_id FROM user_interactions
                        WHERE user_id = :user_id AND content_type = 'chapter'
                    )
                GROUP BY c.id, c.title
                ORDER BY matching_tags DESC
                LIMIT :limit
            """)

            result = self.db.execute(query, {
                'user_id': user_id,
                'limit': limit
            })

            suggestions = []
            for row in result:
                suggestions.append({
                    'id': str(row[0]),
                    'type': row[1],
                    'title': row[2],
                    'reason': 'Matches your reading interests',
                    'score': float(row[3]) / 5.0
                })

            return suggestions

        except Exception as e:
            logger.error(f"Pattern-based suggestions failed: {str(e)}", exc_info=True)
            return []

    def _get_incomplete_readings(
        self,
        user_id: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Get content user started but didn't finish
        """
        try:
            query = text("""
                SELECT DISTINCT ON (ui.content_type, ui.content_id)
                    ui.content_type,
                    ui.content_id,
                    ui.duration_seconds,
                    ui.created_at
                FROM user_interactions ui
                WHERE ui.user_id = :user_id
                    AND ui.interaction_type = 'view'
                    AND ui.duration_seconds < 300  -- Less than 5 minutes
                ORDER BY ui.content_type, ui.content_id, ui.created_at DESC
                LIMIT :limit
            """)

            result = self.db.execute(query, {
                'user_id': user_id,
                'limit': limit
            })

            suggestions = []
            for row in result:
                details = self._get_content_details(row[0], str(row[1]))
                if details:
                    suggestions.append({
                        'id': str(row[1]),
                        'type': row[0],
                        'title': details['title'],
                        'reason': 'Continue reading',
                        'score': 0.7,
                        'metadata': {
                            'previous_duration': row[2],
                            'last_viewed': row[3].isoformat() if row[3] else None
                        }
                    })

            return suggestions

        except Exception as e:
            logger.error(f"Incomplete readings retrieval failed: {str(e)}", exc_info=True)
            return []

    def _get_trending_content(self, limit: int) -> List[Dict[str, Any]]:
        """
        Get currently trending content
        """
        try:
            # Content with most interactions in last 7 days
            query = text("""
                SELECT
                    ui.content_type,
                    ui.content_id,
                    COUNT(*) as interaction_count,
                    COUNT(DISTINCT ui.user_id) as unique_users
                FROM user_interactions ui
                WHERE ui.created_at >= NOW() - INTERVAL '7 days'
                GROUP BY ui.content_type, ui.content_id
                ORDER BY interaction_count DESC, unique_users DESC
                LIMIT :limit
            """)

            result = self.db.execute(query, {'limit': limit})

            suggestions = []
            for row in result:
                details = self._get_content_details(row[0], str(row[1]))
                if details:
                    suggestions.append({
                        'id': str(row[1]),
                        'type': row[0],
                        'title': details['title'],
                        'reason': f'Trending ({row[2]} views this week)',
                        'score': min(1.0, float(row[2]) / 100.0),
                        'metadata': {
                            'view_count': row[2],
                            'unique_users': row[3]
                        }
                    })

            return suggestions

        except Exception as e:
            logger.error(f"Trending content retrieval failed: {str(e)}", exc_info=True)
            return []

    # ==================== Reading List Methods ====================

    def _find_content_for_reading_list(
        self,
        user_id: str,
        topic: Optional[str],
        difficulty: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Find content matching reading list criteria
        """
        try:
            conditions = []
            params = {'limit': limit}

            # Filter by topic (tag)
            if topic:
                conditions.append("""
                    EXISTS (
                        SELECT 1 FROM chapter_tags ct
                        JOIN tags t ON t.id = ct.tag_id
                        WHERE ct.chapter_id = c.id
                            AND (t.name ILIKE :topic OR t.slug ILIKE :topic)
                    )
                """)
                params['topic'] = f'%{topic}%'

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = text(f"""
                SELECT
                    c.id,
                    c.title,
                    c.word_count,
                    c.created_at,
                    u.full_name as author_name
                FROM chapters c
                LEFT JOIN users u ON u.id = c.author_id
                {where_clause}
                ORDER BY c.created_at DESC
                LIMIT :limit
            """)

            result = self.db.execute(query, params)

            content_items = []
            for row in result:
                content_items.append({
                    'id': str(row[0]),
                    'type': 'chapter',
                    'title': row[1],
                    'word_count': row[2] or 0,
                    'created_at': row[3].isoformat() if row[3] else None,
                    'author': row[4]
                })

            return content_items

        except Exception as e:
            logger.error(f"Content search for reading list failed: {str(e)}", exc_info=True)
            return []

    def _order_reading_list(
        self,
        content_items: List[Dict[str, Any]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Intelligently order content items for optimal reading flow
        """
        # Simple ordering for now: newest first
        # In production: consider prerequisites, difficulty progression, etc.
        ordered = sorted(content_items, key=lambda x: x.get('created_at', ''), reverse=True)
        return ordered[:limit]

    def _generate_reading_list_title(
        self,
        topic: Optional[str],
        difficulty: Optional[str]
    ) -> str:
        """
        Generate a descriptive title for reading list
        """
        parts = []

        if topic:
            parts.append(topic.title())

        if difficulty:
            parts.append(difficulty.title())

        parts.append("Reading List")

        return " ".join(parts)

    # ==================== Helper Methods ====================

    def _merge_and_rank_suggestions(
        self,
        all_suggestions: Dict[str, List[Dict[str, Any]]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Merge suggestions from different sources and rank them
        """
        merged = []

        for suggestion_type, suggestions in all_suggestions.items():
            if suggestion_type == 'recommended':
                continue  # Skip to avoid recursion

            for suggestion in suggestions:
                merged.append(suggestion)

        # Remove duplicates
        seen = set()
        unique = []
        for suggestion in merged:
            key = (suggestion['type'], suggestion['id'])
            if key not in seen:
                seen.add(key)
                unique.append(suggestion)

        # Sort by score
        unique.sort(key=lambda x: x.get('score', 0), reverse=True)

        return unique[:limit]

    def _get_content_tags(
        self,
        content_type: str,
        content_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get tags for content
        """
        try:
            if content_type == 'chapter':
                table = 'chapter_tags'
                id_column = 'chapter_id'
            elif content_type == 'pdf':
                table = 'pdf_tags'
                id_column = 'pdf_id'
            else:
                return []

            query = text(f"""
                SELECT t.id, t.name
                FROM tags t
                JOIN {table} ct ON ct.tag_id = t.id
                WHERE ct.{id_column} = :content_id
            """)

            result = self.db.execute(query, {'content_id': content_id})

            tags = []
            for row in result:
                tags.append({'id': str(row[0]), 'name': row[1]})

            return tags

        except Exception as e:
            logger.error(f"Failed to get content tags: {str(e)}", exc_info=True)
            return []

    def _get_content_details(
        self,
        content_type: str,
        content_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get content metadata
        """
        try:
            if content_type == 'chapter':
                query = text("""
                    SELECT id, title, word_count, created_at
                    FROM chapters
                    WHERE id = :content_id
                """)
            elif content_type == 'pdf':
                query = text("""
                    SELECT id, title, NULL as word_count, upload_date as created_at
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
                    'word_count': row[2],
                    'created_at': row[3].isoformat() if row[3] else None
                }

            return None

        except Exception as e:
            logger.error(f"Failed to get content details: {str(e)}", exc_info=True)
            return None
