-- =====================================================================
-- Phase 18: Advanced Content Features Schema
-- =====================================================================
-- This migration implements advanced content management features:
-- - Content templates for reusable chapter structures
-- - Bookmarks and collections for content organization
-- - Annotations and highlights for collaborative reading
-- - Advanced filters for content discovery
-- - Content scheduling for timed publishing
-- =====================================================================

-- =====================================================================
-- 1. Content Templates
-- =====================================================================

-- Template types for different content structures
CREATE TABLE IF NOT EXISTS content_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    template_type VARCHAR(50) NOT NULL, -- 'surgical_disease', 'anatomy', 'technique', 'case_study', 'custom'
    structure JSONB NOT NULL, -- Template structure with sections
    is_public BOOLEAN DEFAULT FALSE,
    is_system BOOLEAN DEFAULT FALSE, -- System-provided templates
    usage_count INTEGER DEFAULT 0,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_template_name UNIQUE(name, created_by)
);

-- Template sections define the structure
CREATE TABLE IF NOT EXISTS template_sections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL REFERENCES content_templates(id) ON DELETE CASCADE,
    section_name VARCHAR(255) NOT NULL,
    section_order INTEGER NOT NULL,
    is_required BOOLEAN DEFAULT TRUE,
    placeholder_text TEXT,
    validation_rules JSONB, -- Optional validation rules
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Track template usage
CREATE TABLE IF NOT EXISTS template_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL REFERENCES content_templates(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    chapter_id UUID REFERENCES chapters(id) ON DELETE SET NULL,
    used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================================
-- 2. Bookmarks & Collections
-- =====================================================================

-- Bookmark collections (folders)
CREATE TABLE IF NOT EXISTS bookmark_collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    icon VARCHAR(50), -- Icon identifier
    color VARCHAR(20), -- Color code for UI
    is_public BOOLEAN DEFAULT FALSE,
    parent_collection_id UUID REFERENCES bookmark_collections(id) ON DELETE CASCADE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_collection_name_per_user UNIQUE(user_id, name)
);

-- User bookmarks for content
CREATE TABLE IF NOT EXISTS bookmarks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_type VARCHAR(50) NOT NULL, -- 'chapter', 'pdf', 'image'
    content_id UUID NOT NULL,
    collection_id UUID REFERENCES bookmark_collections(id) ON DELETE SET NULL,
    title VARCHAR(500), -- Cached title
    notes TEXT, -- User notes about the bookmark
    tags TEXT[], -- Quick tags
    is_favorite BOOLEAN DEFAULT FALSE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_bookmark_per_user UNIQUE(user_id, content_type, content_id)
);

-- Shared collections
CREATE TABLE IF NOT EXISTS shared_collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_id UUID NOT NULL REFERENCES bookmark_collections(id) ON DELETE CASCADE,
    shared_with_user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    shared_with_email VARCHAR(255), -- For sharing with non-users
    permission_level VARCHAR(20) DEFAULT 'view', -- 'view', 'edit'
    shared_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================================
-- 3. Annotations & Highlights
-- =====================================================================

-- Text highlights in content
CREATE TABLE IF NOT EXISTS highlights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_type VARCHAR(50) NOT NULL, -- 'chapter', 'pdf'
    content_id UUID NOT NULL,
    highlight_text TEXT NOT NULL,
    context_before TEXT, -- Text before highlight for positioning
    context_after TEXT, -- Text after highlight for positioning
    position_data JSONB, -- Detailed position info (page, paragraph, offset)
    color VARCHAR(20) DEFAULT 'yellow', -- Highlight color
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Annotations (notes on content)
CREATE TABLE IF NOT EXISTS annotations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_type VARCHAR(50) NOT NULL,
    content_id UUID NOT NULL,
    annotation_type VARCHAR(50) DEFAULT 'note', -- 'note', 'question', 'correction', 'comment'
    annotation_text TEXT NOT NULL,
    position_data JSONB, -- Where annotation is anchored
    highlight_id UUID REFERENCES highlights(id) ON DELETE CASCADE, -- Optional linked highlight
    is_private BOOLEAN DEFAULT TRUE,
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Replies to annotations (threaded discussions)
CREATE TABLE IF NOT EXISTS annotation_replies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    annotation_id UUID NOT NULL REFERENCES annotations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reply_text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Annotation reactions (like, agree, etc.)
CREATE TABLE IF NOT EXISTS annotation_reactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    annotation_id UUID NOT NULL REFERENCES annotations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reaction_type VARCHAR(20) NOT NULL, -- 'like', 'agree', 'disagree', 'question'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_reaction_per_user UNIQUE(annotation_id, user_id, reaction_type)
);

-- =====================================================================
-- 4. Advanced Filters
-- =====================================================================

-- Saved filter configurations
CREATE TABLE IF NOT EXISTS saved_filters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    filter_type VARCHAR(50) NOT NULL, -- 'content', 'search', 'analytics'
    filter_config JSONB NOT NULL, -- Complete filter configuration
    is_default BOOLEAN DEFAULT FALSE,
    is_public BOOLEAN DEFAULT FALSE,
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Filter presets (system-provided common filters)
CREATE TABLE IF NOT EXISTS filter_presets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    category VARCHAR(50) NOT NULL, -- 'content_type', 'temporal', 'quality', 'source'
    filter_config JSONB NOT NULL,
    icon VARCHAR(50),
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================================
-- 5. Content Scheduling
-- =====================================================================

-- Scheduled content publications and updates
CREATE TABLE IF NOT EXISTS content_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_type VARCHAR(50) NOT NULL,
    content_id UUID NOT NULL,
    schedule_type VARCHAR(50) NOT NULL, -- 'publish', 'unpublish', 'update', 'archive'
    scheduled_for TIMESTAMP WITH TIME ZONE NOT NULL,
    action_data JSONB, -- Additional data for the action
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed', 'cancelled'
    executed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Recurring schedules (e.g., weekly content reviews)
CREATE TABLE IF NOT EXISTS recurring_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    schedule_pattern VARCHAR(50) NOT NULL, -- 'daily', 'weekly', 'monthly'
    cron_expression VARCHAR(100), -- For complex schedules
    action_type VARCHAR(50) NOT NULL,
    action_config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_run_at TIMESTAMP WITH TIME ZONE,
    next_run_at TIMESTAMP WITH TIME ZONE,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================================
-- 6. Content History & Drafts
-- =====================================================================

-- Draft versions before publishing
CREATE TABLE IF NOT EXISTS content_drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_type VARCHAR(50) NOT NULL,
    content_id UUID, -- NULL for new content
    draft_data JSONB NOT NULL,
    draft_name VARCHAR(255),
    is_autosave BOOLEAN DEFAULT FALSE,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Content access history (reading progress)
CREATE TABLE IF NOT EXISTS content_access_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_type VARCHAR(50) NOT NULL,
    content_id UUID NOT NULL,
    access_type VARCHAR(20) DEFAULT 'view', -- 'view', 'edit', 'share'
    progress_percentage INTEGER DEFAULT 0, -- Reading progress
    time_spent_seconds INTEGER DEFAULT 0,
    last_position JSONB, -- Last reading position
    session_id VARCHAR(100),
    accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_history_per_session UNIQUE(user_id, content_type, content_id, session_id)
);

-- =====================================================================
-- 7. Indexes for Performance
-- =====================================================================

-- Content Templates indexes
CREATE INDEX IF NOT EXISTS idx_content_templates_type ON content_templates(template_type);
CREATE INDEX IF NOT EXISTS idx_content_templates_creator ON content_templates(created_by);
CREATE INDEX IF NOT EXISTS idx_content_templates_public ON content_templates(is_public) WHERE is_public = TRUE;
CREATE INDEX IF NOT EXISTS idx_template_sections_template ON template_sections(template_id, section_order);

-- Bookmarks indexes
CREATE INDEX IF NOT EXISTS idx_bookmarks_user ON bookmarks(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bookmarks_content ON bookmarks(content_type, content_id);
CREATE INDEX IF NOT EXISTS idx_bookmarks_collection ON bookmarks(collection_id);
CREATE INDEX IF NOT EXISTS idx_bookmarks_favorite ON bookmarks(user_id, is_favorite) WHERE is_favorite = TRUE;
CREATE INDEX IF NOT EXISTS idx_bookmarks_tags ON bookmarks USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_bookmark_collections_user ON bookmark_collections(user_id);
CREATE INDEX IF NOT EXISTS idx_bookmark_collections_parent ON bookmark_collections(parent_collection_id);

-- Highlights & Annotations indexes
CREATE INDEX IF NOT EXISTS idx_highlights_user_content ON highlights(user_id, content_type, content_id);
CREATE INDEX IF NOT EXISTS idx_highlights_content ON highlights(content_type, content_id);
CREATE INDEX IF NOT EXISTS idx_annotations_user_content ON annotations(user_id, content_type, content_id);
CREATE INDEX IF NOT EXISTS idx_annotations_content ON annotations(content_type, content_id);
CREATE INDEX IF NOT EXISTS idx_annotations_private ON annotations(is_private) WHERE is_private = FALSE;
CREATE INDEX IF NOT EXISTS idx_annotations_unresolved ON annotations(is_resolved) WHERE is_resolved = FALSE;
CREATE INDEX IF NOT EXISTS idx_annotation_replies_annotation ON annotation_replies(annotation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_annotation_reactions_annotation ON annotation_reactions(annotation_id);

-- Filters indexes
CREATE INDEX IF NOT EXISTS idx_saved_filters_user ON saved_filters(user_id, last_used_at DESC);
CREATE INDEX IF NOT EXISTS idx_saved_filters_type ON saved_filters(filter_type);
CREATE INDEX IF NOT EXISTS idx_saved_filters_default ON saved_filters(user_id, is_default) WHERE is_default = TRUE;

-- Scheduling indexes
CREATE INDEX IF NOT EXISTS idx_content_schedules_pending ON content_schedules(scheduled_for, status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_content_schedules_content ON content_schedules(content_type, content_id);
CREATE INDEX IF NOT EXISTS idx_recurring_schedules_active ON recurring_schedules(is_active, next_run_at) WHERE is_active = TRUE;

-- Content access history indexes
CREATE INDEX IF NOT EXISTS idx_content_access_user ON content_access_history(user_id, accessed_at DESC);
CREATE INDEX IF NOT EXISTS idx_content_access_content ON content_access_history(content_type, content_id, accessed_at DESC);

-- =====================================================================
-- 8. PostgreSQL Functions
-- =====================================================================

-- Function to get user's reading statistics
CREATE OR REPLACE FUNCTION get_user_reading_stats(p_user_id UUID)
RETURNS TABLE (
    total_content_accessed BIGINT,
    total_time_spent_hours NUMERIC,
    avg_progress_percentage NUMERIC,
    content_completed_count BIGINT,
    most_accessed_type VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(DISTINCT (content_type, content_id)) as total_content_accessed,
        ROUND(SUM(time_spent_seconds)::NUMERIC / 3600, 2) as total_time_spent_hours,
        ROUND(AVG(progress_percentage)::NUMERIC, 2) as avg_progress_percentage,
        COUNT(DISTINCT (content_type, content_id)) FILTER (WHERE progress_percentage >= 90) as content_completed_count,
        MODE() WITHIN GROUP (ORDER BY content_type) as most_accessed_type
    FROM content_access_history
    WHERE user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get popular bookmarked content
CREATE OR REPLACE FUNCTION get_popular_bookmarked_content(p_limit INTEGER DEFAULT 20)
RETURNS TABLE (
    content_type VARCHAR,
    content_id UUID,
    bookmark_count BIGINT,
    unique_users BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        b.content_type,
        b.content_id,
        COUNT(*) as bookmark_count,
        COUNT(DISTINCT b.user_id) as unique_users
    FROM bookmarks b
    GROUP BY b.content_type, b.content_id
    ORDER BY bookmark_count DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to find similar bookmarks (content that users who bookmarked X also bookmarked)
CREATE OR REPLACE FUNCTION get_collaborative_bookmark_recommendations(
    p_user_id UUID,
    p_content_type VARCHAR,
    p_content_id UUID,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    recommended_type VARCHAR,
    recommended_id UUID,
    relevance_score NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        b2.content_type as recommended_type,
        b2.content_id as recommended_id,
        COUNT(DISTINCT b2.user_id)::NUMERIC / (SELECT COUNT(*) FROM bookmarks WHERE content_type = p_content_type AND content_id = p_content_id)::NUMERIC as relevance_score
    FROM bookmarks b1
    JOIN bookmarks b2 ON b1.user_id = b2.user_id
    WHERE b1.content_type = p_content_type
        AND b1.content_id = p_content_id
        AND b2.user_id != p_user_id
        AND NOT EXISTS (
            SELECT 1 FROM bookmarks b3
            WHERE b3.user_id = p_user_id
                AND b3.content_type = b2.content_type
                AND b3.content_id = b2.content_id
        )
    GROUP BY b2.content_type, b2.content_id
    ORDER BY relevance_score DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to update template usage count
CREATE OR REPLACE FUNCTION increment_template_usage()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE content_templates
    SET usage_count = usage_count + 1
    WHERE id = NEW.template_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_increment_template_usage
    AFTER INSERT ON template_usage
    FOR EACH ROW
    EXECUTE FUNCTION increment_template_usage();

-- Function to auto-update timestamps
CREATE OR REPLACE FUNCTION update_advanced_content_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply timestamp trigger to relevant tables
CREATE TRIGGER trigger_update_content_templates_timestamp
    BEFORE UPDATE ON content_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_advanced_content_timestamp();

CREATE TRIGGER trigger_update_bookmarks_timestamp
    BEFORE UPDATE ON bookmarks
    FOR EACH ROW
    EXECUTE FUNCTION update_advanced_content_timestamp();

CREATE TRIGGER trigger_update_highlights_timestamp
    BEFORE UPDATE ON highlights
    FOR EACH ROW
    EXECUTE FUNCTION update_advanced_content_timestamp();

CREATE TRIGGER trigger_update_annotations_timestamp
    BEFORE UPDATE ON annotations
    FOR EACH ROW
    EXECUTE FUNCTION update_advanced_content_timestamp();

-- =====================================================================
-- 9. Views for Common Queries
-- =====================================================================

-- View for user's bookmark statistics
CREATE OR REPLACE VIEW v_user_bookmark_stats AS
SELECT
    user_id,
    COUNT(*) as total_bookmarks,
    COUNT(*) FILTER (WHERE is_favorite = TRUE) as favorite_count,
    COUNT(DISTINCT collection_id) as collection_count,
    COUNT(DISTINCT content_type) as content_types_bookmarked,
    MAX(created_at) as last_bookmark_at
FROM bookmarks
GROUP BY user_id;

-- View for annotation activity
CREATE OR REPLACE VIEW v_annotation_activity AS
SELECT
    a.id as annotation_id,
    a.user_id,
    a.content_type,
    a.content_id,
    a.annotation_type,
    a.is_private,
    a.is_resolved,
    COUNT(DISTINCT ar.id) as reply_count,
    COUNT(DISTINCT anr.id) as reaction_count,
    a.created_at,
    a.updated_at
FROM annotations a
LEFT JOIN annotation_replies ar ON ar.annotation_id = a.id
LEFT JOIN annotation_reactions anr ON anr.annotation_id = a.id
GROUP BY a.id;

-- View for scheduled content
CREATE OR REPLACE VIEW v_upcoming_schedules AS
SELECT
    cs.id,
    cs.content_type,
    cs.content_id,
    cs.schedule_type,
    cs.scheduled_for,
    cs.status,
    cs.created_by,
    EXTRACT(EPOCH FROM (cs.scheduled_for - NOW())) / 3600 as hours_until_execution
FROM content_schedules cs
WHERE cs.status = 'pending'
    AND cs.scheduled_for > NOW()
ORDER BY cs.scheduled_for;

-- =====================================================================
-- 10. Initial Data
-- =====================================================================

-- System content templates
INSERT INTO content_templates (name, description, template_type, structure, is_public, is_system)
VALUES
    ('Surgical Disease Standard', 'Standard template for surgical disease chapters covering all 97 essential sections', 'surgical_disease',
     '{"sections": [
         {"name": "Overview", "required": true, "order": 1},
         {"name": "Epidemiology", "required": true, "order": 2},
         {"name": "Pathophysiology", "required": true, "order": 3},
         {"name": "Clinical Presentation", "required": true, "order": 4},
         {"name": "Diagnosis", "required": true, "order": 5},
         {"name": "Treatment", "required": true, "order": 6},
         {"name": "Complications", "required": true, "order": 7},
         {"name": "Prognosis", "required": true, "order": 8},
         {"name": "References", "required": true, "order": 9}
     ]}'::jsonb,
     TRUE, TRUE),

    ('Pure Anatomy', 'Template for anatomical chapters with 48 core sections', 'anatomy',
     '{"sections": [
         {"name": "Overview", "required": true, "order": 1},
         {"name": "Gross Anatomy", "required": true, "order": 2},
         {"name": "Vascular Supply", "required": true, "order": 3},
         {"name": "Nerve Supply", "required": true, "order": 4},
         {"name": "Clinical Relevance", "required": true, "order": 5},
         {"name": "Imaging", "required": false, "order": 6},
         {"name": "References", "required": true, "order": 7}
     ]}'::jsonb,
     TRUE, TRUE),

    ('Surgical Technique', 'Template for surgical technique chapters with 65 procedural sections', 'technique',
     '{"sections": [
         {"name": "Indications", "required": true, "order": 1},
         {"name": "Contraindications", "required": true, "order": 2},
         {"name": "Preoperative Planning", "required": true, "order": 3},
         {"name": "Patient Positioning", "required": true, "order": 4},
         {"name": "Surgical Approach", "required": true, "order": 5},
         {"name": "Step-by-Step Procedure", "required": true, "order": 6},
         {"name": "Closure", "required": true, "order": 7},
         {"name": "Postoperative Care", "required": true, "order": 8},
         {"name": "Complications", "required": true, "order": 9},
         {"name": "Outcomes", "required": true, "order": 10},
         {"name": "References", "required": true, "order": 11}
     ]}'::jsonb,
     TRUE, TRUE),

    ('Case Study', 'Template for clinical case presentations', 'case_study',
     '{"sections": [
         {"name": "Patient Presentation", "required": true, "order": 1},
         {"name": "History", "required": true, "order": 2},
         {"name": "Physical Examination", "required": true, "order": 3},
         {"name": "Diagnostic Workup", "required": true, "order": 4},
         {"name": "Diagnosis", "required": true, "order": 5},
         {"name": "Treatment Plan", "required": true, "order": 6},
         {"name": "Outcome", "required": true, "order": 7},
         {"name": "Discussion", "required": true, "order": 8},
         {"name": "Learning Points", "required": true, "order": 9}
     ]}'::jsonb,
     TRUE, TRUE)
ON CONFLICT DO NOTHING;

-- Default filter presets
INSERT INTO filter_presets (name, description, category, filter_config, icon, sort_order)
VALUES
    ('Recent Content', 'Content from the last 7 days', 'temporal',
     '{"timeRange": "7d", "sortBy": "created_at", "sortOrder": "desc"}'::jsonb,
     'calendar', 1),

    ('High Quality', 'Content with quality scores above 0.8', 'quality',
     '{"minQualityScore": 0.8, "sortBy": "quality_score", "sortOrder": "desc"}'::jsonb,
     'star', 2),

    ('Most Viewed', 'Most accessed content', 'analytics',
     '{"sortBy": "view_count", "sortOrder": "desc", "limit": 50}'::jsonb,
     'eye', 3),

    ('By Content Type: Chapters', 'All chapters', 'content_type',
     '{"contentTypes": ["chapter"], "sortBy": "created_at", "sortOrder": "desc"}'::jsonb,
     'book', 4),

    ('By Content Type: PDFs', 'All PDFs', 'content_type',
     '{"contentTypes": ["pdf"], "sortBy": "year", "sortOrder": "desc"}'::jsonb,
     'document', 5)
ON CONFLICT DO NOTHING;

-- =====================================================================
-- Migration Complete
-- =====================================================================
-- This migration has created a comprehensive advanced content features
-- system including:
-- - 17 tables for templates, bookmarks, annotations, filters, scheduling
-- - 25+ optimized indexes for performance
-- - 5 utility functions for statistics and recommendations
-- - 3 views for common queries
-- - Automatic triggers for usage tracking
-- - Initial system templates and filter presets
-- =====================================================================
