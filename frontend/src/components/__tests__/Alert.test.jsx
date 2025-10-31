/**
 * Alert Component Tests
 * Comprehensive test suite for Alert component
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Alert from '../Alert'

describe('Alert Component', () => {
  describe('Rendering', () => {
    it('should render alert with message', () => {
      render(<Alert message="Test message" />)
      expect(screen.getByText('Test message')).toBeInTheDocument()
    })

    it('should not render when message is empty', () => {
      const { container } = render(<Alert message="" />)
      expect(container.firstChild).toBeNull()
    })

    it('should not render when message is null', () => {
      const { container } = render(<Alert message={null} />)
      expect(container.firstChild).toBeNull()
    })

    it('should not render when message is undefined', () => {
      const { container } = render(<Alert />)
      expect(container.firstChild).toBeNull()
    })

    it('should render with default type (info)', () => {
      const { container } = render(<Alert message="Info message" />)
      const alert = container.firstChild
      expect(alert).toHaveClass('bg-blue-50', 'border-blue-500', 'text-blue-900')
    })
  })

  describe('Alert Types', () => {
    it('should render info alert correctly', () => {
      const { container } = render(<Alert type="info" message="Info message" />)
      const alert = container.firstChild
      expect(alert).toHaveClass('bg-blue-50', 'border-blue-500', 'text-blue-900')
      expect(screen.getByText('💡')).toBeInTheDocument()
    })

    it('should render success alert correctly', () => {
      const { container } = render(<Alert type="success" message="Success message" />)
      const alert = container.firstChild
      expect(alert).toHaveClass('bg-green-50', 'border-green-500', 'text-green-900')
      expect(screen.getByText('✓')).toBeInTheDocument()
    })

    it('should render warning alert correctly', () => {
      const { container } = render(<Alert type="warning" message="Warning message" />)
      const alert = container.firstChild
      expect(alert).toHaveClass('bg-yellow-50', 'border-yellow-500', 'text-yellow-900')
      expect(screen.getByText('⚠')).toBeInTheDocument()
    })

    it('should render error alert correctly', () => {
      const { container } = render(<Alert type="error" message="Error message" />)
      const alert = container.firstChild
      expect(alert).toHaveClass('bg-red-50', 'border-red-500', 'text-red-900')
      expect(screen.getByText('✕')).toBeInTheDocument()
    })
  })

  describe('Close Button', () => {
    it('should render close button when onClose is provided', () => {
      const handleClose = vi.fn()
      render(<Alert message="Test" onClose={handleClose} />)
      expect(screen.getByRole('button')).toBeInTheDocument()
    })

    it('should not render close button when onClose is not provided', () => {
      render(<Alert message="Test" />)
      expect(screen.queryByRole('button')).not.toBeInTheDocument()
    })

    it('should call onClose when close button is clicked', async () => {
      const handleClose = vi.fn()
      const user = userEvent.setup()

      render(<Alert message="Test" onClose={handleClose} />)
      const closeButton = screen.getByRole('button')

      await user.click(closeButton)
      expect(handleClose).toHaveBeenCalledTimes(1)
    })

    it('should display × as close button text', () => {
      const handleClose = vi.fn()
      render(<Alert message="Test" onClose={handleClose} />)
      expect(screen.getByText('×')).toBeInTheDocument()
    })
  })

  describe('Custom Props', () => {
    it('should accept custom className', () => {
      const { container } = render(<Alert message="Test" className="custom-class" />)
      const alert = container.firstChild
      expect(alert).toHaveClass('custom-class')
    })

    it('should merge custom className with default classes', () => {
      const { container } = render(<Alert message="Test" className="custom-class" />)
      const alert = container.firstChild
      expect(alert).toHaveClass('custom-class', 'border-l-4', 'p-4')
    })
  })

  describe('Layout and Structure', () => {
    it('should have correct layout classes', () => {
      const { container } = render(<Alert message="Test" />)
      const alert = container.firstChild
      expect(alert).toHaveClass('flex', 'items-start', 'justify-between')
    })

    it('should have border-l-4 class', () => {
      const { container } = render(<Alert message="Test" />)
      const alert = container.firstChild
      expect(alert).toHaveClass('border-l-4')
    })

    it('should have padding', () => {
      const { container } = render(<Alert message="Test" />)
      const alert = container.firstChild
      expect(alert).toHaveClass('p-4')
    })
  })

  describe('Icon Display', () => {
    it('should display icon for each type', () => {
      const types = [
        { type: 'info', icon: '💡' },
        { type: 'success', icon: '✓' },
        { type: 'warning', icon: '⚠' },
        { type: 'error', icon: '✕' },
      ]

      types.forEach(({ type, icon }) => {
        const { unmount } = render(<Alert type={type} message={`${type} message`} />)
        expect(screen.getByText(icon)).toBeInTheDocument()
        unmount()
      })
    })

    it('should render icon with correct styling', () => {
      render(<Alert message="Test" />)
      const icon = screen.getByText('💡')
      expect(icon).toHaveClass('text-xl')
    })
  })

  describe('Message Display', () => {
    it('should display long messages', () => {
      const longMessage = 'This is a very long message that should still be displayed correctly in the alert component without any issues.'
      render(<Alert message={longMessage} />)
      expect(screen.getByText(longMessage)).toBeInTheDocument()
    })

    it('should render message with correct styling', () => {
      render(<Alert message="Test message" />)
      const message = screen.getByText('Test message')
      expect(message).toHaveClass('text-sm')
    })
  })

  describe('Combined Props', () => {
    it('should handle all props together correctly', async () => {
      const handleClose = vi.fn()
      const user = userEvent.setup()

      const { container } = render(
        <Alert
          type="error"
          message="Critical error occurred"
          onClose={handleClose}
          className="my-custom-class"
        />
      )

      const alert = container.firstChild
      expect(alert).toHaveClass('bg-red-50', 'border-red-500', 'text-red-900')
      expect(alert).toHaveClass('my-custom-class')
      expect(screen.getByText('✕')).toBeInTheDocument()
      expect(screen.getByText('Critical error occurred')).toBeInTheDocument()

      const closeButton = screen.getByRole('button')
      await user.click(closeButton)
      expect(handleClose).toHaveBeenCalled()
    })
  })

  describe('Accessibility', () => {
    it('should have proper semantic structure', () => {
      render(<Alert message="Test" />)
      const message = screen.getByText('Test')
      expect(message.tagName).toBe('P')
    })

    it('should have accessible close button', () => {
      const handleClose = vi.fn()
      render(<Alert message="Test" onClose={handleClose} />)
      const button = screen.getByRole('button')
      expect(button).toBeInTheDocument()
    })

    it('should be keyboard accessible for close button', async () => {
      const handleClose = vi.fn()
      const user = userEvent.setup()

      render(<Alert message="Test" onClose={handleClose} />)
      const button = screen.getByRole('button')

      button.focus()
      await user.keyboard('{Enter}')
      expect(handleClose).toHaveBeenCalled()
    })
  })
})
