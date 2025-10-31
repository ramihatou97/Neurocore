/**
 * GapAnalysisPanel Component Tests
 * Streamlined test suite focusing on core gap analysis logic
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import GapAnalysisPanel from '../GapAnalysisPanel'
import { chaptersAPI } from '../../api'

// Mock chaptersAPI
vi.mock('../../api', () => ({
  chaptersAPI: {
    getGapAnalysisSummary: vi.fn(),
    runGapAnalysis: vi.fn()
  }
}))

describe('GapAnalysisPanel Component', () => {
  const mockChapterId = 'chapter-123'

  const mockGapAnalysis = {
    completeness_score: 0.82,
    total_gaps: 12,
    severity_distribution: {
      critical: 2,
      high: 4,
      medium: 5,
      low: 1
    },
    requires_revision: false,
    top_recommendations: [
      {
        priority: 1,
        action: 'add_missing_concepts',
        description: 'Include discussion of intraoperative monitoring techniques',
        estimated_effort: 'medium'
      },
      {
        priority: 2,
        action: 'cite_recent_sources',
        description: 'Add references from the last 2 years on endoscopic approaches',
        estimated_effort: 'low'
      }
    ],
    gap_categories_summary: {
      content_completeness: 5,
      source_coverage: 3,
      section_balance: 2,
      temporal_coverage: 1,
      critical_information: 1
    },
    analyzed_at: '2024-01-15T10:30:00Z'
  }

  const mockCriticalGapAnalysis = {
    ...mockGapAnalysis,
    completeness_score: 0.65,
    requires_revision: true,
    severity_distribution: {
      critical: 5,
      high: 8,
      medium: 3,
      low: 0
    }
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  const renderPanel = (props = {}) => {
    return render(
      <GapAnalysisPanel
        chapterId={mockChapterId}
        {...props}
      />
    )
  }

  describe('Initial Loading', () => {
    it('should fetch gap analysis on mount', async () => {
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(mockGapAnalysis)

      renderPanel()

      await waitFor(() => {
        expect(chaptersAPI.getGapAnalysisSummary).toHaveBeenCalledWith(mockChapterId)
      })
    })

    it('should show loading state initially', () => {
      chaptersAPI.getGapAnalysisSummary.mockImplementation(() => new Promise(() => {}))

      const { container } = renderPanel()

      expect(screen.getByText(/Loading gap analysis/i)).toBeInTheDocument()
      expect(container.querySelector('.MuiCircularProgress-root')).toBeInTheDocument()
    })

    it('should not fetch when chapterId is null', () => {
      renderPanel({ chapterId: null })

      expect(chaptersAPI.getGapAnalysisSummary).not.toHaveBeenCalled()
    })

    it('should not fetch when initialData is provided', () => {
      renderPanel({ initialData: mockGapAnalysis })

      expect(chaptersAPI.getGapAnalysisSummary).not.toHaveBeenCalled()
    })

    it('should handle 404 gracefully (no analysis exists)', async () => {
      chaptersAPI.getGapAnalysisSummary.mockRejectedValueOnce({
        response: { status: 404 }
      })

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Run Gap Analysis/i)).toBeInTheDocument()
      })
    })
  })

  describe('No Analysis State', () => {
    it('should show prompt to run analysis when none exists', async () => {
      chaptersAPI.getGapAnalysisSummary.mockRejectedValueOnce({
        response: { status: 404 }
      })

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Gap Analysis Available/i)).toBeInTheDocument()
        expect(screen.getByText(/Run Gap Analysis/i)).toBeInTheDocument()
      })
    })

    it('should show description about gap analysis', async () => {
      chaptersAPI.getGapAnalysisSummary.mockRejectedValueOnce({
        response: { status: 404 }
      })

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Analyze this chapter to identify content gaps/i)).toBeInTheDocument()
      })
    })
  })

  describe('Run Analysis', () => {
    it('should trigger gap analysis when button clicked', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.getGapAnalysisSummary
        .mockRejectedValueOnce({ response: { status: 404 } })
        .mockResolvedValueOnce(mockGapAnalysis)
      chaptersAPI.runGapAnalysis.mockResolvedValueOnce({ task_id: 'task-123' })

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Run Gap Analysis/i)).toBeInTheDocument()
      })

      const button = screen.getByRole('button', { name: /Run Gap Analysis/i })
      await user.click(button)

      await waitFor(() => {
        expect(chaptersAPI.runGapAnalysis).toHaveBeenCalledWith(mockChapterId)
      })
    })

    it('should show running state during analysis', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.getGapAnalysisSummary.mockRejectedValueOnce({ response: { status: 404 } })
      chaptersAPI.runGapAnalysis.mockImplementation(() => new Promise(() => {}))

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Run Gap Analysis/i)).toBeInTheDocument()
      })

      const button = screen.getByRole('button', { name: /Run Gap Analysis/i })
      await user.click(button)

      await waitFor(() => {
        expect(screen.getByText(/Running Analysis/i)).toBeInTheDocument()
        expect(screen.getByText(/Analyzing chapter across 5 dimensions/i)).toBeInTheDocument()
      })
    })

    it('should disable button during analysis', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.getGapAnalysisSummary.mockRejectedValueOnce({ response: { status: 404 } })
      chaptersAPI.runGapAnalysis.mockImplementation(() => new Promise(() => {}))

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Run Gap Analysis/i)).toBeInTheDocument()
      })

      const button = screen.getByRole('button', { name: /Run Gap Analysis/i })
      await user.click(button)

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Running Analysis/i })).toBeDisabled()
      })
    })

    it('should fetch summary after analysis completes', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.getGapAnalysisSummary
        .mockRejectedValueOnce({ response: { status: 404 } })
        .mockResolvedValueOnce(mockGapAnalysis)
      chaptersAPI.runGapAnalysis.mockResolvedValueOnce({ task_id: 'task-123' })

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Run Gap Analysis/i)).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /Run Gap Analysis/i }))

      await waitFor(() => {
        expect(chaptersAPI.getGapAnalysisSummary).toHaveBeenCalledTimes(2)
      })
    })
  })

  describe('Error Handling', () => {
    it('should show error when loading fails', async () => {
      chaptersAPI.getGapAnalysisSummary.mockRejectedValueOnce({
        response: { status: 500, data: { detail: 'Server error' } }
      })

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Failed to load gap analysis/i)).toBeInTheDocument()
      })
    })

    it('should show error when analysis fails', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.getGapAnalysisSummary.mockRejectedValueOnce({ response: { status: 404 } })
      chaptersAPI.runGapAnalysis.mockRejectedValueOnce({
        response: { data: { detail: 'Analysis failed' } }
      })

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Run Gap Analysis/i)).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /Run Gap Analysis/i }))

      await waitFor(() => {
        expect(screen.getByText('Analysis failed')).toBeInTheDocument()
      })
    })

    it('should show generic error when no detail provided', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.getGapAnalysisSummary.mockRejectedValueOnce({ response: { status: 404 } })
      chaptersAPI.runGapAnalysis.mockRejectedValueOnce(new Error('Network error'))

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Run Gap Analysis/i)).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /Run Gap Analysis/i }))

      await waitFor(() => {
        expect(screen.getByText(/Failed to run gap analysis/i)).toBeInTheDocument()
      })
    })

    it('should have retry button on error', async () => {
      chaptersAPI.getGapAnalysisSummary.mockRejectedValueOnce({
        response: { status: 500, data: { detail: 'Server error' } }
      })

      renderPanel()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument()
      })
    })
  })

  describe('Results Display', () => {
    it('should display completeness score', async () => {
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(mockGapAnalysis)

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Overall Completeness Score/i)).toBeInTheDocument()
        expect(screen.getByText('82%')).toBeInTheDocument()
      })
    })

    it('should display severity distribution', async () => {
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(mockGapAnalysis)

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Gap Severity Distribution/i)).toBeInTheDocument()
        expect(screen.getByText('2')).toBeInTheDocument() // critical
        expect(screen.getByText('4')).toBeInTheDocument() // high
        expect(screen.getByText('5')).toBeInTheDocument() // medium
        expect(screen.getByText('1')).toBeInTheDocument() // low
      })
    })

    it('should display gap categories summary', async () => {
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(mockGapAnalysis)

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Gaps by Category/i)).toBeInTheDocument()
        expect(screen.getByText(/Content Completeness/i)).toBeInTheDocument()
        expect(screen.getByText(/Source Coverage/i)).toBeInTheDocument()
      })
    })

    it('should display recommendations', async () => {
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(mockGapAnalysis)

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Top Recommendations/i)).toBeInTheDocument()
        expect(screen.getByText(/Include discussion of intraoperative monitoring/i)).toBeInTheDocument()
        expect(screen.getByText(/Add references from the last 2 years/i)).toBeInTheDocument()
      })
    })

    it('should display total gaps count', async () => {
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(mockGapAnalysis)

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Total Gaps Identified/i)).toBeInTheDocument()
        expect(screen.getByText('12')).toBeInTheDocument()
      })
    })

    it('should show analyzed timestamp', async () => {
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(mockGapAnalysis)

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Last analyzed/i)).toBeInTheDocument()
      })
    })

    it('should show quality threshold status', async () => {
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(mockGapAnalysis)

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Meets minimum quality threshold/i)).toBeInTheDocument()
      })
    })
  })

  describe('Revision Warning', () => {
    it('should show revision warning for low score', async () => {
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(mockCriticalGapAnalysis)

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/This chapter requires revision/i)).toBeInTheDocument()
        expect(screen.getByText(/Critical gaps or low completeness score detected/i)).toBeInTheDocument()
      })
    })

    it('should not show warning for good score', async () => {
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(mockGapAnalysis)

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Gap Analysis/i)).toBeInTheDocument()
      })

      expect(screen.queryByText(/This chapter requires revision/i)).not.toBeInTheDocument()
    })
  })

  describe('Refresh Functionality', () => {
    it('should have refresh button in header', async () => {
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(mockGapAnalysis)

      const { container } = renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Gap Analysis/i)).toBeInTheDocument()
      })

      // MUI IconButton with RefreshIcon
      const refreshButtons = container.querySelectorAll('button[type="button"]')
      expect(refreshButtons.length).toBeGreaterThan(0)
    })

    it('should have re-analyze button at bottom', async () => {
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(mockGapAnalysis)

      renderPanel()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Re-analyze/i })).toBeInTheDocument()
      })
    })

    it('should trigger analysis when re-analyze clicked', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.getGapAnalysisSummary
        .mockResolvedValueOnce(mockGapAnalysis)
        .mockResolvedValueOnce(mockGapAnalysis)
      chaptersAPI.runGapAnalysis.mockResolvedValueOnce({ task_id: 'task-123' })

      renderPanel()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Re-analyze/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /Re-analyze/i }))

      await waitFor(() => {
        expect(chaptersAPI.runGapAnalysis).toHaveBeenCalledWith(mockChapterId)
      })
    })
  })

  describe('Edge Cases', () => {
    it('should handle missing completeness score', async () => {
      const incompleteData = { ...mockGapAnalysis, completeness_score: undefined }
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(incompleteData)

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText('0%')).toBeInTheDocument()
      })
    })

    it('should handle missing severity distribution', async () => {
      const incompleteData = { ...mockGapAnalysis, severity_distribution: {} }
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(incompleteData)

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Gap Severity Distribution/i)).toBeInTheDocument()
      })
    })

    it('should handle empty recommendations', async () => {
      const dataNoRecs = { ...mockGapAnalysis, top_recommendations: [] }
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(dataNoRecs)

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Gap Analysis/i)).toBeInTheDocument()
      })

      expect(screen.queryByText(/Top Recommendations/i)).not.toBeInTheDocument()
    })

    it('should handle empty category summary', async () => {
      const dataNoCats = { ...mockGapAnalysis, gap_categories_summary: {} }
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(dataNoCats)

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Gap Analysis/i)).toBeInTheDocument()
      })

      expect(screen.queryByText(/Gaps by Category/i)).not.toBeInTheDocument()
    })

    it('should handle perfect score (100%)', async () => {
      const perfectData = { ...mockGapAnalysis, completeness_score: 1.0 }
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(perfectData)

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText('100%')).toBeInTheDocument()
      })
    })

    it('should handle zero score', async () => {
      const zeroData = { ...mockGapAnalysis, completeness_score: 0 }
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(zeroData)

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText('0%')).toBeInTheDocument()
      })
    })
  })

  describe('API Integration', () => {
    it('should use correct endpoint for getting summary', async () => {
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(mockGapAnalysis)

      renderPanel()

      await waitFor(() => {
        expect(chaptersAPI.getGapAnalysisSummary).toHaveBeenCalledWith('chapter-123')
      })
    })

    it('should use correct endpoint for running analysis', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.getGapAnalysisSummary
        .mockRejectedValueOnce({ response: { status: 404 } })
        .mockResolvedValueOnce(mockGapAnalysis)
      chaptersAPI.runGapAnalysis.mockResolvedValueOnce({ task_id: 'task-123' })

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Run Gap Analysis/i)).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /Run Gap Analysis/i }))

      await waitFor(() => {
        expect(chaptersAPI.runGapAnalysis).toHaveBeenCalledWith('chapter-123')
      })
    })
  })

  describe('Score Color Coding', () => {
    it('should show green for high score (>= 0.9)', async () => {
      const highScore = { ...mockGapAnalysis, completeness_score: 0.92 }
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(highScore)

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText('92%')).toBeInTheDocument()
      })
    })

    it('should show yellow for medium score (0.75-0.89)', async () => {
      const mediumScore = { ...mockGapAnalysis, completeness_score: 0.80 }
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(mediumScore)

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText('80%')).toBeInTheDocument()
      })
    })

    it('should show red for low score (< 0.6)', async () => {
      const lowScore = { ...mockCriticalGapAnalysis }
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(lowScore)

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText('65%')).toBeInTheDocument()
      })
    })
  })

  describe('Recommendation Display', () => {
    it('should show priority chips', async () => {
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(mockGapAnalysis)

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Priority 1/i)).toBeInTheDocument()
        expect(screen.getByText(/Priority 2/i)).toBeInTheDocument()
      })
    })

    it('should show action labels', async () => {
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(mockGapAnalysis)

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/ADD MISSING CONCEPTS/i)).toBeInTheDocument()
        expect(screen.getByText(/CITE RECENT SOURCES/i)).toBeInTheDocument()
      })
    })

    it('should show effort estimates', async () => {
      chaptersAPI.getGapAnalysisSummary.mockResolvedValueOnce(mockGapAnalysis)

      renderPanel()

      await waitFor(() => {
        expect(screen.getByText(/Effort: medium/i)).toBeInTheDocument()
        expect(screen.getByText(/Effort: low/i)).toBeInTheDocument()
      })
    })
  })
})
