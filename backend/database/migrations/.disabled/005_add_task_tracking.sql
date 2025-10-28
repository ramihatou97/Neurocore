-- Migration: Add task tracking table for background jobs
-- Purpose: Track Celery task status and progress for PDF processing

-- Create tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id VARCHAR(255) UNIQUE NOT NULL,  -- Celery task ID
    task_type VARCHAR(100) NOT NULL,       -- Type: pdf_processing, image_analysis, etc.
    status VARCHAR(50) NOT NULL,           -- queued, processing, completed, failed
    progress INTEGER DEFAULT 0,            -- Progress percentage (0-100)
    total_steps INTEGER DEFAULT 0,         -- Total number of steps
    current_step INTEGER DEFAULT 0,        -- Current step number
    entity_id UUID,                        -- Related entity (PDF ID, Chapter ID, etc.)
    entity_type VARCHAR(50),               -- Entity type: pdf, chapter, image
    result JSONB,                          -- Task result data
    error TEXT,                            -- Error message if failed
    started_at TIMESTAMP,                  -- Task start time
    completed_at TIMESTAMP,                -- Task completion time
    created_by UUID REFERENCES users(id),  -- User who initiated the task
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT chk_status CHECK (status IN (
        'queued', 'processing', 'completed', 'failed', 'cancelled'
    )),
    CONSTRAINT chk_progress CHECK (progress >= 0 AND progress <= 100)
);

-- Create indexes for task queries
CREATE INDEX IF NOT EXISTS idx_tasks_task_id ON tasks(task_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_entity ON tasks(entity_id, entity_type);
CREATE INDEX IF NOT EXISTS idx_tasks_created_by ON tasks(created_by);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at DESC);

-- Create trigger for updated_at
CREATE OR REPLACE FUNCTION update_tasks_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_tasks_updated_at();

-- Add processing timestamps to PDFs table (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pdfs' AND column_name = 'processing_started_at'
    ) THEN
        ALTER TABLE pdfs ADD COLUMN processing_started_at NUMERIC;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pdfs' AND column_name = 'processing_completed_at'
    ) THEN
        ALTER TABLE pdfs ADD COLUMN processing_completed_at NUMERIC;
    END IF;
END $$;

-- Add analysis metadata to images table (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'images' AND column_name = 'analysis_metadata'
    ) THEN
        ALTER TABLE images ADD COLUMN analysis_metadata JSONB;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'images' AND column_name = 'analysis_confidence'
    ) THEN
        ALTER TABLE images ADD COLUMN analysis_confidence NUMERIC DEFAULT 0.0;
    END IF;
END $$;

-- Add citations to PDFs table (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pdfs' AND column_name = 'citations'
    ) THEN
        ALTER TABLE pdfs ADD COLUMN citations JSONB;
    END IF;
END $$;

-- Create Task model in SQLAlchemy (documentation)
COMMENT ON TABLE tasks IS 'Background task tracking for Celery jobs';
COMMENT ON COLUMN tasks.task_id IS 'Celery task UUID for status lookups';
COMMENT ON COLUMN tasks.progress IS 'Task completion percentage (0-100)';
COMMENT ON COLUMN tasks.entity_id IS 'ID of related entity (PDF, Chapter, etc.)';
COMMENT ON COLUMN tasks.result IS 'JSON result data from completed task';
