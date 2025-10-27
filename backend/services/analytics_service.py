"""
Analytics Service
Handles event tracking, aggregation, and analytics data management
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, text
from uuid import UUID
import json

from backend.database.models import User
from backend.utils import get_logger

logger = get_logger(__name__)


class AnalyticsEvent:
    """
    Analytics event model (not a database model, used for tracking)
    Maps to analytics_events table via raw SQL
    """
    def __init__(
        self,
        event_type: str,
        event_category: str,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        duration_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        self.event_type = event_type
        self.event_category = event_category
        self.user_id = user_id
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.metadata = metadata or {}
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.session_id = session_id
        self.duration_ms = duration_ms
        self.success = success
        self.error_message = error_message


class AnalyticsService:
    """
    Service for analytics event tracking and data aggregation

    Handles:
    - Event tracking for user actions
    - Event querying and filtering
    - Aggregation calculations
    - Analytics data retrieval
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== Event Tracking ====================

    def track_event(
        self,
        event_type: str,
        event_category: str,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        duration_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Track an analytics event

        Args:
            event_type: Specific action (search, export, chapter_create, etc.)
            event_category: Broad category (user, content, system, search, export)
            user_id: User performing the action
            resource_type: Type of resource (chapter, pdf, etc.)
            resource_id: ID of the resource
            metadata: Additional event data
            ip_address: User's IP address
            user_agent: User's browser user agent
            session_id: User's session ID
            duration_ms: Operation duration in milliseconds
            success: Whether the operation succeeded
            error_message: Error message if operation failed

        Returns:
            Dict with event_id and success status
        """
        try:
            # Convert UUIDs to strings for JSON serialization
            user_id_str = str(user_id) if user_id else None
            resource_id_str = str(resource_id) if resource_id else None

            # Serialize metadata to JSON
            metadata_json = json.dumps(metadata or {})

            # Insert event using raw SQL for flexibility
            query = text("""
                INSERT INTO analytics_events (
                    event_type, event_category, user_id, resource_type, resource_id,
                    metadata, ip_address, user_agent, session_id, duration_ms,
                    success, error_message, created_at
                )
                VALUES (
                    :event_type, :event_category, :user_id, :resource_type, :resource_id,
                    :metadata::jsonb, :ip_address, :user_agent, :session_id, :duration_ms,
                    :success, :error_message, NOW()
                )
                RETURNING id
            """)

            result = self.db.execute(query, {
                "event_type": event_type,
                "event_category": event_category,
                "user_id": user_id_str,
                "resource_type": resource_type,
                "resource_id": resource_id_str,
                "metadata": metadata_json,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "session_id": session_id,
                "duration_ms": duration_ms,
                "success": success,
                "error_message": error_message
            })

            self.db.commit()

            event_id = result.fetchone()[0]

            logger.debug(f"Tracked event: {event_type} (category: {event_category})")

            return {
                "success": True,
                "event_id": str(event_id),
                "event_type": event_type
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to track event: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    # ==================== Event Querying ====================

    def get_events(
        self,
        event_type: Optional[str] = None,
        event_category: Optional[str] = None,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        success: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Query analytics events with filters

        Args:
            event_type: Filter by event type
            event_category: Filter by category
            user_id: Filter by user
            resource_type: Filter by resource type
            resource_id: Filter by specific resource
            start_date: Start of time range
            end_date: End of time range
            success: Filter by success status
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of event dictionaries
        """
        try:
            # Build query conditions
            conditions = []
            params = {}

            if event_type:
                conditions.append("event_type = :event_type")
                params["event_type"] = event_type

            if event_category:
                conditions.append("event_category = :event_category")
                params["event_category"] = event_category

            if user_id:
                conditions.append("user_id = :user_id")
                params["user_id"] = str(user_id)

            if resource_type:
                conditions.append("resource_type = :resource_type")
                params["resource_type"] = resource_type

            if resource_id:
                conditions.append("resource_id = :resource_id")
                params["resource_id"] = str(resource_id)

            if start_date:
                conditions.append("created_at >= :start_date")
                params["start_date"] = start_date

            if end_date:
                conditions.append("created_at <= :end_date")
                params["end_date"] = end_date

            if success is not None:
                conditions.append("success = :success")
                params["success"] = success

            # Build WHERE clause
            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # Execute query
            query = text(f"""
                SELECT
                    id, event_type, event_category, user_id, resource_type, resource_id,
                    metadata, ip_address, user_agent, session_id, duration_ms,
                    success, error_message, created_at
                FROM analytics_events
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """)

            params["limit"] = limit
            params["offset"] = offset

            result = self.db.execute(query, params)

            events = []
            for row in result:
                events.append({
                    "id": str(row[0]),
                    "event_type": row[1],
                    "event_category": row[2],
                    "user_id": str(row[3]) if row[3] else None,
                    "resource_type": row[4],
                    "resource_id": str(row[5]) if row[5] else None,
                    "metadata": row[6] if row[6] else {},
                    "ip_address": str(row[7]) if row[7] else None,
                    "user_agent": row[8],
                    "session_id": row[9],
                    "duration_ms": row[10],
                    "success": row[11],
                    "error_message": row[12],
                    "created_at": row[13].isoformat() if row[13] else None
                })

            return events

        except Exception as e:
            logger.error(f"Failed to query events: {str(e)}", exc_info=True)
            return []

    def get_event_count(
        self,
        event_type: Optional[str] = None,
        event_category: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        success: Optional[bool] = None
    ) -> int:
        """
        Get count of events matching filters

        Args:
            event_type: Filter by event type
            event_category: Filter by category
            user_id: Filter by user
            start_date: Start of time range
            end_date: End of time range
            success: Filter by success status

        Returns:
            Event count
        """
        try:
            conditions = []
            params = {}

            if event_type:
                conditions.append("event_type = :event_type")
                params["event_type"] = event_type

            if event_category:
                conditions.append("event_category = :event_category")
                params["event_category"] = event_category

            if user_id:
                conditions.append("user_id = :user_id")
                params["user_id"] = str(user_id)

            if start_date:
                conditions.append("created_at >= :start_date")
                params["start_date"] = start_date

            if end_date:
                conditions.append("created_at <= :end_date")
                params["end_date"] = end_date

            if success is not None:
                conditions.append("success = :success")
                params["success"] = success

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = text(f"""
                SELECT COUNT(*) FROM analytics_events WHERE {where_clause}
            """)

            result = self.db.execute(query, params)
            count = result.fetchone()[0]

            return count

        except Exception as e:
            logger.error(f"Failed to get event count: {str(e)}", exc_info=True)
            return 0

    # ==================== Aggregation Methods ====================

    def get_daily_aggregates(
        self,
        metric_type: str,
        metric_category: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get daily aggregated metrics

        Args:
            metric_type: Type of metric (event_count, avg_duration, unique_users)
            metric_category: Filter by metric category
            user_id: Filter by user
            start_date: Start of date range
            end_date: End of date range
            limit: Maximum number of results

        Returns:
            List of daily aggregate dictionaries
        """
        try:
            conditions = ["period_type = 'daily'", "metric_type = :metric_type"]
            params = {"metric_type": metric_type}

            if metric_category:
                conditions.append("metric_category = :metric_category")
                params["metric_category"] = metric_category

            if user_id:
                conditions.append("user_id = :user_id")
                params["user_id"] = str(user_id)

            if start_date:
                conditions.append("period_start >= :start_date")
                params["start_date"] = start_date

            if end_date:
                conditions.append("period_end <= :end_date")
                params["end_date"] = end_date

            where_clause = " AND ".join(conditions)

            query = text(f"""
                SELECT
                    id, period_start, period_end, metric_type, metric_category,
                    user_id, value, metadata, created_at, updated_at
                FROM analytics_aggregates
                WHERE {where_clause}
                ORDER BY period_start DESC
                LIMIT :limit
            """)

            params["limit"] = limit

            result = self.db.execute(query, params)

            aggregates = []
            for row in result:
                aggregates.append({
                    "id": str(row[0]),
                    "period_start": row[1].isoformat() if row[1] else None,
                    "period_end": row[2].isoformat() if row[2] else None,
                    "metric_type": row[3],
                    "metric_category": row[4],
                    "user_id": str(row[5]) if row[5] else None,
                    "value": float(row[6]) if row[6] else 0,
                    "metadata": row[7] if row[7] else {},
                    "created_at": row[8].isoformat() if row[8] else None,
                    "updated_at": row[9].isoformat() if row[9] else None
                })

            return aggregates

        except Exception as e:
            logger.error(f"Failed to get daily aggregates: {str(e)}", exc_info=True)
            return []

    def calculate_aggregates_for_date(self, target_date: date) -> Dict[str, Any]:
        """
        Calculate and store aggregates for a specific date

        Args:
            target_date: Date to calculate aggregates for

        Returns:
            Dict with success status and calculated metrics
        """
        try:
            # Call PostgreSQL function to calculate aggregates
            query = text("SELECT calculate_daily_aggregates(:target_date)")
            self.db.execute(query, {"target_date": target_date})
            self.db.commit()

            logger.info(f"Calculated aggregates for {target_date}")

            return {
                "success": True,
                "date": target_date.isoformat(),
                "message": "Aggregates calculated successfully"
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to calculate aggregates: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    # ==================== Analytics Queries ====================

    def get_user_activity_summary(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get activity summary for a specific user

        Args:
            user_id: User ID
            start_date: Start of time range
            end_date: End of time range

        Returns:
            Dict with user activity statistics
        """
        try:
            # Default to last 30 days if no dates provided
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=30)

            query = text("""
                SELECT
                    COUNT(*) as total_events,
                    COUNT(DISTINCT DATE(created_at)) as active_days,
                    COUNT(CASE WHEN event_type = 'search' THEN 1 END) as searches,
                    COUNT(CASE WHEN event_type = 'export' THEN 1 END) as exports,
                    COUNT(CASE WHEN event_type = 'chapter_create' THEN 1 END) as chapters_created,
                    COUNT(CASE WHEN event_type = 'pdf_upload' THEN 1 END) as pdfs_uploaded,
                    AVG(duration_ms) as avg_duration_ms,
                    MAX(created_at) as last_activity
                FROM analytics_events
                WHERE user_id = :user_id
                    AND created_at BETWEEN :start_date AND :end_date
            """)

            result = self.db.execute(query, {
                "user_id": str(user_id),
                "start_date": start_date,
                "end_date": end_date
            })

            row = result.fetchone()

            return {
                "user_id": str(user_id),
                "time_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "total_events": row[0] or 0,
                "active_days": row[1] or 0,
                "searches": row[2] or 0,
                "exports": row[3] or 0,
                "chapters_created": row[4] or 0,
                "pdfs_uploaded": row[5] or 0,
                "avg_duration_ms": float(row[6]) if row[6] else 0,
                "last_activity": row[7].isoformat() if row[7] else None
            }

        except Exception as e:
            logger.error(f"Failed to get user activity summary: {str(e)}", exc_info=True)
            return {}

    def get_popular_content(
        self,
        resource_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get most popular content by view count

        Args:
            resource_type: Filter by resource type (chapter, pdf)
            limit: Maximum number of results

        Returns:
            List of popular content items
        """
        try:
            conditions = ["event_type IN ('view', 'read', 'open')", "resource_id IS NOT NULL"]
            params = {"limit": limit}

            if resource_type:
                conditions.append("resource_type = :resource_type")
                params["resource_type"] = resource_type

            where_clause = " AND ".join(conditions)

            query = text(f"""
                SELECT
                    resource_type,
                    resource_id,
                    COUNT(*) as view_count,
                    COUNT(DISTINCT user_id) as unique_viewers,
                    MAX(created_at) as last_viewed
                FROM analytics_events
                WHERE {where_clause}
                GROUP BY resource_type, resource_id
                ORDER BY view_count DESC
                LIMIT :limit
            """)

            result = self.db.execute(query, params)

            popular = []
            for row in result:
                popular.append({
                    "resource_type": row[0],
                    "resource_id": str(row[1]),
                    "view_count": row[2],
                    "unique_viewers": row[3],
                    "last_viewed": row[4].isoformat() if row[4] else None
                })

            return popular

        except Exception as e:
            logger.error(f"Failed to get popular content: {str(e)}", exc_info=True)
            return []

    def get_event_timeline(
        self,
        event_type: Optional[str] = None,
        event_category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        interval: str = "1 day"
    ) -> List[Dict[str, Any]]:
        """
        Get event counts over time

        Args:
            event_type: Filter by event type
            event_category: Filter by category
            start_date: Start of time range
            end_date: End of time range
            interval: Time bucket interval (1 hour, 1 day, 1 week)

        Returns:
            List of time buckets with event counts
        """
        try:
            # Default to last 7 days if no dates provided
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=7)

            conditions = ["created_at BETWEEN :start_date AND :end_date"]
            params = {
                "start_date": start_date,
                "end_date": end_date,
                "interval": interval
            }

            if event_type:
                conditions.append("event_type = :event_type")
                params["event_type"] = event_type

            if event_category:
                conditions.append("event_category = :event_category")
                params["event_category"] = event_category

            where_clause = " AND ".join(conditions)

            query = text(f"""
                SELECT
                    date_trunc('hour', created_at) +
                        (extract(hour from created_at)::int /
                         EXTRACT(epoch FROM INTERVAL :interval) / 3600)::int *
                         INTERVAL :interval as time_bucket,
                    COUNT(*) as event_count,
                    COUNT(DISTINCT user_id) as unique_users
                FROM analytics_events
                WHERE {where_clause}
                GROUP BY time_bucket
                ORDER BY time_bucket
            """)

            result = self.db.execute(query, params)

            timeline = []
            for row in result:
                timeline.append({
                    "time_bucket": row[0].isoformat() if row[0] else None,
                    "event_count": row[1],
                    "unique_users": row[2]
                })

            return timeline

        except Exception as e:
            logger.error(f"Failed to get event timeline: {str(e)}", exc_info=True)
            return []

    def get_system_health_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get system health and performance metrics

        Args:
            start_date: Start of time range
            end_date: End of time range

        Returns:
            Dict with system health metrics
        """
        try:
            # Default to last 24 hours if no dates provided
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(hours=24)

            query = text("""
                SELECT
                    COUNT(*) as total_events,
                    AVG(duration_ms) as avg_response_time_ms,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95_response_time_ms,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms) as p99_response_time_ms,
                    SUM(CASE WHEN success = TRUE THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as success_rate,
                    COUNT(DISTINCT user_id) as active_users,
                    COUNT(DISTINCT session_id) as total_sessions,
                    COUNT(CASE WHEN success = FALSE THEN 1 END) as error_count
                FROM analytics_events
                WHERE created_at BETWEEN :start_date AND :end_date
                    AND duration_ms IS NOT NULL
            """)

            result = self.db.execute(query, {
                "start_date": start_date,
                "end_date": end_date
            })

            row = result.fetchone()

            return {
                "time_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "total_events": row[0] or 0,
                "avg_response_time_ms": float(row[1]) if row[1] else 0,
                "p95_response_time_ms": float(row[2]) if row[2] else 0,
                "p99_response_time_ms": float(row[3]) if row[3] else 0,
                "success_rate": float(row[4]) if row[4] else 100.0,
                "active_users": row[5] or 0,
                "total_sessions": row[6] or 0,
                "error_count": row[7] or 0
            }

        except Exception as e:
            logger.error(f"Failed to get system health metrics: {str(e)}", exc_info=True)
            return {}
