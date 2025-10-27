import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  IconButton,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Avatar,
  Divider,
  Paper,
  Collapse,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  CircularProgress,
  Alert
} from '@mui/material';
import {
  HighlightAlt as HighlightIcon,
  Comment as CommentIcon,
  HelpOutline as QuestionIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Reply as ReplyIcon,
  ThumbUp as ThumbUpIcon,
  ThumbDown as ThumbDownIcon,
  CheckCircle as CheckCircleIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Add as AddIcon
} from '@mui/icons-material';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const HIGHLIGHT_COLORS = [
  { name: 'yellow', value: '#fff59d' },
  { name: 'green', value: '#a5d6a7' },
  { name: 'blue', value: '#90caf9' },
  { name: 'pink', value: '#f48fb1' },
  { name: 'orange', value: '#ffcc80' }
];

const ANNOTATION_TYPES = [
  { value: 'note', label: 'Note', icon: <CommentIcon /> },
  { value: 'question', label: 'Question', icon: <QuestionIcon /> },
  { value: 'correction', label: 'Correction', icon: <EditIcon /> },
  { value: 'comment', label: 'Comment', icon: <CommentIcon /> }
];

const REACTION_TYPES = [
  { type: 'like', icon: '👍', label: 'Like' },
  { type: 'agree', icon: '✅', label: 'Agree' },
  { type: 'disagree', icon: '❌', label: 'Disagree' },
  { type: 'question', icon: '❓', label: 'Question' }
];

/**
 * AnnotationPanel Component
 * Manages highlights, annotations, and discussions on content
 *
 * Features:
 * - Create and view highlights with colors
 * - Add annotations (notes, questions, corrections)
 * - Threaded discussions with replies
 * - Reactions to annotations
 * - Public/private visibility
 * - Resolve annotations
 */
const AnnotationPanel = ({ contentType, contentId, selectedText, selectionPosition }) => {
  const [annotations, setAnnotations] = useState([]);
  const [highlights, setHighlights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Dialog states
  const [highlightDialogOpen, setHighlightDialogOpen] = useState(false);
  const [annotationDialogOpen, setAnnotationDialogOpen] = useState(false);
  const [replyDialogOpen, setReplyDialogOpen] = useState(false);

  // Form states
  const [highlightForm, setHighlightForm] = useState({
    highlight_text: '',
    color: 'yellow',
    position_data: null
  });

  const [annotationForm, setAnnotationForm] = useState({
    annotation_text: '',
    annotation_type: 'note',
    is_private: true,
    highlight_id: null
  });

  const [replyForm, setReplyForm] = useState({
    annotation_id: null,
    reply_text: ''
  });

  // UI states
  const [expandedAnnotations, setExpandedAnnotations] = useState({});
  const [annotationReplies, setAnnotationReplies] = useState({});
  const [annotationReactions, setAnnotationReactions] = useState({});
  const [filterType, setFilterType] = useState('all');

  useEffect(() => {
    loadHighlights();
    loadAnnotations();
  }, [contentType, contentId]);

  useEffect(() => {
    if (selectedText) {
      setHighlightForm(prev => ({
        ...prev,
        highlight_text: selectedText,
        position_data: selectionPosition
      }));
      setHighlightDialogOpen(true);
    }
  }, [selectedText, selectionPosition]);

  const getAuthToken = () => {
    return localStorage.getItem('token');
  };

  const getAuthHeaders = () => {
    return {
      headers: {
        'Authorization': `Bearer ${getAuthToken()}`
      }
    };
  };

  const loadHighlights = async () => {
    try {
      const response = await axios.get(
        `${API_BASE}/content/highlights/${contentType}/${contentId}`,
        getAuthHeaders()
      );

      setHighlights(response.data.highlights || []);
    } catch (err) {
      console.error('Failed to load highlights:', err);
    }
  };

  const loadAnnotations = async () => {
    try {
      setLoading(true);
      const response = await axios.get(
        `${API_BASE}/content/annotations/${contentType}/${contentId}`,
        getAuthHeaders()
      );

      setAnnotations(response.data.annotations || []);
      setError('');
    } catch (err) {
      setError('Failed to load annotations');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadReplies = async (annotationId) => {
    try {
      const response = await axios.get(
        `${API_BASE}/content/annotations/${annotationId}/replies`,
        getAuthHeaders()
      );

      setAnnotationReplies(prev => ({
        ...prev,
        [annotationId]: response.data.replies || []
      }));
    } catch (err) {
      console.error('Failed to load replies:', err);
    }
  };

  const loadReactions = async (annotationId) => {
    try {
      const response = await axios.get(
        `${API_BASE}/content/annotations/${annotationId}/reactions`,
        getAuthHeaders()
      );

      setAnnotationReactions(prev => ({
        ...prev,
        [annotationId]: response.data.reactions || {}
      }));
    } catch (err) {
      console.error('Failed to load reactions:', err);
    }
  };

  const handleCreateHighlight = async () => {
    try {
      const response = await axios.post(
        `${API_BASE}/content/highlights`,
        {
          content_type: contentType,
          content_id: contentId,
          ...highlightForm
        },
        getAuthHeaders()
      );

      if (response.data.success) {
        setHighlightDialogOpen(false);
        loadHighlights();

        // Reset form
        setHighlightForm({
          highlight_text: '',
          color: 'yellow',
          position_data: null
        });
      }
    } catch (err) {
      setError('Failed to create highlight');
      console.error(err);
    }
  };

  const handleDeleteHighlight = async (highlightId) => {
    try {
      await axios.delete(
        `${API_BASE}/content/highlights/${highlightId}`,
        getAuthHeaders()
      );

      loadHighlights();
    } catch (err) {
      setError('Failed to delete highlight');
      console.error(err);
    }
  };

  const handleCreateAnnotation = async () => {
    try {
      const response = await axios.post(
        `${API_BASE}/content/annotations`,
        {
          content_type: contentType,
          content_id: contentId,
          ...annotationForm
        },
        getAuthHeaders()
      );

      if (response.data.success) {
        setAnnotationDialogOpen(false);
        loadAnnotations();

        // Reset form
        setAnnotationForm({
          annotation_text: '',
          annotation_type: 'note',
          is_private: true,
          highlight_id: null
        });
      }
    } catch (err) {
      setError('Failed to create annotation');
      console.error(err);
    }
  };

  const handleDeleteAnnotation = async (annotationId) => {
    if (!window.confirm('Delete this annotation?')) return;

    try {
      await axios.delete(
        `${API_BASE}/content/annotations/${annotationId}`,
        getAuthHeaders()
      );

      loadAnnotations();
    } catch (err) {
      setError('Failed to delete annotation');
      console.error(err);
    }
  };

  const handleResolveAnnotation = async (annotationId) => {
    try {
      await axios.post(
        `${API_BASE}/content/annotations/${annotationId}/resolve`,
        {},
        getAuthHeaders()
      );

      loadAnnotations();
    } catch (err) {
      setError('Failed to resolve annotation');
      console.error(err);
    }
  };

  const handleAddReply = async () => {
    try {
      const response = await axios.post(
        `${API_BASE}/content/annotations/${replyForm.annotation_id}/replies`,
        { reply_text: replyForm.reply_text },
        getAuthHeaders()
      );

      if (response.data.success) {
        setReplyDialogOpen(false);
        loadReplies(replyForm.annotation_id);

        // Reset form
        setReplyForm({
          annotation_id: null,
          reply_text: ''
        });
      }
    } catch (err) {
      setError('Failed to add reply');
      console.error(err);
    }
  };

  const handleAddReaction = async (annotationId, reactionType) => {
    try {
      await axios.post(
        `${API_BASE}/content/annotations/${annotationId}/reactions`,
        { reaction_type: reactionType },
        getAuthHeaders()
      );

      loadReactions(annotationId);
    } catch (err) {
      console.error('Failed to add reaction:', err);
    }
  };

  const handleRemoveReaction = async (annotationId, reactionType) => {
    try {
      await axios.delete(
        `${API_BASE}/content/annotations/${annotationId}/reactions/${reactionType}`,
        getAuthHeaders()
      );

      loadReactions(annotationId);
    } catch (err) {
      console.error('Failed to remove reaction:', err);
    }
  };

  const toggleAnnotationExpanded = (annotationId) => {
    const wasExpanded = expandedAnnotations[annotationId];

    setExpandedAnnotations(prev => ({
      ...prev,
      [annotationId]: !wasExpanded
    }));

    if (!wasExpanded) {
      loadReplies(annotationId);
      loadReactions(annotationId);
    }
  };

  const getAnnotationIcon = (type) => {
    const annotationType = ANNOTATION_TYPES.find(t => t.value === type);
    return annotationType ? annotationType.icon : <CommentIcon />;
  };

  const renderHighlightDialog = () => (
    <Dialog open={highlightDialogOpen} onClose={() => setHighlightDialogOpen(false)} maxWidth="sm" fullWidth>
      <DialogTitle>Create Highlight</DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="Highlighted Text"
            fullWidth
            multiline
            rows={3}
            value={highlightForm.highlight_text}
            onChange={(e) => setHighlightForm({ ...highlightForm, highlight_text: e.target.value })}
          />

          <Box>
            <Typography variant="body2" sx={{ mb: 1 }}>Select Color:</Typography>
            <Box sx={{ display: 'flex', gap: 1 }}>
              {HIGHLIGHT_COLORS.map(color => (
                <Box
                  key={color.name}
                  onClick={() => setHighlightForm({ ...highlightForm, color: color.name })}
                  sx={{
                    width: 40,
                    height: 40,
                    bgcolor: color.value,
                    border: highlightForm.color === color.name ? '3px solid #000' : '1px solid #ccc',
                    borderRadius: 1,
                    cursor: 'pointer',
                    '&:hover': { transform: 'scale(1.1)' }
                  }}
                />
              ))}
            </Box>
          </Box>

          <Button
            variant="outlined"
            onClick={() => {
              setAnnotationForm({
                ...annotationForm,
                highlight_id: null
              });
              setAnnotationDialogOpen(true);
            }}
          >
            Add Annotation to Highlight
          </Button>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setHighlightDialogOpen(false)}>Cancel</Button>
        <Button onClick={handleCreateHighlight} variant="contained">Create</Button>
      </DialogActions>
    </Dialog>
  );

  const renderAnnotationDialog = () => (
    <Dialog open={annotationDialogOpen} onClose={() => setAnnotationDialogOpen(false)} maxWidth="sm" fullWidth>
      <DialogTitle>Create Annotation</DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
          <FormControl fullWidth>
            <InputLabel>Type</InputLabel>
            <Select
              value={annotationForm.annotation_type}
              onChange={(e) => setAnnotationForm({ ...annotationForm, annotation_type: e.target.value })}
            >
              {ANNOTATION_TYPES.map(type => (
                <MenuItem key={type.value} value={type.value}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {type.icon}
                    {type.label}
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            label="Annotation Text"
            fullWidth
            multiline
            rows={4}
            required
            value={annotationForm.annotation_text}
            onChange={(e) => setAnnotationForm({ ...annotationForm, annotation_text: e.target.value })}
          />

          <FormControl fullWidth>
            <InputLabel>Visibility</InputLabel>
            <Select
              value={annotationForm.is_private}
              onChange={(e) => setAnnotationForm({ ...annotationForm, is_private: e.target.value })}
            >
              <MenuItem value={true}>Private (only you)</MenuItem>
              <MenuItem value={false}>Public (everyone)</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setAnnotationDialogOpen(false)}>Cancel</Button>
        <Button onClick={handleCreateAnnotation} variant="contained">Create</Button>
      </DialogActions>
    </Dialog>
  );

  const renderReplyDialog = () => (
    <Dialog open={replyDialogOpen} onClose={() => setReplyDialogOpen(false)} maxWidth="sm" fullWidth>
      <DialogTitle>Add Reply</DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 2 }}>
          <TextField
            label="Reply"
            fullWidth
            multiline
            rows={3}
            required
            value={replyForm.reply_text}
            onChange={(e) => setReplyForm({ ...replyForm, reply_text: e.target.value })}
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setReplyDialogOpen(false)}>Cancel</Button>
        <Button onClick={handleAddReply} variant="contained">Post Reply</Button>
      </DialogActions>
    </Dialog>
  );

  const renderAnnotationItem = (annotation) => {
    const isExpanded = expandedAnnotations[annotation.id];
    const replies = annotationReplies[annotation.id] || [];
    const reactions = annotationReactions[annotation.id] || {};

    return (
      <Paper key={annotation.id} sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box sx={{ display: 'flex', gap: 1, flex: 1 }}>
            <Avatar sx={{ width: 32, height: 32 }}>
              {getAnnotationIcon(annotation.annotation_type)}
            </Avatar>
            <Box sx={{ flex: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                <Chip
                  label={annotation.annotation_type}
                  size="small"
                  color={annotation.annotation_type === 'question' ? 'info' : 'default'}
                />
                {annotation.is_private && (
                  <Chip label="Private" size="small" variant="outlined" />
                )}
                {annotation.is_resolved && (
                  <Chip
                    icon={<CheckCircleIcon />}
                    label="Resolved"
                    size="small"
                    color="success"
                  />
                )}
              </Box>

              <Typography variant="body1" sx={{ mb: 1 }}>
                {annotation.annotation_text}
              </Typography>

              <Typography variant="caption" color="text.secondary">
                {new Date(annotation.created_at).toLocaleString()}
                {annotation.reply_count > 0 && ` • ${annotation.reply_count} replies`}
                {annotation.reaction_count > 0 && ` • ${annotation.reaction_count} reactions`}
              </Typography>

              {/* Reactions */}
              <Box sx={{ display: 'flex', gap: 0.5, mt: 1 }}>
                {REACTION_TYPES.map(reaction => (
                  <Tooltip key={reaction.type} title={reaction.label}>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => handleAddReaction(annotation.id, reaction.type)}
                      sx={{ minWidth: 'auto', px: 1 }}
                    >
                      {reaction.icon}
                      {reactions[reaction.type] > 0 && (
                        <Typography variant="caption" sx={{ ml: 0.5 }}>
                          {reactions[reaction.type]}
                        </Typography>
                      )}
                    </Button>
                  </Tooltip>
                ))}
              </Box>
            </Box>
          </Box>

          <Box sx={{ display: 'flex', gap: 0.5 }}>
            {!annotation.is_resolved && (
              <Tooltip title="Mark as resolved">
                <IconButton
                  size="small"
                  onClick={() => handleResolveAnnotation(annotation.id)}
                >
                  <CheckCircleIcon />
                </IconButton>
              </Tooltip>
            )}
            <Tooltip title="Reply">
              <IconButton
                size="small"
                onClick={() => {
                  setReplyForm({ annotation_id: annotation.id, reply_text: '' });
                  setReplyDialogOpen(true);
                }}
              >
                <ReplyIcon />
              </IconButton>
            </Tooltip>
            <IconButton
              size="small"
              onClick={() => handleDeleteAnnotation(annotation.id)}
            >
              <DeleteIcon />
            </IconButton>
            <IconButton
              size="small"
              onClick={() => toggleAnnotationExpanded(annotation.id)}
            >
              {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>
        </Box>

        {/* Replies */}
        <Collapse in={isExpanded}>
          <Box sx={{ mt: 2, pl: 5 }}>
            {replies.length > 0 ? (
              <List dense>
                {replies.map((reply, index) => (
                  <React.Fragment key={reply.id}>
                    {index > 0 && <Divider />}
                    <ListItem>
                      <ListItemAvatar>
                        <Avatar sx={{ width: 24, height: 24 }}>
                          <ReplyIcon fontSize="small" />
                        </Avatar>
                      </ListItemAvatar>
                      <ListItemText
                        primary={reply.reply_text}
                        secondary={new Date(reply.created_at).toLocaleString()}
                      />
                    </ListItem>
                  </React.Fragment>
                ))}
              </List>
            ) : (
              <Typography variant="body2" color="text.secondary" align="center">
                No replies yet
              </Typography>
            )}
          </Box>
        </Collapse>
      </Paper>
    );
  };

  const renderHighlights = () => {
    if (highlights.length === 0) {
      return (
        <Typography variant="body2" color="text.secondary" align="center" sx={{ py: 2 }}>
          No highlights yet
        </Typography>
      );
    }

    return (
      <List>
        {highlights.map((highlight, index) => (
          <React.Fragment key={highlight.id}>
            {index > 0 && <Divider />}
            <ListItem>
              <Box
                sx={{
                  width: 4,
                  height: '100%',
                  bgcolor: HIGHLIGHT_COLORS.find(c => c.name === highlight.color)?.value || '#fff59d',
                  mr: 2,
                  borderRadius: 1
                }}
              />
              <ListItemText
                primary={highlight.highlight_text}
                secondary={new Date(highlight.created_at).toLocaleString()}
              />
              <IconButton
                edge="end"
                onClick={() => handleDeleteHighlight(highlight.id)}
                size="small"
              >
                <DeleteIcon />
              </IconButton>
            </ListItem>
          </React.Fragment>
        ))}
      </List>
    );
  };

  const filteredAnnotations = annotations.filter(annotation => {
    if (filterType === 'all') return true;
    if (filterType === 'unresolved') return !annotation.is_resolved;
    if (filterType === 'resolved') return annotation.is_resolved;
    return annotation.annotation_type === filterType;
  });

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ width: '100%' }}>
      {error && (
        <Alert severity="error" onClose={() => setError('')} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Action Buttons */}
      <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
        <Button
          variant="contained"
          startIcon={<HighlightIcon />}
          onClick={() => setHighlightDialogOpen(true)}
        >
          Add Highlight
        </Button>
        <Button
          variant="contained"
          startIcon={<CommentIcon />}
          onClick={() => setAnnotationDialogOpen(true)}
        >
          Add Annotation
        </Button>
      </Box>

      {/* Filter Buttons */}
      <ToggleButtonGroup
        value={filterType}
        exclusive
        onChange={(e, value) => value && setFilterType(value)}
        size="small"
        sx={{ mb: 2 }}
      >
        <ToggleButton value="all">All</ToggleButton>
        <ToggleButton value="unresolved">Unresolved</ToggleButton>
        <ToggleButton value="resolved">Resolved</ToggleButton>
        <ToggleButton value="note">Notes</ToggleButton>
        <ToggleButton value="question">Questions</ToggleButton>
      </ToggleButtonGroup>

      {/* Highlights Section */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Highlights ({highlights.length})
        </Typography>
        {renderHighlights()}
      </Paper>

      {/* Annotations Section */}
      <Typography variant="h6" sx={{ mb: 2 }}>
        Annotations ({filteredAnnotations.length})
      </Typography>

      {filteredAnnotations.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="body1" color="text.secondary">
            No annotations yet
          </Typography>
        </Paper>
      ) : (
        filteredAnnotations.map(renderAnnotationItem)
      )}

      {renderHighlightDialog()}
      {renderAnnotationDialog()}
      {renderReplyDialog()}
    </Box>
  );
};

export default AnnotationPanel;
