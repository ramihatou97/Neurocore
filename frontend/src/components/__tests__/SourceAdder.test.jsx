/**
 * SourceAdder Component Tests
 * Comprehensive test suite for SourceAdder component
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SourceAdder from '../SourceAdder'
import { chaptersAPI } from '../../api'

// Mock the chaptersAPI
vi.mock('../../api', () => ({
  chaptersAPI: {
    addSources: vi.fn()
  }
}))

describe('SourceAdder Component', () => {
  const mockChapterId = 'chapter-123'
  const mockOnSourcesAdded = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    // Cleanup if needed
  })

  const renderSourceAdder = (props = {}) => {
    return render(
      <SourceAdder
        chapterId={mockChapterId}
        onSourcesAdded={mockOnSourcesAdded}
        {...props}
      />
    )
  }

  // Helper functions to get inputs (labels aren't properly associated with textareas)
  const getPdfInput = () => screen.getByPlaceholderText(/123e4567/)
  const getDoiInput = () => screen.getByPlaceholderText(/10.1234\/example/)
  const getPubmedInput = () => screen.getByPlaceholderText(/12345678/)

  describe('Initial Rendering - Closed State', () => {
    it('should render closed button initially', () => {
      renderSourceAdder()

      expect(screen.getByRole('button', { name: /Add Research Sources/i })).toBeInTheDocument()
    })

    it('should not show form when closed', () => {
      renderSourceAdder()

      expect(screen.queryByRole('form')).not.toBeInTheDocument()
      expect(screen.queryByLabelText(/Internal PDF IDs/i)).not.toBeInTheDocument()
    })

    it('should have outline variant button when closed', () => {
      renderSourceAdder()

      const button = screen.getByRole('button', { name: /Add Research Sources/i })
      expect(button).toHaveClass('text-purple-600')
    })

    it('should show book emoji in button', () => {
      renderSourceAdder()

      expect(screen.getByText(/📚 Add Research Sources/)).toBeInTheDocument()
    })
  })

  describe('Opening Form', () => {
    it('should open form when button clicked', async () => {
      const user = userEvent.setup({ delay: null })
      renderSourceAdder()

      const button = screen.getByRole('button', { name: /Add Research Sources/i })
      await user.click(button)

      expect(screen.getByText('Add Research Sources')).toBeInTheDocument()
      expect(screen.getByPlaceholderText(/123e4567/)).toBeInTheDocument()
    })

    it('should hide button when form is open', async () => {
      const user = userEvent.setup({ delay: null })
      renderSourceAdder()

      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      const buttons = screen.queryAllByRole('button', { name: /Add Research Sources/i })
      // Only submit button should exist, not the toggle button
      expect(buttons.length).toBeLessThanOrEqual(2)
    })

    it('should show all three input fields when open', async () => {
      const user = userEvent.setup({ delay: null })
      renderSourceAdder()

      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      expect(getPdfInput()).toBeInTheDocument()
      expect(getDoiInput()).toBeInTheDocument()
      expect(getPubmedInput()).toBeInTheDocument()
    })

    it('should show info message about source integration', async () => {
      const user = userEvent.setup({ delay: null })
      renderSourceAdder()

      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      expect(screen.getByText(/These sources will be available when regenerating/i)).toBeInTheDocument()
    })

    it('should show action buttons', async () => {
      const user = userEvent.setup({ delay: null })
      renderSourceAdder()

      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /📚 Add Sources/i })).toBeInTheDocument()
    })
  })

  describe('Form Inputs', () => {
    it('should allow typing in PDF IDs field', async () => {
      const user = userEvent.setup({ delay: null })
      renderSourceAdder()

      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))
      const input = getPdfInput()

      await user.type(input, 'pdf-123')

      expect(input).toHaveValue('pdf-123')
    })

    it('should allow typing in DOIs field', async () => {
      const user = userEvent.setup({ delay: null })
      renderSourceAdder()

      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))
      const input = getDoiInput()

      await user.type(input, '10.1234/example')

      expect(input).toHaveValue('10.1234/example')
    })

    it('should allow typing in PubMed IDs field', async () => {
      const user = userEvent.setup({ delay: null })
      renderSourceAdder()

      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))
      const input = getPubmedInput()

      await user.type(input, '12345678')

      expect(input).toHaveValue('12345678')
    })

    it('should show placeholder text in all fields', async () => {
      const user = userEvent.setup({ delay: null })
      renderSourceAdder()

      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      const pdfInput = getPdfInput()
      const doiInput = getDoiInput()
      const pubmedInput = getPubmedInput()

      expect(pdfInput).toHaveAttribute('placeholder')
      expect(doiInput).toHaveAttribute('placeholder')
      expect(pubmedInput).toHaveAttribute('placeholder')
    })

    it('should show helper text for each field', async () => {
      const user = userEvent.setup({ delay: null })
      renderSourceAdder()

      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      expect(screen.getByText(/PDFs from your indexed library/i)).toBeInTheDocument()
      expect(screen.getByText(/Digital Object Identifiers for external papers/i)).toBeInTheDocument()
      expect(screen.getByText(/PubMed article identifiers/i)).toBeInTheDocument()
    })
  })

  describe('Form Validation', () => {
    it('should show error when submitting with no sources', async () => {
      const user = userEvent.setup({ delay: null })
      renderSourceAdder()

      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))
      const submitButton = screen.getByRole('button', { name: /📚 Add Sources/i })
      await user.click(submitButton)

      expect(screen.getByText('Please provide at least one source')).toBeInTheDocument()
    })

    it('should not call API when no sources provided', async () => {
      const user = userEvent.setup({ delay: null })
      renderSourceAdder()

      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      expect(chaptersAPI.addSources).not.toHaveBeenCalled()
    })

    it('should not show error initially', async () => {
      const user = userEvent.setup({ delay: null })
      renderSourceAdder()

      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      expect(screen.queryByText('Please provide at least one source')).not.toBeInTheDocument()
    })
  })

  describe('Source Parsing - PDF IDs', () => {
    it('should accept single PDF ID', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.addSources.mockResolvedValueOnce({
        sources_added: 1,
        total_sources: 5
      })

      renderSourceAdder()
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      const input = getPdfInput()
      await user.type(input, 'pdf-123')
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      await waitFor(() => {
        expect(chaptersAPI.addSources).toHaveBeenCalledWith(
          mockChapterId,
          expect.objectContaining({
            pdf_ids: ['pdf-123']
          })
        )
      })
    })

    it('should parse comma-separated PDF IDs', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.addSources.mockResolvedValueOnce({
        sources_added: 3,
        total_sources: 8
      })

      renderSourceAdder()
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      const input = getPdfInput()
      await user.type(input, 'pdf-1, pdf-2, pdf-3')
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      await waitFor(() => {
        expect(chaptersAPI.addSources).toHaveBeenCalledWith(
          mockChapterId,
          expect.objectContaining({
            pdf_ids: ['pdf-1', 'pdf-2', 'pdf-3']
          })
        )
      })
    })

    it('should parse newline-separated PDF IDs', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.addSources.mockResolvedValueOnce({
        sources_added: 2,
        total_sources: 6
      })

      renderSourceAdder()
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      const input = getPdfInput()
      await user.type(input, 'pdf-1\npdf-2')
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      await waitFor(() => {
        expect(chaptersAPI.addSources).toHaveBeenCalledWith(
          mockChapterId,
          expect.objectContaining({
            pdf_ids: ['pdf-1', 'pdf-2']
          })
        )
      })
    })

    it('should trim whitespace from PDF IDs', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.addSources.mockResolvedValueOnce({
        sources_added: 2,
        total_sources: 6
      })

      renderSourceAdder()
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      const input = getPdfInput()
      await user.type(input, '  pdf-1  ,  pdf-2  ')
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      await waitFor(() => {
        expect(chaptersAPI.addSources).toHaveBeenCalledWith(
          mockChapterId,
          expect.objectContaining({
            pdf_ids: ['pdf-1', 'pdf-2']
          })
        )
      })
    })

    it('should filter empty PDF IDs', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.addSources.mockResolvedValueOnce({
        sources_added: 1,
        total_sources: 5
      })

      renderSourceAdder()
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      const input = getPdfInput()
      await user.type(input, 'pdf-1,,,,pdf-2')
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      await waitFor(() => {
        expect(chaptersAPI.addSources).toHaveBeenCalledWith(
          mockChapterId,
          expect.objectContaining({
            pdf_ids: ['pdf-1', 'pdf-2']
          })
        )
      })
    })
  })

  describe('Source Parsing - DOIs', () => {
    it('should accept single DOI', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.addSources.mockResolvedValueOnce({
        sources_added: 1,
        total_sources: 5
      })

      renderSourceAdder()
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      const input = getDoiInput()
      await user.type(input, '10.1234/example')
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      await waitFor(() => {
        expect(chaptersAPI.addSources).toHaveBeenCalledWith(
          mockChapterId,
          expect.objectContaining({
            external_dois: ['10.1234/example']
          })
        )
      })
    })

    it('should parse comma-separated DOIs', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.addSources.mockResolvedValueOnce({
        sources_added: 2,
        total_sources: 6
      })

      renderSourceAdder()
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      const input = getDoiInput()
      await user.type(input, '10.1234/example, 10.5678/another')
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      await waitFor(() => {
        expect(chaptersAPI.addSources).toHaveBeenCalledWith(
          mockChapterId,
          expect.objectContaining({
            external_dois: ['10.1234/example', '10.5678/another']
          })
        )
      })
    })
  })

  describe('Source Parsing - PubMed IDs', () => {
    it('should accept single PubMed ID', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.addSources.mockResolvedValueOnce({
        sources_added: 1,
        total_sources: 5
      })

      renderSourceAdder()
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      const input = getPubmedInput()
      await user.type(input, '12345678')
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      await waitFor(() => {
        expect(chaptersAPI.addSources).toHaveBeenCalledWith(
          mockChapterId,
          expect.objectContaining({
            pubmed_ids: ['12345678']
          })
        )
      })
    })

    it('should parse comma-separated PubMed IDs', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.addSources.mockResolvedValueOnce({
        sources_added: 2,
        total_sources: 6
      })

      renderSourceAdder()
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      const input = getPubmedInput()
      await user.type(input, '12345678, 87654321')
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      await waitFor(() => {
        expect(chaptersAPI.addSources).toHaveBeenCalledWith(
          mockChapterId,
          expect.objectContaining({
            pubmed_ids: ['12345678', '87654321']
          })
        )
      })
    })
  })

  describe('Mixed Source Types', () => {
    it('should accept all three source types together', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.addSources.mockResolvedValueOnce({
        sources_added: 4,
        total_sources: 10
      })

      renderSourceAdder()
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      await user.type(getPdfInput(), 'pdf-1')
      await user.type(getDoiInput(), '10.1234/example')
      await user.type(getPubmedInput(), '12345678, 87654321')
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      await waitFor(() => {
        expect(chaptersAPI.addSources).toHaveBeenCalledWith(
          mockChapterId,
          {
            pdf_ids: ['pdf-1'],
            external_dois: ['10.1234/example'],
            pubmed_ids: ['12345678', '87654321']
          }
        )
      })
    })

    it('should only send non-empty source arrays', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.addSources.mockResolvedValueOnce({
        sources_added: 1,
        total_sources: 5
      })

      renderSourceAdder()
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      await user.type(getPdfInput(), 'pdf-1')
      // Leave DOIs and PubMed IDs empty
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      await waitFor(() => {
        expect(chaptersAPI.addSources).toHaveBeenCalledWith(
          mockChapterId,
          {
            pdf_ids: ['pdf-1'],
            external_dois: undefined,
            pubmed_ids: undefined
          }
        )
      })
    })
  })

  describe('Success Handling', () => {
    it('should show success message after adding sources', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.addSources.mockResolvedValueOnce({
        sources_added: 3,
        total_sources: 8
      })

      renderSourceAdder()
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))
      await user.type(getPdfInput(), 'pdf-1, pdf-2, pdf-3')
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      await waitFor(() => {
        expect(screen.getByText(/Added 3 sources. Total: 8/)).toBeInTheDocument()
      })
    })

    it('should clear form fields after success', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.addSources.mockResolvedValueOnce({
        sources_added: 1,
        total_sources: 5
      })

      renderSourceAdder()
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      const pdfInput = getPdfInput()
      const doiInput = getDoiInput()
      const pubmedInput = getPubmedInput()

      await user.type(pdfInput, 'pdf-1')
      await user.type(doiInput, '10.1234/example')
      await user.type(pubmedInput, '12345678')
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      await waitFor(() => {
        expect(pdfInput).toHaveValue('')
        expect(doiInput).toHaveValue('')
        expect(pubmedInput).toHaveValue('')
      })
    })

    it('should call onSourcesAdded callback with response', async () => {
      const user = userEvent.setup({ delay: null })
      const mockResponse = {
        sources_added: 2,
        total_sources: 7
      }
      chaptersAPI.addSources.mockResolvedValueOnce(mockResponse)

      renderSourceAdder()
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))
      await user.type(getPdfInput(), 'pdf-1')
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      await waitFor(() => {
        expect(mockOnSourcesAdded).toHaveBeenCalledWith(mockResponse)
      })
    })

    it('should auto-close form after 2 seconds', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.addSources.mockResolvedValueOnce({
        sources_added: 1,
        total_sources: 5
      })

      renderSourceAdder()
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))
      await user.type(getPdfInput(), 'pdf-1')
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      // Wait for success
      await waitFor(() => {
        expect(screen.getByText(/Added 1 sources/)).toBeInTheDocument()
      })

      // Wait for auto-close (2 second delay in component)
      await waitFor(() => {
        expect(screen.queryByPlaceholderText(/123e4567/)).not.toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('should show checkmark in success message', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.addSources.mockResolvedValueOnce({
        sources_added: 1,
        total_sources: 5
      })

      renderSourceAdder()
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))
      await user.type(getPdfInput(), 'pdf-1')
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      await waitFor(() => {
        expect(screen.getByText(/✓/)).toBeInTheDocument()
      })
    })
  })

  describe('Error Handling', () => {
    it('should show error message when API call fails', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.addSources.mockRejectedValueOnce({
        response: {
          data: {
            detail: 'Chapter not found'
          }
        }
      })

      renderSourceAdder()
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))
      await user.type(getPdfInput(), 'pdf-1')
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      await waitFor(() => {
        expect(screen.getByText('Chapter not found')).toBeInTheDocument()
      })
    })

    it('should show generic error when no detail provided', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.addSources.mockRejectedValueOnce(new Error('Network error'))

      renderSourceAdder()
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))
      await user.type(getPdfInput(), 'pdf-1')
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      await waitFor(() => {
        expect(screen.getByText('Failed to add sources')).toBeInTheDocument()
      })
    })

    it('should not close form on error', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.addSources.mockRejectedValueOnce(new Error('Network error'))

      renderSourceAdder()
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))
      await user.type(getPdfInput(), 'pdf-1')
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      await waitFor(() => {
        expect(screen.getByText('Failed to add sources')).toBeInTheDocument()
      })

      expect(getPdfInput()).toBeInTheDocument()
    })

    it('should not call onSourcesAdded callback on error', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.addSources.mockRejectedValueOnce(new Error('Network error'))

      renderSourceAdder()
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))
      await user.type(getPdfInput(), 'pdf-1')
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      await waitFor(() => {
        expect(screen.getByText('Failed to add sources')).toBeInTheDocument()
      })

      expect(mockOnSourcesAdded).not.toHaveBeenCalled()
    })
  })

  describe('Cancel Functionality', () => {
    it('should close form when cancel clicked', async () => {
      const user = userEvent.setup({ delay: null })
      renderSourceAdder()

      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))
      await user.click(screen.getByRole('button', { name: /Cancel/i }))

      expect(screen.queryByLabelText(/Internal PDF IDs/i)).not.toBeInTheDocument()
    })

    it('should clear all fields when cancel clicked', async () => {
      const user = userEvent.setup({ delay: null })
      renderSourceAdder()

      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))
      await user.type(getPdfInput(), 'pdf-1')
      await user.type(getDoiInput(), '10.1234/example')
      await user.click(screen.getByRole('button', { name: /Cancel/i }))

      // Re-open to check fields are cleared
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      expect(getPdfInput()).toHaveValue('')
      expect(getDoiInput()).toHaveValue('')
    })

    it('should clear error message when cancel clicked', async () => {
      const user = userEvent.setup({ delay: null })
      renderSourceAdder()

      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i })) // Trigger validation error

      await waitFor(() => {
        expect(screen.getByText('Please provide at least one source')).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /Cancel/i }))
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      expect(screen.queryByText('Please provide at least one source')).not.toBeInTheDocument()
    })
  })

  describe('Loading State', () => {
    it('should show loading spinner when submitting', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.addSources.mockImplementation(() => new Promise(() => {}))

      renderSourceAdder()
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))
      await user.type(getPdfInput(), 'pdf-1')
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      await waitFor(() => {
        expect(screen.getByText('Adding...')).toBeInTheDocument()
      })
    })

    it('should disable inputs during loading', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.addSources.mockImplementation(() => new Promise(() => {}))

      renderSourceAdder()
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))
      await user.type(getPdfInput(), 'pdf-1')
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      await waitFor(() => {
        expect(getPdfInput()).toBeDisabled()
        expect(getDoiInput()).toBeDisabled()
        expect(getPubmedInput()).toBeDisabled()
      })
    })

    it('should disable buttons during loading', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.addSources.mockImplementation(() => new Promise(() => {}))

      renderSourceAdder()
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))
      await user.type(getPdfInput(), 'pdf-1')
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      await waitFor(() => {
        const buttons = screen.getAllByRole('button')
        buttons.forEach(button => {
          expect(button).toBeDisabled()
        })
      })
    })
  })

  describe('Edge Cases', () => {
    it('should handle missing onSourcesAdded callback', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.addSources.mockResolvedValueOnce({
        sources_added: 1,
        total_sources: 5
      })

      render(<SourceAdder chapterId={mockChapterId} />)

      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))
      await user.type(getPdfInput(), 'pdf-1')
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      await waitFor(() => {
        expect(screen.getByText(/Added 1 sources/)).toBeInTheDocument()
      })
    })

    it('should handle very long input strings', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.addSources.mockResolvedValueOnce({
        sources_added: 100,
        total_sources: 150
      })

      renderSourceAdder()
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      // Use paste instead of type for long strings
      const longList = Array(100).fill().map((_, i) => `pdf-${i}`).join(',')
      const input = getPdfInput()
      await user.clear(input)
      await user.click(input)
      await user.paste(longList)
      await user.click(screen.getByRole('button', { name: /📚 Add Sources/i }))

      await waitFor(() => {
        expect(chaptersAPI.addSources).toHaveBeenCalled()
      }, { timeout: 15000 })
    }, 20000)

    it('should handle rapid open/close', async () => {
      const user = userEvent.setup({ delay: null })
      renderSourceAdder()

      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))
      await user.click(screen.getByRole('button', { name: /Cancel/i }))
      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      expect(getPdfInput()).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('should use semantic form element', async () => {
      const user = userEvent.setup({ delay: null })
      renderSourceAdder()

      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      expect(screen.getByRole('button', { name: /📚 Add Sources/i })).toHaveAttribute('type', 'submit')
    })

    it('should have proper labels for all inputs', async () => {
      const user = userEvent.setup({ delay: null })
      renderSourceAdder()

      await user.click(screen.getByRole('button', { name: /Add Research Sources/i }))

      expect(getPdfInput()).toBeInTheDocument()
      expect(getDoiInput()).toBeInTheDocument()
      expect(getPubmedInput()).toBeInTheDocument()
    })

    it('should use button role for interactive elements', () => {
      renderSourceAdder()

      expect(screen.getByRole('button', { name: /Add Research Sources/i })).toBeInTheDocument()
    })
  })
})
