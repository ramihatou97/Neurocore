/**
 * ProgressBar Component Tests
 * Comprehensive test suite for ProgressBar component
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ProgressBar from '../ProgressBar'

describe('ProgressBar Component', () => {
  describe('Rendering', () => {
    it('should render progress bar', () => {
      const { container } = render(<ProgressBar progress={50} />)
      const progressBar = container.querySelector('.bg-gray-200')
      expect(progressBar).toBeInTheDocument()
    })

    it('should render with percentage text by default', () => {
      render(<ProgressBar progress={75} />)
      expect(screen.getByText('75%')).toBeInTheDocument()
    })

    it('should render with default size (md)', () => {
      const { container } = render(<ProgressBar progress={50} />)
      const progressBar = container.querySelector('.h-4')
      expect(progressBar).toBeInTheDocument()
    })
  })

  describe('Progress Values', () => {
    it('should display correct progress value', () => {
      render(<ProgressBar progress={25} />)
      expect(screen.getByText('25%')).toBeInTheDocument()
    })

    it('should display 0% progress', () => {
      render(<ProgressBar progress={0} />)
      expect(screen.getByText('0%')).toBeInTheDocument()
    })

    it('should display 100% progress', () => {
      render(<ProgressBar progress={100} />)
      expect(screen.getByText('100%')).toBeInTheDocument()
    })

    it('should clamp negative values to 0', () => {
      render(<ProgressBar progress={-10} />)
      expect(screen.getByText('0%')).toBeInTheDocument()
    })

    it('should clamp values over 100 to 100', () => {
      render(<ProgressBar progress={150} />)
      expect(screen.getByText('100%')).toBeInTheDocument()
    })

    it('should handle decimal progress values', () => {
      render(<ProgressBar progress={33.33} />)
      expect(screen.getByText('33.33%')).toBeInTheDocument()
    })
  })

  describe('Progress Bar Width', () => {
    it('should set width based on progress', () => {
      const { container } = render(<ProgressBar progress={60} />)
      const bar = container.querySelector('.bg-blue-600')
      expect(bar).toHaveStyle({ width: '60%' })
    })

    it('should set width to 0% for negative values', () => {
      const { container } = render(<ProgressBar progress={-20} />)
      const bar = container.querySelector('.bg-blue-600')
      expect(bar).toHaveStyle({ width: '0%' })
    })

    it('should set width to 100% for values over 100', () => {
      const { container } = render(<ProgressBar progress={200} />)
      const bar = container.querySelector('.bg-blue-600')
      expect(bar).toHaveStyle({ width: '100%' })
    })
  })

  describe('Size Variants', () => {
    it('should render small size correctly', () => {
      const { container } = render(<ProgressBar progress={50} size="sm" />)
      const progressBar = container.querySelector('.h-2')
      expect(progressBar).toBeInTheDocument()
    })

    it('should render medium size correctly', () => {
      const { container } = render(<ProgressBar progress={50} size="md" />)
      const progressBar = container.querySelector('.h-4')
      expect(progressBar).toBeInTheDocument()
    })

    it('should render large size correctly', () => {
      const { container } = render(<ProgressBar progress={50} size="lg" />)
      const progressBar = container.querySelector('.h-6')
      expect(progressBar).toBeInTheDocument()
    })
  })

  describe('Percentage Display', () => {
    it('should show percentage when showPercentage is true', () => {
      render(<ProgressBar progress={45} showPercentage={true} />)
      expect(screen.getByText('45%')).toBeInTheDocument()
    })

    it('should hide percentage when showPercentage is false', () => {
      render(<ProgressBar progress={45} showPercentage={false} />)
      expect(screen.queryByText('45%')).not.toBeInTheDocument()
    })

    it('should show percentage by default', () => {
      render(<ProgressBar progress={30} />)
      expect(screen.getByText('30%')).toBeInTheDocument()
    })

    it('should render percentage with correct styling', () => {
      render(<ProgressBar progress={50} />)
      const percentage = screen.getByText('50%')
      expect(percentage).toHaveClass('text-sm', 'text-gray-600', 'mt-1', 'text-right')
    })
  })

  describe('Custom Props', () => {
    it('should accept custom className', () => {
      const { container } = render(
        <ProgressBar progress={50} className="custom-class" />
      )
      expect(container.firstChild).toHaveClass('custom-class')
    })

    it('should merge custom className with wrapper', () => {
      const { container } = render(
        <ProgressBar progress={50} className="my-4" />
      )
      expect(container.firstChild).toHaveClass('my-4')
    })
  })

  describe('Styling', () => {
    it('should have gray background', () => {
      const { container } = render(<ProgressBar progress={50} />)
      const track = container.querySelector('.bg-gray-200')
      expect(track).toBeInTheDocument()
    })

    it('should have blue progress bar', () => {
      const { container } = render(<ProgressBar progress={50} />)
      const bar = container.querySelector('.bg-blue-600')
      expect(bar).toBeInTheDocument()
    })

    it('should have rounded corners', () => {
      const { container } = render(<ProgressBar progress={50} />)
      const track = container.querySelector('.rounded-full')
      expect(track).toBeInTheDocument()
    })

    it('should have overflow hidden', () => {
      const { container } = render(<ProgressBar progress={50} />)
      const track = container.querySelector('.overflow-hidden')
      expect(track).toBeInTheDocument()
    })

    it('should have full width', () => {
      const { container } = render(<ProgressBar progress={50} />)
      const track = container.querySelector('.w-full')
      expect(track).toBeInTheDocument()
    })

    it('should have transition animation', () => {
      const { container } = render(<ProgressBar progress={50} />)
      const bar = container.querySelector('.bg-blue-600')
      expect(bar).toHaveClass('transition-all', 'duration-300', 'ease-in-out')
    })

    it('should have full height for progress bar', () => {
      const { container } = render(<ProgressBar progress={50} />)
      const bar = container.querySelector('.bg-blue-600')
      expect(bar).toHaveClass('h-full')
    })
  })

  describe('Combined Props', () => {
    it('should handle all props together correctly', () => {
      const { container } = render(
        <ProgressBar
          progress={80}
          size="lg"
          showPercentage={true}
          className="test-class"
        />
      )

      expect(container.firstChild).toHaveClass('test-class')
      expect(container.querySelector('.h-6')).toBeInTheDocument()
      expect(screen.getByText('80%')).toBeInTheDocument()
    })

    it('should work without percentage display', () => {
      const { container } = render(
        <ProgressBar progress={65} size="sm" showPercentage={false} />
      )

      expect(container.querySelector('.h-2')).toBeInTheDocument()
      expect(screen.queryByText('65%')).not.toBeInTheDocument()
      const bar = container.querySelector('.bg-blue-600')
      expect(bar).toHaveStyle({ width: '65%' })
    })
  })

  describe('Edge Cases', () => {
    it('should handle progress value of exactly 0', () => {
      const { container } = render(<ProgressBar progress={0} />)
      const bar = container.querySelector('.bg-blue-600')
      expect(bar).toHaveStyle({ width: '0%' })
      expect(screen.getByText('0%')).toBeInTheDocument()
    })

    it('should handle progress value of exactly 100', () => {
      const { container } = render(<ProgressBar progress={100} />)
      const bar = container.querySelector('.bg-blue-600')
      expect(bar).toHaveStyle({ width: '100%' })
      expect(screen.getByText('100%')).toBeInTheDocument()
    })

    it('should handle very small progress values', () => {
      render(<ProgressBar progress={0.5} />)
      expect(screen.getByText('0.5%')).toBeInTheDocument()
    })

    it('should handle very large progress values', () => {
      render(<ProgressBar progress={9999} />)
      expect(screen.getByText('100%')).toBeInTheDocument()
    })

    it('should handle undefined size gracefully', () => {
      const { container } = render(<ProgressBar progress={50} size={undefined} />)
      // Should render but may not have a size class or use default
      expect(container.querySelector('.bg-gray-200')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('should have semantic structure', () => {
      const { container } = render(<ProgressBar progress={50} />)
      const wrapper = container.firstChild
      expect(wrapper).toBeInTheDocument()
    })

    it('should have visible percentage for screen readers', () => {
      render(<ProgressBar progress={75} />)
      const percentage = screen.getByText('75%')
      expect(percentage).toBeVisible()
    })

    it('should maintain structure without percentage', () => {
      const { container } = render(<ProgressBar progress={50} showPercentage={false} />)
      const track = container.querySelector('.bg-gray-200')
      const bar = container.querySelector('.bg-blue-600')
      expect(track).toBeInTheDocument()
      expect(bar).toBeInTheDocument()
    })
  })
})
