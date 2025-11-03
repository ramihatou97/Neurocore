-- Migration 006: Chapter-Level Vector Search Architecture
-- Description: Implement hierarchical vector search with book → chapter → chunk granularity
-- Date: 2025-10-31
-- Phase: Vector Search Implementation - True Library Support
-- Dependencies: Requires 001-005 migrations to be applied first

-- ==================== CRITICAL: Embedding Model Upgrade ====================

-- UPGRADE: text-embedding-ada-002 → text-embedding-3-large (with dimensions=1536)
-- WHY: text-embedding-3-large is superior quality even at reduced dimensions
-- DIMENSION CONSTRAINT: pgvector (HNSW/IVFFlat) limited to 2000 dimensions
-- SOLUTION: Use text-embedding-3-large with dimensions parameter set to 1536
-- BENEFIT: Better model + fits within pgvector limits
-- NOTE: Existing PDFs cleared (Phase 0), so no data loss

-- PDFs table: Already 1536 dims from rollback (no change needed)
-- Chapters table: Already 1536 dims from rollback (no change needed)
-- Images table: Already 1536 dims from rollback (no change needed)

-- Update embedding model references
UPDATE pdfs SET embedding_model = 'text-embedding-3-large' WHERE embedding_model IS NOT NULL;
UPDATE chapters SET embedding_model = 'text-embedding-3-large' WHERE embedding_model IS NOT NULL;
UPDATE images SET embedding_model = 'text-embedding-3-large' WHERE embedding_model IS NOT NULL;

-- ==================== PDF Books Table ====================

-- Tracks full textbooks (multi-chapter PDFs)
-- Provides book-level metadata for hierarchical organization
CREATE TABLE IF NOT EXISTS pdf_books (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Book metadata
    title TEXT NOT NULL,
    authors TEXT[],
    edition TEXT,
    publication_year INTEGER,
    publisher TEXT,
    isbn TEXT UNIQUE,

    -- File information
    total_chapters INTEGER,
    total_pages INTEGER,
    file_path TEXT NOT NULL,
    file_size_bytes BIGINT,

    -- Upload tracking
    uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    uploaded_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Processing status for background tasks
    processing_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    processing_started_at TIMESTAMP,
    processing_completed_at TIMESTAMP,
    processing_error TEXT,

    -- Flexible metadata storage
    book_metadata JSONB,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for pdf_books
CREATE INDEX IF NOT EXISTS idx_books_processing_status ON pdf_books(processing_status);
CREATE INDEX IF NOT EXISTS idx_books_uploaded_at ON pdf_books(uploaded_at);
CREATE INDEX IF NOT EXISTS idx_books_publication_year ON pdf_books(publication_year);
CREATE INDEX IF NOT EXISTS idx_books_isbn ON pdf_books(isbn);

-- Comments for pdf_books
COMMENT ON TABLE pdf_books IS 'Full textbooks with multiple chapters - book-level metadata';
COMMENT ON COLUMN pdf_books.processing_status IS 'Background task status: pending, processing, completed, failed';
COMMENT ON COLUMN pdf_books.total_chapters IS 'Number of chapters detected and extracted';
COMMENT ON COLUMN pdf_books.book_metadata IS 'Flexible JSONB storage for additional book metadata';

-- ==================== PDF Chapters Table ====================

-- PRIMARY SEARCH UNIT: Chapters are the main granularity for vector search
-- Supports: textbook chapters, standalone chapters, research papers
CREATE TABLE IF NOT EXISTS pdf_chapters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Hierarchy
    book_id UUID REFERENCES pdf_books(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL
        CHECK (source_type IN ('textbook_chapter', 'standalone_chapter', 'research_paper')),

    -- Chapter identification
    chapter_number INTEGER,
    chapter_title TEXT NOT NULL,
    start_page INTEGER,
    end_page INTEGER,
    page_count INTEGER,

    -- Content
    extracted_text TEXT NOT NULL,
    word_count INTEGER,
    has_images BOOLEAN DEFAULT FALSE,
    image_count INTEGER DEFAULT 0,

    -- Vector search (1536-dim text-embedding-3-large)
    -- Note: Using dimensions=1536 parameter (pgvector limit: 2000)
    embedding vector(1536),
    embedding_model TEXT DEFAULT 'text-embedding-3-large',
    embedding_generated_at TIMESTAMP,

    -- Deduplication (mark-not-delete strategy)
    content_hash VARCHAR(64) NOT NULL,  -- SHA-256 hash of normalized text
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_of_id UUID REFERENCES pdf_chapters(id) ON DELETE SET NULL,
    duplicate_group_id UUID,  -- Groups all duplicates together
    preference_score FLOAT DEFAULT 0.0,  -- Higher = preferred version

    -- Chapter detection metadata
    detection_confidence FLOAT,  -- 0.0-1.0 (TOC=0.9, pattern=0.8, heading=0.6)
    detection_method TEXT,  -- 'toc', 'pattern', 'heading', 'manual'
    quality_score FLOAT DEFAULT 0.5,  -- 0.0-1.0 (user or system assigned)

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    UNIQUE(book_id, content_hash)  -- Prevent exact duplicates within same book
);

-- Indexes for pdf_chapters
-- Vector search index (HNSW for cosine similarity - supports 3072 dims)
-- HNSW: Better accuracy, faster queries, no dimension limit
CREATE INDEX IF NOT EXISTS idx_chapters_embedding_hnsw
ON pdf_chapters USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Query performance indexes
CREATE INDEX IF NOT EXISTS idx_chapters_book_id ON pdf_chapters(book_id);
CREATE INDEX IF NOT EXISTS idx_chapters_source_type ON pdf_chapters(source_type);
CREATE INDEX IF NOT EXISTS idx_chapters_content_hash ON pdf_chapters(content_hash);
CREATE INDEX IF NOT EXISTS idx_chapters_duplicate_group ON pdf_chapters(duplicate_group_id);
CREATE INDEX IF NOT EXISTS idx_chapters_is_duplicate ON pdf_chapters(is_duplicate);
CREATE INDEX IF NOT EXISTS idx_chapters_embedding_status
ON pdf_chapters(embedding) WHERE embedding IS NULL;

-- Comments for pdf_chapters
COMMENT ON TABLE pdf_chapters IS 'Primary search unit: chapters with hierarchical embeddings';
COMMENT ON COLUMN pdf_chapters.source_type IS 'Type: textbook_chapter, standalone_chapter, research_paper';
COMMENT ON COLUMN pdf_chapters.embedding IS '1536-dim vector (text-embedding-3-large with dimensions=1536) for semantic search';
COMMENT ON COLUMN pdf_chapters.content_hash IS 'SHA-256 hash of normalized text for deduplication';
COMMENT ON COLUMN pdf_chapters.is_duplicate IS 'TRUE if duplicate exists with higher preference_score';
COMMENT ON COLUMN pdf_chapters.duplicate_of_id IS 'Points to preferred version if this is duplicate';
COMMENT ON COLUMN pdf_chapters.duplicate_group_id IS 'UUID grouping all duplicates together';
COMMENT ON COLUMN pdf_chapters.preference_score IS 'Ranking for duplicates (higher = preferred)';
COMMENT ON COLUMN pdf_chapters.detection_confidence IS 'Confidence in chapter detection (0.0-1.0)';

-- ==================== PDF Chunks Table ====================

-- Fine-grained chunks for long chapters (>4000 tokens)
-- Enables precise retrieval within large chapters
CREATE TABLE IF NOT EXISTS pdf_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chapter_id UUID NOT NULL REFERENCES pdf_chapters(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,

    -- Content
    chunk_text TEXT NOT NULL,
    token_count INTEGER,
    start_char_offset INTEGER,
    end_char_offset INTEGER,

    -- Context preservation (important for medical content)
    preceding_heading TEXT,  -- Section heading before this chunk
    contains_headings TEXT[],  -- Headings within this chunk

    -- Vector search (1536-dim text-embedding-3-large)
    embedding vector(1536),
    embedding_model TEXT DEFAULT 'text-embedding-3-large',

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    UNIQUE(chapter_id, chunk_index)
);

-- Indexes for pdf_chunks
-- Vector search index (HNSW for cosine similarity)
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
ON pdf_chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Query performance indexes
CREATE INDEX IF NOT EXISTS idx_chunks_chapter_id ON pdf_chunks(chapter_id);
CREATE INDEX IF NOT EXISTS idx_chunks_chapter_index ON pdf_chunks(chapter_id, chunk_index);

-- Comments for pdf_chunks
COMMENT ON TABLE pdf_chunks IS 'Fine-grained chunks for long chapters (enables precise retrieval)';
COMMENT ON COLUMN pdf_chunks.chunk_index IS '0-based index of chunk within chapter';
COMMENT ON COLUMN pdf_chunks.preceding_heading IS 'Section heading before this chunk (context preservation)';
COMMENT ON COLUMN pdf_chunks.contains_headings IS 'Headings within chunk (structure awareness)';

-- ==================== Update PDFs Table ====================

-- Add source_type to distinguish PDF types
ALTER TABLE pdfs
ADD COLUMN IF NOT EXISTS source_type TEXT
    CHECK (source_type IN ('textbook', 'chapter', 'paper'));

-- Update processing_status check constraint (if it doesn't include all statuses)
ALTER TABLE pdfs
DROP CONSTRAINT IF EXISTS chk_indexing_status;

ALTER TABLE pdfs
ADD CONSTRAINT chk_indexing_status
    CHECK (indexing_status IN (
        'uploaded', 'extracting_text', 'text_extracted',
        'extracting_images', 'images_extracted',
        'text_extraction_failed', 'image_extraction_failed',
        'pending', 'processing', 'completed', 'failed'
    ));

-- Add comment
COMMENT ON COLUMN pdfs.source_type IS 'PDF type: textbook (full book), chapter (single chapter), paper (research paper)';

-- ==================== Rebuild Existing Vector Indexes ====================

-- Create HNSW indexes for 1536-dim embeddings
-- HNSW: Better accuracy and speed than IVFFlat for most workloads

-- PDFs embedding index (HNSW)
DROP INDEX IF EXISTS idx_pdfs_embedding_ivfflat;
DROP INDEX IF EXISTS idx_pdfs_embedding_hnsw;
CREATE INDEX IF NOT EXISTS idx_pdfs_embedding_hnsw
ON pdfs USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Chapters embedding index (HNSW)
DROP INDEX IF EXISTS idx_chapters_embedding_ivfflat;
DROP INDEX IF EXISTS idx_chapters_embedding_hnsw;
CREATE INDEX IF NOT EXISTS idx_chapters_embedding_hnsw
ON chapters USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Images embedding index (HNSW)
DROP INDEX IF EXISTS idx_images_embedding_ivfflat;
DROP INDEX IF EXISTS idx_images_embedding_hnsw;
CREATE INDEX IF NOT EXISTS idx_images_embedding_hnsw
ON images USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- ==================== Update Settings Table (if exists) ====================

-- If you have a settings table, update vector dimensions there
-- DO $$
-- BEGIN
--     IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'settings') THEN
--         UPDATE settings SET value = '3072' WHERE key = 'vector_dimensions';
--     END IF;
-- END $$;

-- ==================== Verify Changes ====================

-- Log successful migration
DO $$
DECLARE
    book_count INTEGER;
    chapter_count INTEGER;
    chunk_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO book_count FROM pdf_books;
    SELECT COUNT(*) INTO chapter_count FROM pdf_chapters;
    SELECT COUNT(*) INTO chunk_count FROM pdf_chunks;

    RAISE NOTICE '========================================';
    RAISE NOTICE 'Migration 006 completed successfully';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Embedding model upgraded: ada-002 → text-embedding-3-large';
    RAISE NOTICE 'Embedding dimensions: 1536 (with text-embedding-3-large dimensions=1536)';
    RAISE NOTICE 'Tables created: pdf_books, pdf_chapters, pdf_chunks';
    RAISE NOTICE 'Current state:';
    RAISE NOTICE '  - Books: %', book_count;
    RAISE NOTICE '  - Chapters: %', chapter_count;
    RAISE NOTICE '  - Chunks: %', chunk_count;
    RAISE NOTICE '  - Vector indexes: 6 HNSW (pdfs, chapters, images, pdf_chapters, pdf_chunks)';
    RAISE NOTICE '  - Index type: HNSW (supports unlimited dimensions, better accuracy)';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Chapter-level vector search infrastructure ready!';
    RAISE NOTICE 'Next: Upload true library and generate embeddings';
    RAISE NOTICE '========================================';
END $$;

-- ==================== Usage Notes ====================

/*
-- Embedding model: text-embedding-3-large with dimensions=1536
-- Why 1536: pgvector HNSW/IVFFlat index limit is 2000 dimensions
-- Quality: text-embedding-3-large @ 1536 dims > ada-002 @ 1536 dims
-- Search granularity: Book → Chapter (primary) → Chunk
-- Deduplication strategy: Mark-not-delete (preserve all versions)
--
-- Example: Check indexing progress
SELECT
    COUNT(*) as total_chapters,
    COUNT(embedding) as embedded_chapters,
    ROUND(COUNT(embedding)::numeric / NULLIF(COUNT(*), 0) * 100, 2) as indexing_percent
FROM pdf_chapters;

-- Example: Find duplicates
SELECT
    duplicate_group_id,
    COUNT(*) as versions,
    STRING_AGG(chapter_title, ' | ' ORDER BY preference_score DESC) as titles
FROM pdf_chapters
WHERE duplicate_group_id IS NOT NULL
GROUP BY duplicate_group_id
HAVING COUNT(*) > 1;

-- Example: Check deduplication rate
SELECT
    COUNT(*) as total_chapters,
    COUNT(*) FILTER (WHERE is_duplicate) as duplicates,
    COUNT(*) FILTER (WHERE NOT is_duplicate) as unique_chapters,
    ROUND(COUNT(*) FILTER (WHERE is_duplicate)::numeric / NULLIF(COUNT(*), 0) * 100, 2) as dedup_rate
FROM pdf_chapters;

-- Example: Library statistics
SELECT
    b.title,
    b.publication_year,
    COUNT(c.id) as chapters,
    COUNT(c.id) FILTER (WHERE c.embedding IS NOT NULL) as embedded,
    COUNT(ch.id) as total_chunks
FROM pdf_books b
LEFT JOIN pdf_chapters c ON c.book_id = b.id
LEFT JOIN pdf_chunks ch ON ch.chapter_id = c.id
GROUP BY b.id, b.title, b.publication_year
ORDER BY b.publication_year DESC;
*/

-- ==================== Rollback Script ====================

/*
-- To rollback this migration (use with extreme caution - loses all chapter data):

-- Drop new tables
DROP TABLE IF EXISTS pdf_chunks CASCADE;
DROP TABLE IF EXISTS pdf_chapters CASCADE;
DROP TABLE IF EXISTS pdf_books CASCADE;

-- Revert PDFs table changes
ALTER TABLE pdfs DROP COLUMN IF EXISTS source_type;
ALTER TABLE pdfs DROP COLUMN IF EXISTS embedding CASCADE;
ALTER TABLE pdfs ADD COLUMN embedding vector(1536);

-- Revert Chapters table changes
ALTER TABLE chapters DROP COLUMN IF EXISTS embedding CASCADE;
ALTER TABLE chapters ADD COLUMN embedding vector(1536);

-- Revert Images table changes
ALTER TABLE images DROP COLUMN IF EXISTS embedding CASCADE;
ALTER TABLE images ADD COLUMN embedding vector(1536);

-- Recreate old IVFFlat indexes (for 1536-dim embeddings)
CREATE INDEX IF NOT EXISTS idx_pdfs_embedding_ivfflat
ON pdfs USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_chapters_embedding_ivfflat
ON chapters USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_images_embedding_ivfflat
ON images USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
*/
