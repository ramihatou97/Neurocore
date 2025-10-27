/**
 * ActivityChart Component
 * Displays time-series data as line or bar charts
 */

import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  useTheme
} from '@mui/material';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

function ActivityChart({
  data = [],
  title,
  dataKey,
  secondaryDataKey,
  color = '#1976d2',
  secondaryColor = '#dc004e',
  type = 'line', // line, bar, area
  height = 300,
  showLegend = true,
  showGrid = true,
  formatXAxis,
  formatYAxis,
  formatTooltip
}) {
  const theme = useTheme();

  /**
   * Format date for X-axis display
   */
  const defaultFormatXAxis = (value) => {
    if (!value) return '';

    try {
      const date = new Date(value);
      if (isNaN(date.getTime())) return value;

      // Format as MM/DD
      return `${date.getMonth() + 1}/${date.getDate()}`;
    } catch (e) {
      return value;
    }
  };

  /**
   * Format number for Y-axis display
   */
  const defaultFormatYAxis = (value) => {
    if (value >= 1000000) {
      return `${(value / 1000000).toFixed(1)}M`;
    } else if (value >= 1000) {
      return `${(value / 1000).toFixed(1)}K`;
    }
    return value.toString();
  };

  /**
   * Format tooltip content
   */
  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload || payload.length === 0) return null;

    return (
      <Card sx={{ p: 1.5, boxShadow: 3 }}>
        <Typography variant="body2" sx={{ mb: 1, fontWeight: 600 }}>
          {formatXAxis ? formatXAxis(label) : defaultFormatXAxis(label)}
        </Typography>
        {payload.map((entry, index) => (
          <Box key={index} display="flex" alignItems="center" gap={1}>
            <Box
              sx={{
                width: 12,
                height: 12,
                backgroundColor: entry.color,
                borderRadius: '50%'
              }}
            />
            <Typography variant="body2">
              {entry.name}: {formatTooltip ? formatTooltip(entry.value) : entry.value.toLocaleString()}
            </Typography>
          </Box>
        ))}
      </Card>
    );
  };

  /**
   * Prepare chart data
   */
  const prepareData = () => {
    if (!data || data.length === 0) return [];

    return data.map(item => ({
      ...item,
      // Ensure time_bucket is properly formatted
      time_bucket: item.time_bucket || item.date || item.period || item.timestamp
    }));
  };

  const chartData = prepareData();

  /**
   * Render empty state
   */
  if (!chartData || chartData.length === 0) {
    return (
      <Card>
        <CardContent>
          {title && (
            <Typography variant="h6" gutterBottom>
              {title}
            </Typography>
          )}
          <Box
            display="flex"
            alignItems="center"
            justifyContent="center"
            minHeight={height}
          >
            <Typography variant="body2" color="text.secondary">
              No data available
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  /**
   * Render chart based on type
   */
  const renderChart = () => {
    const commonProps = {
      data: chartData,
      margin: { top: 5, right: 30, left: 20, bottom: 5 }
    };

    const xAxisProps = {
      dataKey: 'time_bucket',
      tickFormatter: formatXAxis || defaultFormatXAxis,
      stroke: theme.palette.text.secondary,
      style: { fontSize: '0.75rem' }
    };

    const yAxisProps = {
      tickFormatter: formatYAxis || defaultFormatYAxis,
      stroke: theme.palette.text.secondary,
      style: { fontSize: '0.75rem' }
    };

    const gridProps = showGrid ? {
      strokeDasharray: '3 3',
      stroke: theme.palette.divider
    } : null;

    switch (type) {
      case 'bar':
        return (
          <BarChart {...commonProps}>
            {showGrid && <CartesianGrid {...gridProps} />}
            <XAxis {...xAxisProps} />
            <YAxis {...yAxisProps} />
            <Tooltip content={<CustomTooltip />} />
            {showLegend && <Legend />}
            <Bar
              dataKey={dataKey}
              fill={color}
              name={title || dataKey}
              radius={[4, 4, 0, 0]}
            />
            {secondaryDataKey && (
              <Bar
                dataKey={secondaryDataKey}
                fill={secondaryColor}
                name={secondaryDataKey}
                radius={[4, 4, 0, 0]}
              />
            )}
          </BarChart>
        );

      case 'area':
        return (
          <AreaChart {...commonProps}>
            {showGrid && <CartesianGrid {...gridProps} />}
            <XAxis {...xAxisProps} />
            <YAxis {...yAxisProps} />
            <Tooltip content={<CustomTooltip />} />
            {showLegend && <Legend />}
            <Area
              type="monotone"
              dataKey={dataKey}
              stroke={color}
              fill={color}
              fillOpacity={0.3}
              name={title || dataKey}
            />
            {secondaryDataKey && (
              <Area
                type="monotone"
                dataKey={secondaryDataKey}
                stroke={secondaryColor}
                fill={secondaryColor}
                fillOpacity={0.3}
                name={secondaryDataKey}
              />
            )}
          </AreaChart>
        );

      case 'line':
      default:
        return (
          <LineChart {...commonProps}>
            {showGrid && <CartesianGrid {...gridProps} />}
            <XAxis {...xAxisProps} />
            <YAxis {...yAxisProps} />
            <Tooltip content={<CustomTooltip />} />
            {showLegend && <Legend />}
            <Line
              type="monotone"
              dataKey={dataKey}
              stroke={color}
              strokeWidth={2}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
              name={title || dataKey}
            />
            {secondaryDataKey && (
              <Line
                type="monotone"
                dataKey={secondaryDataKey}
                stroke={secondaryColor}
                strokeWidth={2}
                dot={{ r: 4 }}
                activeDot={{ r: 6 }}
                name={secondaryDataKey}
              />
            )}
          </LineChart>
        );
    }
  };

  return (
    <Card>
      <CardContent>
        {title && (
          <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
            {title}
          </Typography>
        )}
        <ResponsiveContainer width="100%" height={height}>
          {renderChart()}
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export default ActivityChart;
