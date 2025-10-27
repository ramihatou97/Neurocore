"""
Annotation Service for Phase 18: Advanced Content Features
Manages highlights, annotations, and collaborative discussions
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.utils import get_logger

logger = get_logger(__name__)


class AnnotationService:
    """
    Annotation and highlight management service

    Features:
    - Text highlights with positioning
    - Annotations (notes, questions, corrections)
    - Threaded discussions
    - Reactions to annotations
    - Public and private annotations
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== Highlight Management ====================

    def create_highlight(
        self,
        user_id: str,
        content_type: str,
        content_id: str,
        highlight_text: str,
        context_before: Optional[str] = None,
        context_after: Optional[str] = None,
        position_data: Optional[Dict] = None,
        color: str = 'yellow'
    ) -> Optional[Dict[str, Any]]:
        """Create text highlight"""
        try:
            import json

            query = text("""
                INSERT INTO highlights (
                    user_id, content_type, content_id, highlight_text,
                    context_before, context_after, position_data, color
                )
                VALUES (
                    :user_id, :content_type, :content_id, :highlight_text,
                    :context_before, :context_after, :position_data::jsonb, :color
                )
                RETURNING id, created_at
            """)

            result = self.db.execute(query, {
                'user_id': user_id,
                'content_type': content_type,
                'content_id': content_id,
                'highlight_text': highlight_text,
                'context_before': context_before,
                'context_after': context_after,
                'position_data': json.dumps(position_data) if position_data else None,
                'color': color
            })

            self.db.commit()
            row = result.fetchone()

            if row:
                return {
                    'id': str(row[0]),
                    'user_id': user_id,
                    'content_type': content_type,
                    'content_id': content_id,
                    'highlight_text': highlight_text,
                    'color': color,
                    'created_at': row[1].isoformat()
                }

            return None

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create highlight: {str(e)}")
            return None

    def get_content_highlights(
        self,
        content_type: str,
        content_id: str,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get highlights for content"""
        try:
            conditions = ["h.content_type = :content_type", "h.content_id = :content_id"]
            params = {'content_type': content_type, 'content_id': content_id}

            if user_id:
                conditions.append("h.user_id = :user_id")
                params['user_id'] = user_id

            where_clause = " AND ".join(conditions)

            query = text(f"""
                SELECT
                    h.id, h.user_id, h.highlight_text,
                    h.context_before, h.context_after,
                    h.position_data, h.color, h.created_at
                FROM highlights h
                WHERE {where_clause}
                ORDER BY h.created_at DESC
            """)

            result = self.db.execute(query, params)

            return [
                {
                    'id': str(row[0]),
                    'user_id': str(row[1]),
                    'highlight_text': row[2],
                    'context_before': row[3],
                    'context_after': row[4],
                    'position_data': row[5],
                    'color': row[6],
                    'created_at': row[7].isoformat()
                }
                for row in result.fetchall()
            ]

        except Exception as e:
            logger.error(f"Failed to get highlights: {str(e)}")
            return []

    def delete_highlight(self, highlight_id: str, user_id: str) -> bool:
        """Delete highlight"""
        try:
            query = text("""
                DELETE FROM highlights
                WHERE id = :highlight_id AND user_id = :user_id
            """)

            result = self.db.execute(query, {
                'highlight_id': highlight_id,
                'user_id': user_id
            })

            self.db.commit()
            return result.rowcount > 0

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete highlight: {str(e)}")
            return False

    # ==================== Annotation Management ====================

    def create_annotation(
        self,
        user_id: str,
        content_type: str,
        content_id: str,
        annotation_text: str,
        annotation_type: str = 'note',
        position_data: Optional[Dict] = None,
        highlight_id: Optional[str] = None,
        is_private: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Create annotation"""
        try:
            import json

            query = text("""
                INSERT INTO annotations (
                    user_id, content_type, content_id, annotation_type,
                    annotation_text, position_data, highlight_id, is_private
                )
                VALUES (
                    :user_id, :content_type, :content_id, :annotation_type,
                    :annotation_text, :position_data::jsonb, :highlight_id, :is_private
                )
                RETURNING id, created_at
            """)

            result = self.db.execute(query, {
                'user_id': user_id,
                'content_type': content_type,
                'content_id': content_id,
                'annotation_type': annotation_type,
                'annotation_text': annotation_text,
                'position_data': json.dumps(position_data) if position_data else None,
                'highlight_id': highlight_id,
                'is_private': is_private
            })

            self.db.commit()
            row = result.fetchone()

            if row:
                return {
                    'id': str(row[0]),
                    'user_id': user_id,
                    'content_type': content_type,
                    'content_id': content_id,
                    'annotation_type': annotation_type,
                    'annotation_text': annotation_text,
                    'is_private': is_private,
                    'created_at': row[1].isoformat()
                }

            return None

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create annotation: {str(e)}")
            return None

    def get_content_annotations(
        self,
        content_type: str,
        content_id: str,
        user_id: Optional[str] = None,
        include_private: bool = False
    ) -> List[Dict[str, Any]]:
        """Get annotations for content"""
        try:
            conditions = ["a.content_type = :content_type", "a.content_id = :content_id"]
            params = {'content_type': content_type, 'content_id': content_id}

            if not include_private:
                conditions.append("(a.is_private = FALSE OR a.user_id = :user_id)")
                params['user_id'] = user_id

            where_clause = " AND ".join(conditions)

            query = text(f"""
                SELECT
                    a.id, a.user_id, a.annotation_type, a.annotation_text,
                    a.position_data, a.highlight_id, a.is_private,
                    a.is_resolved, a.resolved_at, a.resolved_by,
                    a.created_at, a.updated_at,
                    aa.reply_count, aa.reaction_count
                FROM annotations a
                LEFT JOIN v_annotation_activity aa ON aa.annotation_id = a.id
                WHERE {where_clause}
                ORDER BY a.created_at DESC
            """)

            result = self.db.execute(query, params)

            return [
                {
                    'id': str(row[0]),
                    'user_id': str(row[1]),
                    'annotation_type': row[2],
                    'annotation_text': row[3],
                    'position_data': row[4],
                    'highlight_id': str(row[5]) if row[5] else None,
                    'is_private': row[6],
                    'is_resolved': row[7],
                    'resolved_at': row[8].isoformat() if row[8] else None,
                    'resolved_by': str(row[9]) if row[9] else None,
                    'created_at': row[10].isoformat(),
                    'updated_at': row[11].isoformat() if row[11] else None,
                    'reply_count': row[12] or 0,
                    'reaction_count': row[13] or 0
                }
                for row in result.fetchall()
            ]

        except Exception as e:
            logger.error(f"Failed to get annotations: {str(e)}")
            return []

    def update_annotation(
        self,
        annotation_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update annotation"""
        try:
            update_fields = []
            params = {'annotation_id': annotation_id, 'user_id': user_id}

            if 'annotation_text' in updates:
                update_fields.append("annotation_text = :annotation_text")
                params['annotation_text'] = updates['annotation_text']

            if 'is_private' in updates:
                update_fields.append("is_private = :is_private")
                params['is_private'] = updates['is_private']

            if not update_fields:
                return True

            query = text(f"""
                UPDATE annotations
                SET {', '.join(update_fields)}, updated_at = NOW()
                WHERE id = :annotation_id AND user_id = :user_id
            """)

            result = self.db.execute(query, params)
            self.db.commit()

            return result.rowcount > 0

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update annotation: {str(e)}")
            return False

    def resolve_annotation(
        self,
        annotation_id: str,
        user_id: str
    ) -> bool:
        """Mark annotation as resolved"""
        try:
            query = text("""
                UPDATE annotations
                SET is_resolved = TRUE, resolved_at = NOW(), resolved_by = :user_id
                WHERE id = :annotation_id
            """)

            self.db.execute(query, {
                'annotation_id': annotation_id,
                'user_id': user_id
            })

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to resolve annotation: {str(e)}")
            return False

    def delete_annotation(self, annotation_id: str, user_id: str) -> bool:
        """Delete annotation"""
        try:
            query = text("""
                DELETE FROM annotations
                WHERE id = :annotation_id AND user_id = :user_id
            """)

            result = self.db.execute(query, {
                'annotation_id': annotation_id,
                'user_id': user_id
            })

            self.db.commit()
            return result.rowcount > 0

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete annotation: {str(e)}")
            return False

    # ==================== Replies ====================

    def add_reply(
        self,
        annotation_id: str,
        user_id: str,
        reply_text: str
    ) -> Optional[Dict[str, Any]]:
        """Add reply to annotation"""
        try:
            query = text("""
                INSERT INTO annotation_replies (annotation_id, user_id, reply_text)
                VALUES (:annotation_id, :user_id, :reply_text)
                RETURNING id, created_at
            """)

            result = self.db.execute(query, {
                'annotation_id': annotation_id,
                'user_id': user_id,
                'reply_text': reply_text
            })

            self.db.commit()
            row = result.fetchone()

            if row:
                return {
                    'id': str(row[0]),
                    'annotation_id': annotation_id,
                    'user_id': user_id,
                    'reply_text': reply_text,
                    'created_at': row[1].isoformat()
                }

            return None

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to add reply: {str(e)}")
            return None

    def get_annotation_replies(self, annotation_id: str) -> List[Dict[str, Any]]:
        """Get replies for annotation"""
        try:
            query = text("""
                SELECT id, user_id, reply_text, created_at, updated_at
                FROM annotation_replies
                WHERE annotation_id = :annotation_id
                ORDER BY created_at ASC
            """)

            result = self.db.execute(query, {'annotation_id': annotation_id})

            return [
                {
                    'id': str(row[0]),
                    'user_id': str(row[1]),
                    'reply_text': row[2],
                    'created_at': row[3].isoformat(),
                    'updated_at': row[4].isoformat() if row[4] else None
                }
                for row in result.fetchall()
            ]

        except Exception as e:
            logger.error(f"Failed to get replies: {str(e)}")
            return []

    # ==================== Reactions ====================

    def add_reaction(
        self,
        annotation_id: str,
        user_id: str,
        reaction_type: str
    ) -> bool:
        """Add reaction to annotation"""
        try:
            query = text("""
                INSERT INTO annotation_reactions (annotation_id, user_id, reaction_type)
                VALUES (:annotation_id, :user_id, :reaction_type)
                ON CONFLICT (annotation_id, user_id, reaction_type) DO NOTHING
            """)

            self.db.execute(query, {
                'annotation_id': annotation_id,
                'user_id': user_id,
                'reaction_type': reaction_type
            })

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to add reaction: {str(e)}")
            return False

    def remove_reaction(
        self,
        annotation_id: str,
        user_id: str,
        reaction_type: str
    ) -> bool:
        """Remove reaction from annotation"""
        try:
            query = text("""
                DELETE FROM annotation_reactions
                WHERE annotation_id = :annotation_id
                    AND user_id = :user_id
                    AND reaction_type = :reaction_type
            """)

            result = self.db.execute(query, {
                'annotation_id': annotation_id,
                'user_id': user_id,
                'reaction_type': reaction_type
            })

            self.db.commit()
            return result.rowcount > 0

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to remove reaction: {str(e)}")
            return False

    def get_annotation_reactions(self, annotation_id: str) -> Dict[str, int]:
        """Get reaction counts for annotation"""
        try:
            query = text("""
                SELECT reaction_type, COUNT(*) as count
                FROM annotation_reactions
                WHERE annotation_id = :annotation_id
                GROUP BY reaction_type
            """)

            result = self.db.execute(query, {'annotation_id': annotation_id})

            return {row[0]: row[1] for row in result.fetchall()}

        except Exception as e:
            logger.error(f"Failed to get reactions: {str(e)}")
            return {}
