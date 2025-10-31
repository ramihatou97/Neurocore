"""
Analytics API Routes
Endpoints for analytics, metrics, and dashboard data
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, date, timedelta
from pydantic import BaseModel, Field

from backend.database.connection import get_db
from backend.database.models import User
from backend.services.analytics_service import AnalyticsService
from backend.services.metrics_service import MetricsService
from backend.services.cache_service import cache_service  # Phase 2: Cache analytics
from backend.utils.dependencies import get_current_user
from backend.utils import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ==================== Request/Response Models ====================

class EventTrackRequest(BaseModel):
    """Track analytics event request"""
    event_type: str = Field(..., description="Event type (search, export, chapter_create, etc.)")
    event_category: str = Field(..., description="Event category (user, content, system, search, export)")
    resource_type: Optional[str] = Field(None, description="Resource type (chapter, pdf, etc.)")
    resource_id: Optional[str] = Field(None, description="Resource ID")
    metadata: Optional[dict] = Field(default={}, description="Additional event data")
    duration_ms: Optional[int] = Field(None, description="Operation duration in milliseconds")
    success: bool = Field(default=True, description="Operation success status")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class CustomMetricRequest(BaseModel):
    """Create custom metric request"""
    metric_key: str = Field(..., description="Unique metric identifier")
    metric_name: str = Field(..., description="Display name")
    metric_value: float = Field(..., description="Initial value")
    metric_category: str = Field(..., description="Category (users, content, activity, system)")
    metric_description: Optional[str] = Field(None, description="Description")
    metric_unit: Optional[str] = Field(None, description="Unit (users, chapters, ms, etc.)")
    metadata: Optional[dict] = Field(default={}, description="Additional metadata")


# ==================== Helper Functions ====================

def check_admin_access(current_user: User):
    """Check if user is admin (for analytics access)"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required for analytics"
        )


# ==================== Dashboard Overview ====================

@router.get("/dashboard")
async def get_dashboard_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get complete dashboard overview

    Returns all key metrics, trends, and summary data for admin dashboard

    **Admin only**
    """
    check_admin_access(current_user)

    try:
        metrics_service = MetricsService(db)
        analytics_service = AnalyticsService(db)

        # Update metrics before returning
        metrics_service.update_all_metrics()

        # Get dashboard summary
        summary = metrics_service.get_dashboard_summary()

        # Get key metrics
        key_metrics = metrics_service.get_key_metrics()

        # Get trending metrics
        trending = metrics_service.get_trending_metrics(limit=5)

        # Get system health
        health = analytics_service.get_system_health_metrics()

        return {
            "success": True,
            "dashboard": {
                "summary": summary,
                "key_metrics": key_metrics,
                "trending": trending,
                "system_health": health
            },
            "generated_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dashboard overview: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")


@router.get("/dashboard/key-metrics")
async def get_key_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get key dashboard metrics only

    Quick endpoint for essential metrics without full dashboard

    **Admin only**
    """
    check_admin_access(current_user)

    try:
        metrics_service = MetricsService(db)
        return metrics_service.get_key_metrics()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get key metrics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get key metrics: {str(e)}")


# ==================== Metrics Endpoints ====================

@router.get("/metrics")
async def get_all_metrics(
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all dashboard metrics

    Optionally filter by category (users, content, activity, system)

    **Admin only**
    """
    check_admin_access(current_user)

    try:
        metrics_service = MetricsService(db)
        metrics = metrics_service.get_all_metrics(category=category)

        return {
            "success": True,
            "metrics": metrics,
            "count": len(metrics),
            "category": category
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get metrics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.get("/metrics/{metric_key}")
async def get_metric(
    metric_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get specific metric by key

    **Admin only**
    """
    check_admin_access(current_user)

    try:
        metrics_service = MetricsService(db)
        metric = metrics_service.get_metric(metric_key)

        if not metric:
            raise HTTPException(status_code=404, detail=f"Metric '{metric_key}' not found")

        return metric

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get metric: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get metric: {str(e)}")


@router.post("/metrics")
async def create_custom_metric(
    request: CustomMetricRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new custom metric

    **Admin only**
    """
    check_admin_access(current_user)

    try:
        metrics_service = MetricsService(db)

        result = metrics_service.create_custom_metric(
            metric_key=request.metric_key,
            metric_name=request.metric_name,
            metric_value=request.metric_value,
            metric_category=request.metric_category,
            metric_description=request.metric_description,
            metric_unit=request.metric_unit,
            metadata=request.metadata
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create metric: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create metric: {str(e)}")


@router.post("/metrics/update")
async def update_all_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger update of all dashboard metrics

    **Admin only**
    """
    check_admin_access(current_user)

    try:
        metrics_service = MetricsService(db)
        return metrics_service.update_all_metrics()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update metrics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update metrics: {str(e)}")


@router.get("/metrics/trending/top")
async def get_trending_metrics(
    limit: int = Query(5, description="Number of trending metrics to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get top trending metrics (up and down)

    **Admin only**
    """
    check_admin_access(current_user)

    try:
        metrics_service = MetricsService(db)
        return metrics_service.get_trending_metrics(limit=limit)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trending metrics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get trending metrics: {str(e)}")


# ==================== Event Tracking Endpoints ====================

@router.post("/events/track")
async def track_event(
    request: EventTrackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Track an analytics event

    Any authenticated user can track events
    """
    try:
        analytics_service = AnalyticsService(db)

        result = analytics_service.track_event(
            event_type=request.event_type,
            event_category=request.event_category,
            user_id=str(current_user.id),
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            metadata=request.metadata,
            duration_ms=request.duration_ms,
            success=request.success,
            error_message=request.error_message
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to track event: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to track event: {str(e)}")


@router.get("/events")
async def get_events(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    event_category: Optional[str] = Query(None, description="Filter by category"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    start_date: Optional[datetime] = Query(None, description="Start of time range"),
    end_date: Optional[datetime] = Query(None, description="End of time range"),
    success: Optional[bool] = Query(None, description="Filter by success status"),
    limit: int = Query(100, description="Maximum results"),
    offset: int = Query(0, description="Results offset"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get analytics events with filters

    **Admin only**
    """
    check_admin_access(current_user)

    try:
        analytics_service = AnalyticsService(db)

        events = analytics_service.get_events(
            event_type=event_type,
            event_category=event_category,
            resource_type=resource_type,
            start_date=start_date,
            end_date=end_date,
            success=success,
            limit=limit,
            offset=offset
        )

        return {
            "success": True,
            "events": events,
            "count": len(events),
            "limit": limit,
            "offset": offset
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get events: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get events: {str(e)}")


@router.get("/events/timeline")
async def get_event_timeline(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    event_category: Optional[str] = Query(None, description="Filter by category"),
    start_date: Optional[datetime] = Query(None, description="Start of time range"),
    end_date: Optional[datetime] = Query(None, description="End of time range"),
    interval: str = Query("1 day", description="Time bucket interval (1 hour, 1 day, 1 week)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get event timeline (events over time)

    **Admin only**
    """
    check_admin_access(current_user)

    try:
        analytics_service = AnalyticsService(db)

        timeline = analytics_service.get_event_timeline(
            event_type=event_type,
            event_category=event_category,
            start_date=start_date,
            end_date=end_date,
            interval=interval
        )

        return {
            "success": True,
            "timeline": timeline,
            "interval": interval
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get event timeline: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get timeline: {str(e)}")


# ==================== User Analytics ====================

@router.get("/users")
async def get_user_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user analytics overview

    **Admin only**
    """
    check_admin_access(current_user)

    try:
        analytics_service = AnalyticsService(db)
        metrics_service = MetricsService(db)

        # Get user metrics
        total_users = metrics_service.get_metric('total_users')
        active_users = metrics_service.get_metric('active_users_24h')

        # Get user activity over time (last 30 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        timeline = analytics_service.get_event_timeline(
            event_category='user',
            start_date=start_date,
            end_date=end_date,
            interval='1 day'
        )

        return {
            "success": True,
            "user_analytics": {
                "total_users": total_users,
                "active_users_24h": active_users,
                "activity_timeline": timeline
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user analytics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get user analytics: {str(e)}")


@router.get("/users/{user_id}/activity")
async def get_user_activity(
    user_id: str,
    start_date: Optional[datetime] = Query(None, description="Start of time range"),
    end_date: Optional[datetime] = Query(None, description="End of time range"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get activity summary for a specific user

    **Admin only or own user**
    """
    # Allow user to view their own activity
    if str(current_user.id) != user_id:
        check_admin_access(current_user)

    try:
        analytics_service = AnalyticsService(db)

        summary = analytics_service.get_user_activity_summary(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )

        return {
            "success": True,
            "user_activity": summary
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user activity: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get user activity: {str(e)}")


# ==================== Content Analytics ====================

@router.get("/chapters")
async def get_chapter_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get chapter analytics overview

    **Admin only**
    """
    check_admin_access(current_user)

    try:
        metrics_service = MetricsService(db)
        analytics_service = AnalyticsService(db)

        # Get chapter metrics
        total_chapters = metrics_service.get_metric('total_chapters')

        # Get chapter creation timeline (last 30 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        timeline = analytics_service.get_event_timeline(
            event_type='chapter_create',
            start_date=start_date,
            end_date=end_date,
            interval='1 day'
        )

        # Get popular chapters
        popular = analytics_service.get_popular_content(
            resource_type='chapter',
            limit=10
        )

        return {
            "success": True,
            "chapter_analytics": {
                "total_chapters": total_chapters,
                "creation_timeline": timeline,
                "popular_chapters": popular
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chapter analytics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get chapter analytics: {str(e)}")


@router.get("/content/popular")
async def get_popular_content(
    resource_type: Optional[str] = Query(None, description="Filter by type (chapter, pdf)"),
    limit: int = Query(10, description="Number of results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get most popular content by views

    **Admin only**
    """
    check_admin_access(current_user)

    try:
        analytics_service = AnalyticsService(db)

        popular = analytics_service.get_popular_content(
            resource_type=resource_type,
            limit=limit
        )

        return {
            "success": True,
            "popular_content": popular,
            "count": len(popular)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get popular content: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get popular content: {str(e)}")


# ==================== Search Analytics ====================

@router.get("/search")
async def get_search_analytics(
    start_date: Optional[datetime] = Query(None, description="Start of time range"),
    end_date: Optional[datetime] = Query(None, description="End of time range"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get search analytics overview

    **Admin only**
    """
    check_admin_access(current_user)

    try:
        analytics_service = AnalyticsService(db)
        metrics_service = MetricsService(db)

        # Get search metrics
        total_searches = metrics_service.get_metric('total_searches_7d')

        # Default to last 7 days
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=7)

        # Get search count
        search_count = analytics_service.get_event_count(
            event_type='search',
            start_date=start_date,
            end_date=end_date
        )

        # Get search timeline
        timeline = analytics_service.get_event_timeline(
            event_type='search',
            start_date=start_date,
            end_date=end_date,
            interval='1 day'
        )

        return {
            "success": True,
            "search_analytics": {
                "total_searches_7d": total_searches,
                "search_count": search_count,
                "timeline": timeline,
                "time_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get search analytics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get search analytics: {str(e)}")


# ==================== Export Analytics ====================

@router.get("/exports")
async def get_export_analytics(
    start_date: Optional[datetime] = Query(None, description="Start of time range"),
    end_date: Optional[datetime] = Query(None, description="End of time range"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get export analytics overview

    **Admin only**
    """
    check_admin_access(current_user)

    try:
        analytics_service = AnalyticsService(db)
        metrics_service = MetricsService(db)

        # Get export metrics
        total_exports = metrics_service.get_metric('total_exports_30d')

        # Default to last 30 days
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Get export count
        export_count = analytics_service.get_event_count(
            event_type='export',
            start_date=start_date,
            end_date=end_date
        )

        # Get export timeline
        timeline = analytics_service.get_event_timeline(
            event_type='export',
            start_date=start_date,
            end_date=end_date,
            interval='1 day'
        )

        return {
            "success": True,
            "export_analytics": {
                "total_exports_30d": total_exports,
                "export_count": export_count,
                "timeline": timeline,
                "time_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get export analytics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get export analytics: {str(e)}")


# ==================== System Health ====================

@router.get("/system/health")
async def get_system_health(
    start_date: Optional[datetime] = Query(None, description="Start of time range"),
    end_date: Optional[datetime] = Query(None, description="End of time range"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get system health and performance metrics

    **Admin only**
    """
    check_admin_access(current_user)

    try:
        analytics_service = AnalyticsService(db)

        health = analytics_service.get_system_health_metrics(
            start_date=start_date,
            end_date=end_date
        )

        return {
            "success": True,
            "system_health": health
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get system health: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get system health: {str(e)}")


# ==================== Aggregates ====================

@router.post("/aggregates/calculate")
async def calculate_aggregates(
    target_date: date = Query(..., description="Date to calculate aggregates for"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger aggregate calculation for a specific date

    **Admin only**
    """
    check_admin_access(current_user)

    try:
        analytics_service = AnalyticsService(db)
        return analytics_service.calculate_aggregates_for_date(target_date)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to calculate aggregates: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to calculate aggregates: {str(e)}")


@router.get("/aggregates/daily")
async def get_daily_aggregates(
    metric_type: str = Query(..., description="Metric type (event_count, avg_duration, unique_users)"),
    metric_category: Optional[str] = Query(None, description="Metric category filter"),
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    limit: int = Query(30, description="Maximum results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get daily aggregated metrics

    **Admin only**
    """
    check_admin_access(current_user)

    try:
        analytics_service = AnalyticsService(db)

        aggregates = analytics_service.get_daily_aggregates(
            metric_type=metric_type,
            metric_category=metric_category,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

        return {
            "success": True,
            "aggregates": aggregates,
            "count": len(aggregates)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get daily aggregates: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get aggregates: {str(e)}")


# ==================== Cache Analytics (Phase 2) ====================

@router.get("/cache/stats")
async def get_cache_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Get cache statistics

    Phase 2: Basic cache statistics including Redis metrics

    **Admin only**
    """
    check_admin_access(current_user)

    try:
        stats = cache_service.get_cache_stats()

        return {
            "success": True,
            "cache_stats": stats,
            "retrieved_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cache stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")


@router.get("/cache/analytics")
async def get_cache_analytics(
    search_type: Optional[str] = Query(None, description="Filter by search type (pubmed, search)"),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed cache performance analytics

    Phase 2: Comprehensive cache analytics including hit rates, response times, and speedup factors

    **Admin only**
    """
    check_admin_access(current_user)

    try:
        analytics = cache_service.get_analytics(search_type=search_type)

        return {
            "success": True,
            "cache_analytics": analytics,
            "retrieved_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cache analytics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get cache analytics: {str(e)}")


@router.get("/cache/pubmed")
async def get_pubmed_cache_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Get PubMed-specific cache statistics

    Phase 2: Dedicated PubMed cache performance tracking with hit rates and speedup metrics

    **Admin only**
    """
    check_admin_access(current_user)

    try:
        stats = cache_service.get_pubmed_cache_stats()

        return {
            "success": True,
            "pubmed_cache_stats": stats,
            "retrieved_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get PubMed cache stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get PubMed cache stats: {str(e)}")


@router.post("/cache/analytics/reset")
async def reset_cache_analytics(
    current_user: User = Depends(get_current_user)
):
    """
    Reset cache analytics counters

    Phase 2: Reset in-memory analytics tracking

    **Admin only**
    """
    check_admin_access(current_user)

    try:
        cache_service.reset_analytics()

        return {
            "success": True,
            "message": "Cache analytics reset successfully",
            "reset_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset cache analytics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reset cache analytics: {str(e)}")


# ==================== Fact-Checking Analytics (Phase 3) ====================

@router.get("/fact-checking/overview")
async def get_fact_checking_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get fact-checking overview across all chapters

    Returns aggregate metrics:
    - Overall accuracy across all chapters
    - Total claims verified
    - Critical issues count
    - Accuracy distribution
    - Trending accuracy over time

    Phase 3: GPT-4o powered medical fact-checking analytics

    **Admin only**
    """
    check_admin_access(current_user)

    try:
        from backend.database.models import Chapter

        # Get all fact-checked chapters
        chapters = db.query(Chapter).filter(
            Chapter.fact_checked == True,
            Chapter.stage_10_fact_check.isnot(None)
        ).all()

        if not chapters:
            return {
                "success": True,
                "message": "No fact-checked chapters found",
                "overview": {
                    "total_chapters_checked": 0,
                    "overall_accuracy": 0.0,
                    "total_claims": 0,
                    "verified_claims": 0,
                    "critical_issues_total": 0
                }
            }

        # Aggregate metrics
        total_chapters = len(chapters)
        total_claims = 0
        total_verified = 0
        total_critical_issues = 0
        total_high_severity = 0
        total_cost = 0.0
        accuracy_scores = []
        pass_count = 0

        # Accuracy distribution buckets
        accuracy_distribution = {
            "excellent": 0,  # >= 95%
            "good": 0,       # 90-95%
            "acceptable": 0,  # 80-90%
            "poor": 0        # < 80%
        }

        # Claim category distribution
        category_stats = {}

        for chapter in chapters:
            fact_check_data = chapter.stage_10_fact_check or {}

            # Skip chapters with errors or no data
            if fact_check_data.get("status") == "error":
                continue

            accuracy = fact_check_data.get("overall_accuracy", 0.0)
            claims = fact_check_data.get("total_claims", 0)
            verified = fact_check_data.get("verified_claims", 0)
            critical = fact_check_data.get("critical_issues_count", 0)
            high_sev = fact_check_data.get("high_severity_claims", 0)
            cost = fact_check_data.get("ai_cost_usd", 0.0)
            passed = fact_check_data.get("passed", False)

            total_claims += claims
            total_verified += verified
            total_critical_issues += critical
            total_high_severity += high_sev
            total_cost += cost
            accuracy_scores.append(accuracy)

            if passed:
                pass_count += 1

            # Accuracy distribution
            if accuracy >= 0.95:
                accuracy_distribution["excellent"] += 1
            elif accuracy >= 0.90:
                accuracy_distribution["good"] += 1
            elif accuracy >= 0.80:
                accuracy_distribution["acceptable"] += 1
            else:
                accuracy_distribution["poor"] += 1

            # Category stats
            by_category = fact_check_data.get("by_category", {})
            for category, stats in by_category.items():
                if category not in category_stats:
                    category_stats[category] = {"verified": 0, "unverified": 0}
                category_stats[category]["verified"] += stats.get("verified", 0)
                category_stats[category]["unverified"] += stats.get("unverified", 0)

        # Calculate overall accuracy
        overall_accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0.0

        # Pass rate
        pass_rate = (pass_count / total_chapters) if total_chapters > 0 else 0.0

        return {
            "success": True,
            "overview": {
                "total_chapters_checked": total_chapters,
                "chapters_passed": pass_count,
                "chapters_failed": total_chapters - pass_count,
                "pass_rate": pass_rate,
                "overall_accuracy": overall_accuracy,
                "overall_accuracy_percentage": overall_accuracy * 100,
                "total_claims": total_claims,
                "verified_claims": total_verified,
                "unverified_claims": total_claims - total_verified,
                "verification_rate": (total_verified / total_claims) if total_claims > 0 else 0.0,
                "critical_issues_total": total_critical_issues,
                "high_severity_claims_total": total_high_severity,
                "total_cost_usd": total_cost,
                "average_cost_per_chapter": total_cost / total_chapters if total_chapters > 0 else 0.0
            },
            "accuracy_distribution": accuracy_distribution,
            "by_category": category_stats,
            "quality_grade": _get_accuracy_grade(overall_accuracy),
            "generated_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get fact-checking overview: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get fact-checking overview: {str(e)}")


@router.get("/fact-checking/chapter/{chapter_id}")
async def get_chapter_fact_check_details(
    chapter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed fact-checking results for a specific chapter

    Returns:
    - Section-by-section fact-check results
    - Individual claim verifications
    - Critical issues list
    - Recommendations

    Phase 3: GPT-4o structured fact-checking details

    **Admin only**
    """
    check_admin_access(current_user)

    try:
        from backend.database.models import Chapter

        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()

        if not chapter:
            raise HTTPException(status_code=404, detail=f"Chapter {chapter_id} not found")

        if not chapter.fact_checked or not chapter.stage_10_fact_check:
            raise HTTPException(
                status_code=404,
                detail=f"Chapter {chapter_id} has not been fact-checked"
            )

        fact_check_data = chapter.stage_10_fact_check

        return {
            "success": True,
            "chapter_id": str(chapter.id),
            "chapter_title": chapter.title,
            "fact_check_data": fact_check_data,
            "generated_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chapter fact-check details: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get fact-check details: {str(e)}")


def _get_accuracy_grade(accuracy: float) -> str:
    """Convert accuracy score to letter grade"""
    if accuracy >= 0.95:
        return "A (Excellent)"
    elif accuracy >= 0.90:
        return "B (Good)"
    elif accuracy >= 0.80:
        return "C (Acceptable)"
    elif accuracy >= 0.70:
        return "D (Needs Improvement)"
    else:
        return "F (Poor - Requires Major Revision)"


# ==================== Health Check ====================

@router.get("/health")
async def health_check():
    """Analytics service health check"""
    return {
        "status": "healthy",
        "service": "analytics",
        "features": [
            "event_tracking",
            "dashboard_metrics",
            "user_analytics",
            "content_analytics",
            "search_analytics",
            "export_analytics",
            "system_health",
            "trend_analysis",
            "cache_analytics",  # Phase 2: Added cache analytics
            "fact_checking_analytics"  # Phase 3: Added fact-checking analytics
        ]
    }
