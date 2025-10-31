/**
 * Input Component Tests
 * Comprehensive test suite for Input component
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Input from '../Input'

describe('Input Component', () => {
  describe('Rendering', () => {
    it('should render input field', () => {
      render(<Input value="" onChange={() => {}} />)
      expect(screen.getByRole('textbox')).toBeInTheDocument()
    })

    it('should render with default type (text)', () => {
      render(<Input value="" onChange={() => {}} />)
      const input = screen.getByRole('textbox')
      expect(input).toHaveAttribute('type', 'text')
    })

    it('should render with label when provided', () => {
      render(<Input label="Username" value="" onChange={() => {}} />)
      expect(screen.getByText('Username')).toBeInTheDocument()
    })

    it('should render without label when not provided', () => {
      render(<Input value="" onChange={() => {}} />)
      expect(screen.queryByRole('label')).not.toBeInTheDocument()
    })

    it('should render with placeholder', () => {
      render(<Input placeholder="Enter text" value="" onChange={() => {}} />)
      expect(screen.getByPlaceholderText('Enter text')).toBeInTheDocument()
    })
  })

  describe('Input Types', () => {
    it('should render email type', () => {
      render(<Input type="email" value="" onChange={() => {}} />)
      const input = screen.getByRole('textbox')
      expect(input).toHaveAttribute('type', 'email')
    })

    it('should render password type', () => {
      render(<Input type="password" value="" onChange={() => {}} />)
      const input = document.querySelector('input[type="password"]')
      expect(input).toBeInTheDocument()
    })

    it('should render number type', () => {
      render(<Input type="number" value="" onChange={() => {}} />)
      const input = screen.getByRole('spinbutton')
      expect(input).toHaveAttribute('type', 'number')
    })
  })

  describe('Required Field', () => {
    it('should show asterisk when required is true', () => {
      render(<Input label="Email" required value="" onChange={() => {}} />)
      expect(screen.getByText('*')).toBeInTheDocument()
    })

    it('should not show asterisk when required is false', () => {
      render(<Input label="Email" value="" onChange={() => {}} />)
      expect(screen.queryByText('*')).not.toBeInTheDocument()
    })

    it('should have required attribute on input', () => {
      render(<Input required value="" onChange={() => {}} />)
      const input = screen.getByRole('textbox')
      expect(input).toBeRequired()
    })
  })

  describe('Error States', () => {
    it('should display error message when error prop is provided', () => {
      render(<Input error="This field is required" value="" onChange={() => {}} />)
      expect(screen.getByText('This field is required')).toBeInTheDocument()
    })

    it('should not display error message when error prop is not provided', () => {
      render(<Input value="" onChange={() => {}} />)
      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    })

    it('should apply error styling when error exists', () => {
      render(<Input error="Error" value="" onChange={() => {}} />)
      const input = screen.getByRole('textbox')
      expect(input).toHaveClass('border-red-500', 'focus:ring-red-500')
    })

    it('should apply normal styling when no error', () => {
      render(<Input value="" onChange={() => {}} />)
      const input = screen.getByRole('textbox')
      expect(input).toHaveClass('border-gray-300', 'focus:ring-blue-500')
    })
  })

  describe('Disabled State', () => {
    it('should be disabled when disabled prop is true', () => {
      render(<Input disabled value="" onChange={() => {}} />)
      const input = screen.getByRole('textbox')
      expect(input).toBeDisabled()
    })

    it('should not be disabled by default', () => {
      render(<Input value="" onChange={() => {}} />)
      const input = screen.getByRole('textbox')
      expect(input).not.toBeDisabled()
    })

    it('should apply disabled styling', () => {
      render(<Input disabled value="" onChange={() => {}} />)
      const input = screen.getByRole('textbox')
      expect(input).toHaveClass('bg-gray-100', 'cursor-not-allowed')
    })

    it('should apply normal styling when not disabled', () => {
      render(<Input value="" onChange={() => {}} />)
      const input = screen.getByRole('textbox')
      expect(input).toHaveClass('bg-white')
    })
  })

  describe('Value and Change Handling', () => {
    it('should display the provided value', () => {
      render(<Input value="test value" onChange={() => {}} />)
      const input = screen.getByRole('textbox')
      expect(input).toHaveValue('test value')
    })

    it('should call onChange when value changes', async () => {
      const handleChange = vi.fn()
      const user = userEvent.setup()

      render(<Input value="" onChange={handleChange} />)
      const input = screen.getByRole('textbox')

      await user.type(input, 'a')
      expect(handleChange).toHaveBeenCalled()
    })

    it('should update value correctly', async () => {
      const handleChange = vi.fn((e) => e.target.value)
      const user = userEvent.setup()

      render(<Input value="" onChange={handleChange} />)
      const input = screen.getByRole('textbox')

      await user.type(input, 'test')
      expect(handleChange).toHaveBeenCalledTimes(4) // Once per character
    })

    it('should not call onChange when disabled', async () => {
      const handleChange = vi.fn()
      const user = userEvent.setup()

      render(<Input disabled value="" onChange={handleChange} />)
      const input = screen.getByRole('textbox')

      await user.type(input, 'test')
      expect(handleChange).not.toHaveBeenCalled()
    })
  })

  describe('Blur Event', () => {
    it('should call onBlur when input loses focus', async () => {
      const handleBlur = vi.fn()
      const user = userEvent.setup()

      render(<Input value="" onChange={() => {}} onBlur={handleBlur} />)
      const input = screen.getByRole('textbox')

      input.focus()
      await user.tab() // Moves focus away

      expect(handleBlur).toHaveBeenCalled()
    })
  })

  describe('Custom Props', () => {
    it('should accept custom className', () => {
      const { container } = render(
        <Input className="custom-wrapper" value="" onChange={() => {}} />
      )
      expect(container.firstChild).toHaveClass('custom-wrapper')
    })

    it('should pass through additional props', () => {
      render(
        <Input
          value=""
          onChange={() => {}}
          data-testid="custom-input"
          maxLength={10}
        />
      )
      const input = screen.getByTestId('custom-input')
      expect(input).toHaveAttribute('maxLength', '10')
    })
  })

  describe('Accessibility', () => {
    it('should render label and input together', () => {
      render(<Input label="Email Address" value="" onChange={() => {}} />)
      expect(screen.getByText(/email address/i)).toBeInTheDocument()
      expect(screen.getByRole('textbox')).toBeInTheDocument()
    })

    it('should have focus ring styles', () => {
      render(<Input value="" onChange={() => {}} />)
      const input = screen.getByRole('textbox')
      expect(input).toHaveClass('focus:outline-none', 'focus:ring-2')
    })

    it('should be keyboard accessible', async () => {
      const handleChange = vi.fn()
      const user = userEvent.setup()

      render(<Input value="" onChange={handleChange} />)
      const input = screen.getByRole('textbox')

      await user.tab()
      expect(input).toHaveFocus()

      await user.keyboard('test')
      expect(handleChange).toHaveBeenCalled()
    })
  })

  describe('Combined Props', () => {
    it('should handle all props together correctly', () => {
      const handleChange = vi.fn()
      const handleBlur = vi.fn()

      render(
        <Input
          label="Username"
          type="text"
          value="john_doe"
          onChange={handleChange}
          onBlur={handleBlur}
          placeholder="Enter username"
          error="Username is taken"
          required
          className="custom-class"
        />
      )

      // Check label (appears in label element)
      const labels = screen.getAllByText(/username/i)
      expect(labels.length).toBeGreaterThan(0)

      expect(screen.getByRole('textbox')).toHaveValue('john_doe')
      expect(screen.getByPlaceholderText('Enter username')).toBeInTheDocument()
      expect(screen.getByText('Username is taken')).toBeInTheDocument()
      expect(screen.getByText('*')).toBeInTheDocument()
    })
  })
})
