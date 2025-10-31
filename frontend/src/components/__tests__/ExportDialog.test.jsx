/**
 * ExportDialog Component Tests
 * Focused test suite for ExportDialog component critical functionality
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ExportDialog from '../ExportDialog'
import axios from 'axios'

// Mock axios
vi.mock('axios')

// Mock window methods
global.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
global.URL.revokeObjectURL = vi.fn()

describe('ExportDialog Component', () => {
  const mockChapterId = 'chapter-123'
  const mockChapterTitle = 'Test Chapter'
  const mockOnClose = vi.fn()
  const mockTemplates = [
    { id: 'template-1', name: 'Standard Template', is_default: true },
    { id: 'template-2', name: 'Minimal Template', is_default: false }
  ]
  const mockCitationStyles = [
    { id: 'style-1', name: 'apa', display_name: 'APA 7th Edition' },
    { id: 'style-2', name: 'mla', display_name: 'MLA 9th Edition' }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.setItem('access_token', 'mock-token')

    // Ensure DOM body exists and is clean
    if (!document.body) {
      document.body = document.createElement('body')
    }
    document.body.innerHTML = ''

    // Mock axios responses
    axios.get.mockImplementation((url) => {
      if (url.includes('/export/templates')) {
        return Promise.resolve({ data: { templates: mockTemplates } })
      }
      if (url.includes('/export/citation-styles')) {
        return Promise.resolve({ data: { styles: mockCitationStyles } })
      }
      return Promise.reject(new Error('Unknown URL'))
    })
  })

  const renderDialog = (props = {}) => {
    return render(
      <ExportDialog
        open={true}
        onClose={mockOnClose}
        chapterId={mockChapterId}
        chapterTitle={mockChapterTitle}
        {...props}
      />
    )
  }

  describe('Dialog Rendering', () => {
    it('should render dialog when open', () => {
      renderDialog()

      expect(screen.getByText('Export Chapter')).toBeInTheDocument()
    })

    it('should not render when closed', () => {
      renderDialog({ open: false })

      expect(screen.queryByText('Export Chapter')).not.toBeInTheDocument()
    })

    it('should show Cancel button', () => {
      renderDialog()

      expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument()
    })

    it('should show Export button', () => {
      renderDialog()

      expect(screen.getByRole('button', { name: /^Export$/i })).toBeInTheDocument()
    })

    it('should show Preview button', () => {
      renderDialog()

      expect(screen.getByRole('button', { name: /Preview/i })).toBeInTheDocument()
    })
  })

  describe('Initial Data Loading', () => {
    it('should load templates on open', async () => {
      renderDialog()

      await waitFor(() => {
        expect(axios.get).toHaveBeenCalledWith(
          expect.stringContaining('/export/templates'),
          expect.objectContaining({
            params: expect.objectContaining({ public_only: true }),
            headers: expect.objectContaining({ Authorization: 'Bearer mock-token' })
          })
        )
      })
    })

    it('should load citation styles on open', async () => {
      renderDialog()

      await waitFor(() => {
        expect(axios.get).toHaveBeenCalledWith(
          expect.stringContaining('/export/citation-styles'),
          expect.objectContaining({
            headers: expect.objectContaining({ Authorization: 'Bearer mock-token' })
          })
        )
      })
    })

    it('should handle template loading error gracefully', async () => {
      axios.get.mockRejectedValueOnce(new Error('Network error'))

      renderDialog()

      // Should not crash
      expect(screen.getByText('Export Chapter')).toBeInTheDocument()
    })
  })

  describe('Format Selection', () => {
    it('should default to PDF format', async () => {
      renderDialog()

      const pdfRadio = await screen.findByRole('radio', { name: /PDF/i })
      expect(pdfRadio).toBeChecked()
    })

    it('should allow selecting DOCX format', async () => {
      const user = userEvent.setup({ delay: null })
      renderDialog()

      const docxRadio = await screen.findByRole('radio', { name: /DOCX/i })
      await user.click(docxRadio)

      expect(docxRadio).toBeChecked()
    })

    it('should allow selecting HTML format', async () => {
      const user = userEvent.setup({ delay: null })
      renderDialog()

      const htmlRadio = await screen.findByRole('radio', { name: /HTML/i })
      await user.click(htmlRadio)

      expect(htmlRadio).toBeChecked()
    })

    it('should reload templates when format changes', async () => {
      const user = userEvent.setup({ delay: null })
      renderDialog()

      axios.get.mockClear()

      const docxRadio = screen.getByRole('radio', { name: /DOCX/i })
      await user.click(docxRadio)

      await waitFor(() => {
        expect(axios.get).toHaveBeenCalledWith(
          expect.stringContaining('/export/templates'),
          expect.objectContaining({
            params: expect.objectContaining({ format: 'docx' })
          })
        )
      })
    })
  })

  describe('Advanced Options', () => {
    it('should show Advanced Options accordion', async () => {
      renderDialog()

      await waitFor(() => {
        expect(screen.getByText('Advanced Options')).toBeInTheDocument()
      })
    })

    it('should have Include Bibliography checked by default', async () => {
      const user = userEvent.setup({ delay: null })
      renderDialog()

      // Expand Advanced Options accordion
      const accordionButton = await screen.findByText('Advanced Options')
      await user.click(accordionButton)

      const checkbox = await screen.findByRole('checkbox', { name: /Include Bibliography/i })
      expect(checkbox).toBeChecked()
    })

    it('should have Include TOC unchecked by default', async () => {
      const user = userEvent.setup({ delay: null })
      renderDialog()

      // Expand Advanced Options accordion
      const accordionButton = await screen.findByText('Advanced Options')
      await user.click(accordionButton)

      const checkbox = await screen.findByRole('checkbox', { name: /Include Table of Contents/i })
      expect(checkbox).not.toBeChecked()
    })

    it('should have Include Images checked by default', async () => {
      const user = userEvent.setup({ delay: null })
      renderDialog()

      // Expand Advanced Options accordion
      const accordionButton = await screen.findByText('Advanced Options')
      await user.click(accordionButton)

      const checkbox = await screen.findByRole('checkbox', { name: /Include Images/i })
      expect(checkbox).toBeChecked()
    })

    it('should allow toggling Bibliography checkbox', async () => {
      const user = userEvent.setup({ delay: null })
      renderDialog()

      // Expand Advanced Options accordion
      const accordionButton = await screen.findByText('Advanced Options')
      await user.click(accordionButton)

      const checkbox = await screen.findByRole('checkbox', { name: /Include Bibliography/i })
      await user.click(checkbox)

      expect(checkbox).not.toBeChecked()
    })

    it('should allow toggling TOC checkbox', async () => {
      const user = userEvent.setup({ delay: null })
      renderDialog()

      // Expand Advanced Options accordion
      const accordionButton = await screen.findByText('Advanced Options')
      await user.click(accordionButton)

      const checkbox = await screen.findByRole('checkbox', { name: /Include Table of Contents/i })
      await user.click(checkbox)

      expect(checkbox).toBeChecked()
    })
  })

  describe('Export Functionality', () => {
    it('should call export API with correct parameters', async () => {
      const user = userEvent.setup({ delay: null })
      axios.post.mockResolvedValueOnce({ data: new Blob(['test']) })

      renderDialog()

      await user.click(screen.getByRole('button', { name: /^Export$/i }))

      await waitFor(() => {
        expect(axios.post).toHaveBeenCalledWith(
          expect.stringContaining('/export/export'),
          expect.objectContaining({
            chapter_id: mockChapterId,
            format: 'pdf',
            citation_style: 'apa',
            options: expect.objectContaining({
              include_bibliography: true,
              include_toc: false,
              include_images: true
            })
          }),
          expect.objectContaining({
            headers: expect.objectContaining({ Authorization: 'Bearer mock-token' }),
            responseType: 'blob'
          })
        )
      })
    })

    it('should create download link on successful export', async () => {
      const user = userEvent.setup({ delay: null })
      const mockBlob = new Blob(['test'], { type: 'application/pdf' })
      axios.post.mockResolvedValueOnce({ data: mockBlob })

      // Render FIRST, before mocking createElement
      renderDialog()

      const exportButton = await screen.findByRole('button', { name: /^Export$/i })

      // Now mock createElement only when export is clicked
      const mockLink = {
        href: '',
        setAttribute: vi.fn(),
        click: vi.fn(),
        remove: vi.fn()
      }
      const createElementSpy = vi.spyOn(document, 'createElement').mockReturnValue(mockLink)
      const appendChildSpy = vi.spyOn(document.body, 'appendChild').mockImplementation(() => {})

      await user.click(exportButton)

      await waitFor(() => {
        expect(mockLink.click).toHaveBeenCalled()
      })

      createElementSpy.mockRestore()
      appendChildSpy.mockRestore()
    })

    it('should show success message after export', async () => {
      const user = userEvent.setup({ delay: null })
      axios.post.mockResolvedValueOnce({ data: new Blob(['test']) })

      // Render FIRST
      renderDialog()

      const exportButton = await screen.findByRole('button', { name: /^Export$/i })

      // Mock createElement after render
      const mockLink = {
        href: '',
        setAttribute: vi.fn(),
        click: vi.fn(),
        remove: vi.fn()
      }
      const createElementSpy = vi.spyOn(document, 'createElement').mockReturnValue(mockLink)
      const appendChildSpy = vi.spyOn(document.body, 'appendChild').mockImplementation(() => {})

      await user.click(exportButton)

      await waitFor(() => {
        expect(screen.getByText(/Export completed successfully/i)).toBeInTheDocument()
      })

      createElementSpy.mockRestore()
      appendChildSpy.mockRestore()
    })

    it('should show error message on export failure', async () => {
      const user = userEvent.setup({ delay: null })
      axios.post.mockRejectedValueOnce({
        response: { data: { detail: 'Export failed' } }
      })

      renderDialog()

      await user.click(screen.getByRole('button', { name: /^Export$/i }))

      await waitFor(() => {
        expect(screen.getByText('Export failed')).toBeInTheDocument()
      })
    })

    it('should show loading state during export', async () => {
      const user = userEvent.setup({ delay: null })
      axios.post.mockImplementation(() => new Promise(() => {}))

      renderDialog()

      await user.click(screen.getByRole('button', { name: /^Export$/i }))

      await waitFor(() => {
        expect(screen.getByText('Exporting...')).toBeInTheDocument()
      })
    })

    it('should disable buttons during export', async () => {
      const user = userEvent.setup({ delay: null })
      axios.post.mockImplementation(() => new Promise(() => {}))

      renderDialog()

      await user.click(screen.getByRole('button', { name: /^Export$/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Cancel/i })).toBeDisabled()
        expect(screen.getByRole('button', { name: /Preview/i })).toBeDisabled()
      })
    })
  })

  describe('Preview Functionality', () => {
    it('should call preview API', async () => {
      const user = userEvent.setup({ delay: null })
      axios.get.mockResolvedValueOnce({ data: '<html>Preview</html>' })

      const mockWindow = {
        document: {
          write: vi.fn(),
          close: vi.fn()
        }
      }
      window.open = vi.fn(() => mockWindow)

      renderDialog()

      const previewButton = await screen.findByRole('button', { name: /Preview/i })
      await user.click(previewButton)

      await waitFor(() => {
        expect(axios.get).toHaveBeenCalledWith(
          expect.stringContaining(`/export/preview/${mockChapterId}`),
          expect.objectContaining({
            params: expect.objectContaining({ format: 'html' }),
            headers: expect.objectContaining({ Authorization: 'Bearer mock-token' })
          })
        )
      })
    })

    it('should open preview in new window', async () => {
      const user = userEvent.setup({ delay: null })
      axios.get.mockResolvedValueOnce({ data: '<html>Preview</html>' })

      const mockWindow = {
        document: {
          write: vi.fn(),
          close: vi.fn()
        }
      }

      // Render FIRST
      renderDialog()

      const previewButton = await screen.findByRole('button', { name: /Preview/i })

      // Mock window.open after render
      window.open = vi.fn(() => mockWindow)

      await user.click(previewButton)

      await waitFor(() => {
        expect(window.open).toHaveBeenCalledWith('', '_blank')
        expect(mockWindow.document.write).toHaveBeenCalledWith('<html>Preview</html>')
        expect(mockWindow.document.close).toHaveBeenCalled()
      })
    })

    it('should show error on preview failure', async () => {
      const user = userEvent.setup({ delay: null })
      axios.get.mockRejectedValueOnce(new Error('Preview failed'))

      renderDialog()

      const previewButton = await screen.findByRole('button', { name: /Preview/i })
      await user.click(previewButton)

      await waitFor(() => {
        expect(screen.getByText(/Preview failed/i)).toBeInTheDocument()
      })
    })
  })

  describe('Cancel Functionality', () => {
    it('should call onClose when Cancel clicked', async () => {
      const user = userEvent.setup({ delay: null })
      renderDialog()

      const cancelButton = await screen.findByRole('button', { name: /Cancel/i })
      await user.click(cancelButton)

      expect(mockOnClose).toHaveBeenCalled()
    })
  })

  describe('Error Handling', () => {
    it('should allow dismissing error message', async () => {
      const user = userEvent.setup({ delay: null })
      axios.post.mockRejectedValueOnce({
        response: { data: { detail: 'Test error' } }
      })

      renderDialog()

      const exportButton = await screen.findByRole('button', { name: /^Export$/i })
      await user.click(exportButton)

      await waitFor(() => {
        expect(screen.getByText('Test error')).toBeInTheDocument()
      })

      // MUI Alert close button - find by aria-label
      const closeButton = screen.getByLabelText(/close/i)
      await user.click(closeButton)

      await waitFor(() => {
        expect(screen.queryByText('Test error')).not.toBeInTheDocument()
      })
    })
  })

  describe('Filename Generation', () => {
    it('should generate safe filename from chapter title', async () => {
      const user = userEvent.setup({ delay: null })
      axios.post.mockResolvedValueOnce({ data: new Blob(['test']) })

      // Render FIRST
      renderDialog({ chapterTitle: 'Test: Chapter! Name?' })

      const exportButton = await screen.findByRole('button', { name: /^Export$/i })

      // Mock createElement after render
      const mockLink = {
        href: '',
        setAttribute: vi.fn(),
        click: vi.fn(),
        remove: vi.fn()
      }
      const createElementSpy = vi.spyOn(document, 'createElement').mockReturnValue(mockLink)
      const appendChildSpy = vi.spyOn(document.body, 'appendChild').mockImplementation(() => {})

      await user.click(exportButton)

      await waitFor(() => {
        expect(mockLink.setAttribute).toHaveBeenCalledWith(
          'download',
          expect.stringMatching(/Test_Chapter_Name_\.pdf/)
        )
      })

      createElementSpy.mockRestore()
      appendChildSpy.mockRestore()
    })

    it('should use correct extension for format', async () => {
      const user = userEvent.setup({ delay: null })
      axios.post.mockResolvedValueOnce({ data: new Blob(['test']) })

      // Render FIRST
      renderDialog()

      // Select DOCX format
      const docxRadio = await screen.findByRole('radio', { name: /DOCX/i })
      await user.click(docxRadio)

      const exportButton = await screen.findByRole('button', { name: /^Export$/i })

      // Mock createElement after render
      const mockLink = {
        href: '',
        setAttribute: vi.fn(),
        click: vi.fn(),
        remove: vi.fn()
      }
      const createElementSpy = vi.spyOn(document, 'createElement').mockReturnValue(mockLink)
      const appendChildSpy = vi.spyOn(document.body, 'appendChild').mockImplementation(() => {})

      await user.click(exportButton)

      await waitFor(() => {
        expect(mockLink.setAttribute).toHaveBeenCalledWith(
          'download',
          expect.stringMatching(/\.docx$/)
        )
      })

      createElementSpy.mockRestore()
      appendChildSpy.mockRestore()
    })
  })

  describe('Info Messages', () => {
    it('should show export note', async () => {
      renderDialog()

      await waitFor(() => {
        expect(screen.getByText(/Export may take a few moments/i)).toBeInTheDocument()
      })
    })
  })
})
