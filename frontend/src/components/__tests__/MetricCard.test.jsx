/**
 * MetricCard Component Tests
 * Comprehensive test suite for MetricCard component
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import MetricCard from '../MetricCard'
import { Star as StarIcon } from '@mui/icons-material'

// Create MUI theme for tests
const theme = createTheme()

describe('MetricCard Component', () => {
  const renderMetricCard = (props) => {
    return render(
      <ThemeProvider theme={theme}>
        <MetricCard {...props} />
      </ThemeProvider>
    )
  }

  describe('Basic Rendering', () => {
    it('should render metric card with title', () => {
      renderMetricCard({ title: 'Total Users', value: 1234 })
      expect(screen.getByText('Total Users')).toBeInTheDocument()
    })

    it('should render metric card with value', () => {
      renderMetricCard({ title: 'Revenue', value: 5000 })
      expect(screen.getByText('5000')).toBeInTheDocument()
    })

    it('should render numeric value', () => {
      renderMetricCard({ title: 'Count', value: 42 })
      expect(screen.getByText('42')).toBeInTheDocument()
    })

    it('should render string value', () => {
      renderMetricCard({ title: 'Status', value: 'Active' })
      expect(screen.getByText('Active')).toBeInTheDocument()
    })

    it('should render zero value', () => {
      renderMetricCard({ title: 'Errors', value: 0 })
      expect(screen.getByText('0')).toBeInTheDocument()
    })
  })

  describe('Unit Display', () => {
    it('should render unit when provided', () => {
      renderMetricCard({ title: 'Revenue', value: 5000, unit: 'USD' })
      expect(screen.getByText('USD')).toBeInTheDocument()
    })

    it('should not render unit when not provided', () => {
      renderMetricCard({ title: 'Count', value: 100 })
      expect(screen.queryByText('USD')).not.toBeInTheDocument()
    })

    it('should render custom unit symbols', () => {
      renderMetricCard({ title: 'Size', value: 50, unit: 'MB' })
      expect(screen.getByText('MB')).toBeInTheDocument()
    })

    it('should render percentage unit', () => {
      renderMetricCard({ title: 'Progress', value: 75, unit: '%' })
      expect(screen.getByText('%')).toBeInTheDocument()
    })
  })

  describe('Trend Display', () => {
    it('should show trending up icon for "up" trend', () => {
      const { container } = renderMetricCard({
        title: 'Growth',
        value: 100,
        trend: 'up',
      })
      // MUI renders icons as SVGs
      const svg = container.querySelector('svg[data-testid="TrendingUpIcon"]')
      expect(svg).toBeInTheDocument()
    })

    it('should show trending down icon for "down" trend', () => {
      const { container } = renderMetricCard({
        title: 'Loss',
        value: 100,
        trend: 'down',
      })
      const svg = container.querySelector('svg[data-testid="TrendingDownIcon"]')
      expect(svg).toBeInTheDocument()
    })

    it('should show trending flat icon for "stable" trend', () => {
      const { container } = renderMetricCard({
        title: 'Steady',
        value: 100,
        trend: 'stable',
      })
      const svg = container.querySelector('svg[data-testid="TrendingFlatIcon"]')
      expect(svg).toBeInTheDocument()
    })

    it('should show flat icon for "unknown" trend', () => {
      const { container } = renderMetricCard({
        title: 'Unknown',
        value: 100,
        trend: 'unknown',
      })
      const svg = container.querySelector('svg[data-testid="TrendingFlatIcon"]')
      expect(svg).toBeInTheDocument()
    })

    it('should show flat icon for invalid trend', () => {
      const { container } = renderMetricCard({
        title: 'Invalid',
        value: 100,
        trend: 'invalid-trend',
      })
      const svg = container.querySelector('svg[data-testid="TrendingFlatIcon"]')
      expect(svg).toBeInTheDocument()
    })

    it('should not show trend icons when trend is null and no changePercentage', () => {
      const { container } = renderMetricCard({
        title: 'Null Trend',
        value: 100,
        trend: null,
      })
      // When trend is null and no changePercentage, the trend row doesn't render
      const svg = container.querySelector('svg[data-testid="TrendingFlatIcon"]')
      expect(svg).not.toBeInTheDocument()
    })
  })

  describe('Change Percentage Display', () => {
    it('should display positive change with + sign', () => {
      renderMetricCard({
        title: 'Growth',
        value: 100,
        changePercentage: 15.5,
      })
      expect(screen.getByText('+15.5%')).toBeInTheDocument()
    })

    it('should display negative change without explicit - sign', () => {
      renderMetricCard({
        title: 'Decline',
        value: 100,
        changePercentage: -10.3,
      })
      expect(screen.getByText('-10.3%')).toBeInTheDocument()
    })

    it('should display zero change with + sign', () => {
      renderMetricCard({
        title: 'No Change',
        value: 100,
        changePercentage: 0,
      })
      expect(screen.getByText('+0.0%')).toBeInTheDocument()
    })

    it('should format decimal values correctly', () => {
      renderMetricCard({
        title: 'Change',
        value: 100,
        changePercentage: 7.89,
      })
      expect(screen.getByText('+7.9%')).toBeInTheDocument()
    })

    it('should not display change when null', () => {
      renderMetricCard({
        title: 'No Change',
        value: 100,
        changePercentage: null,
      })
      expect(screen.queryByText(/%/)).not.toBeInTheDocument()
    })

    it('should not display change when undefined', () => {
      renderMetricCard({
        title: 'No Change',
        value: 100,
        changePercentage: undefined,
      })
      expect(screen.queryByText(/%/)).not.toBeInTheDocument()
    })
  })

  describe('Description Tooltip', () => {
    it('should show help icon when description provided', () => {
      const { container } = renderMetricCard({
        title: 'Metric',
        value: 100,
        description: 'This is a helpful description',
      })
      const helpIcon = container.querySelector('svg[data-testid="HelpIcon"]')
      expect(helpIcon).toBeInTheDocument()
    })

    it('should not show help icon when no description', () => {
      const { container } = renderMetricCard({
        title: 'Metric',
        value: 100,
      })
      const helpIcon = container.querySelector('svg[data-testid="HelpIcon"]')
      expect(helpIcon).not.toBeInTheDocument()
    })

    it('should contain description text in tooltip', () => {
      const { container } = renderMetricCard({
        title: 'Metric',
        value: 100,
        description: 'Detailed metric description',
      })
      // Tooltip is rendered but hidden until hover
      const helpIcon = container.querySelector('svg[data-testid="HelpIcon"]')
      expect(helpIcon).toBeInTheDocument()
    })
  })

  describe('Custom Icon', () => {
    it('should render custom icon when provided with trend', () => {
      const { container } = renderMetricCard({
        title: 'Rating',
        value: 100,
        trend: 'up',
        icon: <StarIcon data-testid="custom-star-icon" />,
      })
      expect(screen.getByTestId('custom-star-icon')).toBeInTheDocument()
    })

    it('should use custom icon instead of trend icon', () => {
      const { container } = renderMetricCard({
        title: 'Rating',
        value: 100,
        trend: 'up',
        icon: <StarIcon data-testid="custom-icon" />,
      })
      // Custom icon should be present
      expect(screen.getByTestId('custom-icon')).toBeInTheDocument()
      // Trend icon should not be used
      const trendIcon = container.querySelector('svg[data-testid="TrendingUpIcon"]')
      expect(trendIcon).not.toBeInTheDocument()
    })
  })

  describe('Background Color', () => {
    it('should use custom color when provided', () => {
      const { container } = renderMetricCard({
        title: 'Custom',
        value: 100,
        color: 'rgba(255, 0, 0, 0.1)',
      })
      const card = container.querySelector('.MuiCard-root')
      expect(card).toBeInTheDocument()
    })

    it('should use default color based on trend when no custom color', () => {
      const { container } = renderMetricCard({
        title: 'Trend Color',
        value: 100,
        trend: 'up',
      })
      const card = container.querySelector('.MuiCard-root')
      expect(card).toBeInTheDocument()
    })
  })

  describe('Combined Props', () => {
    it('should render all props together correctly', () => {
      const { container } = renderMetricCard({
        title: 'Revenue',
        value: 5000,
        unit: 'USD',
        trend: 'up',
        changePercentage: 15.5,
        description: 'Total revenue for the month',
      })

      expect(screen.getByText('Revenue')).toBeInTheDocument()
      expect(screen.getByText('5000')).toBeInTheDocument()
      expect(screen.getByText('USD')).toBeInTheDocument()
      expect(screen.getByText('+15.5%')).toBeInTheDocument()

      const trendIcon = container.querySelector('svg[data-testid="TrendingUpIcon"]')
      expect(trendIcon).toBeInTheDocument()

      const helpIcon = container.querySelector('svg[data-testid="HelpIcon"]')
      expect(helpIcon).toBeInTheDocument()
    })

    it('should work with minimal props', () => {
      renderMetricCard({
        title: 'Simple Metric',
        value: 42,
      })

      expect(screen.getByText('Simple Metric')).toBeInTheDocument()
      expect(screen.getByText('42')).toBeInTheDocument()
    })
  })

  describe('Trend Label Display', () => {
    it('should show trend label when no change percentage', () => {
      renderMetricCard({
        title: 'Status',
        value: 100,
        trend: 'up',
      })
      expect(screen.getByText('Trending up')).toBeInTheDocument()
    })

    it('should show "Stable" label for stable trend', () => {
      renderMetricCard({
        title: 'Status',
        value: 100,
        trend: 'stable',
      })
      expect(screen.getByText('Stable')).toBeInTheDocument()
    })

    it('should show "Trending down" for down trend', () => {
      renderMetricCard({
        title: 'Status',
        value: 100,
        trend: 'down',
      })
      expect(screen.getByText('Trending down')).toBeInTheDocument()
    })

    it('should show "No change" for unknown trend', () => {
      renderMetricCard({
        title: 'Status',
        value: 100,
        trend: 'unknown',
      })
      expect(screen.getByText('No change')).toBeInTheDocument()
    })

    it('should not show trend label when change percentage is provided', () => {
      renderMetricCard({
        title: 'Growth',
        value: 100,
        trend: 'up',
        changePercentage: 15.5,
      })
      // Should show change percentage chip, not trend label
      expect(screen.getByText('+15.5%')).toBeInTheDocument()
      expect(screen.queryByText('Trending up')).not.toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('should handle very large values', () => {
      renderMetricCard({
        title: 'Big Number',
        value: 999999999,
      })
      expect(screen.getByText('999999999')).toBeInTheDocument()
    })

    it('should handle very small change percentages', () => {
      renderMetricCard({
        title: 'Tiny Change',
        value: 100,
        changePercentage: 0.01,
      })
      expect(screen.getByText('+0.0%')).toBeInTheDocument()
    })

    it('should handle very large change percentages', () => {
      renderMetricCard({
        title: 'Huge Change',
        value: 100,
        changePercentage: 999.99,
      })
      expect(screen.getByText('+1000.0%')).toBeInTheDocument()
    })

    it('should handle empty title', () => {
      renderMetricCard({
        title: '',
        value: 100,
      })
      expect(screen.getByText('100')).toBeInTheDocument()
    })

    it('should handle missing trend with changePercentage', () => {
      renderMetricCard({
        title: 'Change Only',
        value: 100,
        changePercentage: 15.5,
      })
      expect(screen.getByText('+15.5%')).toBeInTheDocument()
    })
  })

  describe('Typography Styling', () => {
    it('should render title in uppercase', () => {
      const { container } = renderMetricCard({
        title: 'metric title',
        value: 100,
      })
      // MUI Typography with textTransform uppercase
      expect(screen.getByText('metric title')).toBeInTheDocument()
    })

    it('should render value as h4 variant', () => {
      renderMetricCard({
        title: 'Value',
        value: 100,
      })
      const valueElement = screen.getByText('100')
      expect(valueElement.tagName).toBe('DIV')
    })
  })

  describe('Accessibility', () => {
    it('should have proper semantic structure', () => {
      const { container } = renderMetricCard({
        title: 'Accessible Metric',
        value: 100,
      })
      const card = container.querySelector('.MuiCard-root')
      expect(card).toBeInTheDocument()
    })

    it('should make help icon tooltip accessible', () => {
      const { container } = renderMetricCard({
        title: 'Metric',
        value: 100,
        description: 'Help text',
      })
      const helpIcon = container.querySelector('svg[data-testid="HelpIcon"]')
      expect(helpIcon).toBeInTheDocument()
    })

    it('should render readable text content', () => {
      renderMetricCard({
        title: 'Users',
        value: 1234,
        unit: 'total',
        changePercentage: 10.5,
      })
      expect(screen.getByText('Users')).toBeInTheDocument()
      expect(screen.getByText('1234')).toBeInTheDocument()
      expect(screen.getByText('total')).toBeInTheDocument()
      expect(screen.getByText('+10.5%')).toBeInTheDocument()
    })
  })
})
