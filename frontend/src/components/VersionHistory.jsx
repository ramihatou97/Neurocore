/**
 * VersionHistory Component
 * Timeline view of chapter versions with compare and rollback actions
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Timeline,
  TimelineItem,
  TimelineSeparator,
  TimelineConnector,
  TimelineContent,
  TimelineDot,
  TimelineOppositeContent,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  IconButton,
  Tooltip,
  Paper,
  Divider
} from '@mui/material';
import {
  History as HistoryIcon,
  CompareArrows as CompareIcon,
  RestoreRounded as RestoreIcon,
  Visibility as ViewIcon,
  Person as PersonIcon,
  Schedule as ScheduleIcon,
  Edit as EditIcon,
  Check as CheckIcon,
  Close as CloseIcon
} from '@mui/icons-material';
import axios from 'axios';
import { format } from 'date-fns';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api/v1';

function VersionHistory({ chapterId, onCompare, onViewVersion }) {
  const [versions, setVersions] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedVersions, setSelectedVersions] = useState([]);

  // Rollback dialog state
  const [rollbackDialogOpen, setRollbackDialogOpen] = useState(false);
  const [rollbackVersion, setRollbackVersion] = useState(null);
  const [rollbackReason, setRollbackReason] = useState('');
  const [rollbackLoading, setRollbackLoading] = useState(false);

  useEffect(() => {
    if (chapterId) {
      loadVersionHistory();
      loadVersionStats();
    }
  }, [chapterId]);

  const loadVersionHistory = async () => {
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get(
        `${API_BASE_URL}/chapters/${chapterId}/versions`,
        {
          headers: { Authorization: `Bearer ${token}` },
          params: { limit: 50 }
        }
      );

      setVersions(response.data.versions || []);
    } catch (err) {
      console.error('Failed to load version history:', err);
      setError(err.response?.data?.detail || 'Failed to load version history');
    } finally {
      setLoading(false);
    }
  };

  const loadVersionStats = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get(
        `${API_BASE_URL}/chapters/${chapterId}/versions/stats`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      setStats(response.data.statistics);
    } catch (err) {
      console.error('Failed to load version stats:', err);
    }
  };

  const handleSelectVersion = (version) => {
    setSelectedVersions((prev) => {
      if (prev.find(v => v.version_number === version.version_number)) {
        return prev.filter(v => v.version_number !== version.version_number);
      }

      if (prev.length >= 2) {
        return [prev[1], version];
      }

      return [...prev, version];
    });
  };

  const handleCompare = () => {
    if (selectedVersions.length === 2 && onCompare) {
      onCompare(selectedVersions[0].version_number, selectedVersions[1].version_number);
    }
  };

  const handleOpenRollbackDialog = (version) => {
    setRollbackVersion(version);
    setRollbackReason('');
    setRollbackDialogOpen(true);
  };

  const handleCloseRollbackDialog = () => {
    setRollbackDialogOpen(false);
    setRollbackVersion(null);
    setRollbackReason('');
  };

  const handleRollback = async () => {
    if (!rollbackVersion) return;

    setRollbackLoading(true);

    try {
      const token = localStorage.getItem('access_token');
      await axios.post(
        `${API_BASE_URL}/chapters/${chapterId}/versions/rollback`,
        {
          version_number: rollbackVersion.version_number,
          reason: rollbackReason
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      // Reload version history
      await loadVersionHistory();
      handleCloseRollbackDialog();

      // Show success message (you might want to pass this up to parent)
      alert(`Successfully rolled back to version ${rollbackVersion.version_number}`);

    } catch (err) {
      console.error('Rollback failed:', err);
      alert(err.response?.data?.detail || 'Failed to rollback');
    } finally {
      setRollbackLoading(false);
    }
  };

  const getChangeTypeColor = (changeType) => {
    switch (changeType) {
      case 'initial':
        return 'success';
      case 'update':
        return 'primary';
      case 'rollback':
        return 'warning';
      case 'major_edit':
        return 'secondary';
      default:
        return 'default';
    }
  };

  const formatDate = (dateString) => {
    try {
      return format(new Date(dateString), 'MMM dd, yyyy HH:mm');
    } catch {
      return dateString;
    }
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

  return (
    <Box>
      {/* Header with Stats */}
      <Box mb={3}>
        <Typography variant="h5" gutterBottom display="flex" alignItems="center" gap={1}>
          <HistoryIcon />
          Version History
        </Typography>

        {stats && (
          <Paper sx={{ p: 2, mt: 2, bgcolor: 'primary.50' }}>
            <Box display="flex" gap={3} flexWrap="wrap">
              <Box>
                <Typography variant="body2" color="text.secondary">Total Versions</Typography>
                <Typography variant="h6">{stats.total_versions}</Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">Contributors</Typography>
                <Typography variant="h6">{stats.unique_contributors}</Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">Avg Word Count</Typography>
                <Typography variant="h6">{Math.round(stats.avg_word_count)}</Typography>
              </Box>
            </Box>
          </Paper>
        )}
      </Box>

      {/* Compare Button */}
      {selectedVersions.length === 2 && (
        <Alert
          severity="info"
          sx={{ mb: 2 }}
          action={
            <Button
              color="inherit"
              size="small"
              startIcon={<CompareIcon />}
              onClick={handleCompare}
            >
              Compare Selected
            </Button>
          }
        >
          {selectedVersions.length} versions selected for comparison
        </Alert>
      )}

      {/* Version Timeline */}
      {versions.length === 0 ? (
        <Alert severity="info">
          No version history available for this chapter
        </Alert>
      ) : (
        <Timeline position="right">
          {versions.map((version, index) => (
            <TimelineItem key={version.id}>
              <TimelineOppositeContent color="text.secondary" sx={{ flex: 0.2 }}>
                <Typography variant="body2">
                  {formatDate(version.created_at)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  v{version.version_number}
                </Typography>
              </TimelineOppositeContent>

              <TimelineSeparator>
                <TimelineDot color={getChangeTypeColor(version.change_type)}>
                  {version.change_type === 'initial' ? <CheckIcon /> : <EditIcon />}
                </TimelineDot>
                {index < versions.length - 1 && <TimelineConnector />}
              </TimelineSeparator>

              <TimelineContent>
                <Card
                  sx={{
                    mb: 2,
                    border: selectedVersions.find(v => v.version_number === version.version_number)
                      ? 2
                      : 0,
                    borderColor: 'primary.main'
                  }}
                >
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="start" mb={1}>
                      <Typography variant="h6" component="div">
                        {version.title}
                      </Typography>
                      <Chip
                        label={version.change_type}
                        size="small"
                        color={getChangeTypeColor(version.change_type)}
                      />
                    </Box>

                    {version.summary && (
                      <Typography variant="body2" color="text.secondary" mb={2}>
                        {version.summary.substring(0, 150)}...
                      </Typography>
                    )}

                    {version.change_description && (
                      <Typography variant="body2" sx={{ fontStyle: 'italic' }} mb={1}>
                        "{version.change_description}"
                      </Typography>
                    )}

                    <Divider sx={{ my: 1 }} />

                    <Box display="flex" gap={2} flexWrap="wrap" mt={1}>
                      <Chip
                        icon={<PersonIcon />}
                        label={version.changed_by}
                        size="small"
                        variant="outlined"
                      />
                      <Chip
                        label={`${version.word_count} words`}
                        size="small"
                        variant="outlined"
                      />
                      {version.change_size !== 0 && (
                        <Chip
                          label={`${version.change_size > 0 ? '+' : ''}${version.change_size} chars`}
                          size="small"
                          variant="outlined"
                          color={version.change_size > 0 ? 'success' : 'error'}
                        />
                      )}
                    </Box>
                  </CardContent>

                  <CardActions>
                    <Tooltip title="Select for comparison">
                      <Button
                        size="small"
                        onClick={() => handleSelectVersion(version)}
                        variant={selectedVersions.find(v => v.version_number === version.version_number) ? 'contained' : 'outlined'}
                      >
                        {selectedVersions.find(v => v.version_number === version.version_number) ? 'Selected' : 'Select'}
                      </Button>
                    </Tooltip>

                    <Button
                      size="small"
                      startIcon={<ViewIcon />}
                      onClick={() => onViewVersion && onViewVersion(version)}
                    >
                      View
                    </Button>

                    {index > 0 && (
                      <Button
                        size="small"
                        startIcon={<RestoreIcon />}
                        color="warning"
                        onClick={() => handleOpenRollbackDialog(version)}
                      >
                        Rollback
                      </Button>
                    )}
                  </CardActions>
                </Card>
              </TimelineContent>
            </TimelineItem>
          ))}
        </Timeline>
      )}

      {/* Rollback Confirmation Dialog */}
      <Dialog open={rollbackDialogOpen} onClose={handleCloseRollbackDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          <Box display="flex" alignItems="center" gap={1}>
            <RestoreIcon color="warning" />
            Rollback to Version {rollbackVersion?.version_number}
          </Box>
        </DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            This will restore the chapter to version {rollbackVersion?.version_number}.
            The current version will be preserved in history.
          </Alert>

          {rollbackVersion && (
            <Box mb={2}>
              <Typography variant="body2" color="text.secondary">
                <strong>Title:</strong> {rollbackVersion.title}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                <strong>Created:</strong> {formatDate(rollbackVersion.created_at)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                <strong>Word Count:</strong> {rollbackVersion.word_count}
              </Typography>
            </Box>
          )}

          <TextField
            fullWidth
            multiline
            rows={3}
            label="Reason for rollback (optional)"
            value={rollbackReason}
            onChange={(e) => setRollbackReason(e.target.value)}
            placeholder="Explain why you're rolling back to this version..."
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseRollbackDialog} disabled={rollbackLoading}>
            Cancel
          </Button>
          <Button
            onClick={handleRollback}
            variant="contained"
            color="warning"
            disabled={rollbackLoading}
            startIcon={rollbackLoading ? <CircularProgress size={20} /> : <RestoreIcon />}
          >
            {rollbackLoading ? 'Rolling back...' : 'Rollback'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default VersionHistory;
