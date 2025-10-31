/**
 * Button Component Tests
 * Comprehensive test suite for Button component
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Button from '../Button'

describe('Button Component', () => {
  describe('Rendering', () => {
    it('should render button with children', () => {
      render(<Button>Click Me</Button>)
      expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument()
    })

    it('should render with default variant (primary)', () => {
      render(<Button>Primary</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-blue-600')
    })

    it('should render with default size (md)', () => {
      render(<Button>Medium</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('px-4', 'py-2', 'text-base')
    })

    it('should render with default type (button)', () => {
      render(<Button>Button Type</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('type', 'button')
    })
  })

  describe('Variants', () => {
    it('should render primary variant correctly', () => {
      render(<Button variant="primary">Primary</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-blue-600', 'text-white', 'hover:bg-blue-700')
    })

    it('should render secondary variant correctly', () => {
      render(<Button variant="secondary">Secondary</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-gray-200', 'text-gray-900', 'hover:bg-gray-300')
    })

    it('should render danger variant correctly', () => {
      render(<Button variant="danger">Danger</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-red-600', 'text-white', 'hover:bg-red-700')
    })

    it('should render success variant correctly', () => {
      render(<Button variant="success">Success</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-green-600', 'text-white', 'hover:bg-green-700')
    })

    it('should render outline variant correctly', () => {
      render(<Button variant="outline">Outline</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('border-2', 'border-blue-600', 'text-blue-600')
    })
  })

  describe('Sizes', () => {
    it('should render small size correctly', () => {
      render(<Button size="sm">Small</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('px-3', 'py-1.5', 'text-sm')
    })

    it('should render medium size correctly', () => {
      render(<Button size="md">Medium</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('px-4', 'py-2', 'text-base')
    })

    it('should render large size correctly', () => {
      render(<Button size="lg">Large</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('px-6', 'py-3', 'text-lg')
    })
  })

  describe('States', () => {
    it('should handle disabled state', () => {
      render(<Button disabled>Disabled</Button>)
      const button = screen.getByRole('button')
      expect(button).toBeDisabled()
      expect(button).toHaveClass('disabled:opacity-50', 'disabled:cursor-not-allowed')
    })

    it('should handle loading state', () => {
      render(<Button loading>Loading</Button>)
      const button = screen.getByRole('button')
      expect(button).toBeDisabled()
      // LoadingSpinner should be rendered (it renders a div with animate-spin class)
      const spinner = button.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()
    })

    it('should be disabled when loading is true', () => {
      render(<Button loading>Loading</Button>)
      const button = screen.getByRole('button')
      expect(button).toBeDisabled()
    })
  })

  describe('Width', () => {
    it('should render with full width when fullWidth is true', () => {
      render(<Button fullWidth>Full Width</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('w-full')
    })

    it('should not have full width by default', () => {
      render(<Button>Normal Width</Button>)
      const button = screen.getByRole('button')
      expect(button).not.toHaveClass('w-full')
    })
  })

  describe('Custom Props', () => {
    it('should accept custom className', () => {
      render(<Button className="custom-class">Custom</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('custom-class')
    })

    it('should accept type prop', () => {
      render(<Button type="submit">Submit</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('type', 'submit')
    })
  })

  describe('Interactions', () => {
    it('should call onClick when clicked', async () => {
      const handleClick = vi.fn()
      const user = userEvent.setup()

      render(<Button onClick={handleClick}>Click Me</Button>)
      const button = screen.getByRole('button')

      await user.click(button)
      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('should not call onClick when disabled', async () => {
      const handleClick = vi.fn()
      const user = userEvent.setup()

      render(<Button onClick={handleClick} disabled>Click Me</Button>)
      const button = screen.getByRole('button')

      await user.click(button)
      expect(handleClick).not.toHaveBeenCalled()
    })

    it('should not call onClick when loading', async () => {
      const handleClick = vi.fn()
      const user = userEvent.setup()

      render(<Button onClick={handleClick} loading>Click Me</Button>)
      const button = screen.getByRole('button')

      await user.click(button)
      expect(handleClick).not.toHaveBeenCalled()
    })
  })

  describe('Accessibility', () => {
    it('should have focus ring styles', () => {
      render(<Button>Focus Test</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('focus:outline-none', 'focus:ring-2', 'focus:ring-offset-2')
    })

    it('should be keyboard accessible', async () => {
      const handleClick = vi.fn()
      const user = userEvent.setup()

      render(<Button onClick={handleClick}>Keyboard Test</Button>)
      const button = screen.getByRole('button')

      button.focus()
      await user.keyboard('{Enter}')
      expect(handleClick).toHaveBeenCalledTimes(1)
    })
  })

  describe('Combined Props', () => {
    it('should handle multiple props correctly', () => {
      const handleClick = vi.fn()
      render(
        <Button
          variant="danger"
          size="lg"
          fullWidth
          type="submit"
          className="extra-class"
          onClick={handleClick}
        >
          Complex Button
        </Button>
      )

      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-red-600')
      expect(button).toHaveClass('px-6', 'py-3', 'text-lg')
      expect(button).toHaveClass('w-full')
      expect(button).toHaveClass('extra-class')
      expect(button).toHaveAttribute('type', 'submit')
    })
  })
})
