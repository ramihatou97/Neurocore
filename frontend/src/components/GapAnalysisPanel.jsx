/**
 * Gap Analysis Panel Component
 * Phase 2 Week 5: Comprehensive gap analysis display
 *
 * Features:
 * - Run gap analysis on-demand
 * - Display completeness score with visual progress
 * - Show severity distribution (critical, high, medium, low)
 * - List identified gaps across 5 dimensions
 * - Display actionable recommendations
 * - Expandable/collapsible gap details
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Paper,
  LinearProgress,
  Chip,
  Alert,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider,
  List,
  ListItem,
  ListItemText,
  Grid,
  Card,
  CardContent,
  Tooltip,
  IconButton,
  Collapse
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  Refresh as RefreshIcon,
  Assessment as AssessmentIcon,
  TrendingUp as TrendingUpIcon,
  LibraryBooks as LibraryBooksIcon,
  Schedule as ScheduleIcon,
  Balance as BalanceIcon,
  HealthAndSafety as HealthAndSafetyIcon
} from '@mui/icons-material';
import { chaptersAPI } from '../api';

/**
 * Severity configuration with colors and icons
 */
const SEVERITY_CONFIG = {
  critical: {
    color: '#ef4444',
    bgColor: '#fee2e2',
    textColor: '#991b1b',
    icon: <ErrorIcon />,
    label: 'Critical'
  },
  high: {
    color: '#f97316',
    bgColor: '#ffedd5',
    textColor: '#9a3412',
    icon: <WarningIcon />,
    label: 'High'
  },
  medium: {
    color: '#eab308',
    bgColor: '#fef9c3',
    textColor: '#854d0e',
    icon: <InfoIcon />,
    label: 'Medium'
  },
  low: {
    color: '#22c55e',
    bgColor: '#dcfce7',
    textColor: '#166534',
    icon: <CheckCircleIcon />,
    label: 'Low'
  }
};

/**
 * Gap category configuration with icons and descriptions
 */
const CATEGORY_CONFIG = {
  content_completeness: {
    icon: <LibraryBooksIcon />,
    label: 'Content Completeness',
    description: 'Missing key concepts from research context'
  },
  source_coverage: {
    icon: <AssessmentIcon />,
    label: 'Source Coverage',
    description: 'Unused high-value research sources'
  },
  section_balance: {
    icon: <BalanceIcon />,
    label: 'Section Balance',
    description: 'Uneven depth across sections'
  },
  temporal_coverage: {
    icon: <ScheduleIcon />,
    label: 'Temporal Coverage',
    description: 'Missing recent research developments'
  },
  critical_information: {
    icon: <HealthAndSafetyIcon />,
    label: 'Critical Information',
    description: 'Missing essential clinical/surgical details'
  }
};

const GapAnalysisPanel = ({ chapterId, initialData = null }) => {
  // State management
  const [gapAnalysis, setGapAnalysis] = useState(initialData);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState(false);

  // Load existing gap analysis on mount if not provided
  useEffect(() => {
    if (!initialData && chapterId) {
      loadGapAnalysis();
    }
  }, [chapterId, initialData]);

  /**
   * Load existing gap analysis results
   */
  const loadGapAnalysis = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await chaptersAPI.getGapAnalysisSummary(chapterId);
      setGapAnalysis(data);
    } catch (err) {
      // 404 is expected if no analysis exists yet
      if (err.response?.status !== 404) {
        console.error('Failed to load gap analysis:', err);
        setError('Failed to load gap analysis');
      }
    } finally {
      setLoading(false);
    }
  };

  /**
   * Trigger gap analysis
   */
  const runGapAnalysis = async () => {
    setRunning(true);
    setError('');
    try {
      const result = await chaptersAPI.runGapAnalysis(chapterId);
      // Load the full summary after analysis completes
      const summary = await chaptersAPI.getGapAnalysisSummary(chapterId);
      setGapAnalysis(summary);
      setExpanded(true); // Auto-expand results
    } catch (err) {
      console.error('Failed to run gap analysis:', err);
      const errorMsg = err.response?.data?.detail || 'Failed to run gap analysis';
      setError(errorMsg);
    } finally {
      setRunning(false);
    }
  };

  /**
   * Get severity badge component
   */
  const getSeverityBadge = (severity, count = null) => {
    const config = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.low;
    return (
      <Chip
        icon={config.icon}
        label={count !== null ? `${config.label}: ${count}` : config.label}
        size="small"
        sx={{
          backgroundColor: config.bgColor,
          color: config.textColor,
          fontWeight: 600,
          '& .MuiChip-icon': {
            color: config.textColor
          }
        }}
      />
    );
  };

  /**
   * Get completeness score color
   */
  const getScoreColor = (score) => {
    if (score >= 0.9) return '#22c55e'; // green
    if (score >= 0.75) return '#eab308'; // yellow
    if (score >= 0.6) return '#f97316'; // orange
    return '#ef4444'; // red
  };

  /**
   * Get category icon
   */
  const getCategoryIcon = (category) => {
    return CATEGORY_CONFIG[category]?.icon || <InfoIcon />;
  };

  /**
   * Get category label
   */
  const getCategoryLabel = (category) => {
    return CATEGORY_CONFIG[category]?.label || category;
  };

  // Loading state
  if (loading) {
    return (
      <Paper className="p-6">
        <Box display="flex" alignItems="center" justifyContent="center" gap={2}>
          <CircularProgress size={24} />
          <Typography>Loading gap analysis...</Typography>
        </Box>
      </Paper>
    );
  }

  // No analysis state
  if (!gapAnalysis && !error) {
    return (
      <Paper className="p-6 bg-blue-50 border border-blue-200">
        <Box display="flex" flexDirection="column" gap={2}>
          <Box display="flex" alignItems="center" gap={2}>
            <AssessmentIcon className="text-blue-600" fontSize="large" />
            <div>
              <Typography variant="h6" className="text-blue-900 font-semibold">
                Gap Analysis Available
              </Typography>
              <Typography variant="body2" className="text-blue-700">
                Analyze this chapter to identify content gaps, missing sources, and improvement opportunities.
              </Typography>
            </div>
          </Box>
          <Box>
            <Button
              variant="contained"
              color="primary"
              onClick={runGapAnalysis}
              disabled={running}
              startIcon={running ? <CircularProgress size={20} /> : <AssessmentIcon />}
            >
              {running ? 'Running Analysis...' : 'Run Gap Analysis'}
            </Button>
          </Box>
          {running && (
            <Alert severity="info">
              <Typography variant="body2">
                Analyzing chapter across 5 dimensions... This may take 5-10 seconds.
              </Typography>
            </Alert>
          )}
        </Box>
      </Paper>
    );
  }

  // Error state
  if (error) {
    return (
      <Paper className="p-6">
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" onClick={loadGapAnalysis}>
              Retry
            </Button>
          }
        >
          {error}
        </Alert>
      </Paper>
    );
  }

  // Results display
  const completenessScore = gapAnalysis?.completeness_score || 0;
  const totalGaps = gapAnalysis?.total_gaps || 0;
  const severityDist = gapAnalysis?.severity_distribution || {};
  const requiresRevision = gapAnalysis?.requires_revision || false;
  const recommendations = gapAnalysis?.top_recommendations || [];
  const categorySummary = gapAnalysis?.gap_categories_summary || {};
  const analyzedAt = gapAnalysis?.analyzed_at;

  return (
    <Paper className="overflow-hidden">
      {/* Header */}
      <Box className="bg-gradient-to-r from-blue-500 to-blue-600 p-4 text-white">
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box display="flex" alignItems="center" gap={2}>
            <AssessmentIcon fontSize="large" />
            <div>
              <Typography variant="h6" fontWeight="bold">
                Gap Analysis
              </Typography>
              <Typography variant="caption" className="opacity-90">
                {analyzedAt ? `Last analyzed: ${new Date(analyzedAt).toLocaleString()}` : 'No analysis yet'}
              </Typography>
            </div>
          </Box>
          <Tooltip title="Refresh gap analysis">
            <IconButton
              onClick={runGapAnalysis}
              disabled={running}
              sx={{ color: 'white' }}
            >
              {running ? <CircularProgress size={24} color="inherit" /> : <RefreshIcon />}
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Revision Warning */}
      {requiresRevision && (
        <Alert severity="error" className="m-4">
          <Typography variant="body2" fontWeight="600">
            ⚠️ This chapter requires revision
          </Typography>
          <Typography variant="body2">
            Critical gaps or low completeness score detected. Please address the issues below.
          </Typography>
        </Alert>
      )}

      {/* Main Content */}
      <Box className="p-4">
        {/* Completeness Score */}
        <Card className="mb-4" sx={{ backgroundColor: '#f8fafc' }}>
          <CardContent>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="subtitle1" fontWeight="600">
                Overall Completeness Score
              </Typography>
              <Typography
                variant="h4"
                fontWeight="bold"
                sx={{ color: getScoreColor(completenessScore) }}
              >
                {(completenessScore * 100).toFixed(0)}%
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={completenessScore * 100}
              sx={{
                height: 10,
                borderRadius: 5,
                backgroundColor: '#e2e8f0',
                '& .MuiLinearProgress-bar': {
                  backgroundColor: getScoreColor(completenessScore),
                  borderRadius: 5
                }
              }}
            />
            <Typography variant="caption" className="text-gray-600 mt-2 block">
              {completenessScore >= 0.75
                ? '✓ Meets minimum quality threshold (0.75)'
                : '✗ Below minimum quality threshold (0.75)'}
            </Typography>
          </CardContent>
        </Card>

        {/* Severity Distribution */}
        <Box className="mb-4">
          <Typography variant="subtitle1" fontWeight="600" className="mb-3">
            Gap Severity Distribution
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={6} sm={3}>
              <Card className="text-center p-3" sx={{ backgroundColor: SEVERITY_CONFIG.critical.bgColor }}>
                <Typography variant="h4" fontWeight="bold" sx={{ color: SEVERITY_CONFIG.critical.textColor }}>
                  {severityDist.critical || 0}
                </Typography>
                <Typography variant="caption" sx={{ color: SEVERITY_CONFIG.critical.textColor }}>
                  Critical
                </Typography>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card className="text-center p-3" sx={{ backgroundColor: SEVERITY_CONFIG.high.bgColor }}>
                <Typography variant="h4" fontWeight="bold" sx={{ color: SEVERITY_CONFIG.high.textColor }}>
                  {severityDist.high || 0}
                </Typography>
                <Typography variant="caption" sx={{ color: SEVERITY_CONFIG.high.textColor }}>
                  High
                </Typography>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card className="text-center p-3" sx={{ backgroundColor: SEVERITY_CONFIG.medium.bgColor }}>
                <Typography variant="h4" fontWeight="bold" sx={{ color: SEVERITY_CONFIG.medium.textColor }}>
                  {severityDist.medium || 0}
                </Typography>
                <Typography variant="caption" sx={{ color: SEVERITY_CONFIG.medium.textColor }}>
                  Medium
                </Typography>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card className="text-center p-3" sx={{ backgroundColor: SEVERITY_CONFIG.low.bgColor }}>
                <Typography variant="h4" fontWeight="bold" sx={{ color: SEVERITY_CONFIG.low.textColor }}>
                  {severityDist.low || 0}
                </Typography>
                <Typography variant="caption" sx={{ color: SEVERITY_CONFIG.low.textColor }}>
                  Low
                </Typography>
              </Card>
            </Grid>
          </Grid>
        </Box>

        {/* Gap Categories Summary */}
        {Object.keys(categorySummary).length > 0 && (
          <Box className="mb-4">
            <Typography variant="subtitle1" fontWeight="600" className="mb-3">
              Gaps by Category
            </Typography>
            <Grid container spacing={2}>
              {Object.entries(categorySummary).map(([category, count]) => (
                <Grid item xs={12} sm={6} md={4} key={category}>
                  <Tooltip title={CATEGORY_CONFIG[category]?.description || ''}>
                    <Card className="hover:shadow-md transition-shadow cursor-help">
                      <CardContent>
                        <Box display="flex" alignItems="center" gap={2}>
                          <Box sx={{ color: '#3b82f6' }}>
                            {getCategoryIcon(category)}
                          </Box>
                          <div className="flex-1">
                            <Typography variant="body2" className="text-gray-600">
                              {getCategoryLabel(category)}
                            </Typography>
                            <Typography variant="h6" fontWeight="bold">
                              {count} {count === 1 ? 'gap' : 'gaps'}
                            </Typography>
                          </div>
                        </Box>
                      </CardContent>
                    </Card>
                  </Tooltip>
                </Grid>
              ))}
            </Grid>
          </Box>
        )}

        {/* Recommendations */}
        {recommendations.length > 0 && (
          <Box className="mb-4">
            <Typography variant="subtitle1" fontWeight="600" className="mb-3">
              💡 Top Recommendations
            </Typography>
            <List>
              {recommendations.map((rec, index) => (
                <React.Fragment key={index}>
                  <ListItem
                    alignItems="flex-start"
                    className="bg-yellow-50 rounded-lg mb-2"
                  >
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={1}>
                          <Chip
                            label={`Priority ${rec.priority || index + 1}`}
                            size="small"
                            color="warning"
                          />
                          <Typography variant="body1" fontWeight="600">
                            {rec.action?.replace(/_/g, ' ').toUpperCase() || 'Recommendation'}
                          </Typography>
                        </Box>
                      }
                      secondary={
                        <Box mt={1}>
                          <Typography variant="body2" className="text-gray-700">
                            {rec.description}
                          </Typography>
                          {rec.estimated_effort && (
                            <Chip
                              label={`Effort: ${rec.estimated_effort}`}
                              size="small"
                              variant="outlined"
                              className="mt-2"
                            />
                          )}
                        </Box>
                      }
                    />
                  </ListItem>
                </React.Fragment>
              ))}
            </List>
          </Box>
        )}

        {/* Summary Stats */}
        <Divider className="my-4" />
        <Box display="flex" justifyContent="space-between" alignItems="center" className="text-sm text-gray-600">
          <Typography variant="body2">
            Total Gaps Identified: <strong>{totalGaps}</strong>
          </Typography>
          <Button
            size="small"
            variant="outlined"
            onClick={runGapAnalysis}
            disabled={running}
            startIcon={<RefreshIcon />}
          >
            Re-analyze
          </Button>
        </Box>
      </Box>
    </Paper>
  );
};

export default GapAnalysisPanel;
