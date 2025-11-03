-- Migration 009: Add Missing Chapters Table Columns
-- Date: 2025-11-01
-- Issue: Chapter model defines 6 columns that don't exist in database
-- Impact: Causes 500 errors when accessing fact-checking, formatting, or references features
--
-- Background:
-- The Chapter SQLAlchemy model (backend/database/models/chapter.py) defines several
-- columns that were never added to the database schema. This migration adds them.
--
-- Missing columns discovered during ultrathink analysis following delete chapter bug fix.

-- ==================== Add Missing JSONB Columns ====================

-- References column (citations from all sources)
ALTER TABLE chapters
ADD COLUMN IF NOT EXISTS references JSONB;

COMMENT ON COLUMN chapters.references IS 'Array of reference objects (citations from all sources)';

-- Stage 1: Input validation and topic analysis
ALTER TABLE chapters
ADD COLUMN IF NOT EXISTS stage_1_input JSONB;

COMMENT ON COLUMN chapters.stage_1_input IS 'Topic validation, chapter type analysis, confidence scores';

-- Stage 10: Fact-checking results
ALTER TABLE chapters
ADD COLUMN IF NOT EXISTS stage_10_fact_check JSONB;

COMMENT ON COLUMN chapters.stage_10_fact_check IS 'Fact-checking results: accuracy scores, verified claims, critical issues';

-- Stage 11: Formatting and validation
ALTER TABLE chapters
ADD COLUMN IF NOT EXISTS stage_11_formatting JSONB;

COMMENT ON COLUMN chapters.stage_11_formatting IS 'Markdown validation results, table of contents, formatting statistics, structure validation';

-- ==================== Add Missing Boolean Columns ====================

-- Fact-checking status flags
ALTER TABLE chapters
ADD COLUMN IF NOT EXISTS fact_checked BOOLEAN DEFAULT FALSE NOT NULL;

COMMENT ON COLUMN chapters.fact_checked IS 'Whether fact-checking has been performed (Stage 10)';

ALTER TABLE chapters
ADD COLUMN IF NOT EXISTS fact_check_passed BOOLEAN DEFAULT FALSE NOT NULL;

COMMENT ON COLUMN chapters.fact_check_passed IS 'Whether fact-checking passed quality thresholds';

-- ==================== Add Performance Indexes ====================

-- Index for querying fact-checked chapters
CREATE INDEX IF NOT EXISTS idx_chapters_fact_checked
ON chapters(fact_checked)
WHERE fact_checked = TRUE;

-- Index for querying chapters that passed fact-checking
CREATE INDEX IF NOT EXISTS idx_chapters_fact_check_passed
ON chapters(fact_check_passed)
WHERE fact_check_passed = TRUE;

-- Partial index for chapters awaiting fact-checking
CREATE INDEX IF NOT EXISTS idx_chapters_pending_fact_check
ON chapters(generation_status, fact_checked)
WHERE generation_status = 'completed' AND fact_checked = FALSE;

-- ==================== Verification ====================

-- Verify all columns were added
DO $$
DECLARE
    missing_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO missing_count
    FROM (VALUES
        ('references'),
        ('stage_1_input'),
        ('stage_10_fact_check'),
        ('stage_11_formatting'),
        ('fact_checked'),
        ('fact_check_passed')
    ) AS expected(col_name)
    WHERE NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'chapters'
        AND column_name = expected.col_name
    );

    IF missing_count > 0 THEN
        RAISE EXCEPTION 'Migration 009 failed: % columns still missing from chapters table', missing_count;
    ELSE
        RAISE NOTICE 'Migration 009 successful: All 6 columns added to chapters table';
    END IF;
END $$;

-- Display final schema for verification
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'chapters'
AND column_name IN (
    'references',
    'stage_1_input',
    'stage_10_fact_check',
    'stage_11_formatting',
    'fact_checked',
    'fact_check_passed'
)
ORDER BY column_name;
