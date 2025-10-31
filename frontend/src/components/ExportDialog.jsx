/**
 * ExportDialog Component
 * Dialog for exporting chapters to PDF, DOCX, or HTML
 */

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  Box,
  CircularProgress,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Checkbox,
  FormControlLabel,
  Radio,
  RadioGroup,
  Divider,
  Chip,
  Paper
} from '@mui/material';
import {
  PictureAsPdf as PdfIcon,
  Description as DocxIcon,
  Code as HtmlIcon,
  ExpandMore as ExpandMoreIcon,
  Download as DownloadIcon,
  Visibility as PreviewIcon
} from '@mui/icons-material';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002/api/v1';

function ExportDialog({ open, onClose, chapterId, chapterTitle }) {
  const [exportFormat, setExportFormat] = useState('pdf');
  const [citationStyle, setCitationStyle] = useState('apa');
  const [templateId, setTemplateId] = useState('');
  const [templates, setTemplates] = useState([]);
  const [citationStyles, setCitationStyles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  // Export options
  const [options, setOptions] = useState({
    include_bibliography: true,
    include_toc: false,
    include_images: true,
    page_size: 'A4',
    orientation: 'portrait'
  });

  useEffect(() => {
    if (open) {
      loadTemplates();
      loadCitationStyles();
    }
  }, [open, exportFormat]);

  const loadTemplates = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get(
        `${API_BASE_URL}/export/templates`,
        {
          params: { format: exportFormat, public_only: true },
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      setTemplates(response.data.templates || []);

      // Select default template
      const defaultTemplate = response.data.templates?.find(t => t.is_default);
      if (defaultTemplate) {
        setTemplateId(defaultTemplate.id);
      }
    } catch (err) {
      console.error('Failed to load templates:', err);
    }
  };

  const loadCitationStyles = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get(
        `${API_BASE_URL}/export/citation-styles`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      setCitationStyles(response.data.styles || []);
    } catch (err) {
      console.error('Failed to load citation styles:', err);
    }
  };

  const handleExport = async () => {
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const token = localStorage.getItem('access_token');

      const response = await axios.post(
        `${API_BASE_URL}/export/export`,
        {
          chapter_id: chapterId,
          format: exportFormat,
          template_id: templateId || null,
          citation_style: citationStyle,
          options: options
        },
        {
          headers: {
            Authorization: `Bearer ${token}`
          },
          responseType: 'blob'
        }
      );

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;

      // Generate filename
      const extension = exportFormat;
      const filename = `${chapterTitle.replace(/[^a-z0-9]/gi, '_')}.${extension}`;
      link.setAttribute('download', filename);

      document.body.appendChild(link);
      link.click();
      link.remove();

      setSuccess(true);
      setTimeout(() => {
        onClose();
        setSuccess(false);
      }, 2000);

    } catch (err) {
      console.error('Export failed:', err);
      setError(err.response?.data?.detail || 'Export failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handlePreview = async () => {
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('access_token');

      const response = await axios.get(
        `${API_BASE_URL}/export/export/preview/${chapterId}`,
        {
          params: {
            format: 'html',
            template_id: templateId || undefined,
            citation_style: citationStyle
          },
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      // Open preview in new window
      const previewWindow = window.open('', '_blank');
      previewWindow.document.write(response.data);
      previewWindow.document.close();

    } catch (err) {
      console.error('Preview failed:', err);
      setError('Preview failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getFormatIcon = (format) => {
    switch (format) {
      case 'pdf':
        return <PdfIcon />;
      case 'docx':
        return <DocxIcon />;
      case 'html':
        return <HtmlIcon />;
      default:
        return <DownloadIcon />;
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <DownloadIcon />
          Export Chapter
        </Box>
      </DialogTitle>

      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Export completed successfully! File downloaded.
          </Alert>
        )}

        {/* Format Selection */}
        <Box mb={3}>
          <Typography variant="subtitle2" gutterBottom>
            Export Format
          </Typography>
          <FormControl component="fieldset">
            <RadioGroup
              row
              value={exportFormat}
              onChange={(e) => setExportFormat(e.target.value)}
            >
              <FormControlLabel
                value="pdf"
                control={<Radio />}
                label={
                  <Box display="flex" alignItems="center" gap={1}>
                    <PdfIcon />
                    PDF
                  </Box>
                }
              />
              <FormControlLabel
                value="docx"
                control={<Radio />}
                label={
                  <Box display="flex" alignItems="center" gap={1}>
                    <DocxIcon />
                    DOCX
                  </Box>
                }
              />
              <FormControlLabel
                value="html"
                control={<Radio />}
                label={
                  <Box display="flex" alignItems="center" gap={1}>
                    <HtmlIcon />
                    HTML
                  </Box>
                }
              />
            </RadioGroup>
          </FormControl>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Template Selection */}
        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel>Template</InputLabel>
          <Select
            value={templateId}
            onChange={(e) => setTemplateId(e.target.value)}
            label="Template"
          >
            {templates.map((template) => (
              <MenuItem key={template.id} value={template.id}>
                {template.name}
                {template.is_default && (
                  <Chip label="Default" size="small" sx={{ ml: 1 }} />
                )}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {/* Citation Style Selection */}
        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel>Citation Style</InputLabel>
          <Select
            value={citationStyle}
            onChange={(e) => setCitationStyle(e.target.value)}
            label="Citation Style"
          >
            {citationStyles.map((style) => (
              <MenuItem key={style.id} value={style.name}>
                {style.display_name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {/* Advanced Options */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography>Advanced Options</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Box>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={options.include_bibliography}
                    onChange={(e) =>
                      setOptions({ ...options, include_bibliography: e.target.checked })
                    }
                  />
                }
                label="Include Bibliography"
              />

              <FormControlLabel
                control={
                  <Checkbox
                    checked={options.include_toc}
                    onChange={(e) =>
                      setOptions({ ...options, include_toc: e.target.checked })
                    }
                  />
                }
                label="Include Table of Contents"
              />

              <FormControlLabel
                control={
                  <Checkbox
                    checked={options.include_images}
                    onChange={(e) =>
                      setOptions({ ...options, include_images: e.target.checked })
                    }
                  />
                }
                label="Include Images"
              />

              {exportFormat === 'pdf' && (
                <Box mt={2}>
                  <FormControl fullWidth size="small" sx={{ mb: 1 }}>
                    <InputLabel>Page Size</InputLabel>
                    <Select
                      value={options.page_size}
                      onChange={(e) =>
                        setOptions({ ...options, page_size: e.target.value })
                      }
                      label="Page Size"
                    >
                      <MenuItem value="A4">A4</MenuItem>
                      <MenuItem value="Letter">Letter</MenuItem>
                      <MenuItem value="Legal">Legal</MenuItem>
                    </Select>
                  </FormControl>

                  <FormControl fullWidth size="small">
                    <InputLabel>Orientation</InputLabel>
                    <Select
                      value={options.orientation}
                      onChange={(e) =>
                        setOptions({ ...options, orientation: e.target.value })
                      }
                      label="Orientation"
                    >
                      <MenuItem value="portrait">Portrait</MenuItem>
                      <MenuItem value="landscape">Landscape</MenuItem>
                    </Select>
                  </FormControl>
                </Box>
              )}
            </Box>
          </AccordionDetails>
        </Accordion>

        {/* Preview Info */}
        <Paper sx={{ p: 2, mt: 2, bgcolor: 'info.50' }}>
          <Typography variant="body2" color="text.secondary">
            <strong>Note:</strong> Export may take a few moments depending on chapter length
            and format. You can preview the export before downloading.
          </Typography>
        </Paper>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          onClick={handlePreview}
          disabled={loading}
          startIcon={<PreviewIcon />}
          variant="outlined"
        >
          Preview
        </Button>
        <Button
          onClick={handleExport}
          disabled={loading}
          variant="contained"
          startIcon={loading ? <CircularProgress size={20} /> : getFormatIcon(exportFormat)}
        >
          {loading ? 'Exporting...' : 'Export'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default ExportDialog;
