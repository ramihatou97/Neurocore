-- Migration 004: Comprehensive Feature Activation
-- Description: Enable all features from Phases 5-18 (Chapter Versioning, Tasks, Export, Analytics, AI Features, Performance, Content Features)
-- Date: 2025-10-28
-- Phase: 19 - Fix & Stabilize All Features
-- Dependencies: Requires migrations 001, 002, 003 to be applied first

-- This migration consolidates the schemas from the original migrations 004-009 into one comprehensive upgrade
-- Original migrations: 004 (versioning), 005 (tasks + export), 006 (analytics), 007 (AI), 008 (performance), 009 (content)

SET client_min_messages = WARNING;


-- ==================== PHASE 9: CHAPTER VERSIONING ====================
-- From original migration 004_chapter_versioning.sql

-- Migration: Chapter Versioning & History
-- Description: Add version tracking for chapters with full history and diff support
-- Date: 2025-10-27

-- ==================== Chapter Versions Table ====================

-- Create chapter_versions table to store historical snapshots
CREATE TABLE IF NOT EXISTS chapter_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,

    -- Content snapshot at this version
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,

    -- Metadata about this version (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    version_metadata JSONB DEFAULT '{}',
    word_count INTEGER,
    character_count INTEGER,
    change_size INTEGER DEFAULT 0,  -- Net characters added/removed from previous version

    -- Attribution and tracking
    changed_by UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    change_description TEXT,  -- Optional description of what changed
    change_type VARCHAR(50) DEFAULT 'update',  -- update, rollback, major_edit, etc.

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT unique_chapter_version UNIQUE (chapter_id, version_number),
    CONSTRAINT positive_version_number CHECK (version_number > 0)
);

-- ==================== Indexes for Performance ====================

-- Primary lookup: get versions for a chapter
CREATE INDEX idx_chapter_versions_chapter_id ON chapter_versions(chapter_id);

-- Get versions in chronological order
CREATE INDEX idx_chapter_versions_chapter_created ON chapter_versions(chapter_id, created_at DESC);

-- Fast version number lookup
CREATE INDEX idx_chapter_versions_chapter_version ON chapter_versions(chapter_id, version_number DESC);

-- Track changes by user
CREATE INDEX idx_chapter_versions_changed_by ON chapter_versions(changed_by);

-- Find versions by change type
CREATE INDEX idx_chapter_versions_change_type ON chapter_versions(change_type);

-- Full-text search on change descriptions
CREATE INDEX idx_chapter_versions_change_desc_gin ON chapter_versions
USING gin(to_tsvector('english', COALESCE(change_description, '')));

-- ==================== Helper Functions ====================

-- Function to get the latest version number for a chapter
CREATE OR REPLACE FUNCTION get_next_version_number(chapter_uuid UUID)
RETURNS INTEGER AS $$
DECLARE
    max_version INTEGER;
BEGIN
    SELECT COALESCE(MAX(version_number), 0) INTO max_version
    FROM chapter_versions
    WHERE chapter_id = chapter_uuid;

    RETURN max_version + 1;
END;
$$ LANGUAGE plpgsql;

-- Function to get version count for a chapter
CREATE OR REPLACE FUNCTION get_version_count(chapter_uuid UUID)
RETURNS INTEGER AS $$
DECLARE
    version_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO version_count
    FROM chapter_versions
    WHERE chapter_id = chapter_uuid;

    RETURN version_count;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate storage used by versions
CREATE OR REPLACE FUNCTION calculate_version_storage(chapter_uuid UUID)
RETURNS BIGINT AS $$
DECLARE
    total_size BIGINT;
BEGIN
    SELECT COALESCE(SUM(
        LENGTH(title) +
        LENGTH(content) +
        COALESCE(LENGTH(summary), 0) +
        COALESCE(LENGTH(change_description), 0)
    ), 0) INTO total_size
    FROM chapter_versions
    WHERE chapter_id = chapter_uuid;

    RETURN total_size;
END;
$$ LANGUAGE plpgsql;

-- ==================== Trigger for Automatic Versioning ====================

-- Function to create version snapshot before chapter update
CREATE OR REPLACE FUNCTION create_chapter_version_snapshot()
RETURNS TRIGGER AS $$
DECLARE
    next_version INTEGER;
    old_word_count INTEGER;
    new_word_count INTEGER;
    size_change INTEGER;
BEGIN
    -- Only create version if content actually changed
    IF OLD.content IS DISTINCT FROM NEW.content OR
       OLD.title IS DISTINCT FROM NEW.title OR
       OLD.summary IS DISTINCT FROM NEW.summary THEN

        -- Get next version number
        next_version := get_next_version_number(OLD.id);

        -- Calculate word counts
        old_word_count := array_length(string_to_array(OLD.content, ' '), 1);
        new_word_count := array_length(string_to_array(NEW.content, ' '), 1);
        size_change := LENGTH(NEW.content) - LENGTH(OLD.content);

        -- Create version snapshot of OLD content
        INSERT INTO chapter_versions (
            chapter_id,
            version_number,
            title,
            content,
            summary,
            word_count,
            character_count,
            change_size,
            changed_by,
            change_description,
            change_type,
            metadata
        ) VALUES (
            OLD.id,
            next_version,
            OLD.title,
            OLD.content,
            OLD.summary,
            old_word_count,
            LENGTH(OLD.content),
            size_change,
            NEW.author_id,  -- Assume author_id is the user making the change
            'Automatic version snapshot',
            'update',
            jsonb_build_object(
                'generation_status', OLD.generation_status,
                'stage', OLD.stage,
                'updated_at', OLD.updated_at
            )
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger (initially disabled, can be enabled via application)
CREATE TRIGGER trigger_chapter_version_snapshot
    BEFORE UPDATE ON chapters
    FOR EACH ROW
    EXECUTE FUNCTION create_chapter_version_snapshot();

-- Disable trigger by default (application will handle versioning explicitly)
ALTER TABLE chapters DISABLE TRIGGER trigger_chapter_version_snapshot;

-- ==================== Version Statistics View ====================

-- View for chapter version statistics
CREATE OR REPLACE VIEW chapter_version_stats AS
SELECT
    c.id AS chapter_id,
    c.title AS chapter_title,
    COUNT(cv.id) AS total_versions,
    MIN(cv.created_at) AS first_version_date,
    MAX(cv.created_at) AS last_version_date,
    COUNT(DISTINCT cv.changed_by) AS unique_contributors,
    SUM(LENGTH(cv.content)) AS total_content_size,
    AVG(cv.word_count) AS avg_word_count,
    MAX(cv.version_number) AS latest_version_number
FROM chapters c
LEFT JOIN chapter_versions cv ON c.id = cv.chapter_id
GROUP BY c.id, c.title;

-- ==================== Version Comparison Function ====================

-- Function to get diff statistics between two versions
CREATE OR REPLACE FUNCTION get_version_diff_stats(
    chapter_uuid UUID,
    version_from INTEGER,
    version_to INTEGER
)
RETURNS TABLE (
    title_changed BOOLEAN,
    content_size_change INTEGER,
    word_count_change INTEGER,
    time_between INTERVAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        v_from.title != v_to.title AS title_changed,
        LENGTH(v_to.content) - LENGTH(v_from.content) AS content_size_change,
        v_to.word_count - v_from.word_count AS word_count_change,
        v_to.created_at - v_from.created_at AS time_between
    FROM chapter_versions v_from
    CROSS JOIN chapter_versions v_to
    WHERE v_from.chapter_id = chapter_uuid
      AND v_from.version_number = version_from
      AND v_to.chapter_id = chapter_uuid
      AND v_to.version_number = version_to;
END;
$$ LANGUAGE plpgsql;

-- ==================== Cleanup Functions ====================

-- Function to archive old versions (soft delete)
CREATE OR REPLACE FUNCTION archive_old_versions(
    chapter_uuid UUID,
    keep_count INTEGER DEFAULT 10
)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Keep most recent N versions, delete older ones
    WITH versions_to_delete AS (
        SELECT id
        FROM chapter_versions
        WHERE chapter_id = chapter_uuid
        ORDER BY version_number DESC
        OFFSET keep_count
    )
    DELETE FROM chapter_versions
    WHERE id IN (SELECT id FROM versions_to_delete);

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup versions older than specified days
CREATE OR REPLACE FUNCTION cleanup_versions_by_age(
    days_old INTEGER DEFAULT 365,
    keep_minimum INTEGER DEFAULT 5
)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
BEGIN
    -- For each chapter, keep minimum versions but delete old ones
    WITH old_versions AS (
        SELECT cv.id
        FROM chapter_versions cv
        WHERE cv.created_at < NOW() - INTERVAL '1 day' * days_old
          AND cv.version_number <= (
              SELECT MAX(version_number) - keep_minimum
              FROM chapter_versions
              WHERE chapter_id = cv.chapter_id
          )
    )
    DELETE FROM chapter_versions
    WHERE id IN (SELECT id FROM old_versions);

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ==================== Initial Version Creation ====================

-- Create initial version for existing chapters (version 1)
-- This will be the baseline for all future versions
DO $$
DECLARE
    chapter_record RECORD;
    word_count_val INTEGER;
BEGIN
    FOR chapter_record IN
        SELECT c.id, c.title, c.content, c.summary, c.author_id, c.created_at
        FROM chapters c
        WHERE NOT EXISTS (
            SELECT 1 FROM chapter_versions cv
            WHERE cv.chapter_id = c.id
        )
    LOOP
        word_count_val := array_length(
            string_to_array(chapter_record.content, ' '), 1
        );

        INSERT INTO chapter_versions (
            chapter_id,
            version_number,
            title,
            content,
            summary,
            word_count,
            character_count,
            change_size,
            changed_by,
            change_description,
            change_type,
            created_at
        ) VALUES (
            chapter_record.id,
            1,
            chapter_record.title,
            chapter_record.content,
            chapter_record.summary,
            word_count_val,
            LENGTH(chapter_record.content),
            0,
            chapter_record.author_id,
            'Initial version',
            'initial',
            chapter_record.created_at
        );
    END LOOP;
END $$;

-- ==================== Performance Monitoring ====================

-- View for version activity monitoring
CREATE OR REPLACE VIEW version_activity_summary AS
SELECT
    DATE_TRUNC('day', created_at) AS activity_date,
    COUNT(*) AS versions_created,
    COUNT(DISTINCT chapter_id) AS chapters_modified,
    COUNT(DISTINCT changed_by) AS active_users,
    SUM(change_size) AS total_content_change,
    AVG(word_count) AS avg_words_per_version
FROM chapter_versions
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY activity_date DESC;

-- ==================== Usage Examples ====================

/*
-- Example 1: Get all versions for a chapter
SELECT version_number, title, changed_by, change_description, created_at
FROM chapter_versions
WHERE chapter_id = :chapter_id
ORDER BY version_number DESC;

-- Example 2: Get specific version
SELECT *
FROM chapter_versions
WHERE chapter_id = :chapter_id AND version_number = :version_number;

-- Example 3: Compare two versions
SELECT * FROM get_version_diff_stats(
    :chapter_id::UUID,
    1,  -- from version
    5   -- to version
);

-- Example 4: Get version statistics for a chapter
SELECT * FROM chapter_version_stats WHERE chapter_id = :chapter_id;

-- Example 5: Find chapters with most versions
SELECT chapter_title, total_versions, unique_contributors
FROM chapter_version_stats
ORDER BY total_versions DESC
LIMIT 10;

-- Example 6: Archive old versions (keep 10 most recent)
SELECT archive_old_versions(:chapter_id::UUID, 10);

-- Example 7: Cleanup versions older than 1 year (keep minimum 5)
SELECT cleanup_versions_by_age(365, 5);

-- Example 8: Get recent version activity
SELECT * FROM version_activity_summary;
*/

-- ==================== Rollback Script ====================

/*
-- To rollback this migration:

DROP VIEW IF EXISTS version_activity_summary;
DROP VIEW IF EXISTS chapter_version_stats;

DROP TRIGGER IF EXISTS trigger_chapter_version_snapshot ON chapters;

DROP FUNCTION IF EXISTS create_chapter_version_snapshot();
DROP FUNCTION IF EXISTS cleanup_versions_by_age(INTEGER, INTEGER);
DROP FUNCTION IF EXISTS archive_old_versions(UUID, INTEGER);
DROP FUNCTION IF EXISTS get_version_diff_stats(UUID, INTEGER, INTEGER);
DROP FUNCTION IF EXISTS calculate_version_storage(UUID);
DROP FUNCTION IF EXISTS get_version_count(UUID);
DROP FUNCTION IF EXISTS get_next_version_number(UUID);

DROP TABLE IF EXISTS chapter_versions;
*/

-- ==================== PHASE 5: BACKGROUND TASKS ====================
-- From original migration 005_add_task_tracking.sql

-- Migration: Add task tracking table for background jobs
-- Purpose: Track Celery task status and progress for PDF processing

-- Create tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id VARCHAR(255) UNIQUE NOT NULL,  -- Celery task ID
    task_type VARCHAR(100) NOT NULL,       -- Type: pdf_processing, image_analysis, etc.
    status VARCHAR(50) NOT NULL,           -- queued, processing, completed, failed
    progress INTEGER DEFAULT 0,            -- Progress percentage (0-100)
    total_steps INTEGER DEFAULT 0,         -- Total number of steps
    current_step INTEGER DEFAULT 0,        -- Current step number
    entity_id UUID,                        -- Related entity (PDF ID, Chapter ID, etc.)
    entity_type VARCHAR(50),               -- Entity type: pdf, chapter, image
    result JSONB,                          -- Task result data
    error TEXT,                            -- Error message if failed
    started_at TIMESTAMP,                  -- Task start time
    completed_at TIMESTAMP,                -- Task completion time
    created_by UUID REFERENCES users(id),  -- User who initiated the task
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT chk_status CHECK (status IN (
        'queued', 'processing', 'completed', 'failed', 'cancelled'
    )),
    CONSTRAINT chk_progress CHECK (progress >= 0 AND progress <= 100)
);

-- Create indexes for task queries
CREATE INDEX IF NOT EXISTS idx_tasks_task_id ON tasks(task_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_entity ON tasks(entity_id, entity_type);
CREATE INDEX IF NOT EXISTS idx_tasks_created_by ON tasks(created_by);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at DESC);

-- Create trigger for updated_at
CREATE OR REPLACE FUNCTION update_tasks_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_tasks_updated_at();

-- Add processing timestamps to PDFs table (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pdfs' AND column_name = 'processing_started_at'
    ) THEN
        ALTER TABLE pdfs ADD COLUMN processing_started_at NUMERIC;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pdfs' AND column_name = 'processing_completed_at'
    ) THEN
        ALTER TABLE pdfs ADD COLUMN processing_completed_at NUMERIC;
    END IF;
END $$;

-- Add analysis metadata to images table (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'images' AND column_name = 'analysis_metadata'
    ) THEN
        ALTER TABLE images ADD COLUMN analysis_metadata JSONB;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'images' AND column_name = 'analysis_confidence'
    ) THEN
        ALTER TABLE images ADD COLUMN analysis_confidence NUMERIC DEFAULT 0.0;
    END IF;
END $$;

-- Add citations to PDFs table (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pdfs' AND column_name = 'citations'
    ) THEN
        ALTER TABLE pdfs ADD COLUMN citations JSONB;
    END IF;
END $$;

-- Create Task model in SQLAlchemy (documentation)
COMMENT ON TABLE tasks IS 'Background task tracking for Celery jobs';
COMMENT ON COLUMN tasks.task_id IS 'Celery task UUID for status lookups';
COMMENT ON COLUMN tasks.progress IS 'Task completion percentage (0-100)';
COMMENT ON COLUMN tasks.entity_id IS 'ID of related entity (PDF, Chapter, etc.)';
COMMENT ON COLUMN tasks.result IS 'JSON result data from completed task';

-- ==================== PHASE 11: EXPORT & CITATION MANAGEMENT ====================
-- From original migration 005_export_templates.sql

-- Migration: Export Templates and Citation Styles
-- Description: Add support for export templates, citation styles, and export history
-- Date: 2025-10-27

-- ==================== Citation Styles Table ====================

CREATE TABLE IF NOT EXISTS citation_styles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    format_template JSONB NOT NULL,
    -- Example format_template:
    -- {
    --   "in_text": "{authors} ({year})",
    --   "bibliography": "{authors}. ({year}). {title}. {journal}, {volume}({issue}), {pages}. {doi}",
    --   "author_separator": ", ",
    --   "et_al_threshold": 3
    -- }

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_citation_style_name UNIQUE (name)
);

-- Create index
CREATE INDEX idx_citation_styles_active ON citation_styles(is_active);

-- ==================== Export Templates Table ====================

CREATE TABLE IF NOT EXISTS export_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    format VARCHAR(20) NOT NULL, -- pdf, docx, html

    -- Template content
    template_content TEXT NOT NULL,
    -- For HTML: Jinja2 template
    -- For PDF: HTML template that will be converted
    -- For DOCX: Template structure in JSON

    -- Styling
    styles JSONB DEFAULT '{}',
    -- {
    --   "font_family": "Arial",
    --   "font_size": 12,
    --   "line_height": 1.5,
    --   "margin_top": 1,
    --   "margin_bottom": 1,
    --   "margin_left": 1,
    --   "margin_right": 1,
    --   "header_footer": true,
    --   "page_numbers": true,
    --   "toc": false
    -- }

    -- Template variables
    required_variables JSONB DEFAULT '[]',
    -- ["title", "author", "date", "content", "citations"]

    -- Ownership
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    is_default BOOLEAN DEFAULT FALSE,
    is_public BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_export_format CHECK (format IN ('pdf', 'docx', 'html'))
);

-- Create indexes
CREATE INDEX idx_export_templates_format ON export_templates(format);
CREATE INDEX idx_export_templates_public ON export_templates(is_public);
CREATE INDEX idx_export_templates_creator ON export_templates(created_by);

-- ==================== Export History Table ====================

CREATE TABLE IF NOT EXISTS export_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- References
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    template_id UUID REFERENCES export_templates(id) ON DELETE SET NULL,
    citation_style_id UUID REFERENCES citation_styles(id) ON DELETE SET NULL,

    -- Export details
    export_format VARCHAR(20) NOT NULL,
    file_name VARCHAR(500) NOT NULL,
    file_size BIGINT,
    file_path TEXT, -- Storage path if files are kept

    -- Options used
    export_options JSONB DEFAULT '{}',
    -- {
    --   "include_toc": true,
    --   "include_images": true,
    --   "include_citations": true,
    --   "page_size": "A4",
    --   "orientation": "portrait"
    -- }

    -- Status
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT valid_export_status CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);

-- Create indexes
CREATE INDEX idx_export_history_chapter ON export_history(chapter_id);
CREATE INDEX idx_export_history_user ON export_history(user_id);
CREATE INDEX idx_export_history_status ON export_history(status);
CREATE INDEX idx_export_history_created ON export_history(created_at DESC);

-- ==================== Default Citation Styles ====================

-- APA 7th Edition
INSERT INTO citation_styles (name, display_name, description, format_template) VALUES
('apa', 'APA 7th Edition', 'American Psychological Association 7th edition style',
'{
  "in_text": {
    "one_author": "({author}, {year})",
    "two_authors": "({author1} & {author2}, {year})",
    "multiple": "({first_author} et al., {year})"
  },
  "bibliography": "{authors}. ({year}). {title}. {journal}, {volume}({issue}), {pages}. https://doi.org/{doi}",
  "author_separator": ", & ",
  "et_al_threshold": 3,
  "sort_by": "author"
}'::jsonb);

-- MLA 9th Edition
INSERT INTO citation_styles (name, display_name, description, format_template) VALUES
('mla', 'MLA 9th Edition', 'Modern Language Association 9th edition style',
'{
  "in_text": {
    "one_author": "({author} {page})",
    "two_authors": "({author1} and {author2} {page})",
    "multiple": "({first_author} et al. {page})"
  },
  "bibliography": "{authors}. \"{title}.\" {journal}, vol. {volume}, no. {issue}, {year}, pp. {pages}.",
  "author_separator": ", and ",
  "et_al_threshold": 3,
  "sort_by": "author"
}'::jsonb);

-- Chicago 17th Edition
INSERT INTO citation_styles (name, display_name, description, format_template) VALUES
('chicago', 'Chicago 17th Edition', 'Chicago Manual of Style 17th edition',
'{
  "in_text": {
    "one_author": "({author} {year}, {page})",
    "two_authors": "({author1} and {author2} {year}, {page})",
    "multiple": "({first_author} et al. {year}, {page})"
  },
  "bibliography": "{authors}. {year}. \"{title}.\" {journal} {volume} ({issue}): {pages}. https://doi.org/{doi}.",
  "author_separator": ", and ",
  "et_al_threshold": 4,
  "sort_by": "author"
}'::jsonb);

-- Vancouver
INSERT INTO citation_styles (name, display_name, description, format_template) VALUES
('vancouver', 'Vancouver', 'Vancouver citation style for medical journals',
'{
  "in_text": {
    "format": "[{number}]"
  },
  "bibliography": "{authors}. {title}. {journal}. {year};{volume}({issue}):{pages}. doi:{doi}",
  "author_separator": ", ",
  "et_al_threshold": 6,
  "sort_by": "appearance",
  "numbered": true
}'::jsonb);

-- ==================== Default Export Templates ====================

-- Default PDF Template
INSERT INTO export_templates (name, description, format, template_content, styles, required_variables, is_default, is_public)
VALUES (
    'Academic Paper (PDF)',
    'Professional academic paper template with header, footer, and citations',
    'pdf',
    '<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
    <style>
        @page {
            size: {{ page_size|default("A4") }};
            margin: {{ margin_top|default("2.5cm") }} {{ margin_right|default("2.5cm") }}
                    {{ margin_bottom|default("2.5cm") }} {{ margin_left|default("2.5cm") }};
            @top-right {
                content: "{{ title|truncate(50) }}";
                font-size: 10pt;
                color: #666;
            }
            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 10pt;
            }
        }
        body {
            font-family: {{ font_family|default("Times New Roman") }}, serif;
            font-size: {{ font_size|default("12pt") }};
            line-height: {{ line_height|default("1.5") }};
            color: #333;
        }
        h1 {
            font-size: 20pt;
            text-align: center;
            margin-bottom: 0.5em;
        }
        .metadata {
            text-align: center;
            margin-bottom: 2em;
            color: #666;
        }
        .content {
            text-align: justify;
        }
        .citation {
            margin-left: 2em;
            text-indent: -2em;
            margin-bottom: 0.5em;
        }
    </style>
</head>
<body>
    <h1>{{ title }}</h1>
    <div class="metadata">
        <p>{{ author_name }}<br>{{ date }}</p>
    </div>
    <div class="content">
        {{ content|safe }}
    </div>
    {% if bibliography %}
    <h2>References</h2>
    <div class="bibliography">
        {% for citation in bibliography %}
        <div class="citation">{{ citation|safe }}</div>
        {% endfor %}
    </div>
    {% endif %}
</body>
</html>',
    '{"page_size": "A4", "font_family": "Times New Roman", "font_size": "12pt", "line_height": "1.5", "margins": {"top": "2.5cm", "bottom": "2.5cm", "left": "2.5cm", "right": "2.5cm"}}',
    '["title", "author_name", "date", "content"]',
    true,
    true
);

-- Default HTML Template
INSERT INTO export_templates (name, description, format, template_content, styles, required_variables, is_default, is_public)
VALUES (
    'Web Article (HTML)',
    'Clean web article template with responsive design',
    'html',
    '<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            font-family: {{ font_family|default("Georgia") }}, serif;
            font-size: {{ font_size|default("16px") }};
            line-height: {{ line_height|default("1.6") }};
            color: #333;
        }
        h1 {
            font-size: 2.5em;
            margin-bottom: 0.2em;
        }
        .metadata {
            color: #666;
            margin-bottom: 2em;
            padding-bottom: 1em;
            border-bottom: 1px solid #ddd;
        }
        .content img {
            max-width: 100%;
            height: auto;
        }
        .bibliography {
            margin-top: 3em;
            padding-top: 2em;
            border-top: 2px solid #333;
        }
        .citation {
            margin-bottom: 1em;
        }
    </style>
</head>
<body>
    <article>
        <header>
            <h1>{{ title }}</h1>
            <div class="metadata">
                <p>By {{ author_name }} | {{ date }}</p>
            </div>
        </header>
        <div class="content">
            {{ content|safe }}
        </div>
        {% if bibliography %}
        <section class="bibliography">
            <h2>References</h2>
            {% for citation in bibliography %}
            <div class="citation">{{ citation|safe }}</div>
            {% endfor %}
        </section>
        {% endif %}
    </article>
</body>
</html>',
    '{"font_family": "Georgia", "font_size": "16px", "line_height": "1.6", "max_width": "800px"}',
    '["title", "author_name", "date", "content"]',
    true,
    true
);

-- ==================== Helper Functions ====================

-- Function to get default template for format
CREATE OR REPLACE FUNCTION get_default_template(export_format VARCHAR)
RETURNS UUID AS $$
DECLARE
    template_id UUID;
BEGIN
    SELECT id INTO template_id
    FROM export_templates
    WHERE format = export_format
      AND is_default = true
      AND is_public = true
    LIMIT 1;

    RETURN template_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get export statistics for user
CREATE OR REPLACE FUNCTION get_user_export_stats(user_uuid UUID)
RETURNS TABLE (
    total_exports BIGINT,
    pdf_exports BIGINT,
    docx_exports BIGINT,
    html_exports BIGINT,
    last_export_date TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) AS total_exports,
        COUNT(*) FILTER (WHERE export_format = 'pdf') AS pdf_exports,
        COUNT(*) FILTER (WHERE export_format = 'docx') AS docx_exports,
        COUNT(*) FILTER (WHERE export_format = 'html') AS html_exports,
        MAX(created_at) AS last_export_date
    FROM export_history
    WHERE user_id = user_uuid
      AND status = 'completed';
END;
$$ LANGUAGE plpgsql;

-- ==================== Indexes for Performance ====================

-- Composite index for user export history
CREATE INDEX idx_export_history_user_status_date
ON export_history(user_id, status, created_at DESC);

-- Index for finding popular templates
CREATE INDEX idx_export_history_template
ON export_history(template_id)
WHERE status = 'completed';

-- ==================== Rollback Script ====================

/*
-- To rollback this migration:

DROP FUNCTION IF EXISTS get_user_export_stats(UUID);
DROP FUNCTION IF EXISTS get_default_template(VARCHAR);

DROP TABLE IF EXISTS export_history;
DROP TABLE IF EXISTS export_templates;
DROP TABLE IF EXISTS citation_styles;
*/

-- ==================== PHASE 12: ANALYTICS & INSIGHTS DASHBOARD ====================
-- From original migration 006_analytics_schema.sql

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

-- ==================== PHASE 14: AI-POWERED FEATURES ENHANCEMENT ====================
-- From original migration 007_ai_features_schema.sql

-- ==========================================
-- Phase 14: AI-Powered Features Enhancement
-- AI Features Schema Migration
-- ==========================================

-- Tags Table
-- Store auto-generated and manual tags for content organization
CREATE TABLE IF NOT EXISTS tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    category VARCHAR(50) DEFAULT 'general',
    color VARCHAR(7) DEFAULT '#1976d2',
    is_auto_generated BOOLEAN DEFAULT FALSE,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for tags
CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
CREATE INDEX IF NOT EXISTS idx_tags_slug ON tags(slug);
CREATE INDEX IF NOT EXISTS idx_tags_category ON tags(category);
CREATE INDEX IF NOT EXISTS idx_tags_auto_generated ON tags(is_auto_generated);
CREATE INDEX IF NOT EXISTS idx_tags_usage_count ON tags(usage_count DESC);


-- ==========================================
-- Chapter Tags (Many-to-Many)
-- ==========================================

CREATE TABLE IF NOT EXISTS chapter_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    confidence_score NUMERIC(5, 4),
    is_auto_tagged BOOLEAN DEFAULT FALSE,
    tagged_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_chapter_tag UNIQUE (chapter_id, tag_id)
);

-- Indexes for chapter_tags
CREATE INDEX IF NOT EXISTS idx_chapter_tags_chapter ON chapter_tags(chapter_id);
CREATE INDEX IF NOT EXISTS idx_chapter_tags_tag ON chapter_tags(tag_id);
CREATE INDEX IF NOT EXISTS idx_chapter_tags_confidence ON chapter_tags(confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_chapter_tags_auto ON chapter_tags(is_auto_tagged);


-- ==========================================
-- PDF Tags (Many-to-Many)
-- ==========================================

CREATE TABLE IF NOT EXISTS pdf_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pdf_id UUID NOT NULL REFERENCES pdfs(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    confidence_score NUMERIC(5, 4),
    is_auto_tagged BOOLEAN DEFAULT FALSE,
    tagged_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_pdf_tag UNIQUE (pdf_id, tag_id)
);

-- Indexes for pdf_tags
CREATE INDEX IF NOT EXISTS idx_pdf_tags_pdf ON pdf_tags(pdf_id);
CREATE INDEX IF NOT EXISTS idx_pdf_tags_tag ON pdf_tags(tag_id);
CREATE INDEX IF NOT EXISTS idx_pdf_tags_confidence ON pdf_tags(confidence_score DESC);


-- ==========================================
-- Content Recommendations
-- ==========================================

CREATE TABLE IF NOT EXISTS recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL,
    source_id UUID NOT NULL,
    recommended_type VARCHAR(50) NOT NULL,
    recommended_id UUID NOT NULL,
    recommendation_reason VARCHAR(200),
    relevance_score NUMERIC(5, 4) NOT NULL,
    algorithm VARCHAR(100) DEFAULT 'collaborative_filtering',
    metadata JSONB DEFAULT '{}',
    was_clicked BOOLEAN DEFAULT FALSE,
    was_helpful BOOLEAN,
    feedback_text TEXT,
    clicked_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for recommendations
CREATE INDEX IF NOT EXISTS idx_recommendations_user ON recommendations(user_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_source ON recommendations(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_recommended ON recommendations(recommended_type, recommended_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_score ON recommendations(relevance_score DESC);
CREATE INDEX IF NOT EXISTS idx_recommendations_created ON recommendations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_recommendations_expires ON recommendations(expires_at);
CREATE INDEX IF NOT EXISTS idx_recommendations_clicked ON recommendations(was_clicked);


-- ==========================================
-- Content Summaries
-- ==========================================

CREATE TABLE IF NOT EXISTS content_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_type VARCHAR(50) NOT NULL,
    content_id UUID NOT NULL,
    summary_type VARCHAR(50) DEFAULT 'brief',
    summary_text TEXT NOT NULL,
    word_count INTEGER,
    key_points JSONB DEFAULT '[]',
    generated_by VARCHAR(100) DEFAULT 'gpt-4',
    generation_time_ms INTEGER,
    quality_score NUMERIC(3, 2),
    is_approved BOOLEAN DEFAULT FALSE,
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_content_summary UNIQUE (content_type, content_id, summary_type)
);

-- Indexes for content_summaries
CREATE INDEX IF NOT EXISTS idx_summaries_content ON content_summaries(content_type, content_id);
CREATE INDEX IF NOT EXISTS idx_summaries_type ON content_summaries(summary_type);
CREATE INDEX IF NOT EXISTS idx_summaries_approved ON content_summaries(is_approved);
CREATE INDEX IF NOT EXISTS idx_summaries_created ON content_summaries(created_at DESC);


-- ==========================================
-- Question Answering History
-- ==========================================

CREATE TABLE IF NOT EXISTS qa_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    context_documents JSONB DEFAULT '[]',
    confidence_score NUMERIC(5, 4),
    model_used VARCHAR(100) DEFAULT 'gpt-4',
    response_time_ms INTEGER,
    was_helpful BOOLEAN,
    feedback_text TEXT,
    session_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for qa_history
CREATE INDEX IF NOT EXISTS idx_qa_user ON qa_history(user_id);
CREATE INDEX IF NOT EXISTS idx_qa_session ON qa_history(session_id);
CREATE INDEX IF NOT EXISTS idx_qa_created ON qa_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_qa_helpful ON qa_history(was_helpful);
CREATE INDEX IF NOT EXISTS idx_qa_confidence ON qa_history(confidence_score DESC);

-- GIN index for context documents JSONB
CREATE INDEX IF NOT EXISTS idx_qa_context ON qa_history USING GIN (context_documents);


-- ==========================================
-- Similarity Cache
-- Store pre-computed similarity scores for performance
-- ==========================================

CREATE TABLE IF NOT EXISTS similarity_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_type_a VARCHAR(50) NOT NULL,
    content_id_a UUID NOT NULL,
    content_type_b VARCHAR(50) NOT NULL,
    content_id_b UUID NOT NULL,
    similarity_score NUMERIC(5, 4) NOT NULL,
    similarity_method VARCHAR(50) DEFAULT 'cosine',
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT unique_similarity_pair UNIQUE (content_type_a, content_id_a, content_type_b, content_id_b)
);

-- Indexes for similarity_cache
CREATE INDEX IF NOT EXISTS idx_similarity_content_a ON similarity_cache(content_type_a, content_id_a);
CREATE INDEX IF NOT EXISTS idx_similarity_content_b ON similarity_cache(content_type_b, content_id_b);
CREATE INDEX IF NOT EXISTS idx_similarity_score ON similarity_cache(similarity_score DESC);
CREATE INDEX IF NOT EXISTS idx_similarity_expires ON similarity_cache(expires_at);


-- ==========================================
-- User Interactions (for recommendation training)
-- ==========================================

CREATE TABLE IF NOT EXISTS user_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    interaction_type VARCHAR(50) NOT NULL,
    content_type VARCHAR(50) NOT NULL,
    content_id UUID NOT NULL,
    duration_seconds INTEGER,
    interaction_score NUMERIC(3, 2) DEFAULT 1.0,
    metadata JSONB DEFAULT '{}',
    session_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for user_interactions
CREATE INDEX IF NOT EXISTS idx_interactions_user ON user_interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_interactions_type ON user_interactions(interaction_type);
CREATE INDEX IF NOT EXISTS idx_interactions_content ON user_interactions(content_type, content_id);
CREATE INDEX IF NOT EXISTS idx_interactions_session ON user_interactions(session_id);
CREATE INDEX IF NOT EXISTS idx_interactions_created ON user_interactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_interactions_score ON user_interactions(interaction_score DESC);


-- ==========================================
-- PostgreSQL Functions
-- ==========================================

-- Function to get similar content by vector similarity
CREATE OR REPLACE FUNCTION get_similar_content(
    p_content_type VARCHAR,
    p_content_id UUID,
    p_limit INTEGER DEFAULT 10,
    p_min_similarity NUMERIC DEFAULT 0.7
)
RETURNS TABLE (
    similar_type VARCHAR,
    similar_id UUID,
    similarity_score NUMERIC
) AS $$
BEGIN
    IF p_content_type = 'chapter' THEN
        RETURN QUERY
        SELECT
            'chapter'::VARCHAR as similar_type,
            c.id as similar_id,
            (1 - (ce1.embedding <=> ce2.embedding))::NUMERIC(5,4) as similarity_score
        FROM chapters c
        CROSS JOIN LATERAL (
            SELECT embedding FROM chapter_embeddings WHERE chapter_id = p_content_id LIMIT 1
        ) ce1
        CROSS JOIN LATERAL (
            SELECT embedding FROM chapter_embeddings WHERE chapter_id = c.id LIMIT 1
        ) ce2
        WHERE c.id != p_content_id
            AND (1 - (ce1.embedding <=> ce2.embedding)) >= p_min_similarity
        ORDER BY similarity_score DESC
        LIMIT p_limit;
    ELSIF p_content_type = 'pdf' THEN
        RETURN QUERY
        SELECT
            'pdf'::VARCHAR as similar_type,
            p.id as similar_id,
            (1 - (pe1.embedding <=> pe2.embedding))::NUMERIC(5,4) as similarity_score
        FROM pdfs p
        CROSS JOIN LATERAL (
            SELECT embedding FROM pdf_embeddings WHERE pdf_id = p_content_id LIMIT 1
        ) pe1
        CROSS JOIN LATERAL (
            SELECT embedding FROM pdf_embeddings WHERE pdf_id = p.id LIMIT 1
        ) pe2
        WHERE p.id != p_content_id
            AND (1 - (pe1.embedding <=> pe2.embedding)) >= p_min_similarity
        ORDER BY similarity_score DESC
        LIMIT p_limit;
    END IF;
END;
$$ LANGUAGE plpgsql;


-- Function to update tag usage count
CREATE OR REPLACE FUNCTION update_tag_usage_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE tags SET usage_count = usage_count + 1 WHERE id = NEW.tag_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE tags SET usage_count = GREATEST(0, usage_count - 1) WHERE id = OLD.tag_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Triggers for tag usage count
CREATE TRIGGER chapter_tags_usage_count_trigger
    AFTER INSERT OR DELETE ON chapter_tags
    FOR EACH ROW EXECUTE FUNCTION update_tag_usage_count();

CREATE TRIGGER pdf_tags_usage_count_trigger
    AFTER INSERT OR DELETE ON pdf_tags
    FOR EACH ROW EXECUTE FUNCTION update_tag_usage_count();


-- Function to get popular tags
CREATE OR REPLACE FUNCTION get_popular_tags(p_limit INTEGER DEFAULT 20)
RETURNS TABLE (
    tag_id UUID,
    tag_name VARCHAR,
    tag_slug VARCHAR,
    usage_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.id,
        t.name,
        t.slug,
        t.usage_count
    FROM tags t
    WHERE t.usage_count > 0
    ORDER BY t.usage_count DESC, t.name ASC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;


-- Function to get recommended tags for content
CREATE OR REPLACE FUNCTION suggest_tags_for_content(
    p_content_text TEXT,
    p_limit INTEGER DEFAULT 5
)
RETURNS TABLE (
    tag_id UUID,
    tag_name VARCHAR,
    relevance_score NUMERIC
) AS $$
BEGIN
    -- Simple keyword matching for now
    -- In production, this would use ML/NLP
    RETURN QUERY
    SELECT
        t.id,
        t.name,
        (t.usage_count::NUMERIC / 100.0) as relevance_score
    FROM tags t
    WHERE p_content_text ILIKE '%' || t.name || '%'
    ORDER BY t.usage_count DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;


-- ==========================================
-- Views for AI Features
-- ==========================================

-- Popular content view (for recommendations)
CREATE OR REPLACE VIEW popular_content_view AS
SELECT
    'chapter' as content_type,
    c.id as content_id,
    c.title as content_title,
    COUNT(DISTINCT ui.user_id) as unique_viewers,
    COUNT(ui.id) as total_interactions,
    AVG(ui.interaction_score) as avg_interaction_score,
    MAX(ui.created_at) as last_interaction
FROM chapters c
LEFT JOIN user_interactions ui ON ui.content_type = 'chapter' AND ui.content_id = c.id
GROUP BY c.id, c.title
UNION ALL
SELECT
    'pdf' as content_type,
    p.id as content_id,
    p.title as content_title,
    COUNT(DISTINCT ui.user_id) as unique_viewers,
    COUNT(ui.id) as total_interactions,
    AVG(ui.interaction_score) as avg_interaction_score,
    MAX(ui.created_at) as last_interaction
FROM pdfs p
LEFT JOIN user_interactions ui ON ui.content_type = 'pdf' AND ui.content_id = p.id
GROUP BY p.id, p.title
ORDER BY total_interactions DESC;


-- Tag usage statistics view
CREATE OR REPLACE VIEW tag_statistics AS
SELECT
    t.id,
    t.name,
    t.category,
    t.usage_count,
    t.is_auto_generated,
    COUNT(DISTINCT ct.chapter_id) as chapter_count,
    COUNT(DISTINCT pt.pdf_id) as pdf_count,
    AVG(ct.confidence_score) as avg_confidence_chapter,
    AVG(pt.confidence_score) as avg_confidence_pdf
FROM tags t
LEFT JOIN chapter_tags ct ON ct.tag_id = t.id
LEFT JOIN pdf_tags pt ON pt.tag_id = t.id
GROUP BY t.id, t.name, t.category, t.usage_count, t.is_auto_generated
ORDER BY t.usage_count DESC;


-- User recommendation preferences
CREATE OR REPLACE VIEW user_recommendation_prefs AS
SELECT
    u.id as user_id,
    u.email,
    COUNT(DISTINCT r.id) as total_recommendations_received,
    COUNT(DISTINCT CASE WHEN r.was_clicked THEN r.id END) as clicked_count,
    COUNT(DISTINCT CASE WHEN r.was_helpful = TRUE THEN r.id END) as helpful_count,
    CASE
        WHEN COUNT(DISTINCT r.id) > 0
        THEN (COUNT(DISTINCT CASE WHEN r.was_clicked THEN r.id END)::NUMERIC / COUNT(DISTINCT r.id) * 100)
        ELSE 0
    END as click_through_rate,
    ARRAY_AGG(DISTINCT CASE WHEN r.was_clicked THEN r.recommended_type END) as preferred_content_types
FROM users u
LEFT JOIN recommendations r ON r.user_id = u.id
GROUP BY u.id, u.email;


-- ==========================================
-- Initial Data & Comments
-- ==========================================

COMMENT ON TABLE tags IS 'Tags for content organization and discovery';
COMMENT ON TABLE chapter_tags IS 'Many-to-many relationship between chapters and tags';
COMMENT ON TABLE pdf_tags IS 'Many-to-many relationship between PDFs and tags';
COMMENT ON TABLE recommendations IS 'Content recommendations with tracking and feedback';
COMMENT ON TABLE content_summaries IS 'AI-generated summaries for chapters and PDFs';
COMMENT ON TABLE qa_history IS 'Question-answering history for knowledge base Q&A';
COMMENT ON TABLE similarity_cache IS 'Pre-computed similarity scores for performance';
COMMENT ON TABLE user_interactions IS 'User interactions for recommendation training';

COMMENT ON COLUMN tags.is_auto_generated IS 'Whether tag was created by AI auto-tagging';
COMMENT ON COLUMN recommendations.algorithm IS 'Algorithm used: collaborative_filtering, content_based, hybrid';
COMMENT ON COLUMN content_summaries.summary_type IS 'Type: brief, detailed, technical, layman';
COMMENT ON COLUMN qa_history.confidence_score IS 'Model confidence in answer quality (0-1)';
COMMENT ON COLUMN similarity_cache.similarity_method IS 'Method: cosine, euclidean, jaccard';

-- Insert some default tags
INSERT INTO tags (name, slug, category, color) VALUES
    ('Neurosurgery', 'neurosurgery', 'medical', '#f44336'),
    ('Brain Tumor', 'brain-tumor', 'medical', '#e91e63'),
    ('Spine Surgery', 'spine-surgery', 'medical', '#9c27b0'),
    ('Trauma', 'trauma', 'medical', '#673ab7'),
    ('Pediatric', 'pediatric', 'medical', '#3f51b5'),
    ('Vascular', 'vascular', 'medical', '#2196f3'),
    ('Functional', 'functional', 'medical', '#03a9f4'),
    ('Research', 'research', 'general', '#00bcd4'),
    ('Clinical Trial', 'clinical-trial', 'general', '#009688'),
    ('Case Study', 'case-study', 'general', '#4caf50')
ON CONFLICT (name) DO NOTHING;

-- ==========================================
-- Phase 14 Migration Complete
-- ==========================================

-- ==================== PHASE 15: PERFORMANCE & OPTIMIZATION ====================
-- From original migration 008_performance_optimization.sql

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

-- ==================== PHASE 18: ADVANCED CONTENT FEATURES ====================
-- From original migration 009_advanced_content_features.sql

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
