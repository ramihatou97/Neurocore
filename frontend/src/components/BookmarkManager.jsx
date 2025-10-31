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
  ListItemSecondaryAction,
  Divider,
  Tabs,
  Tab,
  Grid,
  Paper,
  Tooltip,
  CircularProgress,
  Alert
} from '@mui/material';
import {
  Bookmark as BookmarkIcon,
  BookmarkBorder as BookmarkBorderIcon,
  Folder as FolderIcon,
  FolderOpen as FolderOpenIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Share as ShareIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon
} from '@mui/icons-material';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002/api/v1';

/**
 * BookmarkManager Component
 * Manages user bookmarks and collections
 *
 * Features:
 * - View and organize bookmarks
 * - Create and manage collections
 * - Add notes and tags to bookmarks
 * - Share collections
 * - Favorites
 */
const BookmarkManager = ({ contentType, contentId, onBookmarkChange }) => {
  const [activeTab, setActiveTab] = useState(0);
  const [bookmarks, setBookmarks] = useState([]);
  const [collections, setCollections] = useState([]);
  const [selectedCollection, setSelectedCollection] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Dialog states
  const [bookmarkDialogOpen, setBookmarkDialogOpen] = useState(false);
  const [collectionDialogOpen, setCollectionDialogOpen] = useState(false);
  const [shareDialogOpen, setShareDialogOpen] = useState(false);

  // Form states
  const [bookmarkForm, setBookmarkForm] = useState({
    content_type: contentType || '',
    content_id: contentId || '',
    collection_id: '',
    title: '',
    notes: '',
    tags: [],
    is_favorite: false
  });

  const [collectionForm, setCollectionForm] = useState({
    name: '',
    description: '',
    icon: 'folder',
    color: '#1976d2',
    is_public: false,
    parent_collection_id: null
  });

  const [shareForm, setShareForm] = useState({
    shared_with_email: '',
    permission_level: 'view'
  });

  const [tagInput, setTagInput] = useState('');
  const [statistics, setStatistics] = useState(null);

  useEffect(() => {
    loadBookmarks();
    loadCollections();
    loadStatistics();
  }, [selectedCollection]);

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

  const loadBookmarks = async () => {
    try {
      setLoading(true);
      const params = {};
      if (selectedCollection) {
        params.collection_id = selectedCollection;
      }

      const response = await axios.get(
        `${API_BASE}/content/bookmarks`,
        { ...getAuthHeaders(), params }
      );

      setBookmarks(response.data.bookmarks || []);
      setError('');
    } catch (err) {
      setError('Failed to load bookmarks');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadCollections = async () => {
    try {
      const response = await axios.get(
        `${API_BASE}/content/bookmarks/collections`,
        getAuthHeaders()
      );

      setCollections(response.data.collections || []);
    } catch (err) {
      console.error('Failed to load collections:', err);
    }
  };

  const loadStatistics = async () => {
    try {
      const response = await axios.get(
        `${API_BASE}/content/bookmarks/statistics`,
        getAuthHeaders()
      );

      setStatistics(response.data.statistics);
    } catch (err) {
      console.error('Failed to load statistics:', err);
    }
  };

  const handleCreateBookmark = async () => {
    try {
      const response = await axios.post(
        `${API_BASE}/content/bookmarks`,
        bookmarkForm,
        getAuthHeaders()
      );

      if (response.data.success) {
        setBookmarkDialogOpen(false);
        loadBookmarks();
        if (onBookmarkChange) onBookmarkChange(response.data.bookmark);

        // Reset form
        setBookmarkForm({
          content_type: contentType || '',
          content_id: contentId || '',
          collection_id: '',
          title: '',
          notes: '',
          tags: [],
          is_favorite: false
        });
      }
    } catch (err) {
      setError('Failed to create bookmark');
      console.error(err);
    }
  };

  const handleDeleteBookmark = async (bookmarkId) => {
    if (!window.confirm('Delete this bookmark?')) return;

    try {
      await axios.delete(
        `${API_BASE}/content/bookmarks/${bookmarkId}`,
        getAuthHeaders()
      );

      loadBookmarks();
      if (onBookmarkChange) onBookmarkChange(null);
    } catch (err) {
      setError('Failed to delete bookmark');
      console.error(err);
    }
  };

  const handleCreateCollection = async () => {
    try {
      const response = await axios.post(
        `${API_BASE}/content/bookmarks/collections`,
        collectionForm,
        getAuthHeaders()
      );

      if (response.data.success) {
        setCollectionDialogOpen(false);
        loadCollections();

        // Reset form
        setCollectionForm({
          name: '',
          description: '',
          icon: 'folder',
          color: '#1976d2',
          is_public: false,
          parent_collection_id: null
        });
      }
    } catch (err) {
      setError('Failed to create collection');
      console.error(err);
    }
  };

  const handleShareCollection = async () => {
    if (!selectedCollection) return;

    try {
      await axios.post(
        `${API_BASE}/content/bookmarks/collections/${selectedCollection}/share`,
        shareForm,
        getAuthHeaders()
      );

      setShareDialogOpen(false);
      alert('Collection shared successfully');

      // Reset form
      setShareForm({
        shared_with_email: '',
        permission_level: 'view'
      });
    } catch (err) {
      setError('Failed to share collection');
      console.error(err);
    }
  };

  const handleAddTag = () => {
    if (tagInput.trim() && !bookmarkForm.tags.includes(tagInput.trim())) {
      setBookmarkForm({
        ...bookmarkForm,
        tags: [...bookmarkForm.tags, tagInput.trim()]
      });
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove) => {
    setBookmarkForm({
      ...bookmarkForm,
      tags: bookmarkForm.tags.filter(tag => tag !== tagToRemove)
    });
  };

  const renderBookmarkDialog = () => (
    <Dialog open={bookmarkDialogOpen} onClose={() => setBookmarkDialogOpen(false)} maxWidth="sm" fullWidth>
      <DialogTitle>Create Bookmark</DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="Title (optional)"
            fullWidth
            value={bookmarkForm.title}
            onChange={(e) => setBookmarkForm({ ...bookmarkForm, title: e.target.value })}
          />

          <FormControl fullWidth>
            <InputLabel>Collection</InputLabel>
            <Select
              value={bookmarkForm.collection_id}
              onChange={(e) => setBookmarkForm({ ...bookmarkForm, collection_id: e.target.value })}
            >
              <MenuItem value="">None</MenuItem>
              {collections.map(col => (
                <MenuItem key={col.id} value={col.id}>
                  <FolderIcon sx={{ mr: 1, fontSize: 'small' }} />
                  {col.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            label="Notes"
            fullWidth
            multiline
            rows={3}
            value={bookmarkForm.notes}
            onChange={(e) => setBookmarkForm({ ...bookmarkForm, notes: e.target.value })}
          />

          <Box>
            <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
              <TextField
                size="small"
                label="Add tag"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAddTag()}
              />
              <Button onClick={handleAddTag} variant="outlined" size="small">
                Add
              </Button>
            </Box>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
              {bookmarkForm.tags.map(tag => (
                <Chip
                  key={tag}
                  label={tag}
                  size="small"
                  onDelete={() => handleRemoveTag(tag)}
                />
              ))}
            </Box>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <IconButton
              onClick={() => setBookmarkForm({ ...bookmarkForm, is_favorite: !bookmarkForm.is_favorite })}
              color={bookmarkForm.is_favorite ? 'warning' : 'default'}
            >
              {bookmarkForm.is_favorite ? <StarIcon /> : <StarBorderIcon />}
            </IconButton>
            <Typography variant="body2">Mark as favorite</Typography>
          </Box>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setBookmarkDialogOpen(false)}>Cancel</Button>
        <Button onClick={handleCreateBookmark} variant="contained">Create</Button>
      </DialogActions>
    </Dialog>
  );

  const renderCollectionDialog = () => (
    <Dialog open={collectionDialogOpen} onClose={() => setCollectionDialogOpen(false)} maxWidth="sm" fullWidth>
      <DialogTitle>Create Collection</DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="Collection Name"
            fullWidth
            required
            value={collectionForm.name}
            onChange={(e) => setCollectionForm({ ...collectionForm, name: e.target.value })}
          />

          <TextField
            label="Description"
            fullWidth
            multiline
            rows={2}
            value={collectionForm.description}
            onChange={(e) => setCollectionForm({ ...collectionForm, description: e.target.value })}
          />

          <FormControl fullWidth>
            <InputLabel>Parent Collection</InputLabel>
            <Select
              value={collectionForm.parent_collection_id || ''}
              onChange={(e) => setCollectionForm({ ...collectionForm, parent_collection_id: e.target.value || null })}
            >
              <MenuItem value="">None (Top Level)</MenuItem>
              {collections.map(col => (
                <MenuItem key={col.id} value={col.id}>{col.name}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <Box sx={{ display: 'flex', gap: 2 }}>
            <TextField
              label="Color"
              type="color"
              value={collectionForm.color}
              onChange={(e) => setCollectionForm({ ...collectionForm, color: e.target.value })}
              sx={{ width: 120 }}
            />

            <FormControl sx={{ flex: 1 }}>
              <InputLabel>Icon</InputLabel>
              <Select
                value={collectionForm.icon}
                onChange={(e) => setCollectionForm({ ...collectionForm, icon: e.target.value })}
              >
                <MenuItem value="folder">Folder</MenuItem>
                <MenuItem value="star">Star</MenuItem>
                <MenuItem value="bookmark">Bookmark</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setCollectionDialogOpen(false)}>Cancel</Button>
        <Button onClick={handleCreateCollection} variant="contained">Create</Button>
      </DialogActions>
    </Dialog>
  );

  const renderShareDialog = () => (
    <Dialog open={shareDialogOpen} onClose={() => setShareDialogOpen(false)} maxWidth="sm" fullWidth>
      <DialogTitle>Share Collection</DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="Email Address"
            fullWidth
            type="email"
            value={shareForm.shared_with_email}
            onChange={(e) => setShareForm({ ...shareForm, shared_with_email: e.target.value })}
          />

          <FormControl fullWidth>
            <InputLabel>Permission Level</InputLabel>
            <Select
              value={shareForm.permission_level}
              onChange={(e) => setShareForm({ ...shareForm, permission_level: e.target.value })}
            >
              <MenuItem value="view">View Only</MenuItem>
              <MenuItem value="edit">Can Edit</MenuItem>
              <MenuItem value="admin">Admin</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setShareDialogOpen(false)}>Cancel</Button>
        <Button onClick={handleShareCollection} variant="contained">Share</Button>
      </DialogActions>
    </Dialog>
  );

  const renderBookmarksList = () => {
    if (loading) {
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      );
    }

    if (bookmarks.length === 0) {
      return (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <BookmarkBorderIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
          <Typography variant="body1" color="text.secondary">
            No bookmarks yet
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setBookmarkDialogOpen(true)}
            sx={{ mt: 2 }}
          >
            Create Bookmark
          </Button>
        </Box>
      );
    }

    return (
      <List>
        {bookmarks.map((bookmark, index) => (
          <React.Fragment key={bookmark.id}>
            {index > 0 && <Divider />}
            <ListItem>
              <ListItemText
                primary={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="subtitle1">
                      {bookmark.title || `${bookmark.content_type} - ${bookmark.content_id.slice(0, 8)}`}
                    </Typography>
                    {bookmark.is_favorite && <StarIcon color="warning" fontSize="small" />}
                  </Box>
                }
                secondary={
                  <Box>
                    {bookmark.notes && (
                      <Typography variant="body2" color="text.secondary">
                        {bookmark.notes}
                      </Typography>
                    )}
                    {bookmark.collection_name && (
                      <Chip
                        icon={<FolderIcon />}
                        label={bookmark.collection_name}
                        size="small"
                        sx={{ mt: 0.5, mr: 0.5 }}
                      />
                    )}
                    {bookmark.tags && bookmark.tags.map(tag => (
                      <Chip key={tag} label={tag} size="small" sx={{ mt: 0.5, mr: 0.5 }} />
                    ))}
                    <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
                      Created: {new Date(bookmark.created_at).toLocaleDateString()}
                    </Typography>
                  </Box>
                }
              />
              <ListItemSecondaryAction>
                <IconButton
                  edge="end"
                  onClick={() => handleDeleteBookmark(bookmark.id)}
                  size="small"
                >
                  <DeleteIcon />
                </IconButton>
              </ListItemSecondaryAction>
            </ListItem>
          </React.Fragment>
        ))}
      </List>
    );
  };

  const renderCollections = () => (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h6">Collections</Typography>
        <Button
          variant="contained"
          size="small"
          startIcon={<AddIcon />}
          onClick={() => setCollectionDialogOpen(true)}
        >
          New Collection
        </Button>
      </Box>

      {collections.length === 0 ? (
        <Typography variant="body2" color="text.secondary" align="center" sx={{ py: 4 }}>
          No collections yet
        </Typography>
      ) : (
        <Grid container spacing={2}>
          {collections.map(collection => (
            <Grid item xs={12} sm={6} md={4} key={collection.id}>
              <Paper
                sx={{
                  p: 2,
                  cursor: 'pointer',
                  borderLeft: `4px solid ${collection.color || '#1976d2'}`,
                  '&:hover': { bgcolor: 'action.hover' }
                }}
                onClick={() => {
                  setSelectedCollection(collection.id);
                  setActiveTab(0);
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <FolderIcon sx={{ color: collection.color || '#1976d2' }} />
                    <Typography variant="subtitle1">{collection.name}</Typography>
                  </Box>
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedCollection(collection.id);
                      setShareDialogOpen(true);
                    }}
                  >
                    <ShareIcon fontSize="small" />
                  </IconButton>
                </Box>
                {collection.description && (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    {collection.description}
                  </Typography>
                )}
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                  {collection.bookmark_count || 0} bookmarks
                </Typography>
              </Paper>
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );

  const renderStatistics = () => {
    if (!statistics) return null;

    return (
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={6} sm={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h4">{statistics.total_bookmarks || 0}</Typography>
            <Typography variant="body2" color="text.secondary">Total Bookmarks</Typography>
          </Paper>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h4">{statistics.favorite_count || 0}</Typography>
            <Typography variant="body2" color="text.secondary">Favorites</Typography>
          </Paper>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h4">{statistics.collection_count || 0}</Typography>
            <Typography variant="body2" color="text.secondary">Collections</Typography>
          </Paper>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h4">{statistics.content_types_bookmarked || 0}</Typography>
            <Typography variant="body2" color="text.secondary">Content Types</Typography>
          </Paper>
        </Grid>
      </Grid>
    );
  };

  return (
    <Box sx={{ width: '100%' }}>
      {error && (
        <Alert severity="error" onClose={() => setError('')} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {renderStatistics()}

      <Paper sx={{ mb: 2 }}>
        <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)}>
          <Tab label="Bookmarks" />
          <Tab label="Collections" />
        </Tabs>
      </Paper>

      <Box>
        {activeTab === 0 && (
          <Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                {selectedCollection && (
                  <Chip
                    icon={<FolderIcon />}
                    label={collections.find(c => c.id === selectedCollection)?.name || 'Collection'}
                    onDelete={() => setSelectedCollection(null)}
                  />
                )}
              </Box>
              <Button
                variant="contained"
                startIcon={<BookmarkIcon />}
                onClick={() => setBookmarkDialogOpen(true)}
              >
                Add Bookmark
              </Button>
            </Box>
            {renderBookmarksList()}
          </Box>
        )}

        {activeTab === 1 && renderCollections()}
      </Box>

      {renderBookmarkDialog()}
      {renderCollectionDialog()}
      {renderShareDialog()}
    </Box>
  );
};

export default BookmarkManager;
