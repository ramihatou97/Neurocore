"""
AI Provider Metrics Service
Tracks and aggregates AI provider performance, quality, and costs
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, desc, Integer
from sqlalchemy.orm import Session

from backend.database.models.ai_provider_metric import AIProviderMetric
from backend.database.connection import get_db
from backend.utils import get_logger

logger = get_logger(__name__)


class ProviderMetricsService:
    """
    Service for tracking and analyzing AI provider performance

    Features:
    - Record every AI provider call with performance metrics
    - Aggregate metrics by provider × task type
    - Calculate quality distributions
    - Measure cost efficiency (quality per dollar)
    - Track success rates and error patterns
    - Compare provider performance side-by-side
    """

    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or next(get_db())

    def record_metric(
        self,
        provider: str,
        model: str,
        task_type: str,
        success: bool,
        chapter_id: Optional[str] = None,
        image_id: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        quality_score: Optional[float] = None,
        confidence_score: Optional[float] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        cost_usd: Optional[float] = None,
        json_parse_success: Optional[bool] = None,
        output_validated: Optional[bool] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        was_fallback: bool = False,
        original_provider: Optional[str] = None,
        fallback_reason: Optional[str] = None
    ) -> str:
        """
        Record an AI provider metric

        Args:
            provider: Provider name (claude, gpt4o, gemini)
            model: Model version
            task_type: Task performed
            success: Whether request succeeded
            ... (see AIProviderMetric model for full list)

        Returns:
            Metric ID
        """
        try:
            metric = AIProviderMetric(
                provider=provider,
                model=model,
                task_type=task_type,
                chapter_id=chapter_id,
                image_id=image_id,
                success=success,
                response_time_ms=response_time_ms,
                quality_score=quality_score,
                confidence_score=confidence_score,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
                json_parse_success=json_parse_success,
                output_validated=output_validated,
                error_type=error_type,
                error_message=error_message,
                was_fallback=was_fallback,
                original_provider=original_provider,
                fallback_reason=fallback_reason
            )

            self.db.add(metric)
            self.db.commit()

            logger.info(
                f"Recorded {provider} metric: task={task_type}, "
                f"success={success}, quality={quality_score}, cost=${cost_usd}"
            )

            return str(metric.id)

        except Exception as e:
            logger.error(f"Failed to record provider metric: {str(e)}", exc_info=True)
            self.db.rollback()
            raise

    def get_provider_comparison(
        self,
        task_type: Optional[str] = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get side-by-side provider comparison

        Args:
            task_type: Filter by task type (None for all tasks)
            days: Number of days to look back

        Returns:
            List of provider statistics
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(
            AIProviderMetric.provider,
            AIProviderMetric.task_type,
            func.count().label('total_requests'),
            func.sum(func.cast(AIProviderMetric.success, Integer)).label('successful_requests'),
            func.avg(AIProviderMetric.quality_score).label('avg_quality_score'),
            func.avg(AIProviderMetric.confidence_score).label('avg_confidence_score'),
            func.avg(AIProviderMetric.response_time_ms).label('avg_response_time_ms'),
            func.avg(AIProviderMetric.cost_usd).label('avg_cost_usd'),
            func.sum(AIProviderMetric.cost_usd).label('total_cost_usd'),
            func.sum(func.cast(AIProviderMetric.json_parse_success, Integer)).label('json_parse_successes')
        ).filter(
            AIProviderMetric.request_timestamp >= cutoff
        )

        if task_type:
            query = query.filter(AIProviderMetric.task_type == task_type)

        results = query.group_by(
            AIProviderMetric.provider,
            AIProviderMetric.task_type
        ).all()

        comparison = []
        for row in results:
            total = row.total_requests or 0
            successful = row.successful_requests or 0
            json_successes = row.json_parse_successes or 0

            comparison.append({
                'provider': row.provider,
                'task_type': row.task_type,
                'total_requests': total,
                'successful_requests': successful,
                'success_rate_pct': round((successful / total * 100) if total > 0 else 0, 2),
                'avg_quality_score': round(float(row.avg_quality_score), 3) if row.avg_quality_score else None,
                'avg_confidence_score': round(float(row.avg_confidence_score), 3) if row.avg_confidence_score else None,
                'avg_response_time_ms': round(float(row.avg_response_time_ms), 0) if row.avg_response_time_ms else None,
                'avg_cost_usd': round(float(row.avg_cost_usd), 6) if row.avg_cost_usd else None,
                'total_cost_usd': round(float(row.total_cost_usd), 4) if row.total_cost_usd else None,
                'json_parse_success_rate_pct': round((json_successes / total * 100) if total > 0 else 0, 2)
            })

        return comparison

    def get_quality_distribution(
        self,
        provider: Optional[str] = None,
        task_type: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get quality score distribution for providers

        Args:
            provider: Filter by provider (None for all)
            task_type: Filter by task type (None for all)
            days: Number of days to look back

        Returns:
            Quality score statistics and distribution
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(AIProviderMetric).filter(
            and_(
                AIProviderMetric.request_timestamp >= cutoff,
                AIProviderMetric.quality_score.isnot(None),
                AIProviderMetric.success == True
            )
        )

        if provider:
            query = query.filter(AIProviderMetric.provider == provider)
        if task_type:
            query = query.filter(AIProviderMetric.task_type == task_type)

        metrics = query.all()

        if not metrics:
            return {
                'provider': provider,
                'task_type': task_type,
                'count': 0,
                'distribution': {}
            }

        scores = [float(m.quality_score) for m in metrics]

        # Calculate distribution buckets
        distribution = {
            'excellent': sum(1 for s in scores if s >= 0.9),   # 90-100%
            'good': sum(1 for s in scores if 0.7 <= s < 0.9),  # 70-90%
            'acceptable': sum(1 for s in scores if 0.5 <= s < 0.7),  # 50-70%
            'poor': sum(1 for s in scores if s < 0.5)          # < 50%
        }

        return {
            'provider': provider,
            'task_type': task_type,
            'count': len(scores),
            'mean': round(sum(scores) / len(scores), 3),
            'min': round(min(scores), 3),
            'max': round(max(scores), 3),
            'median': round(sorted(scores)[len(scores) // 2], 3),
            'distribution': distribution,
            'distribution_pct': {
                k: round(v / len(scores) * 100, 1)
                for k, v in distribution.items()
            }
        }

    def get_cost_efficiency(
        self,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Calculate cost efficiency (quality per dollar) for each provider × task

        Args:
            days: Number of days to look back

        Returns:
            List of cost efficiency metrics
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        results = self.db.query(
            AIProviderMetric.provider,
            AIProviderMetric.task_type,
            func.count().label('total_requests'),
            func.avg(AIProviderMetric.quality_score).label('avg_quality'),
            func.avg(AIProviderMetric.cost_usd).label('avg_cost')
        ).filter(
            and_(
                AIProviderMetric.request_timestamp >= cutoff,
                AIProviderMetric.success == True,
                AIProviderMetric.quality_score.isnot(None),
                AIProviderMetric.cost_usd > 0
            )
        ).group_by(
            AIProviderMetric.provider,
            AIProviderMetric.task_type
        ).all()

        efficiency = []
        for row in results:
            avg_quality = float(row.avg_quality) if row.avg_quality else 0
            avg_cost = float(row.avg_cost) if row.avg_cost else 0

            quality_per_dollar = (avg_quality / avg_cost) if avg_cost > 0 else 0

            efficiency.append({
                'provider': row.provider,
                'task_type': row.task_type,
                'total_requests': row.total_requests,
                'avg_quality': round(avg_quality, 3),
                'avg_cost_usd': round(avg_cost, 6),
                'quality_per_dollar': round(quality_per_dollar, 2)
            })

        # Sort by quality per dollar (descending)
        efficiency.sort(key=lambda x: x['quality_per_dollar'], reverse=True)

        return efficiency

    def get_success_rates(
        self,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get success/failure rates for each provider

        Args:
            days: Number of days to look back

        Returns:
            List of success rate statistics
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        results = self.db.query(
            AIProviderMetric.provider,
            func.count().label('total_requests'),
            func.sum(func.cast(AIProviderMetric.success, Integer)).label('successful_requests'),
            func.count(AIProviderMetric.error_type).label('total_errors')
        ).filter(
            AIProviderMetric.request_timestamp >= cutoff
        ).group_by(
            AIProviderMetric.provider
        ).all()

        rates = []
        for row in results:
            total = row.total_requests or 0
            successful = row.successful_requests or 0
            errors = row.total_errors or 0

            rates.append({
                'provider': row.provider,
                'total_requests': total,
                'successful_requests': successful,
                'failed_requests': total - successful,
                'success_rate_pct': round((successful / total * 100) if total > 0 else 0, 2),
                'failure_rate_pct': round(((total - successful) / total * 100) if total > 0 else 0, 2),
                'total_errors': errors
            })

        return rates

    def get_error_breakdown(
        self,
        provider: Optional[str] = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get error type breakdown

        Args:
            provider: Filter by provider (None for all)
            days: Number of days to look back

        Returns:
            List of error statistics by type
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(
            AIProviderMetric.provider,
            AIProviderMetric.error_type,
            func.count().label('error_count')
        ).filter(
            and_(
                AIProviderMetric.request_timestamp >= cutoff,
                AIProviderMetric.error_type.isnot(None)
            )
        )

        if provider:
            query = query.filter(AIProviderMetric.provider == provider)

        results = query.group_by(
            AIProviderMetric.provider,
            AIProviderMetric.error_type
        ).order_by(
            desc('error_count')
        ).all()

        return [
            {
                'provider': row.provider,
                'error_type': row.error_type,
                'count': row.error_count
            }
            for row in results
        ]

    def get_fallback_statistics(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get statistics on provider fallback usage

        Args:
            days: Number of days to look back

        Returns:
            Fallback usage statistics
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        total_requests = self.db.query(func.count(AIProviderMetric.id)).filter(
            AIProviderMetric.request_timestamp >= cutoff
        ).scalar()

        fallback_requests = self.db.query(func.count(AIProviderMetric.id)).filter(
            and_(
                AIProviderMetric.request_timestamp >= cutoff,
                AIProviderMetric.was_fallback == True
            )
        ).scalar()

        # Get fallback breakdown by original provider
        fallback_breakdown = self.db.query(
            AIProviderMetric.original_provider,
            AIProviderMetric.provider.label('fallback_provider'),
            AIProviderMetric.fallback_reason,
            func.count().label('count')
        ).filter(
            and_(
                AIProviderMetric.request_timestamp >= cutoff,
                AIProviderMetric.was_fallback == True
            )
        ).group_by(
            AIProviderMetric.original_provider,
            AIProviderMetric.provider,
            AIProviderMetric.fallback_reason
        ).all()

        return {
            'total_requests': total_requests or 0,
            'fallback_requests': fallback_requests or 0,
            'fallback_rate_pct': round((fallback_requests / total_requests * 100) if total_requests > 0 else 0, 2),
            'fallback_breakdown': [
                {
                    'original_provider': row.original_provider,
                    'fallback_provider': row.fallback_provider,
                    'reason': row.fallback_reason,
                    'count': row.count
                }
                for row in fallback_breakdown
            ]
        }

    def get_provider_performance(
        self,
        provider: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive performance report for a single provider

        Args:
            provider: Provider name
            days: Number of days to look back

        Returns:
            Comprehensive performance metrics
        """
        comparison = self.get_provider_comparison(task_type=None, days=days)
        provider_stats = [stat for stat in comparison if stat['provider'] == provider]

        quality_dist = self.get_quality_distribution(provider=provider, days=days)
        error_breakdown = self.get_error_breakdown(provider=provider, days=days)

        return {
            'provider': provider,
            'period_days': days,
            'task_breakdown': provider_stats,
            'quality_distribution': quality_dist,
            'error_breakdown': error_breakdown,
            'generated_at': datetime.utcnow().isoformat()
        }


# Global instance
provider_metrics_service = ProviderMetricsService()
