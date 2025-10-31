/**
 * Card Component Tests
 * Comprehensive test suite for Card component
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import Card from '../Card'

describe('Card Component', () => {
  describe('Rendering', () => {
    it('should render card with children', () => {
      render(<Card>Test Content</Card>)
      expect(screen.getByText('Test Content')).toBeInTheDocument()
    })

    it('should render with default padding (md)', () => {
      const { container } = render(<Card>Default Padding</Card>)
      const card = container.firstChild
      expect(card).toHaveClass('p-6')
    })

    it('should render with default styling', () => {
      const { container } = render(<Card>Styled Card</Card>)
      const card = container.firstChild
      expect(card).toHaveClass('bg-white', 'rounded-lg', 'shadow')
    })
  })

  describe('Padding Variants', () => {
    it('should render with no padding', () => {
      const { container } = render(<Card padding="none">No Padding</Card>)
      const card = container.firstChild
      expect(card).not.toHaveClass('p-4', 'p-6', 'p-8')
    })

    it('should render with small padding', () => {
      const { container } = render(<Card padding="sm">Small Padding</Card>)
      const card = container.firstChild
      expect(card).toHaveClass('p-4')
    })

    it('should render with medium padding', () => {
      const { container } = render(<Card padding="md">Medium Padding</Card>)
      const card = container.firstChild
      expect(card).toHaveClass('p-6')
    })

    it('should render with large padding', () => {
      const { container } = render(<Card padding="lg">Large Padding</Card>)
      const card = container.firstChild
      expect(card).toHaveClass('p-8')
    })
  })

  describe('Hover Effect', () => {
    it('should not have hover effect by default', () => {
      const { container } = render(<Card>No Hover</Card>)
      const card = container.firstChild
      expect(card).not.toHaveClass('hover:shadow-lg', 'transition-shadow', 'cursor-pointer')
    })

    it('should apply hover effect when hover is true', () => {
      const { container } = render(<Card hover>Hover Card</Card>)
      const card = container.firstChild
      expect(card).toHaveClass('hover:shadow-lg', 'transition-shadow', 'cursor-pointer')
    })
  })

  describe('Custom Props', () => {
    it('should accept custom className', () => {
      const { container } = render(<Card className="custom-class">Custom</Card>)
      const card = container.firstChild
      expect(card).toHaveClass('custom-class')
    })

    it('should merge custom className with default classes', () => {
      const { container } = render(<Card className="custom-class">Merged Classes</Card>)
      const card = container.firstChild
      expect(card).toHaveClass('custom-class', 'bg-white', 'rounded-lg', 'shadow')
    })
  })

  describe('Content Rendering', () => {
    it('should render complex children', () => {
      render(
        <Card>
          <h2>Title</h2>
          <p>Description</p>
        </Card>
      )
      expect(screen.getByText('Title')).toBeInTheDocument()
      expect(screen.getByText('Description')).toBeInTheDocument()
    })

    it('should render nested components', () => {
      render(
        <Card>
          <div data-testid="nested">
            <span>Nested Content</span>
          </div>
        </Card>
      )
      expect(screen.getByTestId('nested')).toBeInTheDocument()
      expect(screen.getByText('Nested Content')).toBeInTheDocument()
    })
  })

  describe('Combined Props', () => {
    it('should handle multiple props correctly', () => {
      const { container } = render(
        <Card padding="lg" hover className="extra-class">
          Combined Props
        </Card>
      )
      const card = container.firstChild
      expect(card).toHaveClass('p-8')
      expect(card).toHaveClass('hover:shadow-lg', 'transition-shadow', 'cursor-pointer')
      expect(card).toHaveClass('extra-class')
      expect(card).toHaveClass('bg-white', 'rounded-lg', 'shadow')
    })
  })

  describe('Accessibility', () => {
    it('should render as a div element', () => {
      const { container } = render(<Card>Accessibility Test</Card>)
      const card = container.firstChild
      expect(card.tagName).toBe('DIV')
    })

    it('should preserve children structure for screen readers', () => {
      render(
        <Card>
          <h1>Heading</h1>
          <p>Paragraph</p>
        </Card>
      )
      const heading = screen.getByRole('heading', { level: 1 })
      expect(heading).toBeInTheDocument()
    })
  })
})
