-- Migration 002: Add Vector Embeddings Support
-- Description: Add embedding columns and text extraction fields for vector search
-- Date: 2025-10-27
-- Phase: 8 - Vector Search Infrastructure
-- Dependencies: Requires 001_initial_schema.sql to be applied first

-- ==================== Vector Extension ====================

-- Ensure pgvector extension is enabled (should already be from 001, but verify)
CREATE EXTENSION IF NOT EXISTS vector;

-- ==================== Add Embedding Columns ====================

-- PDFs Table: Add embedding and extracted text columns
-- embedding: 1536-dimensional vector for OpenAI text-embedding-ada-002
-- extracted_text: Full text content extracted from PDF for search and chunking
ALTER TABLE pdfs
ADD COLUMN IF NOT EXISTS embedding vector(1536),
ADD COLUMN IF NOT EXISTS extracted_text TEXT;

-- Chapters Table: Add embedding column
-- Chapters are generated summaries, each gets its own embedding
ALTER TABLE chapters
ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- Images Table: Add embedding and extracted text columns
-- embedding: For image content embeddings (vision models)
-- extracted_text: OCR text extracted from images
ALTER TABLE images
ADD COLUMN IF NOT EXISTS embedding vector(1536),
ADD COLUMN IF NOT EXISTS extracted_text TEXT;

-- ==================== Additional Processing Columns ====================

-- Add columns to track embedding generation status
ALTER TABLE pdfs
ADD COLUMN IF NOT EXISTS embedding_generated_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(100) DEFAULT 'text-embedding-ada-002';

ALTER TABLE chapters
ADD COLUMN IF NOT EXISTS embedding_generated_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(100) DEFAULT 'text-embedding-ada-002';

ALTER TABLE images
ADD COLUMN IF NOT EXISTS embedding_generated_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(100) DEFAULT 'text-embedding-ada-002',
ADD COLUMN IF NOT EXISTS ocr_performed BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS ocr_language VARCHAR(10) DEFAULT 'en';

-- ==================== Indexes for Embedding Status ====================

-- Index for finding items that need embeddings generated
CREATE INDEX IF NOT EXISTS idx_pdfs_embeddings_generated
ON pdfs(embeddings_generated, embedding)
WHERE embedding IS NULL;

CREATE INDEX IF NOT EXISTS idx_chapters_embeddings_generated
ON chapters(embedding)
WHERE embedding IS NULL;

CREATE INDEX IF NOT EXISTS idx_images_embeddings_generated
ON images(embedding)
WHERE embedding IS NULL;

-- ==================== Comments ====================

COMMENT ON COLUMN pdfs.embedding IS 'OpenAI embedding vector (1536 dimensions) for semantic search';
COMMENT ON COLUMN pdfs.extracted_text IS 'Full text content extracted from PDF for search and analysis';
COMMENT ON COLUMN pdfs.embedding_generated_at IS 'Timestamp when embedding was generated';
COMMENT ON COLUMN pdfs.embedding_model IS 'Model used to generate embedding (e.g., text-embedding-ada-002)';

COMMENT ON COLUMN chapters.embedding IS 'OpenAI embedding vector for chapter content';
COMMENT ON COLUMN chapters.embedding_generated_at IS 'Timestamp when embedding was generated';
COMMENT ON COLUMN chapters.embedding_model IS 'Model used to generate embedding';

COMMENT ON COLUMN images.embedding IS 'Embedding vector for image content (vision or OCR text)';
COMMENT ON COLUMN images.extracted_text IS 'OCR text extracted from image';
COMMENT ON COLUMN images.embedding_generated_at IS 'Timestamp when embedding was generated';
COMMENT ON COLUMN images.embedding_model IS 'Model used to generate embedding';
COMMENT ON COLUMN images.ocr_performed IS 'Whether OCR text extraction was performed';
COMMENT ON COLUMN images.ocr_language IS 'Language code for OCR (e.g., en, fr, de)';

-- ==================== Verify Changes ====================

-- Log successful migration
DO $$
BEGIN
    RAISE NOTICE 'Migration 002 completed successfully';
    RAISE NOTICE 'Added embedding columns to: pdfs, chapters, images';
    RAISE NOTICE 'Added text extraction columns to: pdfs, images';
    RAISE NOTICE 'Vector search infrastructure is ready';
END $$;

-- ==================== Usage Notes ====================

/*
-- Embedding dimensions: 1536 (OpenAI text-embedding-ada-002)
-- To generate embeddings, use the AI service in the application
--
-- Example: Check embedding coverage
-- SELECT
--     COUNT(*) as total,
--     COUNT(embedding) as with_embeddings,
--     ROUND(COUNT(embedding)::numeric / COUNT(*) * 100, 2) as coverage_percent
-- FROM pdfs;
--
-- Example: Find items without embeddings
-- SELECT id, title FROM pdfs WHERE embedding IS NULL AND extracted_text IS NOT NULL;
*/

-- ==================== Rollback Script ====================

/*
-- To rollback this migration (use with caution - loses all embeddings):

ALTER TABLE pdfs
DROP COLUMN IF EXISTS embedding,
DROP COLUMN IF EXISTS extracted_text,
DROP COLUMN IF EXISTS embedding_generated_at,
DROP COLUMN IF EXISTS embedding_model;

ALTER TABLE chapters
DROP COLUMN IF EXISTS embedding,
DROP COLUMN IF EXISTS embedding_generated_at,
DROP COLUMN IF EXISTS embedding_model;

ALTER TABLE images
DROP COLUMN IF EXISTS embedding,
DROP COLUMN IF EXISTS extracted_text,
DROP COLUMN IF EXISTS embedding_generated_at,
DROP COLUMN IF EXISTS embedding_model,
DROP COLUMN IF EXISTS ocr_performed,
DROP COLUMN IF EXISTS ocr_language;

DROP INDEX IF EXISTS idx_pdfs_embeddings_generated;
DROP INDEX IF EXISTS idx_chapters_embeddings_generated;
DROP INDEX IF EXISTS idx_images_embeddings_generated;

*/
