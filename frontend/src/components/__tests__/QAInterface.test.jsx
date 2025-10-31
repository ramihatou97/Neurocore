/**
 * QAInterface Component Tests
 * Comprehensive test suite for QAInterface component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import QAInterface from '../QAInterface'

// Mock fetch
global.fetch = vi.fn()

describe('QAInterface Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.setItem('token', 'mock-token')

    // Default fetch mock
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ history: [] })
    })
  })

  const renderInterface = (props = {}) => {
    return render(<QAInterface {...props} />)
  }

  describe('Initial Rendering', () => {
    it('should render main heading', () => {
      renderInterface()

      expect(screen.getByText('Ask the Knowledge Base')).toBeInTheDocument()
    })

    it('should render description', () => {
      renderInterface()

      expect(screen.getByText(/AI-powered answers using RAG/i)).toBeInTheDocument()
    })

    it('should render question input', () => {
      renderInterface()

      expect(screen.getByPlaceholderText(/Ask a question about neurosurgery/i)).toBeInTheDocument()
    })

    it('should render Ask button', () => {
      renderInterface()

      expect(screen.getByRole('button', { name: /Ask/i })).toBeInTheDocument()
    })

    it('should show empty state message', () => {
      renderInterface()

      expect(screen.getByText('Ask me anything about neurosurgery')).toBeInTheDocument()
    })

    it('should show example questions', () => {
      renderInterface()

      expect(screen.getByText(/What are the indications for craniotomy/i)).toBeInTheDocument()
    })

    it('should not show Clear button initially', () => {
      renderInterface()

      expect(screen.queryByRole('button', { name: /Clear/i })).not.toBeInTheDocument()
    })
  })

  describe('History Functionality', () => {
    it('should show History button when showHistory is true', () => {
      renderInterface({ showHistory: true })

      expect(screen.getByRole('button', { name: /History/i })).toBeInTheDocument()
    })

    it('should not show History button when showHistory is false', () => {
      renderInterface({ showHistory: false })

      expect(screen.queryByRole('button', { name: /History/i })).not.toBeInTheDocument()
    })

    it('should fetch history on mount when showHistory is true', async () => {
      renderInterface({ showHistory: true })

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/v1/ai/qa/history'),
          expect.objectContaining({
            headers: expect.objectContaining({
              'Authorization': 'Bearer mock-token'
            })
          })
        )
      })
    })

    it('should not fetch history when showHistory is false', () => {
      renderInterface({ showHistory: false })

      expect(global.fetch).not.toHaveBeenCalled()
    })

    it('should toggle history sidebar when History button clicked', async () => {
      const user = userEvent.setup({ delay: null })
      renderInterface({ showHistory: true })

      await user.click(screen.getByRole('button', { name: /History/i }))

      expect(screen.getByText('Recent Questions')).toBeInTheDocument()
    })

    it('should show empty history message', async () => {
      const user = userEvent.setup({ delay: null })
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ history: [] })
      })

      renderInterface({ showHistory: true })

      await user.click(screen.getByRole('button', { name: /History/i }))

      expect(screen.getByText('No history yet')).toBeInTheDocument()
    })

    it('should display history items', async () => {
      const user = userEvent.setup({ delay: null })
      const mockHistory = [
        {
          id: '1',
          question: 'What is craniotomy?',
          answer: 'A surgical procedure',
          confidence: 0.95,
          asked_at: '2024-01-01T12:00:00Z',
          was_helpful: true
        }
      ]

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ history: mockHistory })
      })

      renderInterface({ showHistory: true })

      await user.click(screen.getByRole('button', { name: /History/i }))

      await waitFor(() => {
        expect(screen.getByText('What is craniotomy?')).toBeInTheDocument()
      })
    })
  })

  describe('Asking Questions', () => {
    it('should allow typing in question input', async () => {
      const user = userEvent.setup({ delay: null })
      renderInterface()

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      await user.type(input, 'Test question')

      expect(input).toHaveValue('Test question')
    })

    it('should disable Ask button when input is empty', () => {
      renderInterface()

      const button = screen.getByRole('button', { name: /Ask/i })
      expect(button).toBeDisabled()
    })

    it('should enable Ask button when input has text', async () => {
      const user = userEvent.setup({ delay: null })
      renderInterface()

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      await user.type(input, 'Test question')

      const button = screen.getByRole('button', { name: /Ask/i })
      expect(button).not.toBeDisabled()
    })

    it('should submit question on Ask button click', async () => {
      const user = userEvent.setup({ delay: null })
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          answer: 'Test answer',
          confidence: 0.85,
          sources: [],
          id: 'qa-1'
        })
      })

      renderInterface()

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      await user.type(input, 'What is a craniotomy?')
      await user.click(screen.getByRole('button', { name: /Ask/i }))

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          '/api/v1/ai/qa/ask',
          expect.objectContaining({
            method: 'POST',
            headers: expect.objectContaining({
              'Authorization': 'Bearer mock-token',
              'Content-Type': 'application/json'
            }),
            body: expect.stringContaining('What is a craniotomy?')
          })
        )
      })
    })

    it('should display user question in conversation', async () => {
      const user = userEvent.setup({ delay: null })
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          answer: 'Test answer',
          confidence: 0.85,
          sources: [],
          id: 'qa-1'
        })
      })

      renderInterface()

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      await user.type(input, 'Test question')
      await user.click(screen.getByRole('button', { name: /Ask/i }))

      expect(screen.getByText('Test question')).toBeInTheDocument()
    })

    it('should clear input after submitting', async () => {
      const user = userEvent.setup({ delay: null })
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          answer: 'Test answer',
          confidence: 0.85,
          sources: [],
          id: 'qa-1'
        })
      })

      renderInterface()

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      await user.type(input, 'Test question')
      await user.click(screen.getByRole('button', { name: /Ask/i }))

      await waitFor(() => {
        expect(input).toHaveValue('')
      })
    })

    it('should show loading state while waiting for answer', async () => {
      const user = userEvent.setup({ delay: null })
      global.fetch.mockImplementation(() => new Promise(() => {}))

      renderInterface()

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      await user.type(input, 'Test question')
      await user.click(screen.getByRole('button', { name: /Ask/i }))

      await waitFor(() => {
        expect(screen.getByText('Thinking...')).toBeInTheDocument()
      })
    })

    it('should display answer after receiving response', async () => {
      const user = userEvent.setup({ delay: null })
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          answer: 'Craniotomy is a surgical procedure',
          confidence: 0.95,
          sources: [],
          id: 'qa-1'
        })
      })

      renderInterface()

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      await user.type(input, 'What is a craniotomy?')
      await user.click(screen.getByRole('button', { name: /Ask/i }))

      await waitFor(() => {
        expect(screen.getByText('Craniotomy is a surgical procedure')).toBeInTheDocument()
      })
    })

    it('should not submit when input is only whitespace', async () => {
      const user = userEvent.setup({ delay: null })
      renderInterface()

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      await user.type(input, '   ')

      const button = screen.getByRole('button', { name: /Ask/i })
      expect(button).toBeDisabled()
    })
  })

  describe('Session Management', () => {
    it('should generate session ID on first question', async () => {
      const user = userEvent.setup({ delay: null })
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          answer: 'Test answer',
          confidence: 0.85,
          sources: [],
          id: 'qa-1'
        })
      })

      renderInterface()

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      await user.type(input, 'Test question')
      await user.click(screen.getByRole('button', { name: /Ask/i }))

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            body: expect.stringMatching(/session_\d+_[a-z0-9]+/)
          })
        )
      })
    })

    it('should call onSessionStart when session is created', async () => {
      const user = userEvent.setup({ delay: null })
      const mockOnSessionStart = vi.fn()
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          answer: 'Test answer',
          confidence: 0.85,
          sources: [],
          id: 'qa-1'
        })
      })

      renderInterface({ onSessionStart: mockOnSessionStart })

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      await user.type(input, 'Test question')
      await user.click(screen.getByRole('button', { name: /Ask/i }))

      await waitFor(() => {
        expect(mockOnSessionStart).toHaveBeenCalledWith(expect.stringMatching(/session_/))
      })
    })

    it('should use provided sessionId', async () => {
      const user = userEvent.setup({ delay: null })
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          answer: 'Test answer',
          confidence: 0.85,
          sources: [],
          id: 'qa-1'
        })
      })

      renderInterface({ sessionId: 'custom-session-123' })

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      await user.type(input, 'Test question')
      await user.click(screen.getByRole('button', { name: /Ask/i }))

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            body: expect.stringContaining('custom-session-123')
          })
        )
      })
    })
  })

  describe('Answer Display', () => {
    it('should display confidence score', async () => {
      const user = userEvent.setup({ delay: null })
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          answer: 'Test answer',
          confidence: 0.87,
          sources: [],
          id: 'qa-1'
        })
      })

      renderInterface()

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      await user.type(input, 'Test')
      await user.click(screen.getByRole('button', { name: /Ask/i }))

      await waitFor(() => {
        expect(screen.getByText('87%')).toBeInTheDocument()
      })
    })

    it('should display sources when available', async () => {
      const user = userEvent.setup({ delay: null })
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          answer: 'Test answer',
          confidence: 0.85,
          sources: [
            { title: 'Source 1', similarity: 0.92 },
            { title: 'Source 2', similarity: 0.88 }
          ],
          id: 'qa-1'
        })
      })

      renderInterface()

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      await user.type(input, 'Test')
      await user.click(screen.getByRole('button', { name: /Ask/i }))

      await waitFor(() => {
        expect(screen.getByText(/Sources \(2\)/i)).toBeInTheDocument()
        expect(screen.getByText('Source 1')).toBeInTheDocument()
      })
    })

    it('should limit sources display to 3', async () => {
      const user = userEvent.setup({ delay: null })
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          answer: 'Test answer',
          confidence: 0.85,
          sources: [
            { title: 'Source 1', similarity: 0.92 },
            { title: 'Source 2', similarity: 0.88 },
            { title: 'Source 3', similarity: 0.85 },
            { title: 'Source 4', similarity: 0.82 }
          ],
          id: 'qa-1'
        })
      })

      renderInterface()

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      await user.type(input, 'Test')
      await user.click(screen.getByRole('button', { name: /Ask/i }))

      await waitFor(() => {
        expect(screen.getByText('Source 3')).toBeInTheDocument()
        expect(screen.queryByText('Source 4')).not.toBeInTheDocument()
      })
    })
  })

  describe('Feedback Functionality', () => {
    it('should show feedback buttons after answer', async () => {
      const user = userEvent.setup({ delay: null })
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          answer: 'Test answer',
          confidence: 0.85,
          sources: [],
          id: 'qa-1'
        })
      })

      renderInterface()

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      await user.type(input, 'Test')
      await user.click(screen.getByRole('button', { name: /Ask/i }))

      await waitFor(() => {
        expect(screen.getByText('Was this helpful?')).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /👍 Yes/i })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /👎 No/i })).toBeInTheDocument()
      })
    })

    it('should submit positive feedback', async () => {
      const user = userEvent.setup({ delay: null })
      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            answer: 'Test answer',
            confidence: 0.85,
            sources: [],
            id: 'qa-1'
          })
        })
        .mockResolvedValueOnce({ ok: true })

      renderInterface()

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      await user.type(input, 'Test')
      await user.click(screen.getByRole('button', { name: /Ask/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /👍 Yes/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /👍 Yes/i }))

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          '/api/v1/ai/qa/qa-1/feedback',
          expect.objectContaining({
            method: 'POST',
            body: expect.stringContaining('"was_helpful":true')
          })
        )
      })
    })

    it('should show feedback confirmation after submission', async () => {
      const user = userEvent.setup({ delay: null })
      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            answer: 'Test answer',
            confidence: 0.85,
            sources: [],
            id: 'qa-1'
          })
        })
        .mockResolvedValueOnce({ ok: true })

      renderInterface()

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      await user.type(input, 'Test')
      await user.click(screen.getByRole('button', { name: /Ask/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /👍 Yes/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /👍 Yes/i }))

      await waitFor(() => {
        expect(screen.getByText(/Thanks for your feedback!/i)).toBeInTheDocument()
      })
    })
  })

  describe('Error Handling', () => {
    it('should show error when API call fails', async () => {
      const user = userEvent.setup({ delay: null })
      global.fetch.mockRejectedValueOnce(new Error('Network error'))

      renderInterface()

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      await user.type(input, 'Test')
      await user.click(screen.getByRole('button', { name: /Ask/i }))

      await waitFor(() => {
        expect(screen.getByText(/Failed to get answer/i)).toBeInTheDocument()
      })
    })

    it('should show error when response not ok', async () => {
      const user = userEvent.setup({ delay: null })
      global.fetch.mockResolvedValueOnce({
        ok: false
      })

      renderInterface()

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      await user.type(input, 'Test')
      await user.click(screen.getByRole('button', { name: /Ask/i }))

      await waitFor(() => {
        expect(screen.getByText(/Failed to get answer/i)).toBeInTheDocument()
      })
    })

    it('should remove question from conversation on error', async () => {
      const user = userEvent.setup({ delay: null })
      global.fetch.mockRejectedValueOnce(new Error('Error'))

      renderInterface()

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      await user.type(input, 'Test question')
      await user.click(screen.getByRole('button', { name: /Ask/i }))

      await waitFor(() => {
        expect(screen.getByText(/Failed to get answer/i)).toBeInTheDocument()
      })

      // Question should be removed
      expect(screen.queryByText('Test question')).not.toBeInTheDocument()
    })
  })

  describe('Clear Functionality', () => {
    it('should show Clear button after asking question', async () => {
      const user = userEvent.setup({ delay: null })
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          answer: 'Test answer',
          confidence: 0.85,
          sources: [],
          id: 'qa-1'
        })
      })

      renderInterface()

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      await user.type(input, 'Test')
      await user.click(screen.getByRole('button', { name: /Ask/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Clear/i })).toBeInTheDocument()
      })
    })

    it('should clear conversation when Clear clicked', async () => {
      const user = userEvent.setup({ delay: null })
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          answer: 'Test answer',
          confidence: 0.85,
          sources: [],
          id: 'qa-1'
        })
      })

      renderInterface()

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      await user.type(input, 'Test question')
      await user.click(screen.getByRole('button', { name: /Ask/i }))

      await waitFor(() => {
        expect(screen.getByText('Test question')).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /Clear/i }))

      expect(screen.queryByText('Test question')).not.toBeInTheDocument()
      expect(screen.getByText('Ask me anything about neurosurgery')).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('should handle missing onSessionStart callback', async () => {
      const user = userEvent.setup({ delay: null })
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          answer: 'Test answer',
          confidence: 0.85,
          sources: [],
          id: 'qa-1'
        })
      })

      renderInterface()

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      await user.type(input, 'Test')
      await user.click(screen.getByRole('button', { name: /Ask/i }))

      await waitFor(() => {
        expect(screen.getByText('Test answer')).toBeInTheDocument()
      })
    })

    it('should handle response with error field', async () => {
      const user = userEvent.setup({ delay: null })
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          error: 'API error message'
        })
      })

      renderInterface()

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      await user.type(input, 'Test')
      await user.click(screen.getByRole('button', { name: /Ask/i }))

      await waitFor(() => {
        expect(screen.getByText('API error message')).toBeInTheDocument()
      })
    })
  })

  describe('Accessibility', () => {
    it('should have accessible form', () => {
      renderInterface()

      const input = screen.getByPlaceholderText(/Ask a question about neurosurgery/i)
      expect(input).toBeInTheDocument()
    })

    it('should have accessible buttons', () => {
      renderInterface()

      const button = screen.getByRole('button', { name: /Ask/i })
      expect(button).toBeInTheDocument()
    })
  })
})
