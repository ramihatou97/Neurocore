-- Migration: Fix chapter_versions metadata column name
-- Date: 2025-11-01
-- Issue: Column named 'metadata' in database but model expects 'version_metadata'
--
-- Background:
-- The SQLAlchemy model was updated to rename 'metadata' to 'version_metadata'
-- to avoid conflicts with SQLAlchemy's reserved 'metadata' attribute.
-- This migration brings the database schema in sync with the model.
--
-- Impact: Fixes DELETE /chapters/:id endpoint which was failing with 500 errors
--         due to "column chapter_versions.version_metadata does not exist"

-- Check if column needs to be renamed
DO $$
BEGIN
    -- Check if 'metadata' column exists (old name)
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'chapter_versions'
        AND column_name = 'metadata'
    ) THEN
        -- Rename metadata to version_metadata
        ALTER TABLE chapter_versions
        RENAME COLUMN metadata TO version_metadata;

        RAISE NOTICE 'Successfully renamed chapter_versions.metadata to version_metadata';
    ELSE
        -- Check if already renamed
        IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'chapter_versions'
            AND column_name = 'version_metadata'
        ) THEN
            RAISE NOTICE 'Column chapter_versions.version_metadata already exists - migration already applied';
        ELSE
            RAISE EXCEPTION 'Neither metadata nor version_metadata column found in chapter_versions table';
        END IF;
    END IF;
END $$;

-- Verify the migration
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name = 'chapter_versions'
AND column_name = 'version_metadata';
