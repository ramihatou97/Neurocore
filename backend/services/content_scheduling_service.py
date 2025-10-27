"""
Content Scheduling Service for Phase 18: Advanced Content Features
Manages timed content publishing and recurring schedules
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
import json

from backend.utils import get_logger

logger = get_logger(__name__)


class ContentSchedulingService:
    """
    Content scheduling and automated publishing service

    Features:
    - Schedule content publication
    - Schedule content unpublication
    - Recurring content schedules
    - Automatic status updates
    - Schedule notifications
    - Timezone support
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== Content Scheduling ====================

    def schedule_publication(
        self,
        user_id: str,
        content_type: str,
        content_id: str,
        publish_at: datetime,
        unpublish_at: Optional[datetime] = None,
        timezone: str = 'UTC',
        notification_enabled: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Schedule content for publication

        Args:
            user_id: User scheduling content
            content_type: Type of content (chapter, pdf, etc.)
            content_id: Content ID
            publish_at: When to publish
            unpublish_at: Optional when to unpublish
            timezone: Timezone for schedule
            notification_enabled: Send notification when published

        Returns:
            Created schedule dict
        """
        try:
            query = text("""
                INSERT INTO content_schedules (
                    user_id, content_type, content_id,
                    publish_at, unpublish_at, timezone,
                    notification_enabled
                )
                VALUES (
                    :user_id, :content_type, :content_id,
                    :publish_at, :unpublish_at, :timezone,
                    :notification_enabled
                )
                RETURNING id, publish_at, status, created_at
            """)

            result = self.db.execute(query, {
                'user_id': user_id,
                'content_type': content_type,
                'content_id': content_id,
                'publish_at': publish_at,
                'unpublish_at': unpublish_at,
                'timezone': timezone,
                'notification_enabled': notification_enabled
            })

            self.db.commit()
            row = result.fetchone()

            if row:
                return {
                    'id': str(row[0]),
                    'content_type': content_type,
                    'content_id': content_id,
                    'publish_at': row[1].isoformat(),
                    'status': row[2],
                    'created_at': row[3].isoformat()
                }

            return None

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to schedule publication: {str(e)}")
            return None

    def get_scheduled_content(
        self,
        user_id: Optional[str] = None,
        content_type: Optional[str] = None,
        status: Optional[str] = None,
        upcoming_only: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get scheduled content"""
        try:
            conditions = []
            params = {'limit': limit}

            if user_id:
                conditions.append("cs.user_id = :user_id")
                params['user_id'] = user_id

            if content_type:
                conditions.append("cs.content_type = :content_type")
                params['content_type'] = content_type

            if status:
                conditions.append("cs.status = :status")
                params['status'] = status

            if upcoming_only:
                conditions.append("cs.publish_at > NOW()")
                conditions.append("cs.status = 'scheduled'")

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = text(f"""
                SELECT
                    cs.id, cs.user_id, cs.content_type, cs.content_id,
                    cs.publish_at, cs.unpublish_at, cs.published_at,
                    cs.status, cs.timezone, cs.notification_enabled,
                    cs.notification_sent, cs.error_message,
                    cs.created_at, cs.updated_at
                FROM content_schedules cs
                WHERE {where_clause}
                ORDER BY cs.publish_at ASC
                LIMIT :limit
            """)

            result = self.db.execute(query, params)

            return [
                {
                    'id': str(row[0]),
                    'user_id': str(row[1]),
                    'content_type': row[2],
                    'content_id': str(row[3]),
                    'publish_at': row[4].isoformat(),
                    'unpublish_at': row[5].isoformat() if row[5] else None,
                    'published_at': row[6].isoformat() if row[6] else None,
                    'status': row[7],
                    'timezone': row[8],
                    'notification_enabled': row[9],
                    'notification_sent': row[10],
                    'error_message': row[11],
                    'created_at': row[12].isoformat(),
                    'updated_at': row[13].isoformat() if row[13] else None
                }
                for row in result.fetchall()
            ]

        except Exception as e:
            logger.error(f"Failed to get scheduled content: {str(e)}")
            return []

    def get_upcoming_schedules(
        self,
        hours: int = 24,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get schedules due within specified hours"""
        try:
            query = text("""
                SELECT * FROM v_upcoming_schedules
                WHERE hours_until_publish <= :hours
                ORDER BY publish_at ASC
                LIMIT :limit
            """)

            result = self.db.execute(query, {
                'hours': hours,
                'limit': limit
            })

            return [
                {
                    'schedule_id': str(row[0]),
                    'content_type': row[1],
                    'content_id': str(row[2]),
                    'publish_at': row[3].isoformat(),
                    'hours_until_publish': float(row[4]),
                    'user_id': str(row[5]),
                    'notification_enabled': row[6]
                }
                for row in result.fetchall()
            ]

        except Exception as e:
            logger.error(f"Failed to get upcoming schedules: {str(e)}")
            return []

    def cancel_schedule(
        self,
        schedule_id: str,
        user_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """Cancel scheduled publication"""
        try:
            query = text("""
                UPDATE content_schedules
                SET status = 'cancelled',
                    error_message = :reason,
                    updated_at = NOW()
                WHERE id = :schedule_id
                    AND user_id = :user_id
                    AND status = 'scheduled'
            """)

            result = self.db.execute(query, {
                'schedule_id': schedule_id,
                'user_id': user_id,
                'reason': reason or 'Cancelled by user'
            })

            self.db.commit()
            return result.rowcount > 0

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to cancel schedule: {str(e)}")
            return False

    def execute_scheduled_publication(self, schedule_id: str) -> bool:
        """
        Execute a scheduled publication

        This method should be called by a background worker

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get schedule details
            query = text("""
                SELECT
                    cs.content_type, cs.content_id, cs.user_id,
                    cs.status, cs.publish_at
                FROM content_schedules cs
                WHERE cs.id = :schedule_id
            """)

            result = self.db.execute(query, {'schedule_id': schedule_id})
            row = result.fetchone()

            if not row:
                logger.error(f"Schedule {schedule_id} not found")
                return False

            content_type, content_id, user_id, status, publish_at = row

            # Check if ready to publish
            if status != 'scheduled':
                logger.warning(f"Schedule {schedule_id} status is {status}, not scheduled")
                return False

            if publish_at > datetime.now():
                logger.warning(f"Schedule {schedule_id} not yet due")
                return False

            # Update content status based on type
            success = False
            error_message = None

            if content_type == 'chapter':
                success = self._publish_chapter(content_id)
                if not success:
                    error_message = "Failed to publish chapter"
            elif content_type == 'pdf':
                success = self._publish_pdf(content_id)
                if not success:
                    error_message = "Failed to publish PDF"
            else:
                error_message = f"Unknown content type: {content_type}"

            # Update schedule status
            if success:
                update_query = text("""
                    UPDATE content_schedules
                    SET status = 'published',
                        published_at = NOW(),
                        updated_at = NOW()
                    WHERE id = :schedule_id
                """)
                self.db.execute(update_query, {'schedule_id': schedule_id})
            else:
                update_query = text("""
                    UPDATE content_schedules
                    SET status = 'failed',
                        error_message = :error_message,
                        updated_at = NOW()
                    WHERE id = :schedule_id
                """)
                self.db.execute(update_query, {
                    'schedule_id': schedule_id,
                    'error_message': error_message
                })

            self.db.commit()
            return success

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to execute scheduled publication: {str(e)}")
            return False

    def _publish_chapter(self, chapter_id: str) -> bool:
        """Publish a chapter"""
        try:
            query = text("""
                UPDATE chapters
                SET status = 'published',
                    published_at = NOW(),
                    updated_at = NOW()
                WHERE id = :chapter_id
                    AND status IN ('draft', 'scheduled')
            """)

            result = self.db.execute(query, {'chapter_id': chapter_id})
            self.db.commit()

            return result.rowcount > 0

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to publish chapter: {str(e)}")
            return False

    def _publish_pdf(self, pdf_id: str) -> bool:
        """Publish a PDF"""
        try:
            # PDFs are typically published immediately on upload
            # This could update visibility or access permissions
            query = text("""
                UPDATE pdfs
                SET is_public = TRUE,
                    updated_at = NOW()
                WHERE id = :pdf_id
            """)

            result = self.db.execute(query, {'pdf_id': pdf_id})
            self.db.commit()

            return result.rowcount > 0

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to publish PDF: {str(e)}")
            return False

    # ==================== Recurring Schedules ====================

    def create_recurring_schedule(
        self,
        user_id: str,
        content_type: str,
        schedule_name: str,
        recurrence_pattern: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        recurrence_config: Optional[Dict[str, Any]] = None,
        timezone: str = 'UTC'
    ) -> Optional[Dict[str, Any]]:
        """
        Create recurring schedule

        Args:
            user_id: User creating schedule
            content_type: Type of content
            schedule_name: Name for schedule
            recurrence_pattern: daily, weekly, monthly, custom
            start_date: When to start
            end_date: Optional end date
            recurrence_config: Additional config (e.g., {"day_of_week": "monday"})
            timezone: Timezone

        Recurrence config examples:
        - Daily: {}
        - Weekly: {"day_of_week": "monday"}
        - Monthly: {"day_of_month": 15}
        - Custom: {"cron": "0 9 * * 1-5"}  # Weekdays at 9am
        """
        try:
            # Calculate next run time
            next_run = self._calculate_next_run(
                start_date,
                recurrence_pattern,
                recurrence_config or {}
            )

            query = text("""
                INSERT INTO recurring_schedules (
                    user_id, content_type, schedule_name,
                    recurrence_pattern, recurrence_config,
                    start_date, end_date, next_run_at, timezone
                )
                VALUES (
                    :user_id, :content_type, :schedule_name,
                    :recurrence_pattern, :recurrence_config::jsonb,
                    :start_date, :end_date, :next_run_at, :timezone
                )
                RETURNING id, schedule_name, next_run_at, created_at
            """)

            result = self.db.execute(query, {
                'user_id': user_id,
                'content_type': content_type,
                'schedule_name': schedule_name,
                'recurrence_pattern': recurrence_pattern,
                'recurrence_config': json.dumps(recurrence_config or {}),
                'start_date': start_date,
                'end_date': end_date,
                'next_run_at': next_run,
                'timezone': timezone
            })

            self.db.commit()
            row = result.fetchone()

            if row:
                return {
                    'id': str(row[0]),
                    'schedule_name': row[1],
                    'recurrence_pattern': recurrence_pattern,
                    'next_run_at': row[2].isoformat() if row[2] else None,
                    'created_at': row[3].isoformat()
                }

            return None

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create recurring schedule: {str(e)}")
            return None

    def get_recurring_schedules(
        self,
        user_id: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get recurring schedules"""
        try:
            conditions = []
            params = {}

            if user_id:
                conditions.append("rs.user_id = :user_id")
                params['user_id'] = user_id

            if active_only:
                conditions.append("rs.is_active = TRUE")
                conditions.append("(rs.end_date IS NULL OR rs.end_date > NOW())")

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = text(f"""
                SELECT
                    rs.id, rs.user_id, rs.content_type, rs.schedule_name,
                    rs.recurrence_pattern, rs.recurrence_config,
                    rs.start_date, rs.end_date, rs.next_run_at,
                    rs.last_run_at, rs.timezone, rs.is_active,
                    rs.created_at, rs.updated_at
                FROM recurring_schedules rs
                WHERE {where_clause}
                ORDER BY rs.next_run_at ASC
            """)

            result = self.db.execute(query, params)

            return [
                {
                    'id': str(row[0]),
                    'user_id': str(row[1]),
                    'content_type': row[2],
                    'schedule_name': row[3],
                    'recurrence_pattern': row[4],
                    'recurrence_config': row[5],
                    'start_date': row[6].isoformat(),
                    'end_date': row[7].isoformat() if row[7] else None,
                    'next_run_at': row[8].isoformat() if row[8] else None,
                    'last_run_at': row[9].isoformat() if row[9] else None,
                    'timezone': row[10],
                    'is_active': row[11],
                    'created_at': row[12].isoformat(),
                    'updated_at': row[13].isoformat() if row[13] else None
                }
                for row in result.fetchall()
            ]

        except Exception as e:
            logger.error(f"Failed to get recurring schedules: {str(e)}")
            return []

    def update_recurring_schedule(
        self,
        schedule_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update recurring schedule"""
        try:
            update_fields = []
            params = {'schedule_id': schedule_id, 'user_id': user_id}

            if 'schedule_name' in updates:
                update_fields.append("schedule_name = :schedule_name")
                params['schedule_name'] = updates['schedule_name']

            if 'is_active' in updates:
                update_fields.append("is_active = :is_active")
                params['is_active'] = updates['is_active']

            if 'end_date' in updates:
                update_fields.append("end_date = :end_date")
                params['end_date'] = updates['end_date']

            if not update_fields:
                return True

            query = text(f"""
                UPDATE recurring_schedules
                SET {', '.join(update_fields)}, updated_at = NOW()
                WHERE id = :schedule_id AND user_id = :user_id
            """)

            result = self.db.execute(query, params)
            self.db.commit()

            return result.rowcount > 0

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update recurring schedule: {str(e)}")
            return False

    def execute_recurring_schedule(self, schedule_id: str) -> bool:
        """Execute recurring schedule and calculate next run"""
        try:
            # Get schedule
            query = text("""
                SELECT
                    rs.user_id, rs.content_type, rs.recurrence_pattern,
                    rs.recurrence_config, rs.next_run_at, rs.end_date
                FROM recurring_schedules rs
                WHERE rs.id = :schedule_id AND rs.is_active = TRUE
            """)

            result = self.db.execute(query, {'schedule_id': schedule_id})
            row = result.fetchone()

            if not row:
                return False

            user_id, content_type, pattern, config, next_run, end_date = row

            # Check if schedule has ended
            if end_date and datetime.now() > end_date:
                self._deactivate_schedule(schedule_id)
                return False

            # Execute the scheduled action (implementation depends on requirements)
            # For now, we'll just update the schedule

            # Calculate next run
            new_next_run = self._calculate_next_run(
                datetime.now(),
                pattern,
                config or {}
            )

            # Update schedule
            update_query = text("""
                UPDATE recurring_schedules
                SET last_run_at = NOW(),
                    next_run_at = :next_run_at,
                    updated_at = NOW()
                WHERE id = :schedule_id
            """)

            self.db.execute(update_query, {
                'schedule_id': schedule_id,
                'next_run_at': new_next_run
            })

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to execute recurring schedule: {str(e)}")
            return False

    def _deactivate_schedule(self, schedule_id: str):
        """Deactivate a recurring schedule"""
        try:
            query = text("""
                UPDATE recurring_schedules
                SET is_active = FALSE, updated_at = NOW()
                WHERE id = :schedule_id
            """)

            self.db.execute(query, {'schedule_id': schedule_id})
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to deactivate schedule: {str(e)}")

    def _calculate_next_run(
        self,
        from_date: datetime,
        pattern: str,
        config: Dict[str, Any]
    ) -> datetime:
        """Calculate next run time based on recurrence pattern"""
        try:
            if pattern == 'daily':
                return from_date + timedelta(days=1)

            elif pattern == 'weekly':
                days = 7
                if 'day_of_week' in config:
                    # Calculate days until target day
                    target_day = self._day_name_to_number(config['day_of_week'])
                    current_day = from_date.weekday()
                    days = (target_day - current_day) % 7
                    if days == 0:
                        days = 7
                return from_date + timedelta(days=days)

            elif pattern == 'monthly':
                # Add one month
                month = from_date.month + 1
                year = from_date.year
                if month > 12:
                    month = 1
                    year += 1

                # Handle day of month
                day = config.get('day_of_month', from_date.day)
                try:
                    return datetime(year, month, day, from_date.hour, from_date.minute)
                except ValueError:
                    # Handle invalid dates (e.g., Feb 31)
                    return datetime(year, month, 1, from_date.hour, from_date.minute)

            else:
                # Default to 1 day
                return from_date + timedelta(days=1)

        except Exception as e:
            logger.error(f"Failed to calculate next run: {str(e)}")
            return from_date + timedelta(days=1)

    def _day_name_to_number(self, day_name: str) -> int:
        """Convert day name to number (0=Monday, 6=Sunday)"""
        days = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2,
            'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
        }
        return days.get(day_name.lower(), 0)

    # ==================== Statistics ====================

    def get_schedule_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get scheduling statistics"""
        try:
            conditions = []
            params = {}

            if user_id:
                conditions.append("cs.user_id = :user_id")
                params['user_id'] = user_id

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = text(f"""
                SELECT
                    COUNT(*) as total_schedules,
                    COUNT(*) FILTER (WHERE cs.status = 'scheduled') as scheduled_count,
                    COUNT(*) FILTER (WHERE cs.status = 'published') as published_count,
                    COUNT(*) FILTER (WHERE cs.status = 'failed') as failed_count,
                    COUNT(*) FILTER (WHERE cs.status = 'cancelled') as cancelled_count,
                    COUNT(*) FILTER (WHERE cs.publish_at > NOW() AND cs.status = 'scheduled') as upcoming_count
                FROM content_schedules cs
                {where_clause}
            """)

            result = self.db.execute(query, params)
            row = result.fetchone()

            if row:
                return {
                    'total_schedules': row[0] or 0,
                    'scheduled_count': row[1] or 0,
                    'published_count': row[2] or 0,
                    'failed_count': row[3] or 0,
                    'cancelled_count': row[4] or 0,
                    'upcoming_count': row[5] or 0
                }

            return {}

        except Exception as e:
            logger.error(f"Failed to get schedule statistics: {str(e)}")
            return {}
