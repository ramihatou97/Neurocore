-- Migration 010: Add Missing Columns to Images and Chapters Tables
-- Date: 2025-11-01
-- Purpose: Fix schema mismatches found during comprehensive audit
--
-- Issues Fixed:
-- 1. images.analysis_metadata - backend/services/background_tasks.py:263 tries to set this
-- 2. chapters.generation_error - backend/services/chapter_orchestrator.py:156 tries to set this

-- ============================================
-- IMAGES TABLE: Add analysis_metadata column
-- ============================================

DO $$
BEGIN
    -- Add analysis_metadata column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'images'
        AND column_name = 'analysis_metadata'
    ) THEN
        ALTER TABLE images
        ADD COLUMN analysis_metadata JSONB;

        RAISE NOTICE 'Successfully added images.analysis_metadata column';
    ELSE
        RAISE NOTICE 'images.analysis_metadata column already exists, skipping';
    END IF;
END $$;

-- Add comment for documentation
COMMENT ON COLUMN images.analysis_metadata IS 'Full analysis metadata from Claude Vision API';

-- ============================================
-- CHAPTERS TABLE: Add generation_error column
-- ============================================

DO $$
BEGIN
    -- Add generation_error column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'chapters'
        AND column_name = 'generation_error'
    ) THEN
        ALTER TABLE chapters
        ADD COLUMN generation_error TEXT;

        RAISE NOTICE 'Successfully added chapters.generation_error column';
    ELSE
        RAISE NOTICE 'chapters.generation_error column already exists, skipping';
    END IF;
END $$;

-- Add comment for documentation
COMMENT ON COLUMN chapters.generation_error IS 'Error message if chapter generation fails';

-- ============================================
-- VERIFICATION
-- ============================================

-- Verify images.analysis_metadata exists
DO $$
DECLARE
    column_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'images'
        AND column_name = 'analysis_metadata'
    ) INTO column_exists;

    IF column_exists THEN
        RAISE NOTICE '✓ Verification: images.analysis_metadata exists';
    ELSE
        RAISE EXCEPTION '✗ Verification failed: images.analysis_metadata does not exist';
    END IF;
END $$;

-- Verify chapters.generation_error exists
DO $$
DECLARE
    column_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'chapters'
        AND column_name = 'generation_error'
    ) INTO column_exists;

    IF column_exists THEN
        RAISE NOTICE '✓ Verification: chapters.generation_error exists';
    ELSE
        RAISE EXCEPTION '✗ Verification failed: chapters.generation_error does not exist';
    END IF;
END $$;

-- Display column information
SELECT
    'images' as table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'images'
    AND column_name = 'analysis_metadata'

UNION ALL

SELECT
    'chapters' as table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'chapters'
    AND column_name = 'generation_error';

-- Migration complete
SELECT 'Migration 010 completed successfully!' as status;
