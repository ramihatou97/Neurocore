/**
 * Badge Component Tests
 * Comprehensive test suite for Badge component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import Badge from '../Badge'

// Mock the helpers module
vi.mock('../../utils/helpers', () => ({
  getStatusColor: vi.fn((status) => {
    const statusColors = {
      pending: 'text-yellow-600 bg-yellow-100',
      running: 'text-blue-600 bg-blue-100',
      completed: 'text-green-600 bg-green-100',
      failed: 'text-red-600 bg-red-100',
    }
    return statusColors[status?.toLowerCase()] || 'text-gray-600 bg-gray-100'
  }),
}))

describe('Badge Component', () => {
  describe('Rendering', () => {
    it('should render badge with children', () => {
      render(<Badge>Test Badge</Badge>)
      expect(screen.getByText('Test Badge')).toBeInTheDocument()
    })

    it('should render with default variant', () => {
      const { container } = render(<Badge>Default</Badge>)
      const badge = container.firstChild
      expect(badge).toHaveClass('text-gray-700', 'bg-gray-100')
    })

    it('should have correct base styling', () => {
      const { container } = render(<Badge>Styled</Badge>)
      const badge = container.firstChild
      expect(badge).toHaveClass(
        'inline-flex',
        'items-center',
        'px-2.5',
        'py-0.5',
        'rounded-full',
        'text-xs',
        'font-medium'
      )
    })
  })

  describe('Variants', () => {
    it('should render default variant correctly', () => {
      const { container } = render(<Badge variant="default">Default</Badge>)
      const badge = container.firstChild
      expect(badge).toHaveClass('text-gray-700', 'bg-gray-100')
    })

    it('should render primary variant correctly', () => {
      const { container } = render(<Badge variant="primary">Primary</Badge>)
      const badge = container.firstChild
      expect(badge).toHaveClass('text-blue-700', 'bg-blue-100')
    })

    it('should render success variant correctly', () => {
      const { container } = render(<Badge variant="success">Success</Badge>)
      const badge = container.firstChild
      expect(badge).toHaveClass('text-green-700', 'bg-green-100')
    })

    it('should render warning variant correctly', () => {
      const { container } = render(<Badge variant="warning">Warning</Badge>)
      const badge = container.firstChild
      expect(badge).toHaveClass('text-yellow-700', 'bg-yellow-100')
    })

    it('should render danger variant correctly', () => {
      const { container } = render(<Badge variant="danger">Danger</Badge>)
      const badge = container.firstChild
      expect(badge).toHaveClass('text-red-700', 'bg-red-100')
    })

    it('should fallback to default for invalid variant', () => {
      const { container } = render(<Badge variant="invalid">Invalid</Badge>)
      const badge = container.firstChild
      expect(badge).toHaveClass('text-gray-700', 'bg-gray-100')
    })
  })

  describe('Status Prop', () => {
    it('should use status color when status is provided', () => {
      const { container } = render(<Badge status="pending">Pending</Badge>)
      const badge = container.firstChild
      expect(badge).toHaveClass('text-yellow-600', 'bg-yellow-100')
    })

    it('should override variant when status is provided', () => {
      const { container } = render(
        <Badge status="completed" variant="danger">
          Completed
        </Badge>
      )
      const badge = container.firstChild
      // Should use status color, not variant
      expect(badge).toHaveClass('text-green-600', 'bg-green-100')
      expect(badge).not.toHaveClass('text-red-700', 'bg-red-100')
    })

    it('should handle running status', () => {
      const { container } = render(<Badge status="running">Running</Badge>)
      const badge = container.firstChild
      expect(badge).toHaveClass('text-blue-600', 'bg-blue-100')
    })

    it('should handle failed status', () => {
      const { container } = render(<Badge status="failed">Failed</Badge>)
      const badge = container.firstChild
      expect(badge).toHaveClass('text-red-600', 'bg-red-100')
    })

    it('should handle unknown status with default colors', () => {
      const { container } = render(<Badge status="unknown">Unknown</Badge>)
      const badge = container.firstChild
      expect(badge).toHaveClass('text-gray-600', 'bg-gray-100')
    })
  })

  describe('Custom Props', () => {
    it('should accept custom className', () => {
      const { container } = render(<Badge className="custom-class">Custom</Badge>)
      const badge = container.firstChild
      expect(badge).toHaveClass('custom-class')
    })

    it('should merge custom className with default classes', () => {
      const { container } = render(<Badge className="ml-2">Merged</Badge>)
      const badge = container.firstChild
      expect(badge).toHaveClass('ml-2', 'inline-flex', 'rounded-full')
    })
  })

  describe('Content Rendering', () => {
    it('should render text content', () => {
      render(<Badge>Text Content</Badge>)
      expect(screen.getByText('Text Content')).toBeInTheDocument()
    })

    it('should render numeric content', () => {
      render(<Badge>{42}</Badge>)
      expect(screen.getByText('42')).toBeInTheDocument()
    })

    it('should render complex children', () => {
      render(
        <Badge>
          <span>Complex</span>
          <span> Badge</span>
        </Badge>
      )
      expect(screen.getByText('Complex')).toBeInTheDocument()
      expect(screen.getByText('Badge')).toBeInTheDocument()
    })
  })

  describe('Combined Props', () => {
    it('should handle multiple props correctly', () => {
      const { container } = render(
        <Badge variant="primary" className="extra-class">
          Combined
        </Badge>
      )
      const badge = container.firstChild
      expect(badge).toHaveClass('text-blue-700', 'bg-blue-100')
      expect(badge).toHaveClass('extra-class')
      expect(badge).toHaveClass('inline-flex', 'rounded-full')
      expect(screen.getByText('Combined')).toBeInTheDocument()
    })

    it('should prioritize status over variant', () => {
      const { container } = render(
        <Badge status="failed" variant="success" className="test-class">
          Priority Test
        </Badge>
      )
      const badge = container.firstChild
      expect(badge).toHaveClass('text-red-600', 'bg-red-100')
      expect(badge).not.toHaveClass('text-green-700', 'bg-green-100')
    })
  })

  describe('Accessibility', () => {
    it('should render as a span element', () => {
      const { container } = render(<Badge>Accessibility</Badge>)
      const badge = container.firstChild
      expect(badge.tagName).toBe('SPAN')
    })

    it('should be inline element', () => {
      const { container } = render(<Badge>Inline</Badge>)
      const badge = container.firstChild
      expect(badge).toHaveClass('inline-flex')
    })

    it('should preserve text content for screen readers', () => {
      render(<Badge>Status: Active</Badge>)
      expect(screen.getByText('Status: Active')).toBeInTheDocument()
    })
  })

  describe('Layout', () => {
    it('should use flexbox layout', () => {
      const { container } = render(<Badge>Flex</Badge>)
      const badge = container.firstChild
      expect(badge).toHaveClass('inline-flex', 'items-center')
    })

    it('should have rounded-full shape', () => {
      const { container } = render(<Badge>Rounded</Badge>)
      const badge = container.firstChild
      expect(badge).toHaveClass('rounded-full')
    })

    it('should have proper padding', () => {
      const { container } = render(<Badge>Padded</Badge>)
      const badge = container.firstChild
      expect(badge).toHaveClass('px-2.5', 'py-0.5')
    })

    it('should have small text size', () => {
      const { container } = render(<Badge>Small Text</Badge>)
      const badge = container.firstChild
      expect(badge).toHaveClass('text-xs')
    })

    it('should have medium font weight', () => {
      const { container } = render(<Badge>Medium Weight</Badge>)
      const badge = container.firstChild
      expect(badge).toHaveClass('font-medium')
    })
  })
})
