"""
Metrics Service
Handles real-time dashboard metrics calculation and retrieval
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
import json

from backend.utils import get_logger

logger = get_logger(__name__)


class MetricsService:
    """
    Service for real-time dashboard metrics

    Handles:
    - Dashboard metric calculations
    - Metric retrieval and updates
    - Trend analysis
    - Metric categories and summaries
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== Metric Update Methods ====================

    def update_all_metrics(self) -> Dict[str, Any]:
        """
        Update all dashboard metrics

        Calls the PostgreSQL function to recalculate all metrics

        Returns:
            Dict with success status and updated metric count
        """
        try:
            # Call PostgreSQL function to update all metrics
            query = text("SELECT update_dashboard_metrics()")
            self.db.execute(query)
            self.db.commit()

            # Get count of updated metrics
            count = self.get_metric_count()

            logger.info(f"Updated {count} dashboard metrics")

            return {
                "success": True,
                "metrics_updated": count,
                "updated_at": datetime.now().isoformat()
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update metrics: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def update_specific_metric(
        self,
        metric_key: str,
        metric_value: float,
        previous_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Update a specific metric value

        Args:
            metric_key: Unique metric identifier
            metric_value: New metric value
            previous_value: Previous value for trend calculation

        Returns:
            Dict with success status and updated metric
        """
        try:
            # Calculate change percentage and trend
            change_percentage = None
            trend = 'unknown'

            if previous_value is not None and previous_value > 0:
                change_percentage = ((metric_value - previous_value) / previous_value) * 100

                if metric_value > previous_value:
                    trend = 'up'
                elif metric_value < previous_value:
                    trend = 'down'
                else:
                    trend = 'stable'

            # Update metric
            query = text("""
                UPDATE dashboard_metrics
                SET
                    previous_value = COALESCE(:previous_value, metric_value),
                    metric_value = :metric_value,
                    change_percentage = :change_percentage,
                    trend = :trend,
                    last_calculated_at = NOW(),
                    updated_at = NOW()
                WHERE metric_key = :metric_key
                RETURNING id
            """)

            result = self.db.execute(query, {
                "metric_key": metric_key,
                "metric_value": metric_value,
                "previous_value": previous_value,
                "change_percentage": change_percentage,
                "trend": trend
            })

            self.db.commit()

            if result.rowcount == 0:
                return {
                    "success": False,
                    "error": f"Metric '{metric_key}' not found"
                }

            logger.debug(f"Updated metric: {metric_key} = {metric_value}")

            return {
                "success": True,
                "metric_key": metric_key,
                "metric_value": metric_value,
                "change_percentage": change_percentage,
                "trend": trend
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update metric {metric_key}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def create_custom_metric(
        self,
        metric_key: str,
        metric_name: str,
        metric_value: float,
        metric_category: str,
        metric_description: Optional[str] = None,
        metric_unit: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new custom metric

        Args:
            metric_key: Unique metric identifier
            metric_name: Display name
            metric_value: Initial value
            metric_category: Category (users, content, activity, system)
            metric_description: Optional description
            metric_unit: Optional unit (users, chapters, ms, etc.)
            metadata: Additional metadata

        Returns:
            Dict with success status and metric ID
        """
        try:
            metadata_json = json.dumps(metadata or {})

            query = text("""
                INSERT INTO dashboard_metrics (
                    metric_key, metric_name, metric_description,
                    metric_value, metric_unit, metric_category,
                    metadata, last_calculated_at, created_at, updated_at
                )
                VALUES (
                    :metric_key, :metric_name, :metric_description,
                    :metric_value, :metric_unit, :metric_category,
                    :metadata::jsonb, NOW(), NOW(), NOW()
                )
                RETURNING id
            """)

            result = self.db.execute(query, {
                "metric_key": metric_key,
                "metric_name": metric_name,
                "metric_description": metric_description,
                "metric_value": metric_value,
                "metric_unit": metric_unit,
                "metric_category": metric_category,
                "metadata": metadata_json
            })

            self.db.commit()

            metric_id = result.fetchone()[0]

            logger.info(f"Created custom metric: {metric_key}")

            return {
                "success": True,
                "metric_id": str(metric_id),
                "metric_key": metric_key
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create metric: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    # ==================== Metric Retrieval Methods ====================

    def get_metric(self, metric_key: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific metric by key

        Args:
            metric_key: Unique metric identifier

        Returns:
            Metric dictionary or None if not found
        """
        try:
            query = text("""
                SELECT
                    id, metric_key, metric_name, metric_description,
                    metric_value, metric_unit, metric_category,
                    previous_value, change_percentage, trend,
                    metadata, last_calculated_at, created_at, updated_at
                FROM dashboard_metrics
                WHERE metric_key = :metric_key
            """)

            result = self.db.execute(query, {"metric_key": metric_key})
            row = result.fetchone()

            if not row:
                return None

            return {
                "id": str(row[0]),
                "metric_key": row[1],
                "metric_name": row[2],
                "metric_description": row[3],
                "metric_value": float(row[4]) if row[4] is not None else 0,
                "metric_unit": row[5],
                "metric_category": row[6],
                "previous_value": float(row[7]) if row[7] is not None else None,
                "change_percentage": float(row[8]) if row[8] is not None else None,
                "trend": row[9],
                "metadata": row[10] if row[10] else {},
                "last_calculated_at": row[11].isoformat() if row[11] else None,
                "created_at": row[12].isoformat() if row[12] else None,
                "updated_at": row[13].isoformat() if row[13] else None
            }

        except Exception as e:
            logger.error(f"Failed to get metric {metric_key}: {str(e)}", exc_info=True)
            return None

    def get_all_metrics(
        self,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all dashboard metrics, optionally filtered by category

        Args:
            category: Optional category filter (users, content, activity, system)

        Returns:
            List of metric dictionaries
        """
        try:
            if category:
                query = text("""
                    SELECT
                        id, metric_key, metric_name, metric_description,
                        metric_value, metric_unit, metric_category,
                        previous_value, change_percentage, trend,
                        metadata, last_calculated_at, created_at, updated_at
                    FROM dashboard_metrics
                    WHERE metric_category = :category
                    ORDER BY metric_category, metric_key
                """)
                result = self.db.execute(query, {"category": category})
            else:
                query = text("""
                    SELECT
                        id, metric_key, metric_name, metric_description,
                        metric_value, metric_unit, metric_category,
                        previous_value, change_percentage, trend,
                        metadata, last_calculated_at, created_at, updated_at
                    FROM dashboard_metrics
                    ORDER BY metric_category, metric_key
                """)
                result = self.db.execute(query)

            metrics = []
            for row in result:
                metrics.append({
                    "id": str(row[0]),
                    "metric_key": row[1],
                    "metric_name": row[2],
                    "metric_description": row[3],
                    "metric_value": float(row[4]) if row[4] is not None else 0,
                    "metric_unit": row[5],
                    "metric_category": row[6],
                    "previous_value": float(row[7]) if row[7] is not None else None,
                    "change_percentage": float(row[8]) if row[8] is not None else None,
                    "trend": row[9],
                    "metadata": row[10] if row[10] else {},
                    "last_calculated_at": row[11].isoformat() if row[11] else None,
                    "created_at": row[12].isoformat() if row[12] else None,
                    "updated_at": row[13].isoformat() if row[13] else None
                })

            return metrics

        except Exception as e:
            logger.error(f"Failed to get metrics: {str(e)}", exc_info=True)
            return []

    def get_metrics_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all metrics grouped by category

        Returns:
            Dict with categories as keys and metric lists as values
        """
        try:
            metrics = self.get_all_metrics()

            # Group by category
            by_category = {}
            for metric in metrics:
                category = metric.get("metric_category", "other")
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(metric)

            return by_category

        except Exception as e:
            logger.error(f"Failed to group metrics by category: {str(e)}", exc_info=True)
            return {}

    def get_metric_count(self) -> int:
        """
        Get total count of dashboard metrics

        Returns:
            Metric count
        """
        try:
            query = text("SELECT COUNT(*) FROM dashboard_metrics")
            result = self.db.execute(query)
            count = result.fetchone()[0]
            return count

        except Exception as e:
            logger.error(f"Failed to get metric count: {str(e)}", exc_info=True)
            return 0

    # ==================== Dashboard Summary Methods ====================

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """
        Get complete dashboard summary with all key metrics

        Returns:
            Dict with dashboard summary data
        """
        try:
            # Get all metrics grouped by category
            by_category = self.get_metrics_by_category()

            # Calculate summary statistics
            total_metrics = sum(len(metrics) for metrics in by_category.values())

            # Get update timestamps
            query = text("""
                SELECT
                    MIN(last_calculated_at) as oldest_update,
                    MAX(last_calculated_at) as newest_update
                FROM dashboard_metrics
            """)
            result = self.db.execute(query)
            row = result.fetchone()

            return {
                "success": True,
                "summary": {
                    "total_metrics": total_metrics,
                    "categories": list(by_category.keys()),
                    "category_counts": {cat: len(metrics) for cat, metrics in by_category.items()},
                    "oldest_update": row[0].isoformat() if row[0] else None,
                    "newest_update": row[1].isoformat() if row[1] else None
                },
                "metrics_by_category": by_category,
                "generated_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get dashboard summary: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def get_key_metrics(self) -> Dict[str, Any]:
        """
        Get key metrics for quick dashboard overview

        Returns:
            Dict with key metrics (total users, chapters, searches, etc.)
        """
        try:
            # Define key metric keys to retrieve
            key_metric_keys = [
                'total_users',
                'total_chapters',
                'total_pdfs',
                'active_users_24h',
                'total_searches_7d',
                'total_exports_30d'
            ]

            metrics = {}
            for key in key_metric_keys:
                metric = self.get_metric(key)
                if metric:
                    metrics[key] = metric

            return {
                "success": True,
                "key_metrics": metrics,
                "retrieved_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get key metrics: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    # ==================== Trend Analysis Methods ====================

    def calculate_metric_trends(
        self,
        metric_key: str,
        lookback_days: int = 7
    ) -> Dict[str, Any]:
        """
        Calculate trends for a specific metric over time

        Args:
            metric_key: Metric to analyze
            lookback_days: Number of days to look back

        Returns:
            Dict with trend analysis
        """
        try:
            # Get current metric value
            current = self.get_metric(metric_key)
            if not current:
                return {
                    "success": False,
                    "error": f"Metric '{metric_key}' not found"
                }

            # For now, return current trend data
            # In the future, could query historical data from aggregates

            return {
                "success": True,
                "metric_key": metric_key,
                "current_value": current["metric_value"],
                "previous_value": current["previous_value"],
                "change_percentage": current["change_percentage"],
                "trend": current["trend"],
                "lookback_days": lookback_days,
                "analyzed_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to calculate trends for {metric_key}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def get_trending_metrics(self, limit: int = 5) -> Dict[str, Any]:
        """
        Get metrics with the biggest changes (up or down)

        Args:
            limit: Number of trending metrics to return

        Returns:
            Dict with top trending up and down metrics
        """
        try:
            # Get metrics with biggest positive changes
            query_up = text("""
                SELECT
                    metric_key, metric_name, metric_value,
                    previous_value, change_percentage, trend
                FROM dashboard_metrics
                WHERE change_percentage IS NOT NULL
                    AND trend = 'up'
                ORDER BY change_percentage DESC
                LIMIT :limit
            """)

            result_up = self.db.execute(query_up, {"limit": limit})

            trending_up = []
            for row in result_up:
                trending_up.append({
                    "metric_key": row[0],
                    "metric_name": row[1],
                    "metric_value": float(row[2]) if row[2] is not None else 0,
                    "previous_value": float(row[3]) if row[3] is not None else None,
                    "change_percentage": float(row[4]) if row[4] is not None else None,
                    "trend": row[5]
                })

            # Get metrics with biggest negative changes
            query_down = text("""
                SELECT
                    metric_key, metric_name, metric_value,
                    previous_value, change_percentage, trend
                FROM dashboard_metrics
                WHERE change_percentage IS NOT NULL
                    AND trend = 'down'
                ORDER BY change_percentage ASC
                LIMIT :limit
            """)

            result_down = self.db.execute(query_down, {"limit": limit})

            trending_down = []
            for row in result_down:
                trending_down.append({
                    "metric_key": row[0],
                    "metric_name": row[1],
                    "metric_value": float(row[2]) if row[2] is not None else 0,
                    "previous_value": float(row[3]) if row[3] is not None else None,
                    "change_percentage": float(row[4]) if row[4] is not None else None,
                    "trend": row[5]
                })

            return {
                "success": True,
                "trending_up": trending_up,
                "trending_down": trending_down,
                "generated_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get trending metrics: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    # ==================== Utility Methods ====================

    def delete_metric(self, metric_key: str) -> Dict[str, Any]:
        """
        Delete a custom metric

        Args:
            metric_key: Metric to delete

        Returns:
            Dict with success status
        """
        try:
            query = text("DELETE FROM dashboard_metrics WHERE metric_key = :metric_key")
            result = self.db.execute(query, {"metric_key": metric_key})
            self.db.commit()

            if result.rowcount == 0:
                return {
                    "success": False,
                    "error": f"Metric '{metric_key}' not found"
                }

            logger.info(f"Deleted metric: {metric_key}")

            return {
                "success": True,
                "metric_key": metric_key
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete metric {metric_key}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def reset_all_metrics(self) -> Dict[str, Any]:
        """
        Reset all metrics to zero (useful for testing)

        Returns:
            Dict with success status
        """
        try:
            query = text("""
                UPDATE dashboard_metrics
                SET
                    metric_value = 0,
                    previous_value = NULL,
                    change_percentage = NULL,
                    trend = 'unknown',
                    updated_at = NOW()
            """)

            result = self.db.execute(query)
            self.db.commit()

            logger.warning(f"Reset {result.rowcount} metrics to zero")

            return {
                "success": True,
                "metrics_reset": result.rowcount
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to reset metrics: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
