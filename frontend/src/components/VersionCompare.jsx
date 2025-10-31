/**
 * VersionCompare Component
 * Side-by-side comparison of two chapter versions with diff highlighting
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Alert,
  ToggleButtonGroup,
  ToggleButton,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableRow
} from '@mui/material';
import {
  CompareArrows as CompareIcon,
  Code as CodeIcon,
  ViewColumn as ColumnsIcon,
  List as ListIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon
} from '@mui/icons-material';
import axios from 'axios';
import { format } from 'date-fns';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002/api/v1';

function VersionCompare({ chapterId, version1, version2, onClose }) {
  const [compareData, setCompareData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState('side_by_side'); // 'side_by_side', 'unified', 'stats'

  useEffect(() => {
    if (chapterId && version1 && version2) {
      loadComparison();
    }
  }, [chapterId, version1, version2, viewMode]);

  const loadComparison = async () => {
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.post(
        `${API_BASE_URL}/chapters/${chapterId}/versions/compare`,
        {
          version1: version1,
          version2: version2,
          format: viewMode
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      setCompareData(response.data);
    } catch (err) {
      console.error('Failed to compare versions:', err);
      setError(err.response?.data?.detail || 'Failed to compare versions');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    try {
      return format(new Date(dateString), 'MMM dd, yyyy HH:mm');
    } catch {
      return dateString;
    }
  };

  const renderSideBySide = () => {
    if (!compareData?.diff?.comparisons) return null;

    return (
      <Box>
        <Grid container spacing={0}>
          {/* Left Side - Version 1 */}
          <Grid item xs={6}>
            <Paper sx={{ p: 2, bgcolor: '#fff9e6', borderRight: 1, borderColor: 'divider' }}>
              <Typography variant="subtitle1" gutterBottom>
                Version {compareData.version1.number}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {formatDate(compareData.version1.created_at)}
              </Typography>
            </Paper>
          </Grid>

          {/* Right Side - Version 2 */}
          <Grid item xs={6}>
            <Paper sx={{ p: 2, bgcolor: '#e6f7ff' }}>
              <Typography variant="subtitle1" gutterBottom>
                Version {compareData.version2.number}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {formatDate(compareData.version2.created_at)}
              </Typography>
            </Paper>
          </Grid>
        </Grid>

        {/* Diff Lines */}
        <TableContainer component={Paper} sx={{ mt: 2, maxHeight: '600px' }}>
          <Table size="small">
            <TableBody>
              {compareData.diff.comparisons.map((comp, index) => (
                <TableRow
                  key={index}
                  sx={{
                    bgcolor:
                      comp.type === 'delete' ? '#ffebee' :
                      comp.type === 'insert' ? '#e8f5e9' :
                      comp.type === 'replace' ? '#fff3e0' :
                      'transparent'
                  }}
                >
                  {/* Left Cell */}
                  <TableCell
                    sx={{
                      width: '50%',
                      fontFamily: 'monospace',
                      fontSize: '0.85rem',
                      verticalAlign: 'top',
                      borderRight: 1,
                      borderColor: 'divider',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word'
                    }}
                  >
                    {comp.left_content && (
                      <Box>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ mr: 1 }}
                        >
                          {comp.left_line}
                        </Typography>
                        <span
                          style={{
                            backgroundColor: comp.type === 'delete' || comp.type === 'replace'
                              ? '#ffcdd2'
                              : 'transparent',
                            textDecoration: comp.type === 'delete' ? 'line-through' : 'none'
                          }}
                        >
                          {comp.left_content}
                        </span>
                      </Box>
                    )}
                  </TableCell>

                  {/* Right Cell */}
                  <TableCell
                    sx={{
                      width: '50%',
                      fontFamily: 'monospace',
                      fontSize: '0.85rem',
                      verticalAlign: 'top',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word'
                    }}
                  >
                    {comp.right_content && (
                      <Box>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ mr: 1 }}
                        >
                          {comp.right_line}
                        </Typography>
                        <span
                          style={{
                            backgroundColor: comp.type === 'insert' || comp.type === 'replace'
                              ? '#c8e6c9'
                              : 'transparent'
                          }}
                        >
                          {comp.right_content}
                        </span>
                      </Box>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>
    );
  };

  const renderUnified = () => {
    if (!compareData?.diff?.diff) return null;

    return (
      <Paper sx={{ p: 2, mt: 2 }}>
        <Typography variant="h6" gutterBottom>
          Unified Diff
        </Typography>
        <Box
          sx={{
            fontFamily: 'monospace',
            fontSize: '0.85rem',
            whiteSpace: 'pre-wrap',
            bgcolor: '#f5f5f5',
            p: 2,
            borderRadius: 1,
            maxHeight: '600px',
            overflow: 'auto'
          }}
        >
          {compareData.diff.diff}
        </Box>
      </Paper>
    );
  };

  const renderStats = () => {
    if (!compareData?.summary) return null;

    const { lines, words, characters, similarity } = compareData.summary;

    return (
      <Box mt={2}>
        <Grid container spacing={2}>
          {/* Lines */}
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Lines
                </Typography>
                <Box display="flex" flexDirection="column" gap={1}>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2">Added:</Typography>
                    <Chip
                      label={lines.added}
                      size="small"
                      color="success"
                      icon={<TrendingUpIcon />}
                    />
                  </Box>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2">Deleted:</Typography>
                    <Chip
                      label={lines.deleted}
                      size="small"
                      color="error"
                      icon={<TrendingDownIcon />}
                    />
                  </Box>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2">Changed:</Typography>
                    <Chip label={lines.changed} size="small" color="warning" />
                  </Box>
                  <Divider />
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2">Before:</Typography>
                    <Typography variant="body2">{lines.total_before}</Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2">After:</Typography>
                    <Typography variant="body2">{lines.total_after}</Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Words */}
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Words
                </Typography>
                <Box display="flex" flexDirection="column" gap={1}>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2">Added:</Typography>
                    <Chip
                      label={words.added}
                      size="small"
                      color="success"
                      icon={<TrendingUpIcon />}
                    />
                  </Box>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2">Deleted:</Typography>
                    <Chip
                      label={words.deleted}
                      size="small"
                      color="error"
                      icon={<TrendingDownIcon />}
                    />
                  </Box>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2">Changed:</Typography>
                    <Chip label={words.changed} size="small" color="warning" />
                  </Box>
                  <Divider />
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2">Before:</Typography>
                    <Typography variant="body2">{words.total_before}</Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2">After:</Typography>
                    <Typography variant="body2">{words.total_after}</Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Similarity */}
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Similarity
                </Typography>
                <Box display="flex" flexDirection="column" gap={2}>
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      Overall Similarity
                    </Typography>
                    <Typography variant="h4" color="primary">
                      {(similarity.overall_similarity * 100).toFixed(1)}%
                    </Typography>
                  </Box>
                  <Divider />
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2">Line Similarity:</Typography>
                    <Typography variant="body2">
                      {(similarity.line_similarity * 100).toFixed(1)}%
                    </Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2">Word Similarity:</Typography>
                    <Typography variant="body2">
                      {(similarity.word_similarity * 100).toFixed(1)}%
                    </Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2">Character Change:</Typography>
                    <Chip
                      label={`${characters.net_change > 0 ? '+' : ''}${characters.net_change}`}
                      size="small"
                      color={characters.net_change > 0 ? 'success' : 'error'}
                    />
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>
    );
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" py={4}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!compareData) {
    return null;
  }

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5" display="flex" alignItems="center" gap={1}>
          <CompareIcon />
          Version Comparison
        </Typography>

        <ToggleButtonGroup
          value={viewMode}
          exclusive
          onChange={(e, newMode) => newMode && setViewMode(newMode)}
          size="small"
        >
          <ToggleButton value="side_by_side">
            <ColumnsIcon sx={{ mr: 1 }} fontSize="small" />
            Side by Side
          </ToggleButton>
          <ToggleButton value="unified">
            <CodeIcon sx={{ mr: 1 }} fontSize="small" />
            Unified
          </ToggleButton>
          <ToggleButton value="stats">
            <ListIcon sx={{ mr: 1 }} fontSize="small" />
            Statistics
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {/* View Modes */}
      {viewMode === 'side_by_side' && renderSideBySide()}
      {viewMode === 'unified' && renderUnified()}
      {viewMode === 'stats' && renderStats()}
    </Box>
  );
}

export default VersionCompare;
