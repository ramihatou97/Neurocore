-- Migration 011: Fix Textbook Display Issues
-- Date: 2025-11-01
-- Purpose: Fix three issues:
--   1. Chapter content display (add fields for text preview)
--   2. UUID titles (add audit fields and fix existing data)
--   3. Embedding labels (add metadata field)

-- ============================================
-- PDF_BOOKS TABLE: Add Title Editing Fields
-- ============================================

DO $$
BEGIN
    -- Add audit trail for title editing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pdf_books' AND column_name = 'title_edited_at'
    ) THEN
        ALTER TABLE pdf_books
        ADD COLUMN title_edited_at TIMESTAMP,
        ADD COLUMN title_edited_by UUID REFERENCES users(id),
        ADD COLUMN original_title TEXT;

        RAISE NOTICE 'Successfully added title editing fields to pdf_books';
    ELSE
        RAISE NOTICE 'Title editing fields already exist in pdf_books, skipping';
    END IF;
END $$;

-- Add comments
COMMENT ON COLUMN pdf_books.title_edited_at IS 'Timestamp when title was manually edited';
COMMENT ON COLUMN pdf_books.title_edited_by IS 'User who edited the title';
COMMENT ON COLUMN pdf_books.original_title IS 'Original title before editing (for audit trail)';

-- ============================================
-- PDF_CHAPTERS TABLE: Add Editing & Metadata Fields
-- ============================================

DO $$
BEGIN
    -- Add audit trail for chapter title editing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pdf_chapters' AND column_name = 'title_edited_at'
    ) THEN
        ALTER TABLE pdf_chapters
        ADD COLUMN title_edited_at TIMESTAMP,
        ADD COLUMN title_edited_by UUID REFERENCES users(id);

        RAISE NOTICE 'Successfully added title editing fields to pdf_chapters';
    ELSE
        RAISE NOTICE 'Title editing fields already exist in pdf_chapters, skipping';
    END IF;
END $$;

DO $$
BEGIN
    -- Add embedding metadata field
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pdf_chapters' AND column_name = 'embedding_metadata'
    ) THEN
        ALTER TABLE pdf_chapters
        ADD COLUMN embedding_metadata JSONB;

        RAISE NOTICE 'Successfully added embedding_metadata to pdf_chapters';
    ELSE
        RAISE NOTICE 'embedding_metadata already exists in pdf_chapters, skipping';
    END IF;
END $$;

-- Add comments
COMMENT ON COLUMN pdf_chapters.title_edited_at IS 'Timestamp when chapter title was manually edited';
COMMENT ON COLUMN pdf_chapters.title_edited_by IS 'User who edited the chapter title';
COMMENT ON COLUMN pdf_chapters.embedding_metadata IS 'Natural language labels and context for embeddings (source, preview, tags)';

-- ============================================
-- FIX EXISTING UUID TITLES IN PDF_BOOKS
-- ============================================

DO $$
DECLARE
    uuid_count INTEGER;
BEGIN
    -- Find how many UUID titles exist
    SELECT COUNT(*) INTO uuid_count
    FROM pdf_books
    WHERE title ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';

    IF uuid_count > 0 THEN
        -- Fix UUID titles
        UPDATE pdf_books
        SET original_title = title,
            title = 'Untitled Book - Please Edit',
            title_edited_at = NOW()
        WHERE title ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';

        RAISE NOTICE '✓ Fixed % UUID titles in pdf_books', uuid_count;
    ELSE
        RAISE NOTICE '✓ No UUID titles found in pdf_books (all good)';
    END IF;
END $$;

-- ============================================
-- ADD SEARCH INDEXES
-- ============================================

-- Full-text search index for book titles
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'idx_books_title_search'
    ) THEN
        CREATE INDEX idx_books_title_search
        ON pdf_books
        USING gin(to_tsvector('english', title));

        RAISE NOTICE '✓ Created full-text search index on pdf_books.title';
    ELSE
        RAISE NOTICE 'Full-text search index already exists on pdf_books.title';
    END IF;
END $$;

-- Full-text search index for chapter titles
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'idx_chapters_title_search'
    ) THEN
        CREATE INDEX idx_chapters_title_search
        ON pdf_chapters
        USING gin(to_tsvector('english', chapter_title));

        RAISE NOTICE '✓ Created full-text search index on pdf_chapters.chapter_title';
    ELSE
        RAISE NOTICE 'Full-text search index already exists on pdf_chapters.chapter_title';
    END IF;
END $$;

-- ============================================
-- VERIFICATION
-- ============================================

-- Verify pdf_books fields
DO $$
DECLARE
    fields_exist BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pdf_books'
          AND column_name IN ('title_edited_at', 'title_edited_by', 'original_title')
        HAVING COUNT(*) = 3
    ) INTO fields_exist;

    IF fields_exist THEN
        RAISE NOTICE '✓ Verification: All pdf_books title editing fields exist';
    ELSE
        RAISE EXCEPTION '✗ Verification failed: Missing pdf_books title editing fields';
    END IF;
END $$;

-- Verify pdf_chapters fields
DO $$
DECLARE
    fields_exist BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pdf_chapters'
          AND column_name IN ('title_edited_at', 'title_edited_by', 'embedding_metadata')
        HAVING COUNT(*) = 3
    ) INTO fields_exist;

    IF fields_exist THEN
        RAISE NOTICE '✓ Verification: All pdf_chapters fields exist';
    ELSE
        RAISE EXCEPTION '✗ Verification failed: Missing pdf_chapters fields';
    END IF;
END $$;

-- Display summary
SELECT
    'pdf_books' as table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'pdf_books'
    AND column_name IN ('title_edited_at', 'title_edited_by', 'original_title')

UNION ALL

SELECT
    'pdf_chapters' as table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'pdf_chapters'
    AND column_name IN ('title_edited_at', 'title_edited_by', 'embedding_metadata')
ORDER BY table_name, column_name;

-- Migration complete
SELECT 'Migration 011 completed successfully!' as status;
