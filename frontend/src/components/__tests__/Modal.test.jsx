/**
 * Modal Component Tests
 * Comprehensive test suite for Modal component
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Modal from '../Modal'

describe('Modal Component', () => {
  // Clean up after each test
  afterEach(() => {
    document.body.style.overflow = 'unset'
  })

  describe('Rendering', () => {
    it('should not render when isOpen is false', () => {
      const { container } = render(
        <Modal isOpen={false} onClose={() => {}} title="Test Modal">
          Content
        </Modal>
      )
      expect(container.firstChild).toBeNull()
    })

    it('should render when isOpen is true', () => {
      render(
        <Modal isOpen={true} onClose={() => {}} title="Test Modal">
          Content
        </Modal>
      )
      expect(screen.getByText('Test Modal')).toBeInTheDocument()
      expect(screen.getByText('Content')).toBeInTheDocument()
    })

    it('should render modal title', () => {
      render(
        <Modal isOpen={true} onClose={() => {}} title="My Modal Title">
          Content
        </Modal>
      )
      expect(screen.getByRole('heading', { name: 'My Modal Title' })).toBeInTheDocument()
    })

    it('should render modal children', () => {
      render(
        <Modal isOpen={true} onClose={() => {}} title="Test">
          <p>Modal body content</p>
        </Modal>
      )
      expect(screen.getByText('Modal body content')).toBeInTheDocument()
    })

    it('should render close button', () => {
      render(
        <Modal isOpen={true} onClose={() => {}} title="Test">
          Content
        </Modal>
      )
      const closeButtons = screen.getAllByText('×')
      expect(closeButtons.length).toBeGreaterThan(0)
    })
  })

  describe('Size Variants', () => {
    it('should render with default size (md)', () => {
      const { container } = render(
        <Modal isOpen={true} onClose={() => {}} title="Test">
          Content
        </Modal>
      )
      const modal = container.querySelector('.max-w-lg')
      expect(modal).toBeInTheDocument()
    })

    it('should render with small size', () => {
      const { container } = render(
        <Modal isOpen={true} onClose={() => {}} title="Test" size="sm">
          Content
        </Modal>
      )
      const modal = container.querySelector('.max-w-md')
      expect(modal).toBeInTheDocument()
    })

    it('should render with large size', () => {
      const { container } = render(
        <Modal isOpen={true} onClose={() => {}} title="Test" size="lg">
          Content
        </Modal>
      )
      const modal = container.querySelector('.max-w-2xl')
      expect(modal).toBeInTheDocument()
    })

    it('should render with xl size', () => {
      const { container } = render(
        <Modal isOpen={true} onClose={() => {}} title="Test" size="xl">
          Content
        </Modal>
      )
      const modal = container.querySelector('.max-w-4xl')
      expect(modal).toBeInTheDocument()
    })

    it('should render with full size', () => {
      const { container } = render(
        <Modal isOpen={true} onClose={() => {}} title="Test" size="full">
          Content
        </Modal>
      )
      const modal = container.querySelector('.max-w-7xl')
      expect(modal).toBeInTheDocument()
    })
  })

  describe('Footer', () => {
    it('should not render footer when not provided', () => {
      const { container } = render(
        <Modal isOpen={true} onClose={() => {}} title="Test">
          Content
        </Modal>
      )
      const footer = container.querySelector('.border-t')
      expect(footer).not.toBeInTheDocument()
    })

    it('should render footer when provided', () => {
      render(
        <Modal
          isOpen={true}
          onClose={() => {}}
          title="Test"
          footer={<button>Save</button>}
        >
          Content
        </Modal>
      )
      expect(screen.getByText('Save')).toBeInTheDocument()
    })

    it('should render custom footer content', () => {
      render(
        <Modal
          isOpen={true}
          onClose={() => {}}
          title="Test"
          footer={
            <>
              <button>Cancel</button>
              <button>Confirm</button>
            </>
          }
        >
          Content
        </Modal>
      )
      expect(screen.getByText('Cancel')).toBeInTheDocument()
      expect(screen.getByText('Confirm')).toBeInTheDocument()
    })
  })

  describe('Close Interactions', () => {
    it('should call onClose when close button is clicked', async () => {
      const handleClose = vi.fn()
      const user = userEvent.setup()

      render(
        <Modal isOpen={true} onClose={handleClose} title="Test">
          Content
        </Modal>
      )

      const closeButtons = screen.getAllByRole('button')
      const headerCloseButton = closeButtons.find((btn) => btn.textContent === '×')

      await user.click(headerCloseButton)
      expect(handleClose).toHaveBeenCalledTimes(1)
    })

    it('should call onClose when backdrop is clicked', async () => {
      const handleClose = vi.fn()
      const user = userEvent.setup()

      const { container } = render(
        <Modal isOpen={true} onClose={handleClose} title="Test">
          Content
        </Modal>
      )

      const backdrop = container.querySelector('.bg-opacity-50')
      await user.click(backdrop)
      expect(handleClose).toHaveBeenCalledTimes(1)
    })

    it('should call onClose when Escape key is pressed', async () => {
      const handleClose = vi.fn()
      const user = userEvent.setup()

      render(
        <Modal isOpen={true} onClose={handleClose} title="Test">
          Content
        </Modal>
      )

      await user.keyboard('{Escape}')
      expect(handleClose).toHaveBeenCalled()
    })

    it('should not call onClose for other keys', async () => {
      const handleClose = vi.fn()
      const user = userEvent.setup()

      render(
        <Modal isOpen={true} onClose={handleClose} title="Test">
          Content
        </Modal>
      )

      await user.keyboard('{Enter}')
      expect(handleClose).not.toHaveBeenCalled()
    })
  })

  describe('Body Overflow', () => {
    it('should set body overflow to hidden when modal opens', () => {
      render(
        <Modal isOpen={true} onClose={() => {}} title="Test">
          Content
        </Modal>
      )
      expect(document.body.style.overflow).toBe('hidden')
    })

    it('should restore body overflow when modal closes', () => {
      const { rerender } = render(
        <Modal isOpen={true} onClose={() => {}} title="Test">
          Content
        </Modal>
      )
      expect(document.body.style.overflow).toBe('hidden')

      rerender(
        <Modal isOpen={false} onClose={() => {}} title="Test">
          Content
        </Modal>
      )
      expect(document.body.style.overflow).toBe('unset')
    })

    it('should restore body overflow on unmount', () => {
      const { unmount } = render(
        <Modal isOpen={true} onClose={() => {}} title="Test">
          Content
        </Modal>
      )
      expect(document.body.style.overflow).toBe('hidden')

      unmount()
      expect(document.body.style.overflow).toBe('unset')
    })
  })

  describe('Layout and Styling', () => {
    it('should have fixed positioning', () => {
      const { container } = render(
        <Modal isOpen={true} onClose={() => {}} title="Test">
          Content
        </Modal>
      )
      const wrapper = container.querySelector('.fixed.inset-0.z-50')
      expect(wrapper).toBeInTheDocument()
    })

    it('should have backdrop with proper opacity', () => {
      const { container } = render(
        <Modal isOpen={true} onClose={() => {}} title="Test">
          Content
        </Modal>
      )
      const backdrop = container.querySelector('.bg-black.bg-opacity-50')
      expect(backdrop).toBeInTheDocument()
    })

    it('should center modal content', () => {
      const { container } = render(
        <Modal isOpen={true} onClose={() => {}} title="Test">
          Content
        </Modal>
      )
      const centerContainer = container.querySelector('.flex.min-h-full.items-center.justify-center')
      expect(centerContainer).toBeInTheDocument()
    })

    it('should have white background with rounded corners', () => {
      const { container } = render(
        <Modal isOpen={true} onClose={() => {}} title="Test">
          Content
        </Modal>
      )
      const modal = container.querySelector('.bg-white.rounded-lg.shadow-xl')
      expect(modal).toBeInTheDocument()
    })
  })

  describe('Header Structure', () => {
    it('should have border-b on header', () => {
      const { container } = render(
        <Modal isOpen={true} onClose={() => {}} title="Test">
          Content
        </Modal>
      )
      const header = container.querySelector('.border-b')
      expect(header).toBeInTheDocument()
    })

    it('should render title with correct styling', () => {
      render(
        <Modal isOpen={true} onClose={() => {}} title="Test Title">
          Content
        </Modal>
      )
      const title = screen.getByRole('heading')
      expect(title).toHaveClass('text-xl', 'font-semibold', 'text-gray-900')
    })
  })

  describe('Accessibility', () => {
    it('should use semantic heading for title', () => {
      render(
        <Modal isOpen={true} onClose={() => {}} title="Accessible Modal">
          Content
        </Modal>
      )
      const heading = screen.getByRole('heading', { name: 'Accessible Modal' })
      expect(heading.tagName).toBe('H3')
    })

    it('should have close button accessible', () => {
      render(
        <Modal isOpen={true} onClose={() => {}} title="Test">
          Content
        </Modal>
      )
      const buttons = screen.getAllByRole('button')
      expect(buttons.length).toBeGreaterThan(0)
    })

    it('should support keyboard navigation', async () => {
      const handleClose = vi.fn()
      const user = userEvent.setup()

      render(
        <Modal isOpen={true} onClose={handleClose} title="Test">
          <button>Focus Me</button>
        </Modal>
      )

      await user.tab()
      await user.keyboard('{Escape}')
      expect(handleClose).toHaveBeenCalled()
    })
  })

  describe('Complex Content', () => {
    it('should render complex children structure', () => {
      render(
        <Modal isOpen={true} onClose={() => {}} title="Test">
          <div>
            <h4>Subtitle</h4>
            <p>Paragraph 1</p>
            <p>Paragraph 2</p>
          </div>
        </Modal>
      )
      expect(screen.getByText('Subtitle')).toBeInTheDocument()
      expect(screen.getByText('Paragraph 1')).toBeInTheDocument()
      expect(screen.getByText('Paragraph 2')).toBeInTheDocument()
    })

    it('should handle forms in modal body', () => {
      render(
        <Modal isOpen={true} onClose={() => {}} title="Form Modal">
          <form>
            <input type="text" placeholder="Username" />
            <input type="password" placeholder="Password" />
          </form>
        </Modal>
      )
      expect(screen.getByPlaceholderText('Username')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('Password')).toBeInTheDocument()
    })
  })
})
