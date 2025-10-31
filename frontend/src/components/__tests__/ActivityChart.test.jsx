/**
 * ActivityChart Component Tests
 * Comprehensive test suite for ActivityChart component
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import ActivityChart from '../ActivityChart'

// Create MUI theme for tests
const theme = createTheme()

// Mock Recharts components to avoid rendering complexity in tests
vi.mock('recharts', () => ({
  LineChart: ({ children, data }) => (
    <div data-testid="line-chart" data-chart-data={JSON.stringify(data)}>
      {children}
    </div>
  ),
  BarChart: ({ children, data }) => (
    <div data-testid="bar-chart" data-chart-data={JSON.stringify(data)}>
      {children}
    </div>
  ),
  AreaChart: ({ children, data }) => (
    <div data-testid="area-chart" data-chart-data={JSON.stringify(data)}>
      {children}
    </div>
  ),
  Line: ({ dataKey, stroke, name }) => (
    <div data-testid="line" data-key={dataKey} data-stroke={stroke} data-name={name} />
  ),
  Bar: ({ dataKey, fill, name }) => (
    <div data-testid="bar" data-key={dataKey} data-fill={fill} data-name={name} />
  ),
  Area: ({ dataKey, stroke, name }) => (
    <div data-testid="area" data-key={dataKey} data-stroke={stroke} data-name={name} />
  ),
  XAxis: ({ dataKey, tickFormatter }) => (
    <div data-testid="x-axis" data-key={dataKey} />
  ),
  YAxis: ({ tickFormatter }) => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: ({ content }) => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
  ResponsiveContainer: ({ children, width, height }) => (
    <div data-testid="responsive-container" style={{ width, height }}>
      {children}
    </div>
  ),
}))

describe('ActivityChart Component', () => {
  const renderActivityChart = (props) => {
    return render(
      <ThemeProvider theme={theme}>
        <ActivityChart {...props} />
      </ThemeProvider>
    )
  }

  const sampleData = [
    { time_bucket: '2024-01-01', count: 10, views: 100 },
    { time_bucket: '2024-01-02', count: 20, views: 200 },
    { time_bucket: '2024-01-03', count: 15, views: 150 },
  ]

  describe('Rendering', () => {
    it('should render chart with title', () => {
      renderActivityChart({
        data: sampleData,
        title: 'Activity Overview',
        dataKey: 'count',
      })
      expect(screen.getByText('Activity Overview')).toBeInTheDocument()
    })

    it('should render chart without title', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
      })
      expect(screen.queryByRole('heading')).not.toBeInTheDocument()
    })

    it('should render with default type (line)', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
      })
      expect(screen.getByTestId('line-chart')).toBeInTheDocument()
    })

    it('should render responsive container', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
      })
      expect(screen.getByTestId('responsive-container')).toBeInTheDocument()
    })

    it('should render MUI Card', () => {
      const { container } = renderActivityChart({
        data: sampleData,
        dataKey: 'count',
      })
      expect(container.querySelector('.MuiCard-root')).toBeInTheDocument()
    })
  })

  describe('Empty State', () => {
    it('should show empty state when data is empty array', () => {
      renderActivityChart({
        data: [],
        title: 'Empty Chart',
        dataKey: 'count',
      })
      expect(screen.getByText('No data available')).toBeInTheDocument()
    })

    it('should show empty state when data is null', () => {
      renderActivityChart({
        data: null,
        title: 'Null Data',
        dataKey: 'count',
      })
      expect(screen.getByText('No data available')).toBeInTheDocument()
    })

    it('should show empty state when data is undefined', () => {
      renderActivityChart({
        dataKey: 'count',
      })
      expect(screen.getByText('No data available')).toBeInTheDocument()
    })

    it('should show title in empty state', () => {
      renderActivityChart({
        data: [],
        title: 'My Chart',
        dataKey: 'count',
      })
      expect(screen.getByText('My Chart')).toBeInTheDocument()
      expect(screen.getByText('No data available')).toBeInTheDocument()
    })

    it('should not render chart elements in empty state', () => {
      renderActivityChart({
        data: [],
        dataKey: 'count',
      })
      expect(screen.queryByTestId('line-chart')).not.toBeInTheDocument()
      expect(screen.queryByTestId('responsive-container')).not.toBeInTheDocument()
    })
  })

  describe('Chart Types', () => {
    it('should render line chart when type is "line"', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
        type: 'line',
      })
      expect(screen.getByTestId('line-chart')).toBeInTheDocument()
      expect(screen.getByTestId('line')).toBeInTheDocument()
    })

    it('should render bar chart when type is "bar"', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
        type: 'bar',
      })
      expect(screen.getByTestId('bar-chart')).toBeInTheDocument()
      expect(screen.getByTestId('bar')).toBeInTheDocument()
    })

    it('should render area chart when type is "area"', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
        type: 'area',
      })
      expect(screen.getByTestId('area-chart')).toBeInTheDocument()
      expect(screen.getByTestId('area')).toBeInTheDocument()
    })

    it('should default to line chart for invalid type', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
        type: 'invalid',
      })
      expect(screen.getByTestId('line-chart')).toBeInTheDocument()
    })
  })

  describe('Data Configuration', () => {
    it('should use provided dataKey', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
      })
      const line = screen.getByTestId('line')
      expect(line).toHaveAttribute('data-key', 'count')
    })

    it('should render secondary data when provided', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
        secondaryDataKey: 'views',
        type: 'line',
      })
      const lines = screen.getAllByTestId('line')
      expect(lines).toHaveLength(2)
      expect(lines[0]).toHaveAttribute('data-key', 'count')
      expect(lines[1]).toHaveAttribute('data-key', 'views')
    })

    it('should not render secondary data when not provided', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
        type: 'line',
      })
      const lines = screen.getAllByTestId('line')
      expect(lines).toHaveLength(1)
    })
  })

  describe('Color Configuration', () => {
    it('should use default primary color', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
        type: 'line',
      })
      const line = screen.getByTestId('line')
      expect(line).toHaveAttribute('data-stroke', '#1976d2')
    })

    it('should use custom primary color', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
        color: '#ff0000',
        type: 'line',
      })
      const line = screen.getByTestId('line')
      expect(line).toHaveAttribute('data-stroke', '#ff0000')
    })

    it('should use default secondary color', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
        secondaryDataKey: 'views',
        type: 'line',
      })
      const lines = screen.getAllByTestId('line')
      expect(lines[1]).toHaveAttribute('data-stroke', '#dc004e')
    })

    it('should use custom secondary color', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
        secondaryDataKey: 'views',
        secondaryColor: '#00ff00',
        type: 'line',
      })
      const lines = screen.getAllByTestId('line')
      expect(lines[1]).toHaveAttribute('data-stroke', '#00ff00')
    })

    it('should apply fill color for bar charts', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
        color: '#1976d2',
        type: 'bar',
      })
      const bar = screen.getByTestId('bar')
      expect(bar).toHaveAttribute('data-fill', '#1976d2')
    })
  })

  describe('Chart Elements', () => {
    it('should render X-axis', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
      })
      expect(screen.getByTestId('x-axis')).toBeInTheDocument()
    })

    it('should render Y-axis', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
      })
      expect(screen.getByTestId('y-axis')).toBeInTheDocument()
    })

    it('should render tooltip', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
      })
      expect(screen.getByTestId('tooltip')).toBeInTheDocument()
    })

    it('should render legend by default', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
      })
      expect(screen.getByTestId('legend')).toBeInTheDocument()
    })

    it('should hide legend when showLegend is false', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
        showLegend: false,
      })
      expect(screen.queryByTestId('legend')).not.toBeInTheDocument()
    })

    it('should render grid by default', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
      })
      expect(screen.getByTestId('cartesian-grid')).toBeInTheDocument()
    })

    it('should hide grid when showGrid is false', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
        showGrid: false,
      })
      expect(screen.queryByTestId('cartesian-grid')).not.toBeInTheDocument()
    })
  })

  describe('Height Configuration', () => {
    it('should use default height of 300', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
      })
      const container = screen.getByTestId('responsive-container')
      expect(container).toHaveStyle({ height: '300px' })
    })

    it('should use custom height', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
        height: 500,
      })
      const container = screen.getByTestId('responsive-container')
      expect(container).toHaveStyle({ height: '500px' })
    })

    it('should apply height to empty state', () => {
      renderActivityChart({
        data: [],
        dataKey: 'count',
        height: 400,
      })
      // Empty state shows "No data available" message
      expect(screen.getByText('No data available')).toBeInTheDocument()
    })
  })

  describe('Data Preparation', () => {
    it('should handle data with time_bucket field', () => {
      const data = [{ time_bucket: '2024-01-01', count: 10 }]
      const { container } = renderActivityChart({
        data,
        dataKey: 'count',
      })
      const chart = screen.getByTestId('line-chart')
      const chartData = JSON.parse(chart.getAttribute('data-chart-data'))
      expect(chartData[0].time_bucket).toBe('2024-01-01')
    })

    it('should handle data with date field', () => {
      const data = [{ date: '2024-01-01', count: 10 }]
      const { container } = renderActivityChart({
        data,
        dataKey: 'count',
      })
      const chart = screen.getByTestId('line-chart')
      const chartData = JSON.parse(chart.getAttribute('data-chart-data'))
      expect(chartData[0].time_bucket).toBe('2024-01-01')
    })

    it('should handle data with period field', () => {
      const data = [{ period: '2024-01-01', count: 10 }]
      const { container } = renderActivityChart({
        data,
        dataKey: 'count',
      })
      const chart = screen.getByTestId('line-chart')
      const chartData = JSON.parse(chart.getAttribute('data-chart-data'))
      expect(chartData[0].time_bucket).toBe('2024-01-01')
    })

    it('should handle data with timestamp field', () => {
      const data = [{ timestamp: '2024-01-01', count: 10 }]
      const { container } = renderActivityChart({
        data,
        dataKey: 'count',
      })
      const chart = screen.getByTestId('line-chart')
      const chartData = JSON.parse(chart.getAttribute('data-chart-data'))
      expect(chartData[0].time_bucket).toBe('2024-01-01')
    })

    it('should preserve other data fields', () => {
      const data = [{ time_bucket: '2024-01-01', count: 10, views: 100 }]
      const { container } = renderActivityChart({
        data,
        dataKey: 'count',
      })
      const chart = screen.getByTestId('line-chart')
      const chartData = JSON.parse(chart.getAttribute('data-chart-data'))
      expect(chartData[0].count).toBe(10)
      expect(chartData[0].views).toBe(100)
    })
  })

  describe('Chart Names', () => {
    it('should use title as chart name when provided', () => {
      renderActivityChart({
        data: sampleData,
        title: 'Activity Count',
        dataKey: 'count',
      })
      const line = screen.getByTestId('line')
      expect(line).toHaveAttribute('data-name', 'Activity Count')
    })

    it('should use dataKey as name when title not provided', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
      })
      const line = screen.getByTestId('line')
      expect(line).toHaveAttribute('data-name', 'count')
    })

    it('should use secondaryDataKey as name for secondary series', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
        secondaryDataKey: 'views',
      })
      const lines = screen.getAllByTestId('line')
      expect(lines[1]).toHaveAttribute('data-name', 'views')
    })
  })

  describe('All Chart Types with Secondary Data', () => {
    it('should render bar chart with two bars', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
        secondaryDataKey: 'views',
        type: 'bar',
      })
      const bars = screen.getAllByTestId('bar')
      expect(bars).toHaveLength(2)
    })

    it('should render area chart with two areas', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
        secondaryDataKey: 'views',
        type: 'area',
      })
      const areas = screen.getAllByTestId('area')
      expect(areas).toHaveLength(2)
    })

    it('should render line chart with two lines', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
        secondaryDataKey: 'views',
        type: 'line',
      })
      const lines = screen.getAllByTestId('line')
      expect(lines).toHaveLength(2)
    })
  })

  describe('Combined Props', () => {
    it('should render complete chart with all features', () => {
      renderActivityChart({
        data: sampleData,
        title: 'Complete Chart',
        dataKey: 'count',
        secondaryDataKey: 'views',
        color: '#ff0000',
        secondaryColor: '#00ff00',
        type: 'line',
        height: 400,
        showLegend: true,
        showGrid: true,
      })

      expect(screen.getByText('Complete Chart')).toBeInTheDocument()
      expect(screen.getByTestId('line-chart')).toBeInTheDocument()
      expect(screen.getByTestId('legend')).toBeInTheDocument()
      expect(screen.getByTestId('cartesian-grid')).toBeInTheDocument()

      const lines = screen.getAllByTestId('line')
      expect(lines).toHaveLength(2)
      expect(lines[0]).toHaveAttribute('data-stroke', '#ff0000')
      expect(lines[1]).toHaveAttribute('data-stroke', '#00ff00')
    })

    it('should render minimal chart', () => {
      renderActivityChart({
        data: sampleData,
        dataKey: 'count',
      })

      expect(screen.queryByRole('heading')).not.toBeInTheDocument()
      expect(screen.getByTestId('line-chart')).toBeInTheDocument()
      expect(screen.getByTestId('line')).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('should handle single data point', () => {
      renderActivityChart({
        data: [{ time_bucket: '2024-01-01', count: 10 }],
        dataKey: 'count',
      })
      expect(screen.getByTestId('line-chart')).toBeInTheDocument()
    })

    it('should handle data with missing time fields', () => {
      renderActivityChart({
        data: [{ count: 10 }],
        dataKey: 'count',
      })
      const chart = screen.getByTestId('line-chart')
      const chartData = JSON.parse(chart.getAttribute('data-chart-data'))
      expect(chartData[0].time_bucket).toBeUndefined()
    })

    it('should handle zero values', () => {
      renderActivityChart({
        data: [
          { time_bucket: '2024-01-01', count: 0 },
          { time_bucket: '2024-01-02', count: 0 },
        ],
        dataKey: 'count',
      })
      expect(screen.getByTestId('line-chart')).toBeInTheDocument()
    })

    it('should handle negative values', () => {
      renderActivityChart({
        data: [
          { time_bucket: '2024-01-01', count: -10 },
          { time_bucket: '2024-01-02', count: -20 },
        ],
        dataKey: 'count',
      })
      expect(screen.getByTestId('line-chart')).toBeInTheDocument()
    })

    it('should handle very large dataset', () => {
      const largeData = Array.from({ length: 1000 }, (_, i) => ({
        time_bucket: `2024-01-${i + 1}`,
        count: i * 10,
      }))
      renderActivityChart({
        data: largeData,
        dataKey: 'count',
      })
      expect(screen.getByTestId('line-chart')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('should render with semantic structure', () => {
      const { container } = renderActivityChart({
        data: sampleData,
        title: 'Accessible Chart',
        dataKey: 'count',
      })
      expect(container.querySelector('.MuiCard-root')).toBeInTheDocument()
    })

    it('should have readable title', () => {
      renderActivityChart({
        data: sampleData,
        title: 'Monthly Activity',
        dataKey: 'count',
      })
      expect(screen.getByText('Monthly Activity')).toBeInTheDocument()
    })

    it('should provide empty state message', () => {
      renderActivityChart({
        data: [],
        title: 'Empty Chart',
        dataKey: 'count',
      })
      const emptyMessage = screen.getByText('No data available')
      expect(emptyMessage).toBeInTheDocument()
    })
  })
})
