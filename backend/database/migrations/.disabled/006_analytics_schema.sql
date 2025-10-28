-- ==========================================
-- Phase 12: Analytics & Insights Dashboard
-- Analytics Schema Migration
-- ==========================================

-- Analytics Events Table
-- Tracks all user actions and system events for analytics
CREATE TABLE IF NOT EXISTS analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    event_category VARCHAR(50) NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    metadata JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    session_id VARCHAR(255),
    duration_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_analytics_events_type ON analytics_events(event_type);
CREATE INDEX IF NOT EXISTS idx_analytics_events_category ON analytics_events(event_category);
CREATE INDEX IF NOT EXISTS idx_analytics_events_user_id ON analytics_events(user_id);
CREATE INDEX IF NOT EXISTS idx_analytics_events_created_at ON analytics_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_events_resource ON analytics_events(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_analytics_events_session ON analytics_events(session_id);
CREATE INDEX IF NOT EXISTS idx_analytics_events_success ON analytics_events(success);

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_analytics_events_user_time ON analytics_events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_events_type_time ON analytics_events(event_type, created_at DESC);

-- GIN index for JSONB metadata queries
CREATE INDEX IF NOT EXISTS idx_analytics_events_metadata ON analytics_events USING GIN (metadata);


-- ==========================================
-- Analytics Aggregates Table
-- Pre-computed daily, weekly, and monthly summaries
-- ==========================================

CREATE TABLE IF NOT EXISTS analytics_aggregates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period_type VARCHAR(20) NOT NULL CHECK (period_type IN ('daily', 'weekly', 'monthly')),
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    metric_type VARCHAR(100) NOT NULL,
    metric_category VARCHAR(50) NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    value NUMERIC NOT NULL DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_aggregate UNIQUE (period_type, period_start, metric_type, metric_category, user_id)
);

-- Indexes for aggregates
CREATE INDEX IF NOT EXISTS idx_analytics_aggregates_period ON analytics_aggregates(period_type, period_start DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_aggregates_metric ON analytics_aggregates(metric_type, metric_category);
CREATE INDEX IF NOT EXISTS idx_analytics_aggregates_user ON analytics_aggregates(user_id);
CREATE INDEX IF NOT EXISTS idx_analytics_aggregates_timerange ON analytics_aggregates(period_start, period_end);


-- ==========================================
-- Dashboard Metrics Table
-- Real-time metrics for dashboard display
-- ==========================================

CREATE TABLE IF NOT EXISTS dashboard_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_key VARCHAR(100) NOT NULL UNIQUE,
    metric_name VARCHAR(200) NOT NULL,
    metric_description TEXT,
    metric_value NUMERIC NOT NULL DEFAULT 0,
    metric_unit VARCHAR(50),
    metric_category VARCHAR(50) NOT NULL,
    previous_value NUMERIC,
    change_percentage NUMERIC,
    trend VARCHAR(20) CHECK (trend IN ('up', 'down', 'stable', 'unknown')),
    metadata JSONB DEFAULT '{}',
    last_calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for dashboard metrics
CREATE INDEX IF NOT EXISTS idx_dashboard_metrics_category ON dashboard_metrics(metric_category);
CREATE INDEX IF NOT EXISTS idx_dashboard_metrics_key ON dashboard_metrics(metric_key);
CREATE INDEX IF NOT EXISTS idx_dashboard_metrics_updated ON dashboard_metrics(updated_at DESC);


-- ==========================================
-- Analytics Functions
-- Helper functions for analytics calculations
-- ==========================================

-- Function to get event count by type for a time range
CREATE OR REPLACE FUNCTION get_event_count(
    p_event_type VARCHAR,
    p_start_date TIMESTAMP WITH TIME ZONE,
    p_end_date TIMESTAMP WITH TIME ZONE,
    p_user_id UUID DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO v_count
    FROM analytics_events
    WHERE event_type = p_event_type
        AND created_at BETWEEN p_start_date AND p_end_date
        AND (p_user_id IS NULL OR user_id = p_user_id);

    RETURN COALESCE(v_count, 0);
END;
$$ LANGUAGE plpgsql;


-- Function to get average duration for event type
CREATE OR REPLACE FUNCTION get_average_duration(
    p_event_type VARCHAR,
    p_start_date TIMESTAMP WITH TIME ZONE,
    p_end_date TIMESTAMP WITH TIME ZONE
)
RETURNS NUMERIC AS $$
DECLARE
    v_avg NUMERIC;
BEGIN
    SELECT AVG(duration_ms)
    INTO v_avg
    FROM analytics_events
    WHERE event_type = p_event_type
        AND duration_ms IS NOT NULL
        AND created_at BETWEEN p_start_date AND p_end_date;

    RETURN COALESCE(v_avg, 0);
END;
$$ LANGUAGE plpgsql;


-- Function to calculate daily aggregates
CREATE OR REPLACE FUNCTION calculate_daily_aggregates(
    p_date DATE
)
RETURNS VOID AS $$
DECLARE
    v_start_time TIMESTAMP WITH TIME ZONE;
    v_end_time TIMESTAMP WITH TIME ZONE;
BEGIN
    v_start_time := p_date::TIMESTAMP WITH TIME ZONE;
    v_end_time := (p_date + INTERVAL '1 day')::TIMESTAMP WITH TIME ZONE;

    -- Total events by category
    INSERT INTO analytics_aggregates (
        period_type, period_start, period_end,
        metric_type, metric_category, value, user_id
    )
    SELECT
        'daily',
        v_start_time,
        v_end_time,
        'event_count',
        event_category,
        COUNT(*),
        user_id
    FROM analytics_events
    WHERE created_at >= v_start_time AND created_at < v_end_time
    GROUP BY event_category, user_id
    ON CONFLICT (period_type, period_start, metric_type, metric_category, user_id)
    DO UPDATE SET
        value = EXCLUDED.value,
        updated_at = NOW();

    -- Unique users per day
    INSERT INTO analytics_aggregates (
        period_type, period_start, period_end,
        metric_type, metric_category, value, user_id
    )
    SELECT
        'daily',
        v_start_time,
        v_end_time,
        'unique_users',
        'system',
        COUNT(DISTINCT user_id),
        NULL
    FROM analytics_events
    WHERE created_at >= v_start_time AND created_at < v_end_time
    ON CONFLICT (period_type, period_start, metric_type, metric_category, user_id)
    DO UPDATE SET
        value = EXCLUDED.value,
        updated_at = NOW();

    -- Average duration by event type
    INSERT INTO analytics_aggregates (
        period_type, period_start, period_end,
        metric_type, metric_category, value, user_id, metadata
    )
    SELECT
        'daily',
        v_start_time,
        v_end_time,
        'avg_duration',
        event_type,
        AVG(duration_ms),
        NULL,
        jsonb_build_object('count', COUNT(*))
    FROM analytics_events
    WHERE created_at >= v_start_time AND created_at < v_end_time
        AND duration_ms IS NOT NULL
    GROUP BY event_type
    ON CONFLICT (period_type, period_start, metric_type, metric_category, user_id)
    DO UPDATE SET
        value = EXCLUDED.value,
        metadata = EXCLUDED.metadata,
        updated_at = NOW();

END;
$$ LANGUAGE plpgsql;


-- Function to update dashboard metrics
CREATE OR REPLACE FUNCTION update_dashboard_metrics()
RETURNS VOID AS $$
DECLARE
    v_now TIMESTAMP WITH TIME ZONE := NOW();
    v_24h_ago TIMESTAMP WITH TIME ZONE := v_now - INTERVAL '24 hours';
    v_7d_ago TIMESTAMP WITH TIME ZONE := v_now - INTERVAL '7 days';
    v_30d_ago TIMESTAMP WITH TIME ZONE := v_now - INTERVAL '30 days';
BEGIN
    -- Total users
    INSERT INTO dashboard_metrics (
        metric_key, metric_name, metric_description,
        metric_value, metric_unit, metric_category
    )
    SELECT
        'total_users',
        'Total Users',
        'Total number of registered users',
        COUNT(*),
        'users',
        'users'
    FROM users
    ON CONFLICT (metric_key) DO UPDATE SET
        previous_value = dashboard_metrics.metric_value,
        metric_value = EXCLUDED.metric_value,
        change_percentage = CASE
            WHEN dashboard_metrics.metric_value > 0 THEN
                ((EXCLUDED.metric_value - dashboard_metrics.metric_value) / dashboard_metrics.metric_value * 100)
            ELSE 0
        END,
        trend = CASE
            WHEN EXCLUDED.metric_value > dashboard_metrics.metric_value THEN 'up'
            WHEN EXCLUDED.metric_value < dashboard_metrics.metric_value THEN 'down'
            ELSE 'stable'
        END,
        last_calculated_at = v_now,
        updated_at = v_now;

    -- Total chapters
    INSERT INTO dashboard_metrics (
        metric_key, metric_name, metric_description,
        metric_value, metric_unit, metric_category
    )
    SELECT
        'total_chapters',
        'Total Chapters',
        'Total number of chapters created',
        COUNT(*),
        'chapters',
        'content'
    FROM chapters
    ON CONFLICT (metric_key) DO UPDATE SET
        previous_value = dashboard_metrics.metric_value,
        metric_value = EXCLUDED.metric_value,
        change_percentage = CASE
            WHEN dashboard_metrics.metric_value > 0 THEN
                ((EXCLUDED.metric_value - dashboard_metrics.metric_value) / dashboard_metrics.metric_value * 100)
            ELSE 0
        END,
        trend = CASE
            WHEN EXCLUDED.metric_value > dashboard_metrics.metric_value THEN 'up'
            WHEN EXCLUDED.metric_value < dashboard_metrics.metric_value THEN 'down'
            ELSE 'stable'
        END,
        last_calculated_at = v_now,
        updated_at = v_now;

    -- Total PDFs
    INSERT INTO dashboard_metrics (
        metric_key, metric_name, metric_description,
        metric_value, metric_unit, metric_category
    )
    SELECT
        'total_pdfs',
        'Total PDFs',
        'Total number of uploaded PDFs',
        COUNT(*),
        'pdfs',
        'content'
    FROM pdfs
    ON CONFLICT (metric_key) DO UPDATE SET
        previous_value = dashboard_metrics.metric_value,
        metric_value = EXCLUDED.metric_value,
        change_percentage = CASE
            WHEN dashboard_metrics.metric_value > 0 THEN
                ((EXCLUDED.metric_value - dashboard_metrics.metric_value) / dashboard_metrics.metric_value * 100)
            ELSE 0
        END,
        trend = CASE
            WHEN EXCLUDED.metric_value > dashboard_metrics.metric_value THEN 'up'
            WHEN EXCLUDED.metric_value < dashboard_metrics.metric_value THEN 'down'
            ELSE 'stable'
        END,
        last_calculated_at = v_now,
        updated_at = v_now;

    -- Active users (24h)
    INSERT INTO dashboard_metrics (
        metric_key, metric_name, metric_description,
        metric_value, metric_unit, metric_category
    )
    SELECT
        'active_users_24h',
        'Active Users (24h)',
        'Unique users active in last 24 hours',
        COUNT(DISTINCT user_id),
        'users',
        'activity'
    FROM analytics_events
    WHERE created_at >= v_24h_ago
    ON CONFLICT (metric_key) DO UPDATE SET
        previous_value = dashboard_metrics.metric_value,
        metric_value = EXCLUDED.metric_value,
        change_percentage = CASE
            WHEN dashboard_metrics.metric_value > 0 THEN
                ((EXCLUDED.metric_value - dashboard_metrics.metric_value) / dashboard_metrics.metric_value * 100)
            ELSE 0
        END,
        trend = CASE
            WHEN EXCLUDED.metric_value > dashboard_metrics.metric_value THEN 'up'
            WHEN EXCLUDED.metric_value < dashboard_metrics.metric_value THEN 'down'
            ELSE 'stable'
        END,
        last_calculated_at = v_now,
        updated_at = v_now;

    -- Total searches (7d)
    INSERT INTO dashboard_metrics (
        metric_key, metric_name, metric_description,
        metric_value, metric_unit, metric_category
    )
    SELECT
        'total_searches_7d',
        'Total Searches (7d)',
        'Total searches in last 7 days',
        COUNT(*),
        'searches',
        'activity'
    FROM analytics_events
    WHERE created_at >= v_7d_ago
        AND event_type = 'search'
    ON CONFLICT (metric_key) DO UPDATE SET
        previous_value = dashboard_metrics.metric_value,
        metric_value = EXCLUDED.metric_value,
        change_percentage = CASE
            WHEN dashboard_metrics.metric_value > 0 THEN
                ((EXCLUDED.metric_value - dashboard_metrics.metric_value) / dashboard_metrics.metric_value * 100)
            ELSE 0
        END,
        trend = CASE
            WHEN EXCLUDED.metric_value > dashboard_metrics.metric_value THEN 'up'
            WHEN EXCLUDED.metric_value < dashboard_metrics.metric_value THEN 'down'
            ELSE 'stable'
        END,
        last_calculated_at = v_now,
        updated_at = v_now;

    -- Total exports (30d)
    INSERT INTO dashboard_metrics (
        metric_key, metric_name, metric_description,
        metric_value, metric_unit, metric_category
    )
    SELECT
        'total_exports_30d',
        'Total Exports (30d)',
        'Total exports in last 30 days',
        COUNT(*),
        'exports',
        'activity'
    FROM analytics_events
    WHERE created_at >= v_30d_ago
        AND event_type = 'export'
    ON CONFLICT (metric_key) DO UPDATE SET
        previous_value = dashboard_metrics.metric_value,
        metric_value = EXCLUDED.metric_value,
        change_percentage = CASE
            WHEN dashboard_metrics.metric_value > 0 THEN
                ((EXCLUDED.metric_value - dashboard_metrics.metric_value) / dashboard_metrics.metric_value * 100)
            ELSE 0
        END,
        trend = CASE
            WHEN EXCLUDED.metric_value > dashboard_metrics.metric_value THEN 'up'
            WHEN EXCLUDED.metric_value < dashboard_metrics.metric_value THEN 'down'
            ELSE 'stable'
        END,
        last_calculated_at = v_now,
        updated_at = v_now;

END;
$$ LANGUAGE plpgsql;


-- ==========================================
-- Analytics Views
-- Convenient views for common analytics queries
-- ==========================================

-- Daily activity summary
CREATE OR REPLACE VIEW daily_activity_summary AS
SELECT
    DATE(created_at) as activity_date,
    event_category,
    COUNT(*) as event_count,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(DISTINCT session_id) as unique_sessions,
    AVG(duration_ms) as avg_duration_ms,
    SUM(CASE WHEN success = TRUE THEN 1 ELSE 0 END) as success_count,
    SUM(CASE WHEN success = FALSE THEN 1 ELSE 0 END) as error_count
FROM analytics_events
GROUP BY DATE(created_at), event_category
ORDER BY activity_date DESC, event_category;


-- User activity summary
CREATE OR REPLACE VIEW user_activity_summary AS
SELECT
    u.id as user_id,
    u.email,
    u.full_name,
    COUNT(ae.id) as total_events,
    COUNT(DISTINCT DATE(ae.created_at)) as active_days,
    MAX(ae.created_at) as last_activity,
    MIN(ae.created_at) as first_activity,
    COUNT(CASE WHEN ae.event_type = 'search' THEN 1 END) as search_count,
    COUNT(CASE WHEN ae.event_type = 'export' THEN 1 END) as export_count,
    COUNT(CASE WHEN ae.event_type = 'chapter_create' THEN 1 END) as chapters_created,
    COUNT(CASE WHEN ae.event_type = 'pdf_upload' THEN 1 END) as pdfs_uploaded
FROM users u
LEFT JOIN analytics_events ae ON u.id = ae.user_id
GROUP BY u.id, u.email, u.full_name
ORDER BY total_events DESC;


-- Popular content view
CREATE OR REPLACE VIEW popular_content AS
SELECT
    resource_type,
    resource_id,
    COUNT(*) as view_count,
    COUNT(DISTINCT user_id) as unique_viewers,
    MAX(created_at) as last_viewed
FROM analytics_events
WHERE event_type IN ('view', 'read', 'open')
    AND resource_type IS NOT NULL
    AND resource_id IS NOT NULL
GROUP BY resource_type, resource_id
ORDER BY view_count DESC;


-- System health metrics view
CREATE OR REPLACE VIEW system_health_metrics AS
SELECT
    DATE(created_at) as metric_date,
    COUNT(*) as total_events,
    AVG(duration_ms) as avg_response_time_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95_response_time_ms,
    SUM(CASE WHEN success = TRUE THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as success_rate,
    COUNT(DISTINCT user_id) as active_users,
    COUNT(DISTINCT session_id) as total_sessions
FROM analytics_events
WHERE duration_ms IS NOT NULL
GROUP BY DATE(created_at)
ORDER BY metric_date DESC;


-- ==========================================
-- Initial Data & Comments
-- ==========================================

COMMENT ON TABLE analytics_events IS 'Tracks all user actions and system events for comprehensive analytics';
COMMENT ON TABLE analytics_aggregates IS 'Pre-computed daily, weekly, and monthly metric summaries for fast dashboard queries';
COMMENT ON TABLE dashboard_metrics IS 'Real-time metrics displayed on admin dashboard with trend indicators';

COMMENT ON COLUMN analytics_events.event_type IS 'Specific action: search, export, chapter_create, pdf_upload, login, etc.';
COMMENT ON COLUMN analytics_events.event_category IS 'Broad category: user, content, system, search, export';
COMMENT ON COLUMN analytics_events.duration_ms IS 'Operation duration in milliseconds for performance tracking';
COMMENT ON COLUMN analytics_events.metadata IS 'Flexible JSONB field for event-specific details';

COMMENT ON COLUMN dashboard_metrics.change_percentage IS 'Percentage change from previous value for trend analysis';
COMMENT ON COLUMN dashboard_metrics.trend IS 'Trend indicator: up, down, stable, or unknown';

-- Insert initial dashboard metric records (will be populated by update function)
INSERT INTO dashboard_metrics (metric_key, metric_name, metric_description, metric_value, metric_unit, metric_category)
VALUES
    ('total_users', 'Total Users', 'Total number of registered users', 0, 'users', 'users'),
    ('total_chapters', 'Total Chapters', 'Total number of chapters created', 0, 'chapters', 'content'),
    ('total_pdfs', 'Total PDFs', 'Total number of uploaded PDFs', 0, 'pdfs', 'content'),
    ('active_users_24h', 'Active Users (24h)', 'Unique users active in last 24 hours', 0, 'users', 'activity'),
    ('total_searches_7d', 'Total Searches (7d)', 'Total searches in last 7 days', 0, 'searches', 'activity'),
    ('total_exports_30d', 'Total Exports (30d)', 'Total exports in last 30 days', 0, 'exports', 'activity')
ON CONFLICT (metric_key) DO NOTHING;

-- ==========================================
-- Phase 12 Migration Complete
-- ==========================================
