"""
Bookmark Service for Phase 18: Advanced Content Features
Manages user bookmarks and collections
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.utils import get_logger

logger = get_logger(__name__)


class BookmarkService:
    """
    Bookmark and collection management service

    Features:
    - Create and organize bookmarks
    - Bookmark collections (folders)
    - Favorites
    - Sharing collections
    - Collaborative recommendations
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== Bookmark Management ====================

    def create_bookmark(
        self,
        user_id: str,
        content_type: str,
        content_id: str,
        collection_id: Optional[str] = None,
        title: Optional[str] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_favorite: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Create new bookmark"""
        try:
            query = text("""
                INSERT INTO bookmarks (
                    user_id, content_type, content_id, collection_id,
                    title, notes, tags, is_favorite
                )
                VALUES (
                    :user_id, :content_type, :content_id, :collection_id,
                    :title, :notes, :tags, :is_favorite
                )
                ON CONFLICT (user_id, content_type, content_id)
                DO UPDATE SET
                    collection_id = EXCLUDED.collection_id,
                    notes = EXCLUDED.notes,
                    tags = EXCLUDED.tags,
                    is_favorite = EXCLUDED.is_favorite,
                    updated_at = NOW()
                RETURNING id, created_at
            """)

            result = self.db.execute(query, {
                'user_id': user_id,
                'content_type': content_type,
                'content_id': content_id,
                'collection_id': collection_id,
                'title': title,
                'notes': notes,
                'tags': tags,
                'is_favorite': is_favorite
            })

            self.db.commit()
            row = result.fetchone()

            if row:
                return {
                    'id': str(row[0]),
                    'user_id': user_id,
                    'content_type': content_type,
                    'content_id': content_id,
                    'created_at': row[1].isoformat()
                }

            return None

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create bookmark: {str(e)}")
            return None

    def get_user_bookmarks(
        self,
        user_id: str,
        collection_id: Optional[str] = None,
        content_type: Optional[str] = None,
        favorites_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's bookmarks"""
        try:
            conditions = ["b.user_id = :user_id"]
            params = {'user_id': user_id, 'limit': limit, 'offset': offset}

            if collection_id:
                conditions.append("b.collection_id = :collection_id")
                params['collection_id'] = collection_id

            if content_type:
                conditions.append("b.content_type = :content_type")
                params['content_type'] = content_type

            if favorites_only:
                conditions.append("b.is_favorite = TRUE")

            where_clause = " AND ".join(conditions)

            query = text(f"""
                SELECT
                    b.id, b.content_type, b.content_id, b.collection_id,
                    b.title, b.notes, b.tags, b.is_favorite,
                    b.sort_order, b.created_at, b.updated_at,
                    bc.name as collection_name
                FROM bookmarks b
                LEFT JOIN bookmark_collections bc ON bc.id = b.collection_id
                WHERE {where_clause}
                ORDER BY b.is_favorite DESC, b.sort_order, b.created_at DESC
                LIMIT :limit OFFSET :offset
            """)

            result = self.db.execute(query, params)

            return [
                {
                    'id': str(row[0]),
                    'content_type': row[1],
                    'content_id': str(row[2]),
                    'collection_id': str(row[3]) if row[3] else None,
                    'title': row[4],
                    'notes': row[5],
                    'tags': row[6] or [],
                    'is_favorite': row[7],
                    'sort_order': row[8],
                    'created_at': row[9].isoformat(),
                    'updated_at': row[10].isoformat() if row[10] else None,
                    'collection_name': row[11]
                }
                for row in result.fetchall()
            ]

        except Exception as e:
            logger.error(f"Failed to get bookmarks: {str(e)}")
            return []

    def delete_bookmark(self, bookmark_id: str, user_id: str) -> bool:
        """Delete bookmark"""
        try:
            query = text("""
                DELETE FROM bookmarks
                WHERE id = :bookmark_id AND user_id = :user_id
            """)

            result = self.db.execute(query, {
                'bookmark_id': bookmark_id,
                'user_id': user_id
            })

            self.db.commit()
            return result.rowcount > 0

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete bookmark: {str(e)}")
            return False

    # ==================== Collection Management ====================

    def create_collection(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        is_public: bool = False,
        parent_collection_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Create bookmark collection"""
        try:
            query = text("""
                INSERT INTO bookmark_collections (
                    user_id, name, description, icon, color,
                    is_public, parent_collection_id
                )
                VALUES (
                    :user_id, :name, :description, :icon, :color,
                    :is_public, :parent_collection_id
                )
                RETURNING id, name, created_at
            """)

            result = self.db.execute(query, {
                'user_id': user_id,
                'name': name,
                'description': description,
                'icon': icon,
                'color': color,
                'is_public': is_public,
                'parent_collection_id': parent_collection_id
            })

            self.db.commit()
            row = result.fetchone()

            if row:
                return {
                    'id': str(row[0]),
                    'name': row[1],
                    'created_at': row[2].isoformat()
                }

            return None

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create collection: {str(e)}")
            return None

    def get_user_collections(
        self,
        user_id: str,
        include_shared: bool = False
    ) -> List[Dict[str, Any]]:
        """Get user's collections"""
        try:
            query = text("""
                SELECT
                    bc.id, bc.name, bc.description, bc.icon, bc.color,
                    bc.is_public, bc.parent_collection_id, bc.sort_order,
                    COUNT(b.id) as bookmark_count,
                    bc.created_at, bc.updated_at
                FROM bookmark_collections bc
                LEFT JOIN bookmarks b ON b.collection_id = bc.id
                WHERE bc.user_id = :user_id
                GROUP BY bc.id
                ORDER BY bc.sort_order, bc.created_at DESC
            """)

            result = self.db.execute(query, {'user_id': user_id})

            collections = [
                {
                    'id': str(row[0]),
                    'name': row[1],
                    'description': row[2],
                    'icon': row[3],
                    'color': row[4],
                    'is_public': row[5],
                    'parent_collection_id': str(row[6]) if row[6] else None,
                    'sort_order': row[7],
                    'bookmark_count': row[8],
                    'created_at': row[9].isoformat(),
                    'updated_at': row[10].isoformat() if row[10] else None
                }
                for row in result.fetchall()
            ]

            # Get shared collections if requested
            if include_shared:
                shared = self._get_shared_collections(user_id)
                collections.extend(shared)

            return collections

        except Exception as e:
            logger.error(f"Failed to get collections: {str(e)}")
            return []

    def _get_shared_collections(self, user_id: str) -> List[Dict[str, Any]]:
        """Get collections shared with user"""
        try:
            query = text("""
                SELECT
                    bc.id, bc.name, bc.description, bc.icon, bc.color,
                    sc.permission_level, sc.shared_by,
                    COUNT(b.id) as bookmark_count
                FROM bookmark_collections bc
                JOIN shared_collections sc ON sc.collection_id = bc.id
                LEFT JOIN bookmarks b ON b.collection_id = bc.id
                WHERE sc.shared_with_user_id = :user_id
                GROUP BY bc.id, sc.permission_level, sc.shared_by
            """)

            result = self.db.execute(query, {'user_id': user_id})

            return [
                {
                    'id': str(row[0]),
                    'name': row[1],
                    'description': row[2],
                    'icon': row[3],
                    'color': row[4],
                    'permission_level': row[5],
                    'shared_by': str(row[6]),
                    'bookmark_count': row[7],
                    'is_shared': True
                }
                for row in result.fetchall()
            ]

        except Exception as e:
            logger.error(f"Failed to get shared collections: {str(e)}")
            return []

    def share_collection(
        self,
        collection_id: str,
        user_id: str,
        shared_with_user_id: Optional[str] = None,
        shared_with_email: Optional[str] = None,
        permission_level: str = 'view'
    ) -> bool:
        """Share collection with another user"""
        try:
            # Verify ownership
            verify_query = text("""
                SELECT 1 FROM bookmark_collections
                WHERE id = :collection_id AND user_id = :user_id
            """)

            verify_result = self.db.execute(verify_query, {
                'collection_id': collection_id,
                'user_id': user_id
            })

            if not verify_result.fetchone():
                return False

            # Create share
            query = text("""
                INSERT INTO shared_collections (
                    collection_id, shared_with_user_id, shared_with_email,
                    permission_level, shared_by
                )
                VALUES (
                    :collection_id, :shared_with_user_id, :shared_with_email,
                    :permission_level, :shared_by
                )
            """)

            self.db.execute(query, {
                'collection_id': collection_id,
                'shared_with_user_id': shared_with_user_id,
                'shared_with_email': shared_with_email,
                'permission_level': permission_level,
                'shared_by': user_id
            })

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to share collection: {str(e)}")
            return False

    # ==================== Recommendations ====================

    def get_collaborative_recommendations(
        self,
        user_id: str,
        content_type: str,
        content_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get bookmark-based recommendations (users who bookmarked X also bookmarked Y)"""
        try:
            query = text("""
                SELECT * FROM get_collaborative_bookmark_recommendations(
                    :user_id::uuid, :content_type, :content_id::uuid, :limit
                )
            """)

            result = self.db.execute(query, {
                'user_id': user_id,
                'content_type': content_type,
                'content_id': content_id,
                'limit': limit
            })

            return [
                {
                    'content_type': row[0],
                    'content_id': str(row[1]),
                    'relevance_score': float(row[2])
                }
                for row in result.fetchall()
            ]

        except Exception as e:
            logger.error(f"Failed to get collaborative recommendations: {str(e)}")
            return []

    def get_popular_bookmarked_content(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get most bookmarked content"""
        try:
            query = text("""
                SELECT * FROM get_popular_bookmarked_content(:limit)
            """)

            result = self.db.execute(query, {'limit': limit})

            return [
                {
                    'content_type': row[0],
                    'content_id': str(row[1]),
                    'bookmark_count': row[2],
                    'unique_users': row[3]
                }
                for row in result.fetchall()
            ]

        except Exception as e:
            logger.error(f"Failed to get popular bookmarked content: {str(e)}")
            return []

    def get_bookmark_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get user's bookmark statistics"""
        try:
            query = text("""
                SELECT * FROM v_user_bookmark_stats
                WHERE user_id = :user_id
            """)

            result = self.db.execute(query, {'user_id': user_id})
            row = result.fetchone()

            if row:
                return {
                    'total_bookmarks': row[1],
                    'favorite_count': row[2],
                    'collection_count': row[3],
                    'content_types_bookmarked': row[4],
                    'last_bookmark_at': row[5].isoformat() if row[5] else None
                }

            return {}

        except Exception as e:
            logger.error(f"Failed to get bookmark statistics: {str(e)}")
            return {}
