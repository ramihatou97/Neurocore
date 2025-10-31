/**
 * Advanced Search Page
 * Comprehensive search interface with hybrid ranking, filters, and suggestions
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  Grid,
  Card,
  CardContent,
  CardActionArea,
  Chip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  CircularProgress,
  Alert,
  Autocomplete,
  Tabs,
  Tab,
  Divider,
  Stack,
  IconButton,
  Tooltip,
  Badge
} from '@mui/material';
import {
  Search as SearchIcon,
  FilterList as FilterIcon,
  Clear as ClearIcon,
  TuneRounded as TuneIcon,
  Article as ArticleIcon,
  MenuBook as ChapterIcon,
  Image as ImageIcon,
  ExpandMore as ExpandMoreIcon,
  AutoAwesome as AutoAwesomeIcon,
  Lightbulb as LightbulbIcon,
  ThumbUp as ThumbUpIcon
} from '@mui/icons-material';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002/api/v1';

function Search() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  // Search state
  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [searchType, setSearchType] = useState(searchParams.get('type') || 'hybrid');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [totalResults, setTotalResults] = useState(0);

  // Pagination
  const [page, setPage] = useState(0);
  const [resultsPerPage] = useState(20);

  // Filters
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    contentType: 'all', // all, pdf, chapter, image
    dateRange: 'all', // all, last_month, last_year, custom
    minSimilarity: 0.7,
    status: 'completed'
  });

  // Suggestions & Autocomplete
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const suggestionsTimerRef = useRef(null);

  // Related content
  const [relatedContent, setRelatedContent] = useState([]);
  const [selectedResult, setSelectedResult] = useState(null);

  // Tab state
  const [activeTab, setActiveTab] = useState(0);

  // Stats
  const [searchStats, setSearchStats] = useState(null);

  // ==================== Effects ====================

  // Initialize search from URL params
  useEffect(() => {
    const urlQuery = searchParams.get('q');
    if (urlQuery && urlQuery !== query) {
      setQuery(urlQuery);
      performSearch(urlQuery);
    }
  }, [searchParams]);

  // Load search stats on mount
  useEffect(() => {
    loadSearchStats();
  }, []);

  // ==================== API Calls ====================

  const performSearch = async (searchQuery = query, offset = 0) => {
    if (!searchQuery.trim()) {
      setError('Please enter a search query');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('access_token');

      const response = await axios.post(
        `${API_BASE_URL}/search`,
        {
          query: searchQuery,
          search_type: searchType,
          filters: buildFiltersObject(),
          max_results: resultsPerPage,
          offset: offset
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      setResults(response.data.results);
      setTotalResults(response.data.total);

      // Update URL
      setSearchParams({ q: searchQuery, type: searchType });

    } catch (err) {
      console.error('Search failed:', err);
      setError(err.response?.data?.detail || 'Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const fetchSuggestions = async (partialQuery) => {
    if (!partialQuery.trim() || partialQuery.length < 2) {
      setSuggestions([]);
      return;
    }

    try {
      const token = localStorage.getItem('access_token');

      const response = await axios.get(
        `${API_BASE_URL}/search/suggestions`,
        {
          params: { q: partialQuery, max_suggestions: 10 },
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      setSuggestions(response.data.suggestions || []);
      setShowSuggestions(true);

    } catch (err) {
      console.error('Failed to fetch suggestions:', err);
      setSuggestions([]);
    }
  };

  const fetchRelatedContent = async (contentId, contentType) => {
    try {
      const token = localStorage.getItem('access_token');

      const response = await axios.post(
        `${API_BASE_URL}/search/related`,
        {
          content_id: contentId,
          content_type: contentType,
          max_results: 5
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      setRelatedContent(response.data.related || []);

    } catch (err) {
      console.error('Failed to fetch related content:', err);
      setRelatedContent([]);
    }
  };

  const loadSearchStats = async () => {
    try {
      const token = localStorage.getItem('access_token');

      const response = await axios.get(
        `${API_BASE_URL}/search/stats`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      setSearchStats(response.data);

    } catch (err) {
      console.error('Failed to load search stats:', err);
    }
  };

  // ==================== Handlers ====================

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(0);
    performSearch(query, 0);
  };

  const handleQueryChange = (e) => {
    const newQuery = e.target.value;
    setQuery(newQuery);

    // Debounce suggestions
    if (suggestionsTimerRef.current) {
      clearTimeout(suggestionsTimerRef.current);
    }

    suggestionsTimerRef.current = setTimeout(() => {
      fetchSuggestions(newQuery);
    }, 300);
  };

  const handleSuggestionSelect = (suggestion) => {
    setQuery(suggestion);
    setShowSuggestions(false);
    performSearch(suggestion, 0);
  };

  const handleFilterChange = (filterName, value) => {
    setFilters(prev => ({ ...prev, [filterName]: value }));
  };

  const handlePageChange = (newPage) => {
    setPage(newPage);
    performSearch(query, newPage * resultsPerPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleResultClick = (result) => {
    setSelectedResult(result);

    // Fetch related content
    if (result.type === 'chapter' || result.type === 'pdf') {
      fetchRelatedContent(result.id, result.type);
    }

    // Navigate to detail page
    if (result.type === 'pdf') {
      navigate(`/pdfs/${result.id}`);
    } else if (result.type === 'chapter') {
      navigate(`/chapters/${result.id}`);
    }
  };

  const clearFilters = () => {
    setFilters({
      contentType: 'all',
      dateRange: 'all',
      minSimilarity: 0.7,
      status: 'completed'
    });
  };

  const buildFiltersObject = () => {
    const filtersObj = {};

    if (filters.contentType !== 'all') {
      filtersObj.content_type = filters.contentType;
    }

    if (filters.status) {
      filtersObj.status = filters.status;
    }

    if (filters.minSimilarity !== 0.7) {
      filtersObj.min_similarity = filters.minSimilarity;
    }

    // Date range filtering
    if (filters.dateRange !== 'all') {
      const now = new Date();
      if (filters.dateRange === 'last_month') {
        filtersObj.created_after = new Date(now.setMonth(now.getMonth() - 1)).toISOString();
      } else if (filters.dateRange === 'last_year') {
        filtersObj.created_after = new Date(now.setFullYear(now.getFullYear() - 1)).toISOString();
      }
    }

    return filtersObj;
  };

  // ==================== Result Rendering ====================

  const getResultIcon = (type) => {
    switch (type) {
      case 'pdf':
        return <ArticleIcon color="primary" />;
      case 'chapter':
        return <ChapterIcon color="secondary" />;
      case 'image':
        return <ImageIcon color="success" />;
      default:
        return <ArticleIcon />;
    }
  };

  const getScoreColor = (score) => {
    if (score >= 0.8) return 'success';
    if (score >= 0.6) return 'warning';
    return 'default';
  };

  const renderSearchResult = (result) => (
    <Card
      key={result.id}
      sx={{ mb: 2, '&:hover': { boxShadow: 3 } }}
    >
      <CardActionArea onClick={() => handleResultClick(result)}>
        <CardContent>
          <Box display="flex" alignItems="flex-start" gap={2}>
            {/* Icon */}
            <Box sx={{ pt: 0.5 }}>
              {getResultIcon(result.type)}
            </Box>

            {/* Content */}
            <Box flex={1}>
              <Typography variant="h6" gutterBottom>
                {result.title}
              </Typography>

              {result.authors && (
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  {result.authors}
                </Typography>
              )}

              {result.summary && (
                <Typography variant="body2" sx={{ mt: 1 }}>
                  {result.summary.substring(0, 200)}...
                </Typography>
              )}

              {/* Metadata */}
              <Box display="flex" gap={1} mt={2} flexWrap="wrap">
                <Chip
                  label={result.type.toUpperCase()}
                  size="small"
                  variant="outlined"
                />

                {result.score !== undefined && (
                  <Chip
                    label={`Relevance: ${(result.score * 100).toFixed(1)}%`}
                    size="small"
                    color={getScoreColor(result.score)}
                  />
                )}

                {result.year && (
                  <Chip label={result.year} size="small" variant="outlined" />
                )}

                {result.journal && (
                  <Chip label={result.journal} size="small" variant="outlined" />
                )}
              </Box>
            </Box>
          </Box>
        </CardContent>
      </CardActionArea>
    </Card>
  );

  // ==================== Render ====================

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Header */}
      <Box mb={4}>
        <Typography variant="h4" gutterBottom display="flex" alignItems="center" gap={1}>
          <AutoAwesomeIcon color="primary" />
          Advanced Search
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Powered by hybrid AI search combining keyword matching, semantic understanding, and recency
        </Typography>
      </Box>

      {/* Search Stats Banner */}
      {searchStats && (
        <Paper sx={{ p: 2, mb: 3, bgcolor: 'primary.50' }}>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={4}>
              <Typography variant="body2" color="text.secondary">PDFs Indexed</Typography>
              <Typography variant="h6">
                {searchStats.pdfs.with_embeddings} / {searchStats.pdfs.total}
                <Chip
                  label={`${searchStats.pdfs.coverage}%`}
                  size="small"
                  sx={{ ml: 1 }}
                  color={searchStats.pdfs.coverage > 80 ? 'success' : 'warning'}
                />
              </Typography>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Typography variant="body2" color="text.secondary">Chapters Indexed</Typography>
              <Typography variant="h6">
                {searchStats.chapters.with_embeddings} / {searchStats.chapters.total}
                <Chip
                  label={`${searchStats.chapters.coverage}%`}
                  size="small"
                  sx={{ ml: 1 }}
                  color={searchStats.chapters.coverage > 80 ? 'success' : 'warning'}
                />
              </Typography>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Typography variant="body2" color="text.secondary">Images Indexed</Typography>
              <Typography variant="h6">
                {searchStats.images.with_embeddings} / {searchStats.images.total}
                <Chip
                  label={`${searchStats.images.coverage}%`}
                  size="small"
                  sx={{ ml: 1 }}
                  color={searchStats.images.coverage > 80 ? 'success' : 'warning'}
                />
              </Typography>
            </Grid>
          </Grid>
        </Paper>
      )}

      {/* Search Form */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <form onSubmit={handleSearchSubmit}>
          <Grid container spacing={2} alignItems="center">
            {/* Search Input */}
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Search query"
                placeholder="e.g., brain tumor classification, surgical techniques..."
                value={query}
                onChange={handleQueryChange}
                onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                InputProps={{
                  startAdornment: <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />
                }}
              />

              {/* Suggestions Dropdown */}
              {showSuggestions && suggestions.length > 0 && (
                <Paper
                  sx={{
                    position: 'absolute',
                    zIndex: 1000,
                    mt: 1,
                    maxHeight: 300,
                    overflow: 'auto',
                    width: '400px'
                  }}
                >
                  {suggestions.map((suggestion, idx) => (
                    <Box
                      key={idx}
                      sx={{
                        p: 1.5,
                        cursor: 'pointer',
                        '&:hover': { bgcolor: 'action.hover' },
                        borderBottom: idx < suggestions.length - 1 ? 1 : 0,
                        borderColor: 'divider'
                      }}
                      onClick={() => handleSuggestionSelect(suggestion)}
                    >
                      <Typography variant="body2">
                        <LightbulbIcon sx={{ fontSize: 16, mr: 1, verticalAlign: 'middle' }} />
                        {suggestion}
                      </Typography>
                    </Box>
                  ))}
                </Paper>
              )}
            </Grid>

            {/* Search Type */}
            <Grid item xs={12} md={3}>
              <FormControl fullWidth>
                <InputLabel>Search Type</InputLabel>
                <Select
                  value={searchType}
                  onChange={(e) => setSearchType(e.target.value)}
                  label="Search Type"
                >
                  <MenuItem value="hybrid">
                    <AutoAwesomeIcon sx={{ fontSize: 16, mr: 1 }} />
                    Hybrid (Recommended)
                  </MenuItem>
                  <MenuItem value="semantic">Semantic (AI)</MenuItem>
                  <MenuItem value="keyword">Keyword</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            {/* Search Button */}
            <Grid item xs={12} md={3}>
              <Stack direction="row" spacing={1}>
                <Button
                  fullWidth
                  variant="contained"
                  type="submit"
                  disabled={loading || !query.trim()}
                  startIcon={loading ? <CircularProgress size={20} /> : <SearchIcon />}
                >
                  {loading ? 'Searching...' : 'Search'}
                </Button>
                <Tooltip title="Advanced Filters">
                  <IconButton
                    color={showFilters ? 'primary' : 'default'}
                    onClick={() => setShowFilters(!showFilters)}
                  >
                    <Badge badgeContent={Object.values(filters).filter(v => v !== 'all' && v !== 'completed' && v !== 0.7).length} color="primary">
                      <TuneIcon />
                    </Badge>
                  </IconButton>
                </Tooltip>
              </Stack>
            </Grid>
          </Grid>

          {/* Advanced Filters */}
          {showFilters && (
            <Box mt={3} pt={3} borderTop={1} borderColor="divider">
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={3}>
                  <FormControl fullWidth size="small">
                    <InputLabel>Content Type</InputLabel>
                    <Select
                      value={filters.contentType}
                      onChange={(e) => handleFilterChange('contentType', e.target.value)}
                      label="Content Type"
                    >
                      <MenuItem value="all">All Content</MenuItem>
                      <MenuItem value="pdf">PDFs Only</MenuItem>
                      <MenuItem value="chapter">Chapters Only</MenuItem>
                      <MenuItem value="image">Images Only</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                  <FormControl fullWidth size="small">
                    <InputLabel>Date Range</InputLabel>
                    <Select
                      value={filters.dateRange}
                      onChange={(e) => handleFilterChange('dateRange', e.target.value)}
                      label="Date Range"
                    >
                      <MenuItem value="all">All Time</MenuItem>
                      <MenuItem value="last_month">Last Month</MenuItem>
                      <MenuItem value="last_year">Last Year</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                  <TextField
                    fullWidth
                    size="small"
                    type="number"
                    label="Min Similarity"
                    value={filters.minSimilarity}
                    onChange={(e) => handleFilterChange('minSimilarity', parseFloat(e.target.value))}
                    inputProps={{ min: 0, max: 1, step: 0.1 }}
                    helperText="0.0 to 1.0"
                  />
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                  <Button
                    fullWidth
                    variant="outlined"
                    startIcon={<ClearIcon />}
                    onClick={clearFilters}
                  >
                    Clear Filters
                  </Button>
                </Grid>
              </Grid>
            </Box>
          )}
        </form>
      </Paper>

      {/* Error Display */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Results Section */}
      {results.length > 0 && (
        <Box>
          {/* Results Header */}
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">
              Found {totalResults} results
              {query && ` for "${query}"`}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Page {page + 1} of {Math.ceil(totalResults / resultsPerPage)}
            </Typography>
          </Box>

          {/* Results List */}
          <Box>
            {results.map(result => renderSearchResult(result))}
          </Box>

          {/* Pagination */}
          {totalResults > resultsPerPage && (
            <Box display="flex" justifyContent="center" mt={3}>
              <Stack direction="row" spacing={1}>
                <Button
                  variant="outlined"
                  disabled={page === 0}
                  onClick={() => handlePageChange(page - 1)}
                >
                  Previous
                </Button>
                <Button
                  variant="outlined"
                  disabled={(page + 1) * resultsPerPage >= totalResults}
                  onClick={() => handlePageChange(page + 1)}
                >
                  Next
                </Button>
              </Stack>
            </Box>
          )}
        </Box>
      )}

      {/* No Results */}
      {!loading && results.length === 0 && query && (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <SearchIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            No results found
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Try different keywords or search type, or adjust your filters
          </Typography>
        </Paper>
      )}

      {/* Empty State */}
      {!loading && results.length === 0 && !query && (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <AutoAwesomeIcon sx={{ fontSize: 60, color: 'primary.main', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            Start Your Search
          </Typography>
          <Typography variant="body2" color="text.secondary" mb={2}>
            Use our advanced AI-powered search to find PDFs, chapters, and images
          </Typography>
          <Box mt={3}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              <strong>Try searching for:</strong>
            </Typography>
            <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap" mt={1}>
              <Chip
                label="brain tumor classification"
                onClick={() => { setQuery('brain tumor classification'); performSearch('brain tumor classification'); }}
                clickable
              />
              <Chip
                label="surgical techniques"
                onClick={() => { setQuery('surgical techniques'); performSearch('surgical techniques'); }}
                clickable
              />
              <Chip
                label="spinal cord injury"
                onClick={() => { setQuery('spinal cord injury'); performSearch('spinal cord injury'); }}
                clickable
              />
            </Stack>
          </Box>
        </Paper>
      )}
    </Container>
  );
}

export default Search;
