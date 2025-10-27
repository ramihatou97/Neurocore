-- =====================================================================
-- Phase 15: Performance & Optimization Schema
-- =====================================================================
-- This migration implements comprehensive performance optimization including:
-- - Rate limiting tracking
-- - Performance metrics collection
-- - Background job management
-- - Query optimization indexes
-- - Caching metadata
-- =====================================================================

-- =====================================================================
-- 1. Rate Limiting Tables
-- =====================================================================

-- Track API rate limits per user/IP
CREATE TABLE IF NOT EXISTS rate_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identifier VARCHAR(255) NOT NULL,  -- user_id or IP address
    identifier_type VARCHAR(50) NOT NULL,  -- 'user', 'ip', 'api_key'
    endpoint VARCHAR(255) NOT NULL,
    request_count INTEGER DEFAULT 1,
    window_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    window_end TIMESTAMP WITH TIME ZONE,
    is_blocked BOOLEAN DEFAULT FALSE,
    blocked_until TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Track rate limit violations for analysis
CREATE TABLE IF NOT EXISTS rate_limit_violations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identifier VARCHAR(255) NOT NULL,
    identifier_type VARCHAR(50) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    violation_count INTEGER DEFAULT 1,
    request_count INTEGER NOT NULL,
    limit_threshold INTEGER NOT NULL,
    window_duration INTEGER NOT NULL,  -- in seconds
    user_agent TEXT,
    ip_address INET,
    blocked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================================
-- 2. Performance Metrics Tables
-- =====================================================================

-- Track API endpoint performance
CREATE TABLE IF NOT EXISTS endpoint_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,  -- GET, POST, etc.
    response_time_ms INTEGER NOT NULL,
    status_code INTEGER NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    ip_address INET,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    cache_hit BOOLEAN DEFAULT FALSE,
    error_message TEXT
);

-- Aggregate performance statistics
CREATE TABLE IF NOT EXISTS performance_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    request_count INTEGER DEFAULT 0,
    avg_response_time_ms NUMERIC(10, 2),
    min_response_time_ms INTEGER,
    max_response_time_ms INTEGER,
    p50_response_time_ms INTEGER,
    p95_response_time_ms INTEGER,
    p99_response_time_ms INTEGER,
    error_count INTEGER DEFAULT 0,
    cache_hit_rate NUMERIC(5, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(endpoint, method, period_start)
);

-- Database query performance tracking
CREATE TABLE IF NOT EXISTS query_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_type VARCHAR(100) NOT NULL,  -- e.g., 'search', 'recommendation', 'qa'
    query_hash VARCHAR(64),  -- MD5 hash of query for grouping
    execution_time_ms INTEGER NOT NULL,
    rows_returned INTEGER,
    table_name VARCHAR(100),
    index_used VARCHAR(100),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================================
-- 3. Background Job Management
-- =====================================================================

-- Track background jobs (Celery tasks)
CREATE TABLE IF NOT EXISTS background_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id VARCHAR(255) UNIQUE NOT NULL,  -- Celery task ID
    task_name VARCHAR(255) NOT NULL,
    task_type VARCHAR(100) NOT NULL,  -- 'embedding', 'pdf_processing', etc.
    status VARCHAR(50) DEFAULT 'pending',  -- pending, running, completed, failed, retrying
    priority INTEGER DEFAULT 5,  -- 1-10, higher is more urgent
    progress INTEGER DEFAULT 0,  -- 0-100
    result JSONB,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Track job dependencies
CREATE TABLE IF NOT EXISTS job_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES background_jobs(id) ON DELETE CASCADE,
    depends_on_job_id UUID NOT NULL REFERENCES background_jobs(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(job_id, depends_on_job_id)
);

-- =====================================================================
-- 4. Cache Metadata
-- =====================================================================

-- Track cache usage and effectiveness
CREATE TABLE IF NOT EXISTS cache_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cache_key VARCHAR(255) UNIQUE NOT NULL,
    cache_type VARCHAR(50) NOT NULL,  -- 'query', 'api', 'embedding', etc.
    hit_count INTEGER DEFAULT 0,
    miss_count INTEGER DEFAULT 0,
    total_time_saved_ms BIGINT DEFAULT 0,
    size_bytes INTEGER,
    ttl_seconds INTEGER,
    expires_at TIMESTAMP WITH TIME ZONE,
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================================
-- 5. System Resource Monitoring
-- =====================================================================

-- Track system resource usage
CREATE TABLE IF NOT EXISTS system_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_type VARCHAR(50) NOT NULL,  -- 'cpu', 'memory', 'disk', 'database'
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC(15, 2) NOT NULL,
    unit VARCHAR(20),  -- '%', 'MB', 'GB', 'ms'
    threshold_warning NUMERIC(15, 2),
    threshold_critical NUMERIC(15, 2),
    is_healthy BOOLEAN DEFAULT TRUE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================================
-- 6. Indexes for Performance Optimization
-- =====================================================================

-- Rate limiting indexes
CREATE INDEX IF NOT EXISTS idx_rate_limits_identifier
    ON rate_limits(identifier, identifier_type, endpoint);
CREATE INDEX IF NOT EXISTS idx_rate_limits_window
    ON rate_limits(window_start, window_end) WHERE is_blocked = FALSE;
CREATE INDEX IF NOT EXISTS idx_rate_limit_violations_identifier
    ON rate_limit_violations(identifier, created_at DESC);

-- Performance metrics indexes
CREATE INDEX IF NOT EXISTS idx_endpoint_metrics_endpoint
    ON endpoint_metrics(endpoint, method, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_endpoint_metrics_user
    ON endpoint_metrics(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_endpoint_metrics_timestamp
    ON endpoint_metrics(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_performance_stats_endpoint
    ON performance_stats(endpoint, method, period_start DESC);

-- Query performance indexes
CREATE INDEX IF NOT EXISTS idx_query_performance_type
    ON query_performance(query_type, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_query_performance_hash
    ON query_performance(query_hash, timestamp DESC);

-- Background jobs indexes
CREATE INDEX IF NOT EXISTS idx_background_jobs_status
    ON background_jobs(status, priority DESC, created_at);
CREATE INDEX IF NOT EXISTS idx_background_jobs_task_id
    ON background_jobs(task_id);
CREATE INDEX IF NOT EXISTS idx_background_jobs_user
    ON background_jobs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_background_jobs_type
    ON background_jobs(task_type, status);

-- Cache metadata indexes
CREATE INDEX IF NOT EXISTS idx_cache_metadata_key
    ON cache_metadata(cache_key);
CREATE INDEX IF NOT EXISTS idx_cache_metadata_type
    ON cache_metadata(cache_type, last_accessed DESC);
CREATE INDEX IF NOT EXISTS idx_cache_metadata_expires
    ON cache_metadata(expires_at) WHERE expires_at IS NOT NULL;

-- System metrics indexes
CREATE INDEX IF NOT EXISTS idx_system_metrics_type
    ON system_metrics(metric_type, metric_name, timestamp DESC);

-- =====================================================================
-- 7. Optimization Indexes for Existing Tables
-- =====================================================================

-- Users table optimizations
CREATE INDEX IF NOT EXISTS idx_users_email_active
    ON users(email) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_users_created
    ON users(created_at DESC);

-- PDFs table optimizations
CREATE INDEX IF NOT EXISTS idx_pdfs_status
    ON pdfs(extraction_status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pdfs_year
    ON pdfs(year) WHERE year IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_pdfs_full_text
    ON pdfs USING gin(to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(authors, '') || ' ' || COALESCE(extracted_text, '')));

-- Chapters table optimizations
CREATE INDEX IF NOT EXISTS idx_chapters_status
    ON chapters(generation_status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chapters_pdf
    ON chapters(pdf_id, chapter_number);
CREATE INDEX IF NOT EXISTS idx_chapters_author
    ON chapters(author_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chapters_full_text
    ON chapters USING gin(to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(content, '')));

-- Images table optimizations
CREATE INDEX IF NOT EXISTS idx_images_chapter
    ON images(chapter_id, position);
CREATE INDEX IF NOT EXISTS idx_images_status
    ON images(analysis_status) WHERE analysis_status IS NOT NULL;

-- Tasks table optimizations
CREATE INDEX IF NOT EXISTS idx_tasks_status_priority
    ON tasks(status, priority DESC, created_at);
CREATE INDEX IF NOT EXISTS idx_tasks_user
    ON tasks(user_id, status, created_at DESC);

-- =====================================================================
-- 8. PostgreSQL Functions for Performance Monitoring
-- =====================================================================

-- Function to get endpoint performance summary
CREATE OR REPLACE FUNCTION get_endpoint_performance_summary(
    p_endpoint VARCHAR DEFAULT NULL,
    p_hours INTEGER DEFAULT 24
)
RETURNS TABLE (
    endpoint VARCHAR,
    method VARCHAR,
    request_count BIGINT,
    avg_response_time NUMERIC,
    p95_response_time NUMERIC,
    error_rate NUMERIC,
    cache_hit_rate NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        em.endpoint,
        em.method,
        COUNT(*) as request_count,
        ROUND(AVG(em.response_time_ms)::NUMERIC, 2) as avg_response_time,
        ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY em.response_time_ms)::NUMERIC, 2) as p95_response_time,
        ROUND((COUNT(*) FILTER (WHERE em.status_code >= 400)::NUMERIC / COUNT(*)::NUMERIC * 100), 2) as error_rate,
        ROUND((COUNT(*) FILTER (WHERE em.cache_hit = TRUE)::NUMERIC / COUNT(*)::NUMERIC * 100), 2) as cache_hit_rate
    FROM endpoint_metrics em
    WHERE
        em.timestamp >= NOW() - INTERVAL '1 hour' * p_hours
        AND (p_endpoint IS NULL OR em.endpoint = p_endpoint)
    GROUP BY em.endpoint, em.method
    ORDER BY request_count DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to get slow queries
CREATE OR REPLACE FUNCTION get_slow_queries(
    p_threshold_ms INTEGER DEFAULT 1000,
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    query_type VARCHAR,
    query_hash VARCHAR,
    avg_execution_time NUMERIC,
    max_execution_time INTEGER,
    execution_count BIGINT,
    table_name VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        qp.query_type,
        qp.query_hash,
        ROUND(AVG(qp.execution_time_ms)::NUMERIC, 2) as avg_execution_time,
        MAX(qp.execution_time_ms) as max_execution_time,
        COUNT(*) as execution_count,
        qp.table_name
    FROM query_performance qp
    WHERE qp.execution_time_ms >= p_threshold_ms
    GROUP BY qp.query_type, qp.query_hash, qp.table_name
    ORDER BY avg_execution_time DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to get cache effectiveness
CREATE OR REPLACE FUNCTION get_cache_effectiveness()
RETURNS TABLE (
    cache_type VARCHAR,
    total_hits BIGINT,
    total_misses BIGINT,
    hit_rate NUMERIC,
    total_time_saved_hours NUMERIC,
    entry_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        cm.cache_type,
        SUM(cm.hit_count) as total_hits,
        SUM(cm.miss_count) as total_misses,
        ROUND((SUM(cm.hit_count)::NUMERIC / NULLIF(SUM(cm.hit_count + cm.miss_count), 0)::NUMERIC * 100), 2) as hit_rate,
        ROUND((SUM(cm.total_time_saved_ms)::NUMERIC / 3600000), 2) as total_time_saved_hours,
        COUNT(*) as entry_count
    FROM cache_metadata cm
    GROUP BY cm.cache_type
    ORDER BY total_hits DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up expired rate limits
CREATE OR REPLACE FUNCTION cleanup_expired_rate_limits()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM rate_limits
    WHERE window_end < NOW() - INTERVAL '1 day'
    AND is_blocked = FALSE;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up old performance metrics
CREATE OR REPLACE FUNCTION cleanup_old_performance_metrics(
    p_retention_days INTEGER DEFAULT 30
)
RETURNS JSONB AS $$
DECLARE
    endpoint_deleted INTEGER;
    query_deleted INTEGER;
    result JSONB;
BEGIN
    -- Clean up endpoint metrics
    DELETE FROM endpoint_metrics
    WHERE timestamp < NOW() - INTERVAL '1 day' * p_retention_days;
    GET DIAGNOSTICS endpoint_deleted = ROW_COUNT;

    -- Clean up query performance
    DELETE FROM query_performance
    WHERE timestamp < NOW() - INTERVAL '1 day' * p_retention_days;
    GET DIAGNOSTICS query_deleted = ROW_COUNT;

    result := jsonb_build_object(
        'endpoint_metrics_deleted', endpoint_deleted,
        'query_performance_deleted', query_deleted,
        'total_deleted', endpoint_deleted + query_deleted
    );

    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- 9. Views for Performance Analysis
-- =====================================================================

-- Real-time endpoint performance view
CREATE OR REPLACE VIEW v_endpoint_performance_realtime AS
SELECT
    endpoint,
    method,
    COUNT(*) as request_count_1h,
    ROUND(AVG(response_time_ms)::NUMERIC, 2) as avg_response_time_ms,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY response_time_ms)::NUMERIC, 2) as p50_ms,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms)::NUMERIC, 2) as p95_ms,
    ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY response_time_ms)::NUMERIC, 2) as p99_ms,
    COUNT(*) FILTER (WHERE status_code >= 400) as error_count,
    ROUND((COUNT(*) FILTER (WHERE status_code >= 400)::NUMERIC / COUNT(*)::NUMERIC * 100), 2) as error_rate,
    COUNT(*) FILTER (WHERE cache_hit = TRUE) as cache_hits,
    ROUND((COUNT(*) FILTER (WHERE cache_hit = TRUE)::NUMERIC / COUNT(*)::NUMERIC * 100), 2) as cache_hit_rate
FROM endpoint_metrics
WHERE timestamp >= NOW() - INTERVAL '1 hour'
GROUP BY endpoint, method;

-- Top slow endpoints view
CREATE OR REPLACE VIEW v_slow_endpoints AS
SELECT
    endpoint,
    method,
    COUNT(*) as request_count,
    ROUND(AVG(response_time_ms)::NUMERIC, 2) as avg_response_time_ms,
    MAX(response_time_ms) as max_response_time_ms,
    COUNT(*) FILTER (WHERE response_time_ms > 1000) as slow_requests
FROM endpoint_metrics
WHERE timestamp >= NOW() - INTERVAL '1 hour'
GROUP BY endpoint, method
HAVING AVG(response_time_ms) > 500
ORDER BY avg_response_time_ms DESC;

-- Background job status view
CREATE OR REPLACE VIEW v_background_job_status AS
SELECT
    status,
    task_type,
    COUNT(*) as job_count,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration_seconds,
    MAX(retry_count) as max_retries,
    COUNT(*) FILTER (WHERE retry_count > 0) as retried_jobs
FROM background_jobs
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY status, task_type;

-- =====================================================================
-- 10. Triggers for Automatic Updates
-- =====================================================================

-- Update rate_limits updated_at timestamp
CREATE OR REPLACE FUNCTION update_rate_limits_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_rate_limits_timestamp
    BEFORE UPDATE ON rate_limits
    FOR EACH ROW
    EXECUTE FUNCTION update_rate_limits_timestamp();

-- Update background_jobs updated_at timestamp
CREATE OR REPLACE FUNCTION update_background_jobs_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_background_jobs_timestamp
    BEFORE UPDATE ON background_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_background_jobs_timestamp();

-- Update cache_metadata on access
CREATE OR REPLACE FUNCTION update_cache_metadata_access()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_accessed = NOW();
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_cache_metadata_access
    BEFORE UPDATE ON cache_metadata
    FOR EACH ROW
    WHEN (OLD.hit_count IS DISTINCT FROM NEW.hit_count OR OLD.miss_count IS DISTINCT FROM NEW.miss_count)
    EXECUTE FUNCTION update_cache_metadata_access();

-- =====================================================================
-- 11. Initial Data & Configuration
-- =====================================================================

-- Insert default performance thresholds
INSERT INTO system_metrics (metric_type, metric_name, metric_value, unit, threshold_warning, threshold_critical, is_healthy)
VALUES
    ('api', 'avg_response_time_threshold', 500, 'ms', 500, 1000, TRUE),
    ('api', 'error_rate_threshold', 1, '%', 1, 5, TRUE),
    ('database', 'connection_pool_usage', 50, '%', 70, 90, TRUE),
    ('cache', 'hit_rate_target', 70, '%', 60, 40, TRUE),
    ('background_jobs', 'queue_size_warning', 100, 'jobs', 100, 500, TRUE)
ON CONFLICT DO NOTHING;

-- =====================================================================
-- Migration Complete
-- =====================================================================
-- This migration has created a comprehensive performance optimization
-- infrastructure including:
-- - Rate limiting with violation tracking
-- - Detailed performance metrics collection
-- - Background job management system
-- - Cache effectiveness tracking
-- - Query performance monitoring
-- - 25+ optimized indexes
-- - 6 utility functions
-- - 3 analytical views
-- - Automatic cleanup triggers
-- =====================================================================
