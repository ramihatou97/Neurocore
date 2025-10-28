time="2025-10-28T00:09:18-04:00" level=warning msg="/Users/ramihatoum/Desktop/The neurosurgical core of knowledge/docker-compose.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion"
--
-- PostgreSQL database dump
--

-- Dumped from database version 15.4 (Debian 15.4-2.pgdg120+1)
-- Dumped by pg_dump version 15.4 (Debian 15.4-2.pgdg120+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: nsurg_admin
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO nsurg_admin;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: cache_analytics; Type: TABLE; Schema: public; Owner: nsurg_admin
--

CREATE TABLE public.cache_analytics (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    cache_type character varying(20) NOT NULL,
    cache_category character varying(50) NOT NULL,
    operation character varying(10) NOT NULL,
    key_hash character varying(64),
    cost_saved_usd numeric(10,4),
    time_saved_ms integer,
    user_id uuid,
    chapter_id uuid,
    recorded_at timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_cache_category CHECK (((cache_category)::text = ANY ((ARRAY['embedding'::character varying, 'template'::character varying, 'structure'::character varying, 'query'::character varying, 'synthesis'::character varying, 'pattern'::character varying])::text[]))),
    CONSTRAINT chk_cache_type CHECK (((cache_type)::text = ANY ((ARRAY['hot'::character varying, 'cold'::character varying])::text[]))),
    CONSTRAINT chk_operation CHECK (((operation)::text = ANY ((ARRAY['hit'::character varying, 'miss'::character varying, 'set'::character varying])::text[])))
);


ALTER TABLE public.cache_analytics OWNER TO nsurg_admin;

--
-- Name: TABLE cache_analytics; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON TABLE public.cache_analytics IS 'Cache performance tracking for observability and cost analysis';


--
-- Name: chapters; Type: TABLE; Schema: public; Owner: nsurg_admin
--

CREATE TABLE public.chapters (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    title text NOT NULL,
    chapter_type character varying(50),
    sections jsonb,
    structure_metadata jsonb,
    stage_2_context jsonb,
    stage_3_internal_research jsonb,
    stage_4_external_research jsonb,
    stage_5_synthesis_metadata jsonb,
    stage_6_gaps_detected jsonb,
    stage_8_integration_log jsonb,
    depth_score real,
    coverage_score real,
    currency_score real,
    evidence_score real,
    version character varying(20) DEFAULT '1.0'::character varying NOT NULL,
    is_current_version boolean DEFAULT true NOT NULL,
    parent_version_id uuid,
    generation_status character varying(50) DEFAULT 'draft'::character varying NOT NULL,
    author_id uuid NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    embedding public.vector(1536),
    embedding_generated_at timestamp without time zone,
    embedding_model character varying(100) DEFAULT 'text-embedding-ada-002'::character varying,
    CONSTRAINT chk_chapter_type CHECK (((chapter_type)::text = ANY ((ARRAY['surgical_disease'::character varying, 'pure_anatomy'::character varying, 'surgical_technique'::character varying])::text[]))),
    CONSTRAINT chk_generation_status CHECK (((generation_status)::text = ANY ((ARRAY['stage_1_input'::character varying, 'stage_2_context'::character varying, 'stage_3_research_internal'::character varying, 'stage_4_research_external'::character varying, 'stage_5_planning'::character varying, 'stage_6_generation'::character varying, 'stage_7_images'::character varying, 'stage_8_citations'::character varying, 'stage_9_qa'::character varying, 'stage_10_fact_check'::character varying, 'stage_11_formatting'::character varying, 'stage_12_review'::character varying, 'stage_13_finalization'::character varying, 'completed'::character varying, 'failed'::character varying])::text[]))),
    CONSTRAINT chk_quality_scores CHECK ((((depth_score IS NULL) OR ((depth_score >= (0)::double precision) AND (depth_score <= (1)::double precision))) AND ((coverage_score IS NULL) OR ((coverage_score >= (0)::double precision) AND (coverage_score <= (1)::double precision))) AND ((currency_score IS NULL) OR ((currency_score >= (0)::double precision) AND (currency_score <= (1)::double precision))) AND ((evidence_score IS NULL) OR ((evidence_score >= (0)::double precision) AND (evidence_score <= (1)::double precision)))))
);


ALTER TABLE public.chapters OWNER TO nsurg_admin;

--
-- Name: TABLE chapters; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON TABLE public.chapters IS 'Generated neurosurgery chapters with 14-stage workflow tracking';


--
-- Name: COLUMN chapters.sections; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON COLUMN public.chapters.sections IS 'Array of section objects with content';


--
-- Name: COLUMN chapters.stage_2_context; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON COLUMN public.chapters.stage_2_context IS 'Medical entities extracted, chapter type reasoning';


--
-- Name: COLUMN chapters.stage_3_internal_research; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON COLUMN public.chapters.stage_3_internal_research IS 'Sources from indexed library';


--
-- Name: COLUMN chapters.stage_5_synthesis_metadata; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON COLUMN public.chapters.stage_5_synthesis_metadata IS 'AI provider, tokens, cost, quality scores';


--
-- Name: COLUMN chapters.stage_6_gaps_detected; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON COLUMN public.chapters.stage_6_gaps_detected IS 'Detected content gaps';


--
-- Name: COLUMN chapters.embedding; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON COLUMN public.chapters.embedding IS 'OpenAI embedding vector for chapter content';


--
-- Name: COLUMN chapters.embedding_generated_at; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON COLUMN public.chapters.embedding_generated_at IS 'Timestamp when embedding was generated';


--
-- Name: COLUMN chapters.embedding_model; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON COLUMN public.chapters.embedding_model IS 'Model used to generate embedding';


--
-- Name: citations; Type: TABLE; Schema: public; Owner: nsurg_admin
--

CREATE TABLE public.citations (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    pdf_id uuid NOT NULL,
    cited_title text,
    cited_authors text[],
    cited_journal character varying(500),
    cited_year integer,
    cited_doi character varying(255),
    cited_pmid character varying(50),
    citation_context text,
    page_number integer,
    citation_count integer DEFAULT 0 NOT NULL,
    relevance_score real,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_citation_count CHECK ((citation_count >= 0)),
    CONSTRAINT chk_relevance_score CHECK (((relevance_score IS NULL) OR ((relevance_score >= (0)::double precision) AND (relevance_score <= (1)::double precision))))
);


ALTER TABLE public.citations OWNER TO nsurg_admin;

--
-- Name: TABLE citations; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON TABLE public.citations IS 'Extracted bibliographic references for citation network';


--
-- Name: images; Type: TABLE; Schema: public; Owner: nsurg_admin
--

CREATE TABLE public.images (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    pdf_id uuid NOT NULL,
    page_number integer NOT NULL,
    image_index_on_page integer NOT NULL,
    file_path character varying(1000) NOT NULL,
    thumbnail_path character varying(1000),
    width integer,
    height integer,
    format character varying(20),
    file_size_bytes integer,
    ai_description text,
    image_type character varying(100),
    anatomical_structures text[],
    clinical_context text,
    quality_score real,
    confidence_score real,
    ocr_text text,
    contains_text boolean DEFAULT false NOT NULL,
    embedding public.vector(1536),
    caption text,
    figure_number character varying(50),
    is_duplicate boolean DEFAULT false NOT NULL,
    duplicate_of_id uuid,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    extracted_text text,
    embedding_generated_at timestamp without time zone,
    embedding_model character varying(100) DEFAULT 'text-embedding-ada-002'::character varying,
    ocr_performed boolean DEFAULT false,
    ocr_language character varying(10) DEFAULT 'en'::character varying,
    CONSTRAINT chk_image_scores CHECK ((((quality_score IS NULL) OR ((quality_score >= (0)::double precision) AND (quality_score <= (1)::double precision))) AND ((confidence_score IS NULL) OR ((confidence_score >= (0)::double precision) AND (confidence_score <= (1)::double precision)))))
);


ALTER TABLE public.images OWNER TO nsurg_admin;

--
-- Name: TABLE images; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON TABLE public.images IS 'Extracted images with comprehensive AI analysis';


--
-- Name: COLUMN images.ai_description; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON COLUMN public.images.ai_description IS 'Claude Vision detailed description';


--
-- Name: COLUMN images.image_type; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON COLUMN public.images.image_type IS 'Type: anatomical_diagram, surgical_photo, mri, ct, etc.';


--
-- Name: COLUMN images.embedding; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON COLUMN public.images.embedding IS 'Embedding vector for image content (vision or OCR text)';


--
-- Name: COLUMN images.extracted_text; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON COLUMN public.images.extracted_text IS 'OCR text extracted from image';


--
-- Name: COLUMN images.embedding_generated_at; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON COLUMN public.images.embedding_generated_at IS 'Timestamp when embedding was generated';


--
-- Name: COLUMN images.embedding_model; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON COLUMN public.images.embedding_model IS 'Model used to generate embedding';


--
-- Name: COLUMN images.ocr_performed; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON COLUMN public.images.ocr_performed IS 'Whether OCR text extraction was performed';


--
-- Name: COLUMN images.ocr_language; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON COLUMN public.images.ocr_language IS 'Language code for OCR (e.g., en, fr, de)';


--
-- Name: pdfs; Type: TABLE; Schema: public; Owner: nsurg_admin
--

CREATE TABLE public.pdfs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    filename character varying(500) NOT NULL,
    file_path character varying(1000) NOT NULL,
    file_size_bytes bigint,
    total_pages integer,
    title text,
    authors text[],
    publication_year integer,
    journal character varying(500),
    doi character varying(255),
    pmid character varying(50),
    indexing_status character varying(50) DEFAULT 'pending'::character varying NOT NULL,
    text_extracted boolean DEFAULT false NOT NULL,
    images_extracted boolean DEFAULT false NOT NULL,
    embeddings_generated boolean DEFAULT false NOT NULL,
    uploaded_at timestamp without time zone DEFAULT now() NOT NULL,
    indexed_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    embedding public.vector(1536),
    extracted_text text,
    embedding_generated_at timestamp without time zone,
    embedding_model character varying(100) DEFAULT 'text-embedding-ada-002'::character varying,
    CONSTRAINT chk_indexing_status CHECK (((indexing_status)::text = ANY ((ARRAY['uploaded'::character varying, 'extracting_text'::character varying, 'text_extracted'::character varying, 'extracting_images'::character varying, 'images_extracted'::character varying, 'text_extraction_failed'::character varying, 'image_extraction_failed'::character varying, 'pending'::character varying, 'processing'::character varying, 'completed'::character varying, 'failed'::character varying])::text[])))
);


ALTER TABLE public.pdfs OWNER TO nsurg_admin;

--
-- Name: TABLE pdfs; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON TABLE public.pdfs IS 'Uploaded research papers and textbooks for indexation';


--
-- Name: COLUMN pdfs.indexing_status; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON COLUMN public.pdfs.indexing_status IS 'Status: pending, processing, completed, failed';


--
-- Name: COLUMN pdfs.embedding; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON COLUMN public.pdfs.embedding IS 'OpenAI embedding vector (1536 dimensions) for semantic search';


--
-- Name: COLUMN pdfs.extracted_text; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON COLUMN public.pdfs.extracted_text IS 'Full text content extracted from PDF for search and analysis';


--
-- Name: COLUMN pdfs.embedding_generated_at; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON COLUMN public.pdfs.embedding_generated_at IS 'Timestamp when embedding was generated';


--
-- Name: COLUMN pdfs.embedding_model; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON COLUMN public.pdfs.embedding_model IS 'Model used to generate embedding (e.g., text-embedding-ada-002)';


--
-- Name: users; Type: TABLE; Schema: public; Owner: nsurg_admin
--

CREATE TABLE public.users (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    email character varying(255) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    full_name character varying(255),
    is_active boolean DEFAULT true NOT NULL,
    is_admin boolean DEFAULT false NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.users OWNER TO nsurg_admin;

--
-- Name: TABLE users; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON TABLE public.users IS 'Authenticated users for the system';


--
-- Name: COLUMN users.email; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON COLUMN public.users.email IS 'User email address - must be unique';


--
-- Name: COLUMN users.hashed_password; Type: COMMENT; Schema: public; Owner: nsurg_admin
--

COMMENT ON COLUMN public.users.hashed_password IS 'Bcrypt hashed password - never store plain text';


--
-- Data for Name: cache_analytics; Type: TABLE DATA; Schema: public; Owner: nsurg_admin
--

COPY public.cache_analytics (id, cache_type, cache_category, operation, key_hash, cost_saved_usd, time_saved_ms, user_id, chapter_id, recorded_at) FROM stdin;
\.


--
-- Data for Name: chapters; Type: TABLE DATA; Schema: public; Owner: nsurg_admin
--

COPY public.chapters (id, title, chapter_type, sections, structure_metadata, stage_2_context, stage_3_internal_research, stage_4_external_research, stage_5_synthesis_metadata, stage_6_gaps_detected, stage_8_integration_log, depth_score, coverage_score, currency_score, evidence_score, version, is_current_version, parent_version_id, generation_status, author_id, created_at, updated_at, embedding, embedding_generated_at, embedding_model) FROM stdin;
\.


--
-- Data for Name: citations; Type: TABLE DATA; Schema: public; Owner: nsurg_admin
--

COPY public.citations (id, pdf_id, cited_title, cited_authors, cited_journal, cited_year, cited_doi, cited_pmid, citation_context, page_number, citation_count, relevance_score, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: images; Type: TABLE DATA; Schema: public; Owner: nsurg_admin
--

COPY public.images (id, pdf_id, page_number, image_index_on_page, file_path, thumbnail_path, width, height, format, file_size_bytes, ai_description, image_type, anatomical_structures, clinical_context, quality_score, confidence_score, ocr_text, contains_text, embedding, caption, figure_number, is_duplicate, duplicate_of_id, created_at, updated_at, extracted_text, embedding_generated_at, embedding_model, ocr_performed, ocr_language) FROM stdin;
\.


--
-- Data for Name: pdfs; Type: TABLE DATA; Schema: public; Owner: nsurg_admin
--

COPY public.pdfs (id, filename, file_path, file_size_bytes, total_pages, title, authors, publication_year, journal, doi, pmid, indexing_status, text_extracted, images_extracted, embeddings_generated, uploaded_at, indexed_at, created_at, updated_at, embedding, extracted_text, embedding_generated_at, embedding_model) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: nsurg_admin
--

COPY public.users (id, email, hashed_password, full_name, is_active, is_admin, created_at, updated_at) FROM stdin;
\.


--
-- Name: cache_analytics cache_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: nsurg_admin
--

ALTER TABLE ONLY public.cache_analytics
    ADD CONSTRAINT cache_analytics_pkey PRIMARY KEY (id);


--
-- Name: chapters chapters_pkey; Type: CONSTRAINT; Schema: public; Owner: nsurg_admin
--

ALTER TABLE ONLY public.chapters
    ADD CONSTRAINT chapters_pkey PRIMARY KEY (id);


--
-- Name: citations citations_pkey; Type: CONSTRAINT; Schema: public; Owner: nsurg_admin
--

ALTER TABLE ONLY public.citations
    ADD CONSTRAINT citations_pkey PRIMARY KEY (id);


--
-- Name: images images_file_path_key; Type: CONSTRAINT; Schema: public; Owner: nsurg_admin
--

ALTER TABLE ONLY public.images
    ADD CONSTRAINT images_file_path_key UNIQUE (file_path);


--
-- Name: images images_pkey; Type: CONSTRAINT; Schema: public; Owner: nsurg_admin
--

ALTER TABLE ONLY public.images
    ADD CONSTRAINT images_pkey PRIMARY KEY (id);


--
-- Name: pdfs pdfs_doi_key; Type: CONSTRAINT; Schema: public; Owner: nsurg_admin
--

ALTER TABLE ONLY public.pdfs
    ADD CONSTRAINT pdfs_doi_key UNIQUE (doi);


--
-- Name: pdfs pdfs_file_path_key; Type: CONSTRAINT; Schema: public; Owner: nsurg_admin
--

ALTER TABLE ONLY public.pdfs
    ADD CONSTRAINT pdfs_file_path_key UNIQUE (file_path);


--
-- Name: pdfs pdfs_pkey; Type: CONSTRAINT; Schema: public; Owner: nsurg_admin
--

ALTER TABLE ONLY public.pdfs
    ADD CONSTRAINT pdfs_pkey PRIMARY KEY (id);


--
-- Name: pdfs pdfs_pmid_key; Type: CONSTRAINT; Schema: public; Owner: nsurg_admin
--

ALTER TABLE ONLY public.pdfs
    ADD CONSTRAINT pdfs_pmid_key UNIQUE (pmid);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: nsurg_admin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: nsurg_admin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_cache_analytics_cache_category; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_cache_analytics_cache_category ON public.cache_analytics USING btree (cache_category);


--
-- Name: idx_cache_analytics_cache_type; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_cache_analytics_cache_type ON public.cache_analytics USING btree (cache_type);


--
-- Name: idx_cache_analytics_chapter_id; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_cache_analytics_chapter_id ON public.cache_analytics USING btree (chapter_id);


--
-- Name: idx_cache_analytics_key_hash; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_cache_analytics_key_hash ON public.cache_analytics USING btree (key_hash);


--
-- Name: idx_cache_analytics_operation; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_cache_analytics_operation ON public.cache_analytics USING btree (operation);


--
-- Name: idx_cache_analytics_recorded_at; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_cache_analytics_recorded_at ON public.cache_analytics USING btree (recorded_at);


--
-- Name: idx_cache_analytics_user_id; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_cache_analytics_user_id ON public.cache_analytics USING btree (user_id);


--
-- Name: idx_chapters_author_id; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_chapters_author_id ON public.chapters USING btree (author_id);


--
-- Name: idx_chapters_chapter_type; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_chapters_chapter_type ON public.chapters USING btree (chapter_type);


--
-- Name: idx_chapters_created_at; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_chapters_created_at ON public.chapters USING btree (created_at);


--
-- Name: idx_chapters_embeddings_generated; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_chapters_embeddings_generated ON public.chapters USING btree (embedding) WHERE (embedding IS NULL);


--
-- Name: idx_chapters_generation_status; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_chapters_generation_status ON public.chapters USING btree (generation_status);


--
-- Name: idx_chapters_is_current_version; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_chapters_is_current_version ON public.chapters USING btree (is_current_version);


--
-- Name: idx_chapters_sections_gin; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_chapters_sections_gin ON public.chapters USING gin (sections);


--
-- Name: idx_chapters_stage_2_context_gin; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_chapters_stage_2_context_gin ON public.chapters USING gin (stage_2_context);


--
-- Name: idx_citations_citation_count; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_citations_citation_count ON public.citations USING btree (citation_count);


--
-- Name: idx_citations_cited_doi; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_citations_cited_doi ON public.citations USING btree (cited_doi);


--
-- Name: idx_citations_cited_pmid; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_citations_cited_pmid ON public.citations USING btree (cited_pmid);


--
-- Name: idx_citations_cited_year; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_citations_cited_year ON public.citations USING btree (cited_year);


--
-- Name: idx_citations_pdf_id; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_citations_pdf_id ON public.citations USING btree (pdf_id);


--
-- Name: idx_images_created_at; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_images_created_at ON public.images USING btree (created_at);


--
-- Name: idx_images_embedding_cosine; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_images_embedding_cosine ON public.images USING ivfflat (embedding public.vector_cosine_ops) WITH (lists='100');


--
-- Name: idx_images_embeddings_generated; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_images_embeddings_generated ON public.images USING btree (embedding) WHERE (embedding IS NULL);


--
-- Name: idx_images_image_type; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_images_image_type ON public.images USING btree (image_type);


--
-- Name: idx_images_is_duplicate; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_images_is_duplicate ON public.images USING btree (is_duplicate);


--
-- Name: idx_images_pdf_id; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_images_pdf_id ON public.images USING btree (pdf_id);


--
-- Name: idx_pdfs_doi; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_pdfs_doi ON public.pdfs USING btree (doi);


--
-- Name: idx_pdfs_embeddings_generated; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_pdfs_embeddings_generated ON public.pdfs USING btree (embeddings_generated, embedding) WHERE (embedding IS NULL);


--
-- Name: idx_pdfs_indexing_status; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_pdfs_indexing_status ON public.pdfs USING btree (indexing_status);


--
-- Name: idx_pdfs_pmid; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_pdfs_pmid ON public.pdfs USING btree (pmid);


--
-- Name: idx_pdfs_publication_year; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_pdfs_publication_year ON public.pdfs USING btree (publication_year);


--
-- Name: idx_pdfs_uploaded_at; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_pdfs_uploaded_at ON public.pdfs USING btree (uploaded_at);


--
-- Name: idx_users_created_at; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_users_created_at ON public.users USING btree (created_at);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- Name: idx_users_is_active; Type: INDEX; Schema: public; Owner: nsurg_admin
--

CREATE INDEX idx_users_is_active ON public.users USING btree (is_active);


--
-- Name: chapters update_chapters_updated_at; Type: TRIGGER; Schema: public; Owner: nsurg_admin
--

CREATE TRIGGER update_chapters_updated_at BEFORE UPDATE ON public.chapters FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: citations update_citations_updated_at; Type: TRIGGER; Schema: public; Owner: nsurg_admin
--

CREATE TRIGGER update_citations_updated_at BEFORE UPDATE ON public.citations FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: images update_images_updated_at; Type: TRIGGER; Schema: public; Owner: nsurg_admin
--

CREATE TRIGGER update_images_updated_at BEFORE UPDATE ON public.images FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: pdfs update_pdfs_updated_at; Type: TRIGGER; Schema: public; Owner: nsurg_admin
--

CREATE TRIGGER update_pdfs_updated_at BEFORE UPDATE ON public.pdfs FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: users update_users_updated_at; Type: TRIGGER; Schema: public; Owner: nsurg_admin
--

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: cache_analytics cache_analytics_chapter_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nsurg_admin
--

ALTER TABLE ONLY public.cache_analytics
    ADD CONSTRAINT cache_analytics_chapter_id_fkey FOREIGN KEY (chapter_id) REFERENCES public.chapters(id) ON DELETE CASCADE;


--
-- Name: cache_analytics cache_analytics_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nsurg_admin
--

ALTER TABLE ONLY public.cache_analytics
    ADD CONSTRAINT cache_analytics_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: chapters chapters_author_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nsurg_admin
--

ALTER TABLE ONLY public.chapters
    ADD CONSTRAINT chapters_author_id_fkey FOREIGN KEY (author_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: chapters chapters_parent_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nsurg_admin
--

ALTER TABLE ONLY public.chapters
    ADD CONSTRAINT chapters_parent_version_id_fkey FOREIGN KEY (parent_version_id) REFERENCES public.chapters(id) ON DELETE SET NULL;


--
-- Name: citations citations_pdf_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nsurg_admin
--

ALTER TABLE ONLY public.citations
    ADD CONSTRAINT citations_pdf_id_fkey FOREIGN KEY (pdf_id) REFERENCES public.pdfs(id) ON DELETE CASCADE;


--
-- Name: images images_duplicate_of_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nsurg_admin
--

ALTER TABLE ONLY public.images
    ADD CONSTRAINT images_duplicate_of_id_fkey FOREIGN KEY (duplicate_of_id) REFERENCES public.images(id) ON DELETE SET NULL;


--
-- Name: images images_pdf_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nsurg_admin
--

ALTER TABLE ONLY public.images
    ADD CONSTRAINT images_pdf_id_fkey FOREIGN KEY (pdf_id) REFERENCES public.pdfs(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

