/**
 * MetricCard Component
 * Displays a single metric with value, trend, and change indicator
 */

import React from 'react';
import {
  Card,
  CardContent,
  Box,
  Typography,
  Chip,
  Tooltip
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  TrendingFlat as TrendingFlatIcon,
  Help as HelpIcon
} from '@mui/icons-material';

function MetricCard({
  title,
  value,
  unit,
  trend,
  changePercentage,
  icon,
  description,
  color
}) {
  /**
   * Get trend icon and color based on trend value
   */
  const getTrendDisplay = () => {
    if (!trend || trend === 'unknown') {
      return {
        icon: <TrendingFlatIcon />,
        color: 'default',
        label: 'No change'
      };
    }

    switch (trend) {
      case 'up':
        return {
          icon: <TrendingUpIcon />,
          color: 'success',
          label: 'Trending up'
        };
      case 'down':
        return {
          icon: <TrendingDownIcon />,
          color: 'error',
          label: 'Trending down'
        };
      case 'stable':
        return {
          icon: <TrendingFlatIcon />,
          color: 'info',
          label: 'Stable'
        };
      default:
        return {
          icon: <TrendingFlatIcon />,
          color: 'default',
          label: 'Unknown'
        };
    }
  };

  /**
   * Format change percentage for display
   */
  const formatChange = () => {
    if (changePercentage === null || changePercentage === undefined) {
      return null;
    }

    const sign = changePercentage >= 0 ? '+' : '';
    return `${sign}${changePercentage.toFixed(1)}%`;
  };

  const trendDisplay = getTrendDisplay();
  const changeText = formatChange();

  /**
   * Get background color based on trend
   */
  const getBackgroundColor = () => {
    if (color) return color;

    switch (trend) {
      case 'up':
        return 'rgba(46, 125, 50, 0.05)'; // Light green
      case 'down':
        return 'rgba(211, 47, 47, 0.05)'; // Light red
      default:
        return 'rgba(25, 118, 210, 0.05)'; // Light blue
    }
  };

  /**
   * Get border color based on trend
   */
  const getBorderColor = () => {
    switch (trend) {
      case 'up':
        return '#2e7d32'; // Green
      case 'down':
        return '#d32f2f'; // Red
      case 'stable':
        return '#0288d1'; // Blue
      default:
        return '#e0e0e0'; // Gray
    }
  };

  return (
    <Card
      sx={{
        height: '100%',
        backgroundColor: getBackgroundColor(),
        borderLeft: `4px solid ${getBorderColor()}`,
        transition: 'transform 0.2s, box-shadow 0.2s',
        '&:hover': {
          transform: 'translateY(-4px)',
          boxShadow: 3
        }
      }}
    >
      <CardContent>
        {/* Title Row */}
        <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
          <Typography
            variant="subtitle2"
            color="text.secondary"
            sx={{
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              fontSize: '0.75rem'
            }}
          >
            {title}
          </Typography>
          {description && (
            <Tooltip title={description} arrow>
              <HelpIcon fontSize="small" sx={{ color: 'text.secondary', opacity: 0.6 }} />
            </Tooltip>
          )}
        </Box>

        {/* Value Row */}
        <Box display="flex" alignItems="baseline" gap={1} mb={1}>
          <Typography
            variant="h4"
            component="div"
            sx={{
              fontWeight: 700,
              color: 'text.primary'
            }}
          >
            {value}
          </Typography>
          {unit && (
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ fontWeight: 500 }}
            >
              {unit}
            </Typography>
          )}
        </Box>

        {/* Trend and Change Row */}
        {(trend || changeText) && (
          <Box display="flex" alignItems="center" gap={1} mt={2}>
            {/* Custom icon or trend icon */}
            {icon ? (
              <Box display="flex" alignItems="center">
                {icon}
              </Box>
            ) : (
              <Box display="flex" alignItems="center" color={`${trendDisplay.color}.main`}>
                {trendDisplay.icon}
              </Box>
            )}

            {/* Change percentage chip */}
            {changeText && (
              <Chip
                label={changeText}
                size="small"
                color={trendDisplay.color}
                sx={{
                  fontWeight: 600,
                  fontSize: '0.75rem'
                }}
              />
            )}

            {/* Trend label */}
            {!changeText && (
              <Typography
                variant="caption"
                color={`${trendDisplay.color}.main`}
                sx={{ fontWeight: 600 }}
              >
                {trendDisplay.label}
              </Typography>
            )}
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

export default MetricCard;
