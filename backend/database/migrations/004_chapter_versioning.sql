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

    -- Metadata about this version
    metadata JSONB DEFAULT '{}',
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
