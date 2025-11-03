-- Migration 013: AI Provider Metrics Tracking
-- Adds comprehensive tracking for AI provider performance and accuracy

-- ============================================================================
-- 1. Add Missing Columns to Images Table
-- ============================================================================

-- These columns are referenced in code but missing from schema
ALTER TABLE images
ADD COLUMN IF NOT EXISTS ai_provider VARCHAR(50),
ADD COLUMN IF NOT EXISTS analysis_cost_usd DECIMAL(10, 6) DEFAULT 0.0;

COMMENT ON COLUMN images.ai_provider IS 'AI provider used for analysis (claude, gpt4o, gemini)';
COMMENT ON COLUMN images.analysis_cost_usd IS 'Cost of AI analysis in USD';

-- ============================================================================
-- 2. Create AI Provider Metrics Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS ai_provider_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Provider Information
    provider VARCHAR(50) NOT NULL,  -- 'claude', 'gpt4o', 'gemini'
    model VARCHAR(100) NOT NULL,    -- 'claude-sonnet-4', 'gpt-4o', 'gemini-2.0-flash'
    task_type VARCHAR(100) NOT NULL, -- 'image_analysis', 'fact_checking', 'chapter_generation', etc.

    -- Request Details
    chapter_id UUID REFERENCES chapters(id) ON DELETE CASCADE,
    image_id UUID REFERENCES images(id) ON DELETE CASCADE,
    request_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Performance Metrics
    success BOOLEAN NOT NULL,
    response_time_ms INTEGER,  -- Time to get response from AI provider

    -- Quality Metrics
    quality_score DECIMAL(4, 3),  -- 0.0 to 1.0 (from AI analysis)
    confidence_score DECIMAL(4, 3),  -- 0.0 to 1.0 (AI confidence)

    -- Token & Cost Tracking
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    cost_usd DECIMAL(10, 6),

    -- Output Quality
    json_parse_success BOOLEAN,  -- Did JSON parsing succeed?
    output_validated BOOLEAN,    -- Did output pass schema validation?

    -- Error Tracking
    error_type VARCHAR(100),     -- 'rate_limit', 'timeout', 'invalid_response', 'json_parse_error', etc.
    error_message TEXT,

    -- Fallback Tracking
    was_fallback BOOLEAN DEFAULT FALSE,  -- Was this a fallback provider?
    original_provider VARCHAR(50),       -- Original provider that failed (if fallback)
    fallback_reason VARCHAR(200),        -- Why fallback was triggered

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 3. Create Indexes for Fast Aggregation
-- ============================================================================

-- Index for provider × task aggregation (most common query)
CREATE INDEX IF NOT EXISTS idx_provider_metrics_provider_task
ON ai_provider_metrics(provider, task_type, success);

-- Index for chapter-level drill-down
CREATE INDEX IF NOT EXISTS idx_provider_metrics_chapter
ON ai_provider_metrics(chapter_id, provider);

-- Index for image-level drill-down
CREATE INDEX IF NOT EXISTS idx_provider_metrics_image
ON ai_provider_metrics(image_id, provider);

-- Index for time-based queries
CREATE INDEX IF NOT EXISTS idx_provider_metrics_timestamp
ON ai_provider_metrics(request_timestamp DESC);

-- Index for quality analysis
CREATE INDEX IF NOT EXISTS idx_provider_metrics_quality
ON ai_provider_metrics(provider, task_type, quality_score)
WHERE quality_score IS NOT NULL;

-- Index for error analysis
CREATE INDEX IF NOT EXISTS idx_provider_metrics_errors
ON ai_provider_metrics(provider, error_type)
WHERE error_type IS NOT NULL;

-- ============================================================================
-- 4. Add Table Comments
-- ============================================================================

COMMENT ON TABLE ai_provider_metrics IS 'Tracks AI provider performance, quality, and costs for all AI tasks';

COMMENT ON COLUMN ai_provider_metrics.provider IS 'AI provider name (claude, gpt4o, gemini)';
COMMENT ON COLUMN ai_provider_metrics.model IS 'Specific model version used';
COMMENT ON COLUMN ai_provider_metrics.task_type IS 'Type of AI task performed';
COMMENT ON COLUMN ai_provider_metrics.success IS 'Whether the request succeeded';
COMMENT ON COLUMN ai_provider_metrics.response_time_ms IS 'Time taken for AI response in milliseconds';
COMMENT ON COLUMN ai_provider_metrics.quality_score IS 'Quality score from AI analysis (0.0-1.0)';
COMMENT ON COLUMN ai_provider_metrics.confidence_score IS 'AI confidence in the result (0.0-1.0)';
COMMENT ON COLUMN ai_provider_metrics.json_parse_success IS 'Whether JSON response was successfully parsed';
COMMENT ON COLUMN ai_provider_metrics.output_validated IS 'Whether output passed schema validation';
COMMENT ON COLUMN ai_provider_metrics.was_fallback IS 'True if this was a fallback provider after primary failed';
COMMENT ON COLUMN ai_provider_metrics.fallback_reason IS 'Reason for using fallback provider';

-- ============================================================================
-- 5. Create Aggregation Views for Common Queries
-- ============================================================================

-- View: Provider Performance Summary
CREATE OR REPLACE VIEW v_provider_performance_summary AS
SELECT
    provider,
    task_type,
    COUNT(*) as total_requests,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_requests,
    ROUND(SUM(CASE WHEN success THEN 1 ELSE 0 END)::numeric / COUNT(*)::numeric * 100, 2) as success_rate_pct,
    ROUND(AVG(quality_score), 3) as avg_quality_score,
    ROUND(AVG(confidence_score), 3) as avg_confidence_score,
    ROUND(AVG(response_time_ms), 0) as avg_response_time_ms,
    ROUND(AVG(cost_usd), 6) as avg_cost_usd,
    ROUND(SUM(cost_usd), 4) as total_cost_usd,
    SUM(CASE WHEN json_parse_success THEN 1 ELSE 0 END) as json_parse_successes,
    ROUND(SUM(CASE WHEN json_parse_success THEN 1 ELSE 0 END)::numeric / COUNT(*)::numeric * 100, 2) as json_parse_success_rate_pct
FROM ai_provider_metrics
GROUP BY provider, task_type;

COMMENT ON VIEW v_provider_performance_summary IS 'Aggregated provider performance metrics by provider and task type';

-- View: Provider Cost Efficiency (Quality per Dollar)
CREATE OR REPLACE VIEW v_provider_cost_efficiency AS
SELECT
    provider,
    task_type,
    COUNT(*) as total_requests,
    ROUND(AVG(quality_score), 3) as avg_quality,
    ROUND(AVG(cost_usd), 6) as avg_cost,
    ROUND(AVG(quality_score) / NULLIF(AVG(cost_usd), 0), 2) as quality_per_dollar
FROM ai_provider_metrics
WHERE success = TRUE AND quality_score IS NOT NULL AND cost_usd > 0
GROUP BY provider, task_type;

COMMENT ON VIEW v_provider_cost_efficiency IS 'Provider cost efficiency: quality score per dollar spent';

-- View: Recent Provider Activity (Last 24 hours)
CREATE OR REPLACE VIEW v_provider_recent_activity AS
SELECT
    provider,
    task_type,
    success,
    quality_score,
    cost_usd,
    response_time_ms,
    error_type,
    request_timestamp
FROM ai_provider_metrics
WHERE request_timestamp >= NOW() - INTERVAL '24 hours'
ORDER BY request_timestamp DESC;

COMMENT ON VIEW v_provider_recent_activity IS 'Recent provider activity for real-time monitoring';

-- ============================================================================
-- 6. Create Function: Record Provider Metric
-- ============================================================================

CREATE OR REPLACE FUNCTION record_provider_metric(
    p_provider VARCHAR,
    p_model VARCHAR,
    p_task_type VARCHAR,
    p_chapter_id UUID DEFAULT NULL,
    p_image_id UUID DEFAULT NULL,
    p_success BOOLEAN DEFAULT TRUE,
    p_response_time_ms INTEGER DEFAULT NULL,
    p_quality_score DECIMAL DEFAULT NULL,
    p_confidence_score DECIMAL DEFAULT NULL,
    p_input_tokens INTEGER DEFAULT NULL,
    p_output_tokens INTEGER DEFAULT NULL,
    p_total_tokens INTEGER DEFAULT NULL,
    p_cost_usd DECIMAL DEFAULT NULL,
    p_json_parse_success BOOLEAN DEFAULT NULL,
    p_output_validated BOOLEAN DEFAULT NULL,
    p_error_type VARCHAR DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL,
    p_was_fallback BOOLEAN DEFAULT FALSE,
    p_original_provider VARCHAR DEFAULT NULL,
    p_fallback_reason VARCHAR DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_metric_id UUID;
BEGIN
    INSERT INTO ai_provider_metrics (
        provider, model, task_type,
        chapter_id, image_id,
        success, response_time_ms,
        quality_score, confidence_score,
        input_tokens, output_tokens, total_tokens, cost_usd,
        json_parse_success, output_validated,
        error_type, error_message,
        was_fallback, original_provider, fallback_reason
    ) VALUES (
        p_provider, p_model, p_task_type,
        p_chapter_id, p_image_id,
        p_success, p_response_time_ms,
        p_quality_score, p_confidence_score,
        p_input_tokens, p_output_tokens, p_total_tokens, p_cost_usd,
        p_json_parse_success, p_output_validated,
        p_error_type, p_error_message,
        p_was_fallback, p_original_provider, p_fallback_reason
    )
    RETURNING id INTO v_metric_id;

    RETURN v_metric_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION record_provider_metric IS 'Convenience function to record AI provider metrics';

-- ============================================================================
-- 7. Grant Permissions
-- ============================================================================

GRANT SELECT, INSERT ON ai_provider_metrics TO nsurg_admin;
GRANT SELECT ON v_provider_performance_summary TO nsurg_admin;
GRANT SELECT ON v_provider_cost_efficiency TO nsurg_admin;
GRANT SELECT ON v_provider_recent_activity TO nsurg_admin;
GRANT EXECUTE ON FUNCTION record_provider_metric TO nsurg_admin;

-- ============================================================================
-- Migration Complete
-- ============================================================================

-- Verify tables exist
DO $$
BEGIN
    RAISE NOTICE 'Migration 013 complete:';
    RAISE NOTICE '  - Added ai_provider and analysis_cost_usd columns to images';
    RAISE NOTICE '  - Created ai_provider_metrics table';
    RAISE NOTICE '  - Created 6 indexes for fast aggregation';
    RAISE NOTICE '  - Created 3 aggregation views';
    RAISE NOTICE '  - Created record_provider_metric() function';
    RAISE NOTICE '';
    RAISE NOTICE 'Ready to track provider performance!';
END $$;
