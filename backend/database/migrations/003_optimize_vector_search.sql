-- Migration: Optimize Vector Search with IVFFlat Indexes
-- Description: Add IVFFlat indexes for faster vector similarity search
-- Date: 2025-10-27

-- ==================== Vector Index Optimization ====================

-- Drop existing indexes if they exist (for idempotency)
DROP INDEX IF EXISTS idx_pdfs_embedding_ivfflat;
DROP INDEX IF EXISTS idx_chapters_embedding_ivfflat;
DROP INDEX IF EXISTS idx_images_embedding_ivfflat;

-- Create IVFFlat index for PDFs
-- IVFFlat parameters:
-- - lists: Number of clusters (sqrt of expected rows, typically 100-1000)
-- - probes: Number of clusters to search (higher = more accurate but slower)
-- For 1000 PDFs: lists = 32
-- For 10000 PDFs: lists = 100
-- For 100000 PDFs: lists = 316

CREATE INDEX IF NOT EXISTS idx_pdfs_embedding_ivfflat
ON pdfs
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create IVFFlat index for Chapters
CREATE INDEX IF NOT EXISTS idx_chapters_embedding_ivfflat
ON chapters
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create IVFFlat index for Images
CREATE INDEX IF NOT EXISTS idx_images_embedding_ivfflat
ON images
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- ==================== Full-Text Search Indexes ====================

-- Add GIN indexes for full-text search (if not already exist)

-- PDFs full-text search index
CREATE INDEX IF NOT EXISTS idx_pdfs_title_gin ON pdfs USING gin(to_tsvector('english', COALESCE(title, '')));
CREATE INDEX IF NOT EXISTS idx_pdfs_authors_gin ON pdfs USING gin(to_tsvector('english', COALESCE(authors, '')));

-- Note: Don't index extracted_text with GIN (too large), use trigram instead
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS idx_pdfs_extracted_text_trgm ON pdfs USING gin(extracted_text gin_trgm_ops);

-- Chapters full-text search index
CREATE INDEX IF NOT EXISTS idx_chapters_title_gin ON chapters USING gin(to_tsvector('english', COALESCE(title, '')));
CREATE INDEX IF NOT EXISTS idx_chapters_summary_gin ON chapters USING gin(to_tsvector('english', COALESCE(summary, '')));

-- ==================== Composite Indexes for Filtering ====================

-- PDF search with filters
CREATE INDEX IF NOT EXISTS idx_pdfs_status_created ON pdfs(extraction_status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pdfs_year_created ON pdfs(year DESC, created_at DESC);

-- Chapter search with filters
CREATE INDEX IF NOT EXISTS idx_chapters_status_created ON chapters(generation_status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chapters_author_created ON chapters(author_id, created_at DESC);

-- Images search
CREATE INDEX IF NOT EXISTS idx_images_pdf_page ON images(pdf_id, page_number);

-- ==================== Performance Analysis Functions ====================

-- Function to analyze vector index usage
CREATE OR REPLACE FUNCTION analyze_vector_index_usage()
RETURNS TABLE (
    table_name TEXT,
    index_name TEXT,
    index_size TEXT,
    rows_count BIGINT,
    index_scans BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        schemaname || '.' || tablename AS table_name,
        indexrelname AS index_name,
        pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
        n_tup_ins + n_tup_upd AS rows_count,
        idx_scan AS index_scans
    FROM pg_stat_user_indexes
    WHERE indexrelname LIKE '%embedding%' OR indexrelname LIKE '%ivfflat%'
    ORDER BY pg_relation_size(indexrelid) DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to get vector search statistics
CREATE OR REPLACE FUNCTION vector_search_stats()
RETURNS TABLE (
    entity_type TEXT,
    total_count BIGINT,
    with_embeddings BIGINT,
    coverage_percent NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        'PDFs' AS entity_type,
        COUNT(*)::BIGINT AS total_count,
        COUNT(embedding)::BIGINT AS with_embeddings,
        ROUND((COUNT(embedding)::NUMERIC / NULLIF(COUNT(*), 0) * 100), 2) AS coverage_percent
    FROM pdfs
    UNION ALL
    SELECT
        'Chapters' AS entity_type,
        COUNT(*)::BIGINT,
        COUNT(embedding)::BIGINT,
        ROUND((COUNT(embedding)::NUMERIC / NULLIF(COUNT(*), 0) * 100), 2)
    FROM chapters
    UNION ALL
    SELECT
        'Images' AS entity_type,
        COUNT(*)::BIGINT,
        COUNT(embedding)::BIGINT,
        ROUND((COUNT(embedding)::NUMERIC / NULLIF(COUNT(*), 0) * 100), 2)
    FROM images;
END;
$$ LANGUAGE plpgsql;

-- ==================== Index Maintenance ====================

-- Analyze tables to update statistics for query planner
ANALYZE pdfs;
ANALYZE chapters;
ANALYZE images;

-- Vacuum tables to reclaim space and update statistics
VACUUM ANALYZE pdfs;
VACUUM ANALYZE chapters;
VACUUM ANALYZE images;

-- ==================== Performance Configuration ====================

-- Set search parameters for IVFFlat indexes
-- probes: Number of clusters to search (default: 1)
-- Higher probes = more accurate but slower
-- Recommended: 10 for good balance

-- This can be set per-session or globally:
-- SET ivfflat.probes = 10;

-- To set globally (requires superuser):
-- ALTER SYSTEM SET ivfflat.probes = 10;
-- SELECT pg_reload_conf();

-- ==================== Usage Examples ====================

/*
-- Example 1: Vector similarity search with proper index usage
SELECT
    id,
    title,
    1 - (embedding <=> '[0.1, 0.2, ...]'::vector) as similarity
FROM pdfs
WHERE embedding IS NOT NULL
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 10;

-- Example 2: Hybrid search (keyword + vector)
WITH keyword_results AS (
    SELECT id, title, ts_rank(to_tsvector('english', title), plainto_tsquery('english', 'brain tumor')) as rank
    FROM pdfs
    WHERE to_tsvector('english', title) @@ plainto_tsquery('english', 'brain tumor')
),
vector_results AS (
    SELECT id, title, 1 - (embedding <=> :query_embedding) as similarity
    FROM pdfs
    WHERE embedding IS NOT NULL
    ORDER BY embedding <=> :query_embedding
    LIMIT 20
)
SELECT DISTINCT id, title FROM keyword_results
UNION
SELECT DISTINCT id, title FROM vector_results
ORDER BY id;

-- Example 3: Check index usage
SELECT * FROM analyze_vector_index_usage();

-- Example 4: Get embedding coverage statistics
SELECT * FROM vector_search_stats();

*/

-- ==================== Rollback Script ====================

/*
-- To rollback this migration:

DROP INDEX IF EXISTS idx_pdfs_embedding_ivfflat;
DROP INDEX IF EXISTS idx_chapters_embedding_ivfflat;
DROP INDEX IF EXISTS idx_images_embedding_ivfflat;

DROP INDEX IF EXISTS idx_pdfs_title_gin;
DROP INDEX IF EXISTS idx_pdfs_authors_gin;
DROP INDEX IF EXISTS idx_pdfs_extracted_text_trgm;

DROP INDEX IF EXISTS idx_chapters_title_gin;
DROP INDEX IF EXISTS idx_chapters_summary_gin;

DROP INDEX IF EXISTS idx_pdfs_status_created;
DROP INDEX IF EXISTS idx_pdfs_year_created;
DROP INDEX IF EXISTS idx_chapters_status_created;
DROP INDEX IF EXISTS idx_chapters_author_created;
DROP INDEX IF EXISTS idx_images_pdf_page;

DROP FUNCTION IF EXISTS analyze_vector_index_usage();
DROP FUNCTION IF EXISTS vector_search_stats();

*/
