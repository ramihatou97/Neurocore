/**
 * TagDisplay Component Tests
 * Comprehensive test suite for TagDisplay component
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TagDisplay from '../TagDisplay'

describe('TagDisplay Component', () => {
  let mockFetch

  beforeEach(() => {
    // Mock localStorage
    Storage.prototype.getItem = vi.fn(() => 'mock-token')

    // Mock fetch
    mockFetch = vi.fn()
    global.fetch = mockFetch
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  const renderTagDisplay = (props = {}) => {
    const defaultProps = {
      contentType: 'chapter',
      contentId: '123',
      contentText: 'Sample content text for tagging',
      contentTitle: 'Sample Title',
      ...props,
    }
    return render(<TagDisplay {...defaultProps} />)
  }

  describe('Initial Rendering', () => {
    it('should render tags section', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ tags: [] }),
      })

      renderTagDisplay()

      await waitFor(() => {
        expect(screen.getByText('Tags')).toBeInTheDocument()
      })
    })

    it('should show loading state initially', () => {
      mockFetch.mockImplementation(() => new Promise(() => {}))

      renderTagDisplay()

      expect(screen.getByText('Loading tags...')).toBeInTheDocument()
    })

    it('should fetch tags on mount', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ tags: [] }),
      })

      renderTagDisplay({
        contentType: 'chapter',
        contentId: '456',
      })

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          '/api/v1/ai/content/chapter/456/tags',
          expect.objectContaining({
            headers: expect.objectContaining({
              'Authorization': 'Bearer mock-token'
            })
          })
        )
      })
    })

    it('should not fetch tags if contentType missing', () => {
      renderTagDisplay({
        contentType: null,
        contentId: '123',
      })

      expect(mockFetch).not.toHaveBeenCalled()
    })

    it('should not fetch tags if contentId missing', () => {
      renderTagDisplay({
        contentType: 'chapter',
        contentId: null,
      })

      expect(mockFetch).not.toHaveBeenCalled()
    })
  })

  describe('Tags Display', () => {
    it('should display existing tags', async () => {
      const mockTags = [
        { id: '1', name: 'Neurology', confidence: 0.95 },
        { id: '2', name: 'Surgery', confidence: 0.87 },
      ]

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ tags: mockTags }),
      })

      renderTagDisplay()

      await waitFor(() => {
        expect(screen.getByText('Neurology')).toBeInTheDocument()
        expect(screen.getByText('Surgery')).toBeInTheDocument()
      })
    })

    it('should display tag confidence scores', async () => {
      const mockTags = [
        { id: '1', name: 'Neurology', confidence: 0.95 },
      ]

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ tags: mockTags }),
      })

      renderTagDisplay()

      await waitFor(() => {
        expect(screen.getByText('(95%)')).toBeInTheDocument()
      })
    })

    it('should display tags without confidence scores', async () => {
      const mockTags = [
        { id: '1', name: 'Neurology' },
      ]

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ tags: mockTags }),
      })

      renderTagDisplay()

      await waitFor(() => {
        expect(screen.getByText('Neurology')).toBeInTheDocument()
        expect(screen.queryByText(/\(\d+%\)/)).not.toBeInTheDocument()
      })
    })

    it('should show empty state when no tags', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ tags: [] }),
      })

      renderTagDisplay()

      await waitFor(() => {
        expect(screen.getByText(/No tags yet/)).toBeInTheDocument()
      })
    })
  })

  describe('Auto-Tag Button', () => {
    it('should render auto-tag button by default', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ tags: [] }),
      })

      renderTagDisplay()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Auto-Tag/i })).toBeInTheDocument()
      })
    })

    it('should not render auto-tag button when showAutoTag is false', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ tags: [] }),
      })

      renderTagDisplay({ showAutoTag: false })

      await waitFor(() => {
        expect(screen.queryByRole('button', { name: /Auto-Tag/i })).not.toBeInTheDocument()
      })
    })

    it('should disable auto-tag button when no content', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ tags: [] }),
      })

      renderTagDisplay({ contentText: '' })

      await waitFor(() => {
        const button = screen.getByRole('button', { name: /Auto-Tag/i })
        expect(button).toBeDisabled()
      })
    })

    it('should trigger auto-tagging on click', async () => {
      const user = userEvent.setup()

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ tags: [] }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            success: true,
            tags: [{ id: '1', name: 'AI Generated', confidence: 0.9 }]
          }),
        })

      renderTagDisplay()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Auto-Tag/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /Auto-Tag/i }))

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          '/api/v1/ai/tags/auto-tag',
          expect.objectContaining({
            method: 'POST',
            headers: expect.objectContaining({
              'Authorization': 'Bearer mock-token',
              'Content-Type': 'application/json'
            }),
            body: expect.stringContaining('content_type')
          })
        )
      })
    })

    it('should show loading state during auto-tagging', async () => {
      const user = userEvent.setup()

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ tags: [] }),
        })
        .mockImplementation(() => new Promise(() => {}))

      renderTagDisplay()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Auto-Tag/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /Auto-Tag/i }))

      await waitFor(() => {
        expect(screen.getByText(/Auto-Tagging.../i)).toBeInTheDocument()
      })
    })

    it('should call onTagsUpdated callback after auto-tagging', async () => {
      const user = userEvent.setup()
      const onTagsUpdated = vi.fn()
      const newTags = [{ id: '1', name: 'New Tag', confidence: 0.9 }]

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ tags: [] }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ success: true, tags: newTags }),
        })

      renderTagDisplay({ onTagsUpdated })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Auto-Tag/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /Auto-Tag/i }))

      await waitFor(() => {
        expect(onTagsUpdated).toHaveBeenCalledWith(newTags)
      })
    })
  })

  describe('Tag Removal', () => {
    it('should show remove button on tag hover', async () => {
      const mockTags = [
        { id: '1', name: 'Neurology', confidence: 0.95 },
      ]

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ tags: mockTags }),
      })

      const { container } = renderTagDisplay()

      await waitFor(() => {
        expect(screen.getByText('Neurology')).toBeInTheDocument()
      })

      // Check remove button exists (it has opacity-0 by default)
      const removeButtons = container.querySelectorAll('button[title="Remove tag"]')
      expect(removeButtons).toHaveLength(1)
    })

    it('should remove tag on click', async () => {
      const user = userEvent.setup()
      const mockTags = [
        { id: '1', name: 'Neurology', confidence: 0.95 },
        { id: '2', name: 'Surgery', confidence: 0.87 },
      ]

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ tags: mockTags }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({}),
        })

      const { container } = renderTagDisplay()

      await waitFor(() => {
        expect(screen.getByText('Neurology')).toBeInTheDocument()
      })

      const removeButtons = container.querySelectorAll('button[title="Remove tag"]')
      await user.click(removeButtons[0])

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          '/api/v1/ai/tags/1/remove/chapter/123',
          expect.objectContaining({
            method: 'DELETE'
          })
        )
      })
    })

    it('should call onTagsUpdated after removal', async () => {
      const user = userEvent.setup()
      const onTagsUpdated = vi.fn()
      const mockTags = [
        { id: '1', name: 'Neurology' },
        { id: '2', name: 'Surgery' },
      ]

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ tags: mockTags }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({}),
        })

      const { container } = renderTagDisplay({ onTagsUpdated })

      await waitFor(() => {
        expect(screen.getByText('Neurology')).toBeInTheDocument()
      })

      const removeButtons = container.querySelectorAll('button[title="Remove tag"]')
      await user.click(removeButtons[0])

      await waitFor(() => {
        expect(onTagsUpdated).toHaveBeenCalledWith([{ id: '2', name: 'Surgery' }])
      })
    })
  })

  describe('Tag Suggestions', () => {
    it('should show suggestions button when content available', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ tags: [] }),
      })

      renderTagDisplay({ contentText: 'Sample content' })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Get Tag Suggestions/i })).toBeInTheDocument()
      })
    })

    it('should not show suggestions button when no content', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ tags: [] }),
      })

      renderTagDisplay({ contentText: '' })

      await waitFor(() => {
        expect(screen.queryByRole('button', { name: /Get Tag Suggestions/i })).not.toBeInTheDocument()
      })
    })

    it('should fetch suggestions on click', async () => {
      const user = userEvent.setup()

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ tags: [] }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            suggestions: [
              { name: 'Suggested1', confidence: 0.8 },
              { name: 'Suggested2', confidence: 0.7 },
            ]
          }),
        })

      renderTagDisplay()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Get Tag Suggestions/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /Get Tag Suggestions/i }))

      await waitFor(() => {
        expect(screen.getByText(/\+ Suggested1/)).toBeInTheDocument()
        expect(screen.getByText(/\+ Suggested2/)).toBeInTheDocument()
      })
    })

    it('should add suggested tag on click', async () => {
      const user = userEvent.setup()

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ tags: [] }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            suggestions: [{ name: 'Suggested1', confidence: 0.8 }]
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({}),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ tags: [{ id: '1', name: 'Suggested1' }] }),
        })

      renderTagDisplay()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Get Tag Suggestions/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /Get Tag Suggestions/i }))

      await waitFor(() => {
        expect(screen.getByText(/\+ Suggested1/)).toBeInTheDocument()
      })

      await user.click(screen.getByText(/\+ Suggested1/))

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          '/api/v1/ai/tags/add',
          expect.objectContaining({
            method: 'POST',
            body: expect.stringContaining('Suggested1')
          })
        )
      })
    })
  })

  describe('Error Handling', () => {
    it('should handle fetch tags error gracefully', async () => {
      // When fetch fails but tags exist, component still shows tags section
      mockFetch.mockRejectedValueOnce(new Error('Network error'))

      renderTagDisplay()

      // Component shows loading initially
      expect(screen.getByText('Loading tags...')).toBeInTheDocument()

      // Wait for loading to complete
      await waitFor(() => {
        expect(screen.queryByText('Loading tags...')).not.toBeInTheDocument()
      }, { timeout: 3000 })

      // Since loading failed with empty tags, still shows the empty state
      expect(screen.getByText(/No tags yet/)).toBeInTheDocument()
    })

    it('should call auto-tag API when button clicked', async () => {
      const user = userEvent.setup()

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ tags: [] }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ success: true, tags: [] }),
        })

      renderTagDisplay()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Auto-Tag/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /Auto-Tag/i }))

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          '/api/v1/ai/tags/auto-tag',
          expect.objectContaining({
            method: 'POST'
          })
        )
      })
    })

    it('should disable auto-tag button when no content', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ tags: [] }),
      })

      renderTagDisplay({ contentText: '' })

      await waitFor(() => {
        const button = screen.getByRole('button', { name: /Auto-Tag/i })
        // Button should be disabled when no content
        expect(button).toBeDisabled()
      })
    })
  })

  describe('Edge Cases', () => {
    it('should handle empty suggestions array', async () => {
      const user = userEvent.setup()

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ tags: [] }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ suggestions: [] }),
        })

      renderTagDisplay()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Get Tag Suggestions/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /Get Tag Suggestions/i }))

      await waitFor(() => {
        // Should not show suggestions section if empty
        expect(screen.queryByText(/Suggested tags/i)).not.toBeInTheDocument()
      })
    })

    it('should handle null onTagsUpdated callback', async () => {
      const user = userEvent.setup()

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ tags: [] }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            success: true,
            tags: [{ id: '1', name: 'New Tag' }]
          }),
        })

      renderTagDisplay({ onTagsUpdated: null })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Auto-Tag/i })).toBeInTheDocument()
      })

      // Should not throw error
      await user.click(screen.getByRole('button', { name: /Auto-Tag/i }))

      await waitFor(() => {
        expect(screen.getByText('New Tag')).toBeInTheDocument()
      })
    })

    it('should truncate long content for suggestions', async () => {
      const user = userEvent.setup()
      const longContent = 'a'.repeat(2000)

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ tags: [] }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ suggestions: [] }),
        })

      renderTagDisplay({ contentText: longContent })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Get Tag Suggestions/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /Get Tag Suggestions/i }))

      await waitFor(() => {
        const fetchCall = mockFetch.mock.calls.find(call =>
          call[0].includes('/api/v1/ai/tags/suggest')
        )
        expect(fetchCall[0]).toContain(encodeURIComponent('a'.repeat(1000)))
      })
    })
  })

  describe('Accessibility', () => {
    it('should have accessible buttons', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ tags: [] }),
      })

      renderTagDisplay()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Auto-Tag/i })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /Get Tag Suggestions/i })).toBeInTheDocument()
      })
    })

    it('should have title attributes on remove buttons', async () => {
      const mockTags = [{ id: '1', name: 'Neurology' }]

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ tags: mockTags }),
      })

      const { container } = renderTagDisplay()

      await waitFor(() => {
        const removeButton = container.querySelector('button[title="Remove tag"]')
        expect(removeButton).toBeInTheDocument()
      })
    })

    it('should provide clear loading states', async () => {
      mockFetch.mockImplementation(() => new Promise(() => {}))

      renderTagDisplay()

      expect(screen.getByText('Loading tags...')).toBeInTheDocument()
    })
  })
})
