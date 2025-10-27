"""
Performance Monitoring API Routes
Endpoints for monitoring and optimizing system performance
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.utils.dependencies import get_current_user
from backend.database.models import User
from backend.services.performance_cache_service import PerformanceCacheService
from backend.services.rate_limit_service import RateLimitService
from backend.services.query_optimization_service import QueryOptimizationService
from backend.config.redis import redis_manager

router = APIRouter()


# ==================== Cache Monitoring ====================

@router.get("/cache/stats")
async def get_cache_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive cache statistics

    Returns statistics about Redis cache, memory cache, and database cache metadata
    """
    cache_service = PerformanceCacheService(db)
    stats = cache_service.get_cache_statistics()

    return {
        'success': True,
        'statistics': stats
    }


@router.get("/cache/top-keys")
async def get_top_cached_keys(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get most frequently accessed cache keys"""
    cache_service = PerformanceCacheService(db)
    top_keys = cache_service.get_top_cached_keys(limit=limit)

    return {
        'success': True,
        'top_keys': top_keys,
        'count': len(top_keys)
    }


@router.post("/cache/cleanup")
async def cleanup_expired_cache(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clean up expired cache entries from database"""
    cache_service = PerformanceCacheService(db)
    deleted_count = cache_service.cleanup_expired()

    return {
        'success': True,
        'deleted_count': deleted_count
    }


@router.delete("/cache/pattern/{pattern}")
async def invalidate_cache_pattern(
    pattern: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Invalidate all cache keys matching pattern"""
    cache_service = PerformanceCacheService(db)
    deleted_count = cache_service.invalidate_pattern(pattern)

    return {
        'success': True,
        'pattern': pattern,
        'deleted_count': deleted_count
    }


# ==================== Rate Limiting Monitoring ====================

@router.get("/rate-limits/stats")
async def get_rate_limit_statistics(
    identifier: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get rate limit statistics"""
    rate_limit_service = RateLimitService(db)
    stats = rate_limit_service.get_rate_limit_statistics(identifier=identifier)

    return {
        'success': True,
        'statistics': stats,
        'identifier': identifier
    }


@router.post("/rate-limits/unblock")
async def unblock_identifier(
    identifier: str,
    identifier_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually unblock a rate-limited identifier"""
    rate_limit_service = RateLimitService(db)
    success = rate_limit_service.unblock_identifier(identifier, identifier_type)

    return {
        'success': success,
        'identifier': identifier,
        'identifier_type': identifier_type
    }


# ==================== Query Optimization ====================

@router.get("/queries/slow")
async def get_slow_queries(
    threshold_ms: int = Query(1000, ge=100, le=10000),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get slow queries from monitoring"""
    query_service = QueryOptimizationService(db)
    slow_queries = query_service.get_slow_queries(threshold_ms=threshold_ms, limit=limit)

    return {
        'success': True,
        'slow_queries': slow_queries,
        'count': len(slow_queries),
        'threshold_ms': threshold_ms
    }


@router.get("/queries/stats")
async def get_query_statistics(
    query_type: Optional[str] = None,
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get query performance statistics"""
    query_service = QueryOptimizationService(db)
    stats = query_service.get_query_statistics(query_type=query_type, hours=hours)

    return {
        'success': True,
        'statistics': stats
    }


@router.get("/queries/trends")
async def get_performance_trends(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get performance trends over time"""
    query_service = QueryOptimizationService(db)
    trends = query_service.get_performance_trends(hours=hours)

    return {
        'success': True,
        'trends': trends
    }


@router.get("/database/indexes/{table_name}")
async def analyze_table_indexes(
    table_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Analyze indexes for a specific table"""
    query_service = QueryOptimizationService(db)
    analysis = query_service.analyze_table_indexes(table_name)

    return {
        'success': True,
        'analysis': analysis
    }


@router.get("/database/unused-indexes")
async def get_unused_indexes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Find unused indexes that could be dropped"""
    query_service = QueryOptimizationService(db)
    unused = query_service.get_unused_indexes()

    return {
        'success': True,
        'unused_indexes': unused,
        'count': len(unused)
    }


@router.get("/database/connections")
async def get_connection_pool_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get database connection pool statistics"""
    query_service = QueryOptimizationService(db)
    stats = query_service.get_connection_pool_stats()

    return {
        'success': True,
        'connection_pool': stats
    }


@router.get("/optimization/recommendations")
async def get_optimization_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get optimization recommendations"""
    query_service = QueryOptimizationService(db)
    recommendations = query_service.get_optimization_recommendations()

    return {
        'success': True,
        'recommendations': recommendations,
        'count': len(recommendations)
    }


# ==================== System Health ====================

@router.get("/health")
async def performance_health_check(
    db: Session = Depends(get_db)
):
    """
    Comprehensive performance health check

    Checks Redis, database, cache, and rate limiting
    """
    health = {
        'redis': {
            'connected': redis_manager.health_check(),
            'dbsize': redis_manager.dbsize() if redis_manager.health_check() else 0
        },
        'database': {
            'connected': True  # If we got here, DB is connected
        },
        'cache': {},
        'queries': {}
    }

    try:
        # Cache stats
        cache_service = PerformanceCacheService(db)
        cache_stats = cache_service.get_cache_statistics()
        health['cache'] = {
            'operational': True,
            'memory_utilization': cache_stats.get('memory', {}).get('utilization', 0)
        }

        # Query stats
        query_service = QueryOptimizationService(db)
        query_stats = query_service.get_query_statistics(hours=1)
        health['queries'] = {
            'total_last_hour': query_stats.get('total_queries', 0),
            'avg_execution_time_ms': query_stats.get('avg_execution_time_ms', 0),
            'slow_queries': query_stats.get('slow_queries', 0)
        }

    except Exception as e:
        health['error'] = str(e)

    # Overall health status
    health['status'] = 'healthy' if all([
        health['redis']['connected'],
        health['database']['connected'],
        health['cache'].get('operational', False)
    ]) else 'degraded'

    return health


# ==================== System Metrics ====================

@router.get("/metrics")
async def get_system_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive system performance metrics

    Combines cache, rate limiting, query, and connection pool metrics
    """
    try:
        cache_service = PerformanceCacheService(db)
        query_service = QueryOptimizationService(db)
        rate_limit_service = RateLimitService(db)

        metrics = {
            'cache': cache_service.get_cache_statistics(),
            'queries': query_service.get_query_statistics(hours=24),
            'connection_pool': query_service.get_connection_pool_stats(),
            'rate_limits': rate_limit_service.get_rate_limit_statistics(),
            'timestamp': cache_service.get_cache_statistics().get('timestamp')
        }

        return {
            'success': True,
            'metrics': metrics
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
