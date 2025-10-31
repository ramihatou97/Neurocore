-- Migration 005: Add Gap Analysis Support
-- Phase 2 Week 5: Gap Analysis Feature
-- Date: 2025-10-29

-- ============================================================================
-- Add gap_analysis column to chapters table
-- ============================================================================

-- Add gap_analysis JSONB column to store comprehensive gap analysis results
ALTER TABLE chapters
ADD COLUMN IF NOT EXISTS gap_analysis JSONB;

-- Add index on gap_analysis for faster queries on gap status
CREATE INDEX IF NOT EXISTS idx_chapters_gap_analysis
ON chapters USING gin (gap_analysis);

-- Add index for chapters that require revision based on gap analysis
CREATE INDEX IF NOT EXISTS idx_chapters_requires_revision
ON chapters ((gap_analysis->>'requires_revision'))
WHERE gap_analysis IS NOT NULL;

-- Add index for completeness score queries
CREATE INDEX IF NOT EXISTS idx_chapters_completeness_score
ON chapters (((gap_analysis->>'overall_completeness_score')::float))
WHERE gap_analysis IS NOT NULL;

-- ============================================================================
-- Comments for documentation
-- ============================================================================

COMMENT ON COLUMN chapters.gap_analysis IS
'Phase 2 Week 5: Comprehensive gap analysis results including identified gaps, severity distribution, recommendations, and completeness score. Structure: {analyzed_at, gaps_identified, recommendations, severity_distribution, gap_categories, overall_completeness_score, requires_revision, total_gaps}';

-- ============================================================================
-- Example gap_analysis structure:
-- {
--   "analyzed_at": "2025-10-29T10:00:00Z",
--   "chapter_title": "Glioblastoma Management",
--   "total_sections": 12,
--   "total_gaps": 8,
--   "gaps_identified": [
--     {
--       "type": "missing_critical_information",
--       "severity": "critical",
--       "description": "Complications section missing",
--       "recommendation": "Add comprehensive complications coverage"
--     }
--   ],
--   "severity_distribution": {
--     "critical": 1,
--     "high": 2,
--     "medium": 3,
--     "low": 2
--   },
--   "gap_categories": {
--     "content_completeness": [...],
--     "source_coverage": [...],
--     "section_balance": [...],
--     "temporal_coverage": [...],
--     "critical_information": [...]
--   },
--   "recommendations": [
--     {
--       "priority": 1,
--       "action": "address_critical_gaps",
--       "description": "Immediately address 1 critical gaps",
--       "estimated_effort": "high"
--     }
--   ],
--   "overall_completeness_score": 0.82,
--   "requires_revision": false
-- }
-- ============================================================================

-- Migration complete
SELECT 'Migration 005: Gap Analysis column added successfully' as status;
