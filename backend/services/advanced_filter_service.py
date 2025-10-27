"""
Advanced Filter Service for Phase 18: Advanced Content Features
Manages advanced filtering and content discovery
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
import json

from backend.utils import get_logger

logger = get_logger(__name__)


class AdvancedFilterService:
    """
    Advanced filtering and content discovery service

    Features:
    - Save and manage filter configurations
    - System filter presets
    - Dynamic filter application
    - Filter sharing and collaboration
    - Usage tracking and recommendations
    - Complex multi-criteria filtering
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== Saved Filters ====================

    def save_filter(
        self,
        user_id: str,
        name: str,
        filter_config: Dict[str, Any],
        description: Optional[str] = None,
        is_favorite: bool = False,
        is_shared: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Save user filter configuration

        Args:
            user_id: User creating filter
            name: Filter name
            filter_config: Filter configuration dict
            description: Filter description
            is_favorite: Mark as favorite
            is_shared: Share with other users

        Filter config structure:
        {
            "content_type": ["pdf", "chapter"],
            "date_range": {"start": "2024-01-01", "end": "2024-12-31"},
            "tags": ["brain", "tumor"],
            "status": ["published"],
            "complexity": {"min": 1, "max": 5},
            "author_ids": ["uuid1", "uuid2"],
            "has_images": true,
            "min_word_count": 500,
            "sort_by": "created_at",
            "sort_order": "desc"
        }
        """
        try:
            query = text("""
                INSERT INTO saved_filters (
                    user_id, name, description, filter_config,
                    is_favorite, is_shared
                )
                VALUES (
                    :user_id, :name, :description, :filter_config::jsonb,
                    :is_favorite, :is_shared
                )
                RETURNING id, name, created_at
            """)

            result = self.db.execute(query, {
                'user_id': user_id,
                'name': name,
                'description': description,
                'filter_config': json.dumps(filter_config),
                'is_favorite': is_favorite,
                'is_shared': is_shared
            })

            self.db.commit()
            row = result.fetchone()

            if row:
                return {
                    'id': str(row[0]),
                    'name': row[1],
                    'filter_config': filter_config,
                    'created_at': row[2].isoformat()
                }

            return None

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save filter: {str(e)}")
            return None

    def get_user_filters(
        self,
        user_id: str,
        include_shared: bool = True,
        favorites_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get user's saved filters"""
        try:
            conditions = ["(sf.user_id = :user_id"]
            params = {'user_id': user_id}

            if include_shared:
                conditions[0] += " OR sf.is_shared = TRUE)"
            else:
                conditions[0] += ")"

            if favorites_only:
                conditions.append("sf.is_favorite = TRUE")

            where_clause = " AND ".join(conditions)

            query = text(f"""
                SELECT
                    sf.id, sf.name, sf.description, sf.filter_config,
                    sf.is_favorite, sf.is_shared, sf.usage_count,
                    sf.last_used_at, sf.created_at, sf.updated_at,
                    sf.user_id
                FROM saved_filters sf
                WHERE {where_clause}
                ORDER BY sf.is_favorite DESC, sf.usage_count DESC, sf.created_at DESC
            """)

            result = self.db.execute(query, params)

            return [
                {
                    'id': str(row[0]),
                    'name': row[1],
                    'description': row[2],
                    'filter_config': row[3],
                    'is_favorite': row[4],
                    'is_shared': row[5],
                    'usage_count': row[6],
                    'last_used_at': row[7].isoformat() if row[7] else None,
                    'created_at': row[8].isoformat(),
                    'updated_at': row[9].isoformat() if row[9] else None,
                    'is_owner': str(row[10]) == user_id
                }
                for row in result.fetchall()
            ]

        except Exception as e:
            logger.error(f"Failed to get user filters: {str(e)}")
            return []

    def update_filter(
        self,
        filter_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update saved filter"""
        try:
            update_fields = []
            params = {'filter_id': filter_id, 'user_id': user_id}

            if 'name' in updates:
                update_fields.append("name = :name")
                params['name'] = updates['name']

            if 'description' in updates:
                update_fields.append("description = :description")
                params['description'] = updates['description']

            if 'filter_config' in updates:
                update_fields.append("filter_config = :filter_config::jsonb")
                params['filter_config'] = json.dumps(updates['filter_config'])

            if 'is_favorite' in updates:
                update_fields.append("is_favorite = :is_favorite")
                params['is_favorite'] = updates['is_favorite']

            if 'is_shared' in updates:
                update_fields.append("is_shared = :is_shared")
                params['is_shared'] = updates['is_shared']

            if not update_fields:
                return True

            query = text(f"""
                UPDATE saved_filters
                SET {', '.join(update_fields)}, updated_at = NOW()
                WHERE id = :filter_id AND user_id = :user_id
            """)

            result = self.db.execute(query, params)
            self.db.commit()

            return result.rowcount > 0

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update filter: {str(e)}")
            return False

    def delete_filter(self, filter_id: str, user_id: str) -> bool:
        """Delete saved filter"""
        try:
            query = text("""
                DELETE FROM saved_filters
                WHERE id = :filter_id AND user_id = :user_id
            """)

            result = self.db.execute(query, {
                'filter_id': filter_id,
                'user_id': user_id
            })

            self.db.commit()
            return result.rowcount > 0

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete filter: {str(e)}")
            return False

    def track_filter_usage(self, filter_id: str, user_id: str):
        """Track filter usage for recommendations"""
        try:
            query = text("""
                UPDATE saved_filters
                SET usage_count = usage_count + 1, last_used_at = NOW()
                WHERE id = :filter_id
            """)

            self.db.execute(query, {'filter_id': filter_id})
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to track filter usage: {str(e)}")

    # ==================== Filter Presets ====================

    def get_filter_presets(
        self,
        preset_type: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get system filter presets"""
        try:
            conditions = []
            params = {}

            if active_only:
                conditions.append("fp.is_active = TRUE")

            if preset_type:
                conditions.append("fp.preset_type = :preset_type")
                params['preset_type'] = preset_type

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = text(f"""
                SELECT
                    fp.id, fp.name, fp.description, fp.preset_type,
                    fp.filter_config, fp.icon, fp.sort_order
                FROM filter_presets fp
                WHERE {where_clause}
                ORDER BY fp.sort_order, fp.name
            """)

            result = self.db.execute(query, params)

            return [
                {
                    'id': str(row[0]),
                    'name': row[1],
                    'description': row[2],
                    'preset_type': row[3],
                    'filter_config': row[4],
                    'icon': row[5],
                    'sort_order': row[6]
                }
                for row in result.fetchall()
            ]

        except Exception as e:
            logger.error(f"Failed to get filter presets: {str(e)}")
            return []

    # ==================== Filter Application ====================

    def apply_filter(
        self,
        filter_config: Dict[str, Any],
        base_table: str = "chapters",
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Apply filter to content query

        Args:
            filter_config: Filter configuration
            base_table: Table to filter (chapters, pdfs, etc.)
            user_id: User applying filter
            limit: Results limit
            offset: Pagination offset

        Returns:
            Tuple of (filtered results, total count)
        """
        try:
            # Build WHERE conditions
            conditions, params = self._build_filter_conditions(filter_config, base_table)
            params['limit'] = limit
            params['offset'] = offset

            if user_id:
                params['user_id'] = user_id

            # Build ORDER BY
            order_by = self._build_order_by(filter_config)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # Query based on table type
            if base_table == "chapters":
                results = self._apply_chapter_filter(where_clause, order_by, params)
            elif base_table == "pdfs":
                results = self._apply_pdf_filter(where_clause, order_by, params)
            else:
                results = []

            # Get total count
            count_query = text(f"""
                SELECT COUNT(*)
                FROM {base_table} t
                WHERE {where_clause}
            """)

            count_result = self.db.execute(count_query, params)
            total_count = count_result.scalar() or 0

            return results, total_count

        except Exception as e:
            logger.error(f"Failed to apply filter: {str(e)}")
            return [], 0

    def _build_filter_conditions(
        self,
        filter_config: Dict[str, Any],
        base_table: str
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Build SQL WHERE conditions from filter config"""
        conditions = []
        params = {}

        # Content type filter
        if 'content_type' in filter_config and filter_config['content_type']:
            # This is handled by base_table parameter
            pass

        # Date range filter
        if 'date_range' in filter_config:
            date_range = filter_config['date_range']
            if 'start' in date_range:
                conditions.append("t.created_at >= :date_start")
                params['date_start'] = date_range['start']
            if 'end' in date_range:
                conditions.append("t.created_at <= :date_end")
                params['date_end'] = date_range['end']

        # Tags filter
        if 'tags' in filter_config and filter_config['tags']:
            conditions.append("t.tags && :tags")
            params['tags'] = filter_config['tags']

        # Status filter
        if 'status' in filter_config and filter_config['status']:
            if base_table == "chapters":
                conditions.append("t.status = ANY(:status_list)")
                params['status_list'] = filter_config['status']

        # Complexity filter
        if 'complexity' in filter_config:
            complexity = filter_config['complexity']
            if 'min' in complexity:
                conditions.append("t.complexity_level >= :complexity_min")
                params['complexity_min'] = complexity['min']
            if 'max' in complexity:
                conditions.append("t.complexity_level <= :complexity_max")
                params['complexity_max'] = complexity['max']

        # Author filter
        if 'author_ids' in filter_config and filter_config['author_ids']:
            conditions.append("t.created_by = ANY(:author_ids)")
            params['author_ids'] = filter_config['author_ids']

        # Has images filter
        if 'has_images' in filter_config and filter_config['has_images']:
            if base_table == "chapters":
                conditions.append("""
                    EXISTS (
                        SELECT 1 FROM chapter_images ci
                        WHERE ci.chapter_id = t.id
                    )
                """)

        # Word count filter
        if 'min_word_count' in filter_config:
            conditions.append("LENGTH(t.content) / 5 >= :min_word_count")
            params['min_word_count'] = filter_config['min_word_count']

        if 'max_word_count' in filter_config:
            conditions.append("LENGTH(t.content) / 5 <= :max_word_count")
            params['max_word_count'] = filter_config['max_word_count']

        # Text search filter
        if 'search_text' in filter_config and filter_config['search_text']:
            conditions.append("""
                (t.title ILIKE :search_text OR t.content ILIKE :search_text)
            """)
            params['search_text'] = f"%{filter_config['search_text']}%"

        return conditions, params

    def _build_order_by(self, filter_config: Dict[str, Any]) -> str:
        """Build ORDER BY clause from filter config"""
        sort_by = filter_config.get('sort_by', 'created_at')
        sort_order = filter_config.get('sort_order', 'desc').upper()

        # Validate sort order
        if sort_order not in ['ASC', 'DESC']:
            sort_order = 'DESC'

        # Map sort fields
        sort_fields = {
            'created_at': 't.created_at',
            'updated_at': 't.updated_at',
            'title': 't.title',
            'complexity': 't.complexity_level',
            'views': 't.view_count',
            'bookmarks': 't.bookmark_count'
        }

        sort_field = sort_fields.get(sort_by, 't.created_at')

        return f"{sort_field} {sort_order}"

    def _apply_chapter_filter(
        self,
        where_clause: str,
        order_by: str,
        params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply filter to chapters"""
        try:
            query = text(f"""
                SELECT
                    t.id, t.title, t.summary, t.status,
                    t.complexity_level, t.tags, t.created_at,
                    t.updated_at, t.created_by,
                    LENGTH(t.content) as content_length,
                    (SELECT COUNT(*) FROM chapter_images ci WHERE ci.chapter_id = t.id) as image_count
                FROM chapters t
                WHERE {where_clause}
                ORDER BY {order_by}
                LIMIT :limit OFFSET :offset
            """)

            result = self.db.execute(query, params)

            return [
                {
                    'id': str(row[0]),
                    'title': row[1],
                    'summary': row[2],
                    'status': row[3],
                    'complexity_level': row[4],
                    'tags': row[5] or [],
                    'created_at': row[6].isoformat(),
                    'updated_at': row[7].isoformat() if row[7] else None,
                    'created_by': str(row[8]) if row[8] else None,
                    'content_length': row[9],
                    'image_count': row[10]
                }
                for row in result.fetchall()
            ]

        except Exception as e:
            logger.error(f"Failed to apply chapter filter: {str(e)}")
            return []

    def _apply_pdf_filter(
        self,
        where_clause: str,
        order_by: str,
        params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply filter to PDFs"""
        try:
            query = text(f"""
                SELECT
                    t.id, t.title, t.author, t.publication_year,
                    t.tags, t.page_count, t.file_size,
                    t.created_at, t.uploaded_by
                FROM pdfs t
                WHERE {where_clause}
                ORDER BY {order_by}
                LIMIT :limit OFFSET :offset
            """)

            result = self.db.execute(query, params)

            return [
                {
                    'id': str(row[0]),
                    'title': row[1],
                    'author': row[2],
                    'publication_year': row[3],
                    'tags': row[4] or [],
                    'page_count': row[5],
                    'file_size': row[6],
                    'created_at': row[7].isoformat(),
                    'uploaded_by': str(row[8]) if row[8] else None
                }
                for row in result.fetchall()
            ]

        except Exception as e:
            logger.error(f"Failed to apply PDF filter: {str(e)}")
            return []

    # ==================== Filter Recommendations ====================

    def get_popular_filters(
        self,
        limit: int = 10,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get most popular shared filters"""
        try:
            query = text("""
                SELECT
                    sf.id, sf.name, sf.description, sf.filter_config,
                    sf.usage_count, sf.user_id,
                    COUNT(DISTINCT sf.user_id) as unique_users
                FROM saved_filters sf
                WHERE sf.is_shared = TRUE
                    AND sf.last_used_at >= NOW() - INTERVAL ':days days'
                GROUP BY sf.id
                ORDER BY sf.usage_count DESC, unique_users DESC
                LIMIT :limit
            """)

            result = self.db.execute(query, {
                'days': days,
                'limit': limit
            })

            return [
                {
                    'id': str(row[0]),
                    'name': row[1],
                    'description': row[2],
                    'filter_config': row[3],
                    'usage_count': row[4],
                    'created_by': str(row[5]),
                    'unique_users': row[6]
                }
                for row in result.fetchall()
            ]

        except Exception as e:
            logger.error(f"Failed to get popular filters: {str(e)}")
            return []

    def validate_filter_config(self, filter_config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate filter configuration

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check required structure
            if not isinstance(filter_config, dict):
                return False, "Filter config must be a dictionary"

            # Validate date range
            if 'date_range' in filter_config:
                date_range = filter_config['date_range']
                if not isinstance(date_range, dict):
                    return False, "date_range must be a dictionary"

                if 'start' in date_range and 'end' in date_range:
                    try:
                        start = datetime.fromisoformat(date_range['start'])
                        end = datetime.fromisoformat(date_range['end'])
                        if start > end:
                            return False, "date_range start must be before end"
                    except ValueError:
                        return False, "Invalid date format in date_range"

            # Validate complexity
            if 'complexity' in filter_config:
                complexity = filter_config['complexity']
                if not isinstance(complexity, dict):
                    return False, "complexity must be a dictionary"

                if 'min' in complexity and not (1 <= complexity['min'] <= 5):
                    return False, "complexity.min must be between 1 and 5"

                if 'max' in complexity and not (1 <= complexity['max'] <= 5):
                    return False, "complexity.max must be between 1 and 5"

                if 'min' in complexity and 'max' in complexity:
                    if complexity['min'] > complexity['max']:
                        return False, "complexity.min must be <= complexity.max"

            # Validate sort order
            if 'sort_order' in filter_config:
                if filter_config['sort_order'].lower() not in ['asc', 'desc']:
                    return False, "sort_order must be 'asc' or 'desc'"

            # Validate arrays
            for array_field in ['content_type', 'tags', 'status', 'author_ids']:
                if array_field in filter_config:
                    if not isinstance(filter_config[array_field], list):
                        return False, f"{array_field} must be an array"

            return True, None

        except Exception as e:
            logger.error(f"Filter validation error: {str(e)}")
            return False, str(e)
