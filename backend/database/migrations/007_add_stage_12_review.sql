-- Migration: Add Stage 12 Review Column
-- Date: 2025-01-31
-- Description: Add stage_12_review JSONB column to chapters table for AI-powered quality review

-- Add stage_12_review column to store comprehensive AI review results
ALTER TABLE chapters
ADD COLUMN IF NOT EXISTS stage_12_review JSONB;

-- Add comment to describe the column
COMMENT ON COLUMN chapters.stage_12_review IS 'AI-powered quality review: contradictions, readability issues, flow problems, improvement suggestions';

-- Create index for faster queries on review status
CREATE INDEX IF NOT EXISTS idx_chapters_stage_12_review
ON chapters USING gin (stage_12_review);

-- Migration complete
-- This enables Stage 12: Quality Review & Refinement with structured feedback
