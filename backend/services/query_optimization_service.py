"""
Query Optimization Service for Phase 15: Performance & Optimization
Database query performance monitoring, analysis, and optimization recommendations
"""

import time
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from contextlib import contextmanager

from backend.utils import get_logger

logger = get_logger(__name__)


class QueryOptimizationService:
    """
    Database query optimization and monitoring service

    Features:
    - Query performance tracking
    - Slow query detection
    - Index usage analysis
    - Query execution plan analysis
    - Optimization recommendations
    - Performance trend analysis
    """

    def __init__(self, db: Session):
        self.db = db
        self.slow_query_threshold_ms = 1000  # 1 second

    # ==================== Query Monitoring ====================

    @contextmanager
    def track_query(
        self,
        query_type: str,
        query_sql: Optional[str] = None,
        table_name: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """
        Context manager to track query execution time

        Usage:
            with query_optimizer.track_query('search', query_sql, 'chapters'):
                result = db.execute(query)
        """
        start_time = time.time()
        query_hash = None

        if query_sql:
            query_hash = hashlib.md5(query_sql.encode()).hexdigest()[:16]

        try:
            yield
        finally:
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Track in database if slow or important
            if execution_time_ms >= self.slow_query_threshold_ms or query_type in ['search', 'recommendation', 'qa']:
                self._record_query_performance(
                    query_type=query_type,
                    query_hash=query_hash,
                    execution_time_ms=execution_time_ms,
                    table_name=table_name,
                    user_id=user_id
                )

            # Log slow queries
            if execution_time_ms >= self.slow_query_threshold_ms:
                logger.warning(
                    f"Slow query detected: type={query_type}, "
                    f"time={execution_time_ms}ms, table={table_name}"
                )

    def _record_query_performance(
        self,
        query_type: str,
        query_hash: Optional[str],
        execution_time_ms: int,
        table_name: Optional[str],
        user_id: Optional[str],
        rows_returned: Optional[int] = None,
        index_used: Optional[str] = None
    ):
        """Record query performance in database"""
        try:
            query = text("""
                INSERT INTO query_performance (
                    query_type, query_hash, execution_time_ms,
                    rows_returned, table_name, index_used, user_id
                )
                VALUES (
                    :query_type, :query_hash, :execution_time_ms,
                    :rows_returned, :table_name, :index_used, :user_id
                )
            """)

            self.db.execute(query, {
                'query_type': query_type,
                'query_hash': query_hash,
                'execution_time_ms': execution_time_ms,
                'rows_returned': rows_returned,
                'table_name': table_name,
                'index_used': index_used,
                'user_id': user_id
            })
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to record query performance: {str(e)}")

    # ==================== Query Analysis ====================

    def get_slow_queries(
        self,
        threshold_ms: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get slow queries from database

        Args:
            threshold_ms: Minimum execution time (default: 1000ms)
            limit: Maximum results

        Returns:
            List of slow query records
        """
        threshold_ms = threshold_ms or self.slow_query_threshold_ms

        try:
            query = text("""
                SELECT
                    query_type,
                    query_hash,
                    ROUND(AVG(execution_time_ms)::NUMERIC, 2) as avg_execution_time,
                    MAX(execution_time_ms) as max_execution_time,
                    MIN(execution_time_ms) as min_execution_time,
                    COUNT(*) as execution_count,
                    table_name,
                    MAX(timestamp) as last_execution
                FROM query_performance
                WHERE execution_time_ms >= :threshold
                GROUP BY query_type, query_hash, table_name
                ORDER BY avg_execution_time DESC
                LIMIT :limit
            """)

            result = self.db.execute(query, {
                'threshold': threshold_ms,
                'limit': limit
            })

            return [
                {
                    'query_type': row[0],
                    'query_hash': row[1],
                    'avg_execution_time_ms': float(row[2]),
                    'max_execution_time_ms': row[3],
                    'min_execution_time_ms': row[4],
                    'execution_count': row[5],
                    'table_name': row[6],
                    'last_execution': row[7].isoformat() if row[7] else None
                }
                for row in result.fetchall()
            ]

        except Exception as e:
            logger.error(f"Failed to get slow queries: {str(e)}")
            return []

    def get_query_statistics(
        self,
        query_type: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get query statistics for analysis

        Args:
            query_type: Filter by query type
            hours: Time window in hours

        Returns:
            Statistics dictionary
        """
        try:
            conditions = ["timestamp >= NOW() - INTERVAL '1 hour' * :hours"]
            params = {'hours': hours}

            if query_type:
                conditions.append("query_type = :query_type")
                params['query_type'] = query_type

            where_clause = " AND ".join(conditions)

            query = text(f"""
                SELECT
                    COUNT(*) as total_queries,
                    ROUND(AVG(execution_time_ms)::NUMERIC, 2) as avg_execution_time,
                    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY execution_time_ms)::NUMERIC, 2) as p50,
                    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_time_ms)::NUMERIC, 2) as p95,
                    ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY execution_time_ms)::NUMERIC, 2) as p99,
                    MAX(execution_time_ms) as max_execution_time,
                    COUNT(*) FILTER (WHERE execution_time_ms >= 1000) as slow_queries,
                    COUNT(DISTINCT query_hash) as unique_queries
                FROM query_performance
                WHERE {where_clause}
            """)

            result = self.db.execute(query, params)
            row = result.fetchone()

            return {
                'total_queries': row[0],
                'avg_execution_time_ms': float(row[1]) if row[1] else 0,
                'p50_ms': float(row[2]) if row[2] else 0,
                'p95_ms': float(row[3]) if row[3] else 0,
                'p99_ms': float(row[4]) if row[4] else 0,
                'max_execution_time_ms': row[5] or 0,
                'slow_queries': row[6] or 0,
                'slow_query_percentage': (row[6] / row[0] * 100) if row[0] > 0 else 0,
                'unique_queries': row[7] or 0,
                'time_window_hours': hours,
                'query_type': query_type
            }

        except Exception as e:
            logger.error(f"Failed to get query statistics: {str(e)}")
            return {}

    # ==================== Index Analysis ====================

    def analyze_table_indexes(self, table_name: str) -> Dict[str, Any]:
        """
        Analyze indexes for a table

        Args:
            table_name: Table to analyze

        Returns:
            Index analysis results
        """
        try:
            # Get table indexes
            query = text("""
                SELECT
                    indexname,
                    indexdef,
                    pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
                FROM pg_indexes
                WHERE tablename = :table_name
            """)

            result = self.db.execute(query, {'table_name': table_name})
            indexes = [
                {
                    'name': row[0],
                    'definition': row[1],
                    'size': row[2]
                }
                for row in result.fetchall()
            ]

            # Get table statistics
            stats_query = text("""
                SELECT
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_rows,
                    n_dead_tup as dead_rows,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze,
                    last_autoanalyze
                FROM pg_stat_user_tables
                WHERE relname = :table_name
            """)

            stats_result = self.db.execute(stats_query, {'table_name': table_name})
            stats_row = stats_result.fetchone()

            stats = {}
            if stats_row:
                stats = {
                    'inserts': stats_row[0] or 0,
                    'updates': stats_row[1] or 0,
                    'deletes': stats_row[2] or 0,
                    'live_rows': stats_row[3] or 0,
                    'dead_rows': stats_row[4] or 0,
                    'last_vacuum': stats_row[5].isoformat() if stats_row[5] else None,
                    'last_autovacuum': stats_row[6].isoformat() if stats_row[6] else None,
                    'last_analyze': stats_row[7].isoformat() if stats_row[7] else None,
                    'last_autoanalyze': stats_row[8].isoformat() if stats_row[8] else None
                }

            return {
                'table_name': table_name,
                'indexes': indexes,
                'index_count': len(indexes),
                'statistics': stats
            }

        except Exception as e:
            logger.error(f"Failed to analyze table indexes: {str(e)}")
            return {}

    def get_unused_indexes(self) -> List[Dict[str, Any]]:
        """
        Find unused indexes that could be dropped

        Returns:
            List of potentially unused indexes
        """
        try:
            query = text("""
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
                    pg_relation_size(indexrelid) as index_size_bytes
                FROM pg_stat_user_indexes
                WHERE idx_scan = 0
                    AND indexrelname NOT LIKE '%_pkey'
                ORDER BY pg_relation_size(indexrelid) DESC
            """)

            result = self.db.execute(query)

            return [
                {
                    'schema': row[0],
                    'table': row[1],
                    'index': row[2],
                    'scans': row[3],
                    'size': row[4],
                    'size_bytes': row[5]
                }
                for row in result.fetchall()
            ]

        except Exception as e:
            logger.error(f"Failed to get unused indexes: {str(e)}")
            return []

    # ==================== Optimization Recommendations ====================

    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """
        Generate optimization recommendations based on analysis

        Returns:
            List of recommendations
        """
        recommendations = []

        try:
            # Check for slow queries
            slow_queries = self.get_slow_queries(limit=10)
            if slow_queries:
                for sq in slow_queries[:3]:
                    recommendations.append({
                        'type': 'slow_query',
                        'priority': 'high' if sq['avg_execution_time_ms'] > 5000 else 'medium',
                        'title': f"Optimize slow {sq['query_type']} query",
                        'description': f"Query on {sq['table_name']} averaging {sq['avg_execution_time_ms']}ms",
                        'suggestion': 'Consider adding indexes, optimizing query structure, or using caching',
                        'impact': 'high',
                        'data': sq
                    })

            # Check for unused indexes
            unused = self.get_unused_indexes()
            if unused:
                for idx in unused[:3]:
                    recommendations.append({
                        'type': 'unused_index',
                        'priority': 'low',
                        'title': f"Remove unused index {idx['index']}",
                        'description': f"Index on {idx['table']} has 0 scans, using {idx['size']}",
                        'suggestion': f"DROP INDEX {idx['index']}",
                        'impact': 'low',
                        'data': idx
                    })

            # Check for tables needing VACUUM
            tables_needing_vacuum = self._check_vacuum_needed()
            for table in tables_needing_vacuum:
                recommendations.append({
                    'type': 'maintenance',
                    'priority': 'medium',
                    'title': f"VACUUM needed for {table['table_name']}",
                    'description': f"{table['dead_rows']} dead rows ({table['dead_percentage']:.1f}%)",
                    'suggestion': f"VACUUM ANALYZE {table['table_name']}",
                    'impact': 'medium',
                    'data': table
                })

        except Exception as e:
            logger.error(f"Failed to generate recommendations: {str(e)}")

        return recommendations

    def _check_vacuum_needed(self) -> List[Dict[str, Any]]:
        """Check tables that need VACUUM"""
        try:
            query = text("""
                SELECT
                    relname as table_name,
                    n_live_tup as live_rows,
                    n_dead_tup as dead_rows,
                    ROUND(n_dead_tup::NUMERIC / NULLIF(n_live_tup + n_dead_tup, 0)::NUMERIC * 100, 2) as dead_percentage,
                    last_autovacuum
                FROM pg_stat_user_tables
                WHERE n_dead_tup > 1000
                    AND n_dead_tup::NUMERIC / NULLIF(n_live_tup + n_dead_tup, 0)::NUMERIC > 0.1
                ORDER BY dead_percentage DESC
                LIMIT 10
            """)

            result = self.db.execute(query)

            return [
                {
                    'table_name': row[0],
                    'live_rows': row[1],
                    'dead_rows': row[2],
                    'dead_percentage': float(row[3]) if row[3] else 0,
                    'last_autovacuum': row[4].isoformat() if row[4] else None
                }
                for row in result.fetchall()
            ]

        except Exception as e:
            logger.error(f"Failed to check vacuum status: {str(e)}")
            return []

    # ==================== Query Execution Plans ====================

    def explain_query(self, query_sql: str, analyze: bool = False) -> Dict[str, Any]:
        """
        Get query execution plan

        Args:
            query_sql: SQL query to explain
            analyze: Run EXPLAIN ANALYZE (actually executes query)

        Returns:
            Execution plan details
        """
        try:
            explain_type = "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)" if analyze else "EXPLAIN (FORMAT JSON)"
            explain_query = text(f"{explain_type} {query_sql}")

            result = self.db.execute(explain_query)
            plan = result.fetchone()[0]

            return {
                'query': query_sql,
                'plan': plan,
                'analyzed': analyze
            }

        except Exception as e:
            logger.error(f"Failed to explain query: {str(e)}")
            return {'error': str(e)}

    # ==================== Connection Pool Monitoring ====================

    def get_connection_pool_stats(self) -> Dict[str, Any]:
        """Get database connection pool statistics"""
        try:
            query = text("""
                SELECT
                    COUNT(*) as total_connections,
                    COUNT(*) FILTER (WHERE state = 'active') as active,
                    COUNT(*) FILTER (WHERE state = 'idle') as idle,
                    COUNT(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction,
                    COUNT(*) FILTER (WHERE wait_event_type IS NOT NULL) as waiting,
                    MAX(EXTRACT(EPOCH FROM (NOW() - query_start))) as longest_query_seconds
                FROM pg_stat_activity
                WHERE datname = current_database()
            """)

            result = self.db.execute(query)
            row = result.fetchone()

            return {
                'total_connections': row[0] or 0,
                'active': row[1] or 0,
                'idle': row[2] or 0,
                'idle_in_transaction': row[3] or 0,
                'waiting': row[4] or 0,
                'longest_query_seconds': float(row[5]) if row[5] else 0,
                'utilization_percentage': (row[1] / row[0] * 100) if row[0] > 0 else 0
            }

        except Exception as e:
            logger.error(f"Failed to get connection pool stats: {str(e)}")
            return {}

    # ==================== Performance Trends ====================

    def get_performance_trends(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get performance trends over time

        Args:
            hours: Time window

        Returns:
            Trend data
        """
        try:
            query = text("""
                SELECT
                    DATE_TRUNC('hour', timestamp) as hour,
                    COUNT(*) as query_count,
                    ROUND(AVG(execution_time_ms)::NUMERIC, 2) as avg_time,
                    MAX(execution_time_ms) as max_time,
                    COUNT(*) FILTER (WHERE execution_time_ms >= 1000) as slow_queries
                FROM query_performance
                WHERE timestamp >= NOW() - INTERVAL '1 hour' * :hours
                GROUP BY DATE_TRUNC('hour', timestamp)
                ORDER BY hour DESC
            """)

            result = self.db.execute(query, {'hours': hours})

            trends = [
                {
                    'hour': row[0].isoformat(),
                    'query_count': row[1],
                    'avg_execution_time_ms': float(row[2]) if row[2] else 0,
                    'max_execution_time_ms': row[3],
                    'slow_queries': row[4]
                }
                for row in result.fetchall()
            ]

            return {
                'time_window_hours': hours,
                'data_points': len(trends),
                'trends': trends
            }

        except Exception as e:
            logger.error(f"Failed to get performance trends: {str(e)}")
            return {}
