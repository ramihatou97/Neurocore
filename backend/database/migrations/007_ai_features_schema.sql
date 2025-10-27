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
