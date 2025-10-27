import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Card,
  CardContent,
  CardActions,
  Grid,
  Chip,
  IconButton,
  List,
  ListItem,
  ListItemText,
  Divider,
  ToggleButton,
  ToggleButtonGroup,
  CircularProgress,
  Alert,
  Tooltip
} from '@mui/material';
import {
  Description as TemplateIcon,
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
  Public as PublicIcon,
  Lock as LockIcon,
  CheckCircle as CheckIcon,
  Star as StarIcon
} from '@mui/icons-material';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const TEMPLATE_TYPES = [
  { value: 'surgical_disease', label: 'Surgical Disease', icon: '🏥' },
  { value: 'anatomy', label: 'Anatomy', icon: '🧠' },
  { value: 'technique', label: 'Surgical Technique', icon: '✂️' },
  { value: 'case_study', label: 'Case Study', icon: '📋' },
  { value: 'custom', label: 'Custom', icon: '⚙️' }
];

/**
 * TemplateSelector Component
 * Allows users to browse, select, and apply content templates
 *
 * Features:
 * - Browse system and user templates
 * - Filter by template type
 * - Preview template structure
 * - Apply template to new or existing content
 * - Create custom templates
 * - Track template usage statistics
 */
const TemplateSelector = ({ onTemplateSelect, chapterId }) => {
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Dialog states
  const [previewDialogOpen, setPreviewDialogOpen] = useState(false);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);

  // Filter states
  const [filterType, setFilterType] = useState('all');
  const [showSystemOnly, setShowSystemOnly] = useState(false);
  const [showPublicOnly, setShowPublicOnly] = useState(false);

  // Form state for creating templates
  const [templateForm, setTemplateForm] = useState({
    name: '',
    template_type: 'custom',
    description: '',
    structure: {
      sections: []
    },
    is_public: false
  });

  const [sectionForm, setSectionForm] = useState({
    name: '',
    required: true,
    placeholder: ''
  });

  useEffect(() => {
    loadTemplates();
  }, []);

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

  const loadTemplates = async () => {
    try {
      setLoading(true);
      const response = await axios.get(
        `${API_BASE}/content/templates`,
        {
          ...getAuthHeaders(),
          params: {
            include_public: true,
            include_system: true
          }
        }
      );

      setTemplates(response.data.templates || []);
      setError('');
    } catch (err) {
      setError('Failed to load templates');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleApplyTemplate = async (templateId) => {
    try {
      const response = await axios.post(
        `${API_BASE}/content/templates/${templateId}/apply`,
        { chapter_id: chapterId },
        getAuthHeaders()
      );

      if (response.data.success) {
        if (onTemplateSelect) {
          onTemplateSelect(response.data.template_content);
        }
        alert('Template applied successfully!');
      }
    } catch (err) {
      setError('Failed to apply template');
      console.error(err);
    }
  };

  const handleCreateTemplate = async () => {
    try {
      const response = await axios.post(
        `${API_BASE}/content/templates`,
        templateForm,
        getAuthHeaders()
      );

      if (response.data.success) {
        setCreateDialogOpen(false);
        loadTemplates();

        // Reset form
        setTemplateForm({
          name: '',
          template_type: 'custom',
          description: '',
          structure: { sections: [] },
          is_public: false
        });
      }
    } catch (err) {
      setError('Failed to create template');
      console.error(err);
    }
  };

  const handleDeleteTemplate = async (templateId) => {
    if (!window.confirm('Delete this template?')) return;

    try {
      await axios.delete(
        `${API_BASE}/content/templates/${templateId}`,
        getAuthHeaders()
      );

      loadTemplates();
    } catch (err) {
      setError('Failed to delete template');
      console.error(err);
    }
  };

  const handleAddSection = () => {
    if (!sectionForm.name.trim()) return;

    setTemplateForm({
      ...templateForm,
      structure: {
        ...templateForm.structure,
        sections: [
          ...templateForm.structure.sections,
          {
            ...sectionForm,
            order: templateForm.structure.sections.length
          }
        ]
      }
    });

    // Reset section form
    setSectionForm({
      name: '',
      required: true,
      placeholder: ''
    });
  };

  const handleRemoveSection = (index) => {
    setTemplateForm({
      ...templateForm,
      structure: {
        ...templateForm.structure,
        sections: templateForm.structure.sections.filter((_, i) => i !== index)
      }
    });
  };

  const getTemplateTypeIcon = (type) => {
    const templateType = TEMPLATE_TYPES.find(t => t.value === type);
    return templateType ? templateType.icon : '📄';
  };

  const getTemplateTypeLabel = (type) => {
    const templateType = TEMPLATE_TYPES.find(t => t.value === type);
    return templateType ? templateType.label : type;
  };

  const filteredTemplates = templates.filter(template => {
    if (filterType !== 'all' && template.template_type !== filterType) {
      return false;
    }
    if (showSystemOnly && !template.is_system) {
      return false;
    }
    if (showPublicOnly && !template.is_public) {
      return false;
    }
    return true;
  });

  const renderTemplateCard = (template) => (
    <Grid item xs={12} sm={6} md={4} key={template.id}>
      <Card
        sx={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
          '&:hover': { boxShadow: 4 }
        }}
      >
        <CardContent sx={{ flex: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="h6" component="div" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <span>{getTemplateTypeIcon(template.template_type)}</span>
              {template.name}
            </Typography>
            {template.is_system && (
              <Chip icon={<StarIcon />} label="System" size="small" color="primary" />
            )}
          </Box>

          <Chip
            label={getTemplateTypeLabel(template.template_type)}
            size="small"
            sx={{ mb: 1 }}
          />

          {template.description && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              {template.description}
            </Typography>
          )}

          <Box sx={{ display: 'flex', gap: 0.5, mt: 1, flexWrap: 'wrap' }}>
            {template.is_public && (
              <Chip icon={<PublicIcon />} label="Public" size="small" variant="outlined" />
            )}
            {!template.is_public && !template.is_system && (
              <Chip icon={<LockIcon />} label="Private" size="small" variant="outlined" />
            )}
          </Box>

          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
            Used {template.usage_count || 0} times
          </Typography>
        </CardContent>

        <CardActions sx={{ justifyContent: 'space-between', p: 2 }}>
          <Box sx={{ display: 'flex', gap: 0.5 }}>
            <Tooltip title="Preview">
              <IconButton
                size="small"
                onClick={() => {
                  setSelectedTemplate(template);
                  setPreviewDialogOpen(true);
                }}
              >
                <ViewIcon />
              </IconButton>
            </Tooltip>
            {!template.is_system && (
              <Tooltip title="Delete">
                <IconButton
                  size="small"
                  onClick={() => handleDeleteTemplate(template.id)}
                >
                  <DeleteIcon />
                </IconButton>
              </Tooltip>
            )}
          </Box>
          <Button
            variant="contained"
            size="small"
            onClick={() => handleApplyTemplate(template.id)}
            startIcon={<CheckIcon />}
          >
            Use Template
          </Button>
        </CardActions>
      </Card>
    </Grid>
  );

  const renderPreviewDialog = () => {
    if (!selectedTemplate) return null;

    return (
      <Dialog open={previewDialogOpen} onClose={() => setPreviewDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <span>{getTemplateTypeIcon(selectedTemplate.template_type)}</span>
            {selectedTemplate.name}
          </Box>
        </DialogTitle>
        <DialogContent>
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="text.secondary">
              {selectedTemplate.description}
            </Typography>
          </Box>

          <Typography variant="h6" sx={{ mb: 2 }}>
            Template Structure
          </Typography>

          {selectedTemplate.sections && selectedTemplate.sections.length > 0 ? (
            <List>
              {selectedTemplate.sections.map((section, index) => (
                <React.Fragment key={index}>
                  {index > 0 && <Divider />}
                  <ListItem>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="subtitle1">{section.name}</Typography>
                          {section.required && (
                            <Chip label="Required" size="small" color="error" />
                          )}
                        </Box>
                      }
                      secondary={section.placeholder}
                    />
                  </ListItem>
                </React.Fragment>
              ))}
            </List>
          ) : (
            <Typography variant="body2" color="text.secondary">
              No sections defined
            </Typography>
          )}

          <Box sx={{ mt: 2 }}>
            <Typography variant="caption" color="text.secondary">
              Type: {getTemplateTypeLabel(selectedTemplate.template_type)}
            </Typography>
            <br />
            <Typography variant="caption" color="text.secondary">
              Used: {selectedTemplate.usage_count || 0} times
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewDialogOpen(false)}>Close</Button>
          <Button
            variant="contained"
            onClick={() => {
              handleApplyTemplate(selectedTemplate.id);
              setPreviewDialogOpen(false);
            }}
          >
            Use This Template
          </Button>
        </DialogActions>
      </Dialog>
    );
  };

  const renderCreateDialog = () => (
    <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="md" fullWidth>
      <DialogTitle>Create Custom Template</DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="Template Name"
            fullWidth
            required
            value={templateForm.name}
            onChange={(e) => setTemplateForm({ ...templateForm, name: e.target.value })}
          />

          <TextField
            label="Description"
            fullWidth
            multiline
            rows={2}
            value={templateForm.description}
            onChange={(e) => setTemplateForm({ ...templateForm, description: e.target.value })}
          />

          <ToggleButtonGroup
            value={templateForm.template_type}
            exclusive
            onChange={(e, value) => value && setTemplateForm({ ...templateForm, template_type: value })}
            size="small"
            fullWidth
          >
            {TEMPLATE_TYPES.map(type => (
              <ToggleButton key={type.value} value={type.value}>
                {type.icon} {type.label}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>

          <Divider />

          <Typography variant="h6">Template Sections</Typography>

          <Box sx={{ display: 'flex', gap: 1 }}>
            <TextField
              size="small"
              label="Section Name"
              value={sectionForm.name}
              onChange={(e) => setSectionForm({ ...sectionForm, name: e.target.value })}
              sx={{ flex: 1 }}
            />
            <TextField
              size="small"
              label="Placeholder"
              value={sectionForm.placeholder}
              onChange={(e) => setSectionForm({ ...sectionForm, placeholder: e.target.value })}
              sx={{ flex: 1 }}
            />
            <Button
              variant="outlined"
              onClick={handleAddSection}
              startIcon={<AddIcon />}
            >
              Add
            </Button>
          </Box>

          {templateForm.structure.sections.length > 0 && (
            <List dense>
              {templateForm.structure.sections.map((section, index) => (
                <React.Fragment key={index}>
                  {index > 0 && <Divider />}
                  <ListItem
                    secondaryAction={
                      <IconButton edge="end" onClick={() => handleRemoveSection(index)}>
                        <DeleteIcon />
                      </IconButton>
                    }
                  >
                    <ListItemText
                      primary={`${index + 1}. ${section.name}`}
                      secondary={section.placeholder}
                    />
                    {section.required && (
                      <Chip label="Required" size="small" color="error" sx={{ mr: 1 }} />
                    )}
                  </ListItem>
                </React.Fragment>
              ))}
            </List>
          )}

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <input
              type="checkbox"
              checked={templateForm.is_public}
              onChange={(e) => setTemplateForm({ ...templateForm, is_public: e.target.checked })}
            />
            <Typography variant="body2">Make this template public</Typography>
          </Box>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
        <Button onClick={handleCreateTemplate} variant="contained">Create Template</Button>
      </DialogActions>
    </Dialog>
  );

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

      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5">Content Templates</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateDialogOpen(true)}
        >
          Create Template
        </Button>
      </Box>

      {/* Filters */}
      <Box sx={{ mb: 3 }}>
        <ToggleButtonGroup
          value={filterType}
          exclusive
          onChange={(e, value) => value && setFilterType(value)}
          size="small"
          sx={{ mb: 1 }}
        >
          <ToggleButton value="all">All Types</ToggleButton>
          {TEMPLATE_TYPES.map(type => (
            <ToggleButton key={type.value} value={type.value}>
              {type.icon} {type.label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </Box>

      {/* Templates Grid */}
      {filteredTemplates.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <TemplateIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" color="text.secondary">
            No templates found
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
            sx={{ mt: 2 }}
          >
            Create Your First Template
          </Button>
        </Box>
      ) : (
        <Grid container spacing={2}>
          {filteredTemplates.map(renderTemplateCard)}
        </Grid>
      )}

      {renderPreviewDialog()}
      {renderCreateDialog()}
    </Box>
  );
};

export default TemplateSelector;
