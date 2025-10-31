/**
 * SectionEditor Component Tests
 * Comprehensive test suite for SectionEditor component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SectionEditor from '../SectionEditor'
import { chaptersAPI } from '../../api'

// Mock the chaptersAPI
vi.mock('../../api', () => ({
  chaptersAPI: {
    editSection: vi.fn(),
    regenerateSection: vi.fn()
  }
}))

describe('SectionEditor Component', () => {
  const mockChapterId = 'chapter-123'
  const mockSection = {
    title: 'Test Section',
    content: '<p>Original content here</p>',
    word_count: 150,
    edited_at: null,
    regenerated_at: null
  }
  const mockSectionNumber = 0
  const mockOnSave = vi.fn()
  const mockOnRegenerate = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  const renderEditor = (props = {}) => {
    return render(
      <SectionEditor
        chapterId={mockChapterId}
        section={mockSection}
        sectionNumber={mockSectionNumber}
        onSave={mockOnSave}
        onRegenerate={mockOnRegenerate}
        {...props}
      />
    )
  }

  describe('Initial Rendering - View Mode', () => {
    it('should render section title', () => {
      renderEditor()

      expect(screen.getByText('Test Section')).toBeInTheDocument()
    })

    it('should render default title when section has no title', () => {
      renderEditor({
        section: { ...mockSection, title: null },
        sectionNumber: 2
      })

      expect(screen.getByText('Section 3')).toBeInTheDocument()
    })

    it('should render word count', () => {
      renderEditor()

      expect(screen.getByText('150 words')).toBeInTheDocument()
    })

    it('should render zero word count when not provided', () => {
      renderEditor({
        section: { ...mockSection, word_count: null }
      })

      expect(screen.getByText('0 words')).toBeInTheDocument()
    })

    it('should show Edit button', () => {
      renderEditor()

      expect(screen.getByRole('button', { name: /Edit/i })).toBeInTheDocument()
    })

    it('should show Regenerate button', () => {
      renderEditor()

      expect(screen.getByRole('button', { name: /Regenerate/i })).toBeInTheDocument()
    })

    it('should render content with HTML', () => {
      const { container } = renderEditor()

      const proseDiv = container.querySelector('.prose')
      expect(proseDiv).toBeInTheDocument()
      expect(proseDiv.innerHTML).toContain('<p>Original content here</p>')
    })

    it('should not show textarea in view mode', () => {
      renderEditor()

      expect(screen.queryByPlaceholderText(/Enter section content/i)).not.toBeInTheDocument()
    })

    it('should not show regenerate options initially', () => {
      renderEditor()

      expect(screen.queryByText('AI Regeneration Options')).not.toBeInTheDocument()
    })
  })

  describe('Status Badges', () => {
    it('should show Edited badge when section was edited', () => {
      renderEditor({
        section: { ...mockSection, edited_at: '2024-01-01T12:00:00Z' }
      })

      expect(screen.getByText('Edited')).toBeInTheDocument()
      expect(screen.getByText('Edited')).toHaveClass('text-blue-600')
    })

    it('should show Regenerated badge when section was regenerated', () => {
      renderEditor({
        section: { ...mockSection, regenerated_at: '2024-01-01T12:00:00Z' }
      })

      expect(screen.getByText('Regenerated')).toBeInTheDocument()
      expect(screen.getByText('Regenerated')).toHaveClass('text-green-600')
    })

    it('should show both badges when section was edited and regenerated', () => {
      renderEditor({
        section: {
          ...mockSection,
          edited_at: '2024-01-01T12:00:00Z',
          regenerated_at: '2024-01-02T12:00:00Z'
        }
      })

      expect(screen.getByText('Edited')).toBeInTheDocument()
      expect(screen.getByText('Regenerated')).toBeInTheDocument()
    })

    it('should not show badges when section is pristine', () => {
      renderEditor()

      expect(screen.queryByText('Edited')).not.toBeInTheDocument()
      expect(screen.queryByText('Regenerated')).not.toBeInTheDocument()
    })
  })

  describe('Edit Mode', () => {
    it('should enter edit mode when Edit button clicked', async () => {
      const user = userEvent.setup({ delay: null })
      renderEditor()

      await user.click(screen.getByRole('button', { name: /Edit/i }))

      expect(screen.getByPlaceholderText(/Enter section content/i)).toBeInTheDocument()
    })

    it('should show textarea with current content', async () => {
      const user = userEvent.setup({ delay: null })
      renderEditor()

      await user.click(screen.getByRole('button', { name: /Edit/i }))

      const textarea = screen.getByPlaceholderText(/Enter section content/i)
      expect(textarea).toHaveValue('<p>Original content here</p>')
    })

    it('should hide Edit and Regenerate buttons in edit mode', async () => {
      const user = userEvent.setup({ delay: null })
      renderEditor()

      await user.click(screen.getByRole('button', { name: /Edit/i }))

      expect(screen.queryByRole('button', { name: /✏️ Edit/i })).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /🔄 Regenerate/i })).not.toBeInTheDocument()
    })

    it('should show Save and Cancel buttons in edit mode', async () => {
      const user = userEvent.setup({ delay: null })
      renderEditor()

      await user.click(screen.getByRole('button', { name: /Edit/i }))

      expect(screen.getByRole('button', { name: /Save Changes/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument()
    })

    it('should allow editing textarea content', async () => {
      const user = userEvent.setup({ delay: null })
      renderEditor()

      await user.click(screen.getByRole('button', { name: /Edit/i }))
      const textarea = screen.getByPlaceholderText(/Enter section content/i)

      await user.clear(textarea)
      await user.type(textarea, 'New content')

      expect(textarea).toHaveValue('New content')
    })

    it('should show editing tip', async () => {
      const user = userEvent.setup({ delay: null })
      renderEditor()

      await user.click(screen.getByRole('button', { name: /Edit/i }))

      expect(screen.getByText(/You can use HTML tags for formatting/i)).toBeInTheDocument()
    })

    it('should show cost info for manual edit', async () => {
      const user = userEvent.setup({ delay: null })
      renderEditor()

      await user.click(screen.getByRole('button', { name: /Edit/i }))

      expect(screen.getByText(/~\$0 \(manual edit, no AI\)/i)).toBeInTheDocument()
    })
  })

  describe('Save Functionality', () => {
    it('should save edited content', async () => {
      const user = userEvent.setup({ delay: null })
      const mockResponse = { success: true }
      chaptersAPI.editSection.mockResolvedValueOnce(mockResponse)

      renderEditor()
      await user.click(screen.getByRole('button', { name: /Edit/i }))

      const textarea = screen.getByPlaceholderText(/Enter section content/i)
      await user.clear(textarea)
      await user.type(textarea, 'Updated content')
      await user.click(screen.getByRole('button', { name: /Save Changes/i }))

      await waitFor(() => {
        expect(chaptersAPI.editSection).toHaveBeenCalledWith(
          mockChapterId,
          mockSectionNumber,
          { content: 'Updated content' }
        )
      })
    })

    it('should call onSave callback with response', async () => {
      const user = userEvent.setup({ delay: null })
      const mockResponse = { success: true, updated_content: 'New content' }
      chaptersAPI.editSection.mockResolvedValueOnce(mockResponse)

      renderEditor()
      await user.click(screen.getByRole('button', { name: /Edit/i }))
      await user.click(screen.getByRole('button', { name: /Save Changes/i }))

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith(mockResponse)
      })
    })

    it('should exit edit mode after successful save', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.editSection.mockResolvedValueOnce({ success: true })

      renderEditor()
      await user.click(screen.getByRole('button', { name: /Edit/i }))
      await user.click(screen.getByRole('button', { name: /Save Changes/i }))

      await waitFor(() => {
        expect(screen.queryByPlaceholderText(/Enter section content/i)).not.toBeInTheDocument()
      })
    })

    it('should show loading state while saving', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.editSection.mockImplementation(() => new Promise(() => {}))

      renderEditor()
      await user.click(screen.getByRole('button', { name: /Edit/i }))
      await user.click(screen.getByRole('button', { name: /Save Changes/i }))

      await waitFor(() => {
        expect(screen.getByText('Saving...')).toBeInTheDocument()
      })
    })

    it('should disable buttons while saving', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.editSection.mockImplementation(() => new Promise(() => {}))

      renderEditor()
      await user.click(screen.getByRole('button', { name: /Edit/i }))
      await user.click(screen.getByRole('button', { name: /Save Changes/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Saving.../i })).toBeDisabled()
        expect(screen.getByRole('button', { name: /Cancel/i })).toBeDisabled()
      })
    })
  })

  describe('Save Validation', () => {
    it('should show error when saving empty content', async () => {
      const user = userEvent.setup({ delay: null })
      renderEditor()

      await user.click(screen.getByRole('button', { name: /Edit/i }))
      const textarea = screen.getByPlaceholderText(/Enter section content/i)
      await user.clear(textarea)
      await user.click(screen.getByRole('button', { name: /Save Changes/i }))

      expect(screen.getByText('Content cannot be empty')).toBeInTheDocument()
    })

    it('should show error when saving whitespace-only content', async () => {
      const user = userEvent.setup({ delay: null })
      renderEditor()

      await user.click(screen.getByRole('button', { name: /Edit/i }))
      const textarea = screen.getByPlaceholderText(/Enter section content/i)
      await user.clear(textarea)
      await user.type(textarea, '   ')
      await user.click(screen.getByRole('button', { name: /Save Changes/i }))

      expect(screen.getByText('Content cannot be empty')).toBeInTheDocument()
    })

    it('should not call API when validation fails', async () => {
      const user = userEvent.setup({ delay: null })
      renderEditor()

      await user.click(screen.getByRole('button', { name: /Edit/i }))
      const textarea = screen.getByPlaceholderText(/Enter section content/i)
      await user.clear(textarea)
      await user.click(screen.getByRole('button', { name: /Save Changes/i }))

      expect(chaptersAPI.editSection).not.toHaveBeenCalled()
    })
  })

  describe('Save Error Handling', () => {
    it('should show error message when save fails', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.editSection.mockRejectedValueOnce({
        response: { data: { detail: 'Network error' } }
      })

      renderEditor()
      await user.click(screen.getByRole('button', { name: /Edit/i }))
      await user.click(screen.getByRole('button', { name: /Save Changes/i }))

      await waitFor(() => {
        expect(screen.getByText('Network error')).toBeInTheDocument()
      })
    })

    it('should show generic error when no detail provided', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.editSection.mockRejectedValueOnce(new Error('Failed'))

      renderEditor()
      await user.click(screen.getByRole('button', { name: /Edit/i }))
      await user.click(screen.getByRole('button', { name: /Save Changes/i }))

      await waitFor(() => {
        expect(screen.getByText('Failed to save section')).toBeInTheDocument()
      })
    })

    it('should remain in edit mode after save error', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.editSection.mockRejectedValueOnce(new Error('Failed'))

      renderEditor()
      await user.click(screen.getByRole('button', { name: /Edit/i }))
      await user.click(screen.getByRole('button', { name: /Save Changes/i }))

      await waitFor(() => {
        expect(screen.getByText('Failed to save section')).toBeInTheDocument()
      })

      expect(screen.getByPlaceholderText(/Enter section content/i)).toBeInTheDocument()
    })
  })

  describe('Cancel Editing', () => {
    it('should exit edit mode when Cancel clicked', async () => {
      const user = userEvent.setup({ delay: null })
      renderEditor()

      await user.click(screen.getByRole('button', { name: /Edit/i }))
      await user.click(screen.getByRole('button', { name: /Cancel/i }))

      expect(screen.queryByPlaceholderText(/Enter section content/i)).not.toBeInTheDocument()
    })

    it('should restore original content when Cancel clicked', async () => {
      const user = userEvent.setup({ delay: null })
      renderEditor()

      await user.click(screen.getByRole('button', { name: /Edit/i }))
      const textarea = screen.getByPlaceholderText(/Enter section content/i)
      await user.clear(textarea)
      await user.type(textarea, 'Changed content')
      await user.click(screen.getByRole('button', { name: /Cancel/i }))

      // Re-open edit mode to verify content was restored
      await user.click(screen.getByRole('button', { name: /Edit/i }))
      const newTextarea = screen.getByPlaceholderText(/Enter section content/i)
      expect(newTextarea).toHaveValue('<p>Original content here</p>')
    })

    it('should clear error message when Cancel clicked', async () => {
      const user = userEvent.setup({ delay: null })
      renderEditor()

      await user.click(screen.getByRole('button', { name: /Edit/i }))
      const textarea = screen.getByPlaceholderText(/Enter section content/i)
      await user.clear(textarea)
      await user.click(screen.getByRole('button', { name: /Save Changes/i }))

      expect(screen.getByText('Content cannot be empty')).toBeInTheDocument()

      await user.click(screen.getByRole('button', { name: /Cancel/i }))

      expect(screen.queryByText('Content cannot be empty')).not.toBeInTheDocument()
    })
  })

  describe('Regenerate Options', () => {
    it('should show regenerate options when Regenerate button clicked', async () => {
      const user = userEvent.setup({ delay: null })
      renderEditor()

      await user.click(screen.getByRole('button', { name: /Regenerate/i }))

      expect(screen.getByText('AI Regeneration Options')).toBeInTheDocument()
    })

    it('should hide regenerate options when Regenerate button clicked again', async () => {
      const user = userEvent.setup({ delay: null })
      renderEditor()

      await user.click(screen.getByRole('button', { name: /🔄 Regenerate$/i }))
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate$/i }))

      expect(screen.queryByText('AI Regeneration Options')).not.toBeInTheDocument()
    })

    it('should show instructions textarea in regenerate options', async () => {
      const user = userEvent.setup({ delay: null })
      renderEditor()

      await user.click(screen.getByRole('button', { name: /Regenerate/i }))

      expect(screen.getByPlaceholderText(/Focus more on surgical technique/i)).toBeInTheDocument()
    })

    it('should show cost and time info for regeneration', async () => {
      const user = userEvent.setup({ delay: null })
      renderEditor()

      await user.click(screen.getByRole('button', { name: /Regenerate/i }))

      expect(screen.getByText(/~\$0.08/i)).toBeInTheDocument()
      expect(screen.getByText(/~10-20 seconds/i)).toBeInTheDocument()
    })

    it('should show Regenerate with AI button', async () => {
      const user = userEvent.setup({ delay: null })
      renderEditor()

      await user.click(screen.getByRole('button', { name: /🔄 Regenerate/i }))

      expect(screen.getByRole('button', { name: /🔄 Regenerate with AI/i })).toBeInTheDocument()
    })

    it('should allow typing instructions', async () => {
      const user = userEvent.setup({ delay: null })
      renderEditor()

      await user.click(screen.getByRole('button', { name: /Regenerate/i }))
      const textarea = screen.getByPlaceholderText(/Focus more on surgical technique/i)
      await user.type(textarea, 'Add more details')

      expect(textarea).toHaveValue('Add more details')
    })
  })

  describe('Regenerate Functionality', () => {
    it('should regenerate section without instructions', async () => {
      const user = userEvent.setup({ delay: null })
      const mockResponse = { updated_content: '<p>New AI content</p>' }
      chaptersAPI.regenerateSection.mockResolvedValueOnce(mockResponse)

      renderEditor()
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate/i }))
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate with AI/i }))

      await waitFor(() => {
        expect(chaptersAPI.regenerateSection).toHaveBeenCalledWith(
          mockChapterId,
          mockSectionNumber,
          { instructions: undefined }
        )
      })
    })

    it('should regenerate section with instructions', async () => {
      const user = userEvent.setup({ delay: null })
      const mockResponse = { updated_content: '<p>New AI content</p>' }
      chaptersAPI.regenerateSection.mockResolvedValueOnce(mockResponse)

      renderEditor()
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate/i }))

      const textarea = screen.getByPlaceholderText(/Focus more on surgical technique/i)
      await user.type(textarea, 'Add more recent studies')
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate with AI/i }))

      await waitFor(() => {
        expect(chaptersAPI.regenerateSection).toHaveBeenCalledWith(
          mockChapterId,
          mockSectionNumber,
          { instructions: 'Add more recent studies' }
        )
      })
    })

    it('should call onRegenerate callback with response', async () => {
      const user = userEvent.setup({ delay: null })
      const mockResponse = { updated_content: '<p>New content</p>' }
      chaptersAPI.regenerateSection.mockResolvedValueOnce(mockResponse)

      renderEditor()
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate/i }))
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate with AI/i }))

      await waitFor(() => {
        expect(mockOnRegenerate).toHaveBeenCalledWith(mockResponse)
      })
    })

    it('should hide regenerate options after successful regeneration', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.regenerateSection.mockResolvedValueOnce({ updated_content: '<p>New</p>' })

      renderEditor()
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate/i }))
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate with AI/i }))

      await waitFor(() => {
        expect(screen.queryByText('AI Regeneration Options')).not.toBeInTheDocument()
      })
    })

    it('should clear instructions after successful regeneration', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.regenerateSection.mockResolvedValueOnce({ updated_content: '<p>New</p>' })

      renderEditor()
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate/i }))

      const textarea = screen.getByPlaceholderText(/Focus more on surgical technique/i)
      await user.type(textarea, 'Instructions')
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate with AI/i }))

      await waitFor(() => {
        expect(chaptersAPI.regenerateSection).toHaveBeenCalled()
      })

      // Re-open to check instructions cleared
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate/i }))
      const newTextarea = screen.getByPlaceholderText(/Focus more on surgical technique/i)
      expect(newTextarea).toHaveValue('')
    })

    it('should update content with response.updated_content', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.regenerateSection.mockResolvedValueOnce({
        updated_content: '<p>AI generated content</p>'
      })

      const { container } = renderEditor()
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate/i }))
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate with AI/i }))

      await waitFor(() => {
        const proseDiv = container.querySelector('.prose')
        expect(proseDiv.innerHTML).toContain('<p>AI generated content</p>')
      })
    })

    it('should update content with response.new_content as fallback', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.regenerateSection.mockResolvedValueOnce({
        new_content: '<p>New AI content</p>'
      })

      const { container } = renderEditor()
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate/i }))
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate with AI/i }))

      await waitFor(() => {
        const proseDiv = container.querySelector('.prose')
        expect(proseDiv.innerHTML).toContain('<p>New AI content</p>')
      })
    })

    it('should show loading state while regenerating', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.regenerateSection.mockImplementation(() => new Promise(() => {}))

      renderEditor()
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate/i }))
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate with AI/i }))

      await waitFor(() => {
        expect(screen.getByText('Regenerating...')).toBeInTheDocument()
      })
    })

    it('should disable buttons while regenerating', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.regenerateSection.mockImplementation(() => new Promise(() => {}))

      renderEditor()
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate/i }))
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate with AI/i }))

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText(/Focus more on surgical technique/i)
        expect(textarea).toBeDisabled()

        const buttons = screen.getAllByRole('button')
        buttons.forEach(button => {
          if (button.textContent.includes('Cancel') || button.textContent.includes('Regenerating')) {
            expect(button).toBeDisabled()
          }
        })
      })
    })
  })

  describe('Regenerate Error Handling', () => {
    it('should show error message when regenerate fails', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.regenerateSection.mockRejectedValueOnce({
        response: { data: { detail: 'AI service unavailable' } }
      })

      renderEditor()
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate/i }))
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate with AI/i }))

      await waitFor(() => {
        expect(screen.getByText('AI service unavailable')).toBeInTheDocument()
      })
    })

    it('should show generic error when no detail provided', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.regenerateSection.mockRejectedValueOnce(new Error('Failed'))

      renderEditor()
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate/i }))
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate with AI/i }))

      await waitFor(() => {
        expect(screen.getByText('Failed to regenerate section')).toBeInTheDocument()
      })
    })

    it('should keep regenerate options open after error', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.regenerateSection.mockRejectedValueOnce(new Error('Failed'))

      renderEditor()
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate/i }))
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate with AI/i }))

      await waitFor(() => {
        expect(screen.getByText('Failed to regenerate section')).toBeInTheDocument()
      })

      expect(screen.getByText('AI Regeneration Options')).toBeInTheDocument()
    })
  })

  describe('Cancel Regenerate', () => {
    it('should hide regenerate options when cancel clicked', async () => {
      const user = userEvent.setup({ delay: null })
      renderEditor()

      await user.click(screen.getByRole('button', { name: /🔄 Regenerate/i }))

      // Find the Cancel button within regenerate options (not the edit mode Cancel)
      const cancelButtons = screen.getAllByRole('button', { name: /Cancel/i })
      await user.click(cancelButtons[0])

      expect(screen.queryByText('AI Regeneration Options')).not.toBeInTheDocument()
    })

    it('should clear instructions when cancel clicked', async () => {
      const user = userEvent.setup({ delay: null })
      renderEditor()

      await user.click(screen.getByRole('button', { name: /🔄 Regenerate/i }))
      const textarea = screen.getByPlaceholderText(/Focus more on surgical technique/i)
      await user.type(textarea, 'Some instructions')

      const cancelButtons = screen.getAllByRole('button', { name: /Cancel/i })
      await user.click(cancelButtons[0])

      // Re-open to verify cleared
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate/i }))
      const newTextarea = screen.getByPlaceholderText(/Focus more on surgical technique/i)
      expect(newTextarea).toHaveValue('')
    })
  })

  describe('Edge Cases', () => {
    it('should handle section with no content', () => {
      const { container } = renderEditor({
        section: { ...mockSection, content: null }
      })

      const proseDiv = container.querySelector('.prose')
      expect(proseDiv).toBeInTheDocument()
    })

    it('should handle missing onSave callback', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.editSection.mockResolvedValueOnce({ success: true })

      render(
        <SectionEditor
          chapterId={mockChapterId}
          section={mockSection}
          sectionNumber={mockSectionNumber}
        />
      )

      await user.click(screen.getByRole('button', { name: /Edit/i }))
      await user.click(screen.getByRole('button', { name: /Save Changes/i }))

      await waitFor(() => {
        expect(chaptersAPI.editSection).toHaveBeenCalled()
      })
    })

    it('should handle missing onRegenerate callback', async () => {
      const user = userEvent.setup({ delay: null })
      chaptersAPI.regenerateSection.mockResolvedValueOnce({ updated_content: '<p>New</p>' })

      render(
        <SectionEditor
          chapterId={mockChapterId}
          section={mockSection}
          sectionNumber={mockSectionNumber}
        />
      )

      await user.click(screen.getByRole('button', { name: /🔄 Regenerate/i }))
      await user.click(screen.getByRole('button', { name: /🔄 Regenerate with AI/i }))

      await waitFor(() => {
        expect(chaptersAPI.regenerateSection).toHaveBeenCalled()
      })
    })
  })

  describe('Accessibility', () => {
    it('should use semantic buttons', () => {
      renderEditor()

      const editButton = screen.getByRole('button', { name: /Edit/i })
      const regenerateButton = screen.getByRole('button', { name: /Regenerate/i })

      expect(editButton).toBeInTheDocument()
      expect(regenerateButton).toBeInTheDocument()
    })

    it('should have accessible textarea in edit mode', async () => {
      const user = userEvent.setup({ delay: null })
      renderEditor()

      await user.click(screen.getByRole('button', { name: /Edit/i }))

      const textarea = screen.getByPlaceholderText(/Enter section content/i)
      expect(textarea).toBeInTheDocument()
    })

    it('should have accessible labels in regenerate options', async () => {
      const user = userEvent.setup({ delay: null })
      renderEditor()

      await user.click(screen.getByRole('button', { name: /Regenerate/i }))

      expect(screen.getByText('Special Instructions (optional)')).toBeInTheDocument()
    })
  })
})
