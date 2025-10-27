-- =========================================================
-- Neurosurgery Knowledge Base - Initial Schema Migration
-- Version: 001
-- Description: Create all base tables with indexes and constraints
-- =========================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- =========================================================
-- USERS TABLE
-- Tracks authenticated users who can upload PDFs and request chapters
-- =========================================================

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for users table
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

COMMENT ON TABLE users IS 'Authenticated users for the system';
COMMENT ON COLUMN users.email IS 'User email address - must be unique';
COMMENT ON COLUMN users.hashed_password IS 'Bcrypt hashed password - never store plain text';

-- =========================================================
-- PDFS TABLE
-- Tracks uploaded research papers and textbooks (Process A)
-- =========================================================

CREATE TABLE IF NOT EXISTS pdfs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) UNIQUE NOT NULL,
    file_size_bytes BIGINT,
    total_pages INTEGER,

    -- Metadata
    title TEXT,
    authors TEXT[],
    publication_year INTEGER,
    journal VARCHAR(500),
    doi VARCHAR(255) UNIQUE,
    pmid VARCHAR(50) UNIQUE,

    -- Processing status
    indexing_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    text_extracted BOOLEAN NOT NULL DEFAULT FALSE,
    images_extracted BOOLEAN NOT NULL DEFAULT FALSE,
    embeddings_generated BOOLEAN NOT NULL DEFAULT FALSE,

    -- Timestamps
    uploaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    indexed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chk_indexing_status CHECK (indexing_status IN ('pending', 'processing', 'completed', 'failed'))
);

-- Indexes for pdfs table
CREATE INDEX IF NOT EXISTS idx_pdfs_indexing_status ON pdfs(indexing_status);
CREATE INDEX IF NOT EXISTS idx_pdfs_uploaded_at ON pdfs(uploaded_at);
CREATE INDEX IF NOT EXISTS idx_pdfs_publication_year ON pdfs(publication_year);
CREATE INDEX IF NOT EXISTS idx_pdfs_doi ON pdfs(doi);
CREATE INDEX IF NOT EXISTS idx_pdfs_pmid ON pdfs(pmid);

COMMENT ON TABLE pdfs IS 'Uploaded research papers and textbooks for indexation';
COMMENT ON COLUMN pdfs.indexing_status IS 'Status: pending, processing, completed, failed';

-- =========================================================
-- CHAPTERS TABLE
-- Generated neurosurgery chapters (Process B - 14-stage workflow)
-- =========================================================

CREATE TABLE IF NOT EXISTS chapters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    chapter_type VARCHAR(50),

    -- Content (JSONB for flexibility)
    sections JSONB,
    structure_metadata JSONB,

    -- Workflow stages (JSONB)
    stage_2_context JSONB,
    stage_3_internal_research JSONB,
    stage_4_external_research JSONB,
    stage_5_synthesis_metadata JSONB,
    stage_6_gaps_detected JSONB,
    stage_8_integration_log JSONB,

    -- Quality scores
    depth_score REAL,
    coverage_score REAL,
    currency_score REAL,
    evidence_score REAL,

    -- Version control
    version VARCHAR(20) NOT NULL DEFAULT '1.0',
    is_current_version BOOLEAN NOT NULL DEFAULT TRUE,
    parent_version_id UUID REFERENCES chapters(id) ON DELETE SET NULL,

    -- Status
    generation_status VARCHAR(50) NOT NULL DEFAULT 'draft',

    -- Foreign keys
    author_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chk_chapter_type CHECK (chapter_type IN ('surgical_disease', 'pure_anatomy', 'surgical_technique')),
    CONSTRAINT chk_generation_status CHECK (generation_status IN ('draft', 'in_progress', 'completed', 'failed')),
    CONSTRAINT chk_quality_scores CHECK (
        (depth_score IS NULL OR (depth_score >= 0 AND depth_score <= 1)) AND
        (coverage_score IS NULL OR (coverage_score >= 0 AND coverage_score <= 1)) AND
        (currency_score IS NULL OR (currency_score >= 0 AND currency_score <= 1)) AND
        (evidence_score IS NULL OR (evidence_score >= 0 AND evidence_score <= 1))
    )
);

-- Indexes for chapters table
CREATE INDEX IF NOT EXISTS idx_chapters_author_id ON chapters(author_id);
CREATE INDEX IF NOT EXISTS idx_chapters_chapter_type ON chapters(chapter_type);
CREATE INDEX IF NOT EXISTS idx_chapters_generation_status ON chapters(generation_status);
CREATE INDEX IF NOT EXISTS idx_chapters_is_current_version ON chapters(is_current_version);
CREATE INDEX IF NOT EXISTS idx_chapters_created_at ON chapters(created_at);

-- GIN indexes for JSONB columns (for efficient querying)
CREATE INDEX IF NOT EXISTS idx_chapters_sections_gin ON chapters USING GIN(sections);
CREATE INDEX IF NOT EXISTS idx_chapters_stage_2_context_gin ON chapters USING GIN(stage_2_context);

COMMENT ON TABLE chapters IS 'Generated neurosurgery chapters with 14-stage workflow tracking';
COMMENT ON COLUMN chapters.sections IS 'Array of section objects with content';
COMMENT ON COLUMN chapters.stage_2_context IS 'Medical entities extracted, chapter type reasoning';
COMMENT ON COLUMN chapters.stage_3_internal_research IS 'Sources from indexed library';
COMMENT ON COLUMN chapters.stage_5_synthesis_metadata IS 'AI provider, tokens, cost, quality scores';
COMMENT ON COLUMN chapters.stage_6_gaps_detected IS 'Detected content gaps';

-- =========================================================
-- IMAGES TABLE
-- Extracted images from PDFs with AI analysis (Process A)
-- Images are first-class citizens with extensive metadata
-- =========================================================

CREATE TABLE IF NOT EXISTS images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Source
    pdf_id UUID NOT NULL REFERENCES pdfs(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    image_index_on_page INTEGER NOT NULL,

    -- Storage
    file_path VARCHAR(1000) UNIQUE NOT NULL,
    thumbnail_path VARCHAR(1000),
    width INTEGER,
    height INTEGER,
    format VARCHAR(20),
    file_size_bytes INTEGER,

    -- AI Analysis (Claude Vision)
    ai_description TEXT,
    image_type VARCHAR(100),
    anatomical_structures TEXT[],
    clinical_context TEXT,
    quality_score REAL,
    confidence_score REAL,

    -- OCR
    ocr_text TEXT,
    contains_text BOOLEAN NOT NULL DEFAULT FALSE,

    -- Vector embedding for semantic search
    embedding VECTOR(1536),

    -- Metadata
    caption TEXT,
    figure_number VARCHAR(50),

    -- Deduplication
    is_duplicate BOOLEAN NOT NULL DEFAULT FALSE,
    duplicate_of_id UUID REFERENCES images(id) ON DELETE SET NULL,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chk_image_scores CHECK (
        (quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 1)) AND
        (confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1))
    )
);

-- Indexes for images table
CREATE INDEX IF NOT EXISTS idx_images_pdf_id ON images(pdf_id);
CREATE INDEX IF NOT EXISTS idx_images_image_type ON images(image_type);
CREATE INDEX IF NOT EXISTS idx_images_is_duplicate ON images(is_duplicate);
CREATE INDEX IF NOT EXISTS idx_images_created_at ON images(created_at);

-- Vector index for semantic similarity search
CREATE INDEX IF NOT EXISTS idx_images_embedding_cosine ON images USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

COMMENT ON TABLE images IS 'Extracted images with comprehensive AI analysis';
COMMENT ON COLUMN images.ai_description IS 'Claude Vision detailed description';
COMMENT ON COLUMN images.image_type IS 'Type: anatomical_diagram, surgical_photo, mri, ct, etc.';
COMMENT ON COLUMN images.embedding IS 'Vector embedding for semantic image search';

-- =========================================================
-- CITATIONS TABLE
-- Extracted bibliographic references from PDFs (Process A)
-- =========================================================

CREATE TABLE IF NOT EXISTS citations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Source
    pdf_id UUID NOT NULL REFERENCES pdfs(id) ON DELETE CASCADE,

    -- Cited work metadata
    cited_title TEXT,
    cited_authors TEXT[],
    cited_journal VARCHAR(500),
    cited_year INTEGER,
    cited_doi VARCHAR(255),
    cited_pmid VARCHAR(50),

    -- Context
    citation_context TEXT,
    page_number INTEGER,

    -- Network analysis
    citation_count INTEGER NOT NULL DEFAULT 0,
    relevance_score REAL,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chk_citation_count CHECK (citation_count >= 0),
    CONSTRAINT chk_relevance_score CHECK (relevance_score IS NULL OR (relevance_score >= 0 AND relevance_score <= 1))
);

-- Indexes for citations table
CREATE INDEX IF NOT EXISTS idx_citations_pdf_id ON citations(pdf_id);
CREATE INDEX IF NOT EXISTS idx_citations_cited_year ON citations(cited_year);
CREATE INDEX IF NOT EXISTS idx_citations_cited_doi ON citations(cited_doi);
CREATE INDEX IF NOT EXISTS idx_citations_cited_pmid ON citations(cited_pmid);
CREATE INDEX IF NOT EXISTS idx_citations_citation_count ON citations(citation_count);

COMMENT ON TABLE citations IS 'Extracted bibliographic references for citation network';

-- =========================================================
-- CACHE_ANALYTICS TABLE
-- Tracks cache performance and cost savings
-- =========================================================

CREATE TABLE IF NOT EXISTS cache_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Cache type & category
    cache_type VARCHAR(20) NOT NULL,
    cache_category VARCHAR(50) NOT NULL,

    -- Operation
    operation VARCHAR(10) NOT NULL,

    -- Key information
    key_hash VARCHAR(64),

    -- Performance metrics
    cost_saved_usd NUMERIC(10, 4),
    time_saved_ms INTEGER,

    -- Context (optional)
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    chapter_id UUID REFERENCES chapters(id) ON DELETE CASCADE,

    -- Timestamp
    recorded_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chk_cache_type CHECK (cache_type IN ('hot', 'cold')),
    CONSTRAINT chk_cache_category CHECK (cache_category IN ('embedding', 'template', 'structure', 'query', 'synthesis', 'pattern')),
    CONSTRAINT chk_operation CHECK (operation IN ('hit', 'miss', 'set'))
);

-- Indexes for cache_analytics table
CREATE INDEX IF NOT EXISTS idx_cache_analytics_cache_type ON cache_analytics(cache_type);
CREATE INDEX IF NOT EXISTS idx_cache_analytics_cache_category ON cache_analytics(cache_category);
CREATE INDEX IF NOT EXISTS idx_cache_analytics_operation ON cache_analytics(operation);
CREATE INDEX IF NOT EXISTS idx_cache_analytics_key_hash ON cache_analytics(key_hash);
CREATE INDEX IF NOT EXISTS idx_cache_analytics_user_id ON cache_analytics(user_id);
CREATE INDEX IF NOT EXISTS idx_cache_analytics_chapter_id ON cache_analytics(chapter_id);
CREATE INDEX IF NOT EXISTS idx_cache_analytics_recorded_at ON cache_analytics(recorded_at);

COMMENT ON TABLE cache_analytics IS 'Cache performance tracking for observability and cost analysis';

-- =========================================================
-- TRIGGERS FOR UPDATED_AT TIMESTAMPS
-- Automatically update updated_at columns
-- =========================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to all tables with updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_pdfs_updated_at BEFORE UPDATE ON pdfs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_chapters_updated_at BEFORE UPDATE ON chapters FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_images_updated_at BEFORE UPDATE ON images FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_citations_updated_at BEFORE UPDATE ON citations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =========================================================
-- COMPLETION MESSAGE
-- =========================================================

DO $$
BEGIN
    RAISE NOTICE 'Initial schema migration completed successfully';
    RAISE NOTICE 'Tables created: users, pdfs, chapters, images, citations, cache_analytics';
    RAISE NOTICE 'Extensions enabled: uuid-ossp, vector';
    RAISE NOTICE 'Indexes created: All primary indexes and vector indexes';
END $$;
