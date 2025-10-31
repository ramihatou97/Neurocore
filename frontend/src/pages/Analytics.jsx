/**
 * Analytics Dashboard Page
 * Comprehensive analytics and metrics dashboard for admins
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Grid,
  Typography,
  Paper,
  Tabs,
  Tab,
  CircularProgress,
  Alert,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  People as PeopleIcon,
  Description as ChapterIcon,
  Search as SearchIcon,
  GetApp as ExportIcon,
  Computer as SystemIcon,
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  TrendingFlat as TrendingFlatIcon
} from '@mui/icons-material';
import axios from 'axios';
import MetricCard from '../components/MetricCard';
import ActivityChart from '../components/ActivityChart';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002/api/v1';

function TabPanel({ children, value, index, ...other }) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`analytics-tabpanel-${index}`}
      aria-labelledby={`analytics-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

function Analytics() {
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  // Dashboard data
  const [dashboardData, setDashboardData] = useState(null);
  const [keyMetrics, setKeyMetrics] = useState({});
  const [trendingMetrics, setTrendingMetrics] = useState({ trending_up: [], trending_down: [] });
  const [systemHealth, setSystemHealth] = useState({});

  // Analytics data by category
  const [userAnalytics, setUserAnalytics] = useState(null);
  const [chapterAnalytics, setChapterAnalytics] = useState(null);
  const [searchAnalytics, setSearchAnalytics] = useState(null);
  const [exportAnalytics, setExportAnalytics] = useState(null);

  // Time range for charts
  const [timeRange, setTimeRange] = useState('7d');

  useEffect(() => {
    loadDashboard();
  }, []);

  useEffect(() => {
    if (activeTab === 1) loadUserAnalytics();
    else if (activeTab === 2) loadChapterAnalytics();
    else if (activeTab === 3) loadSearchAnalytics();
    else if (activeTab === 4) loadExportAnalytics();
  }, [activeTab, timeRange]);

  const loadDashboard = async () => {
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get(
        `${API_BASE_URL}/analytics/dashboard`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const { dashboard } = response.data;

      setDashboardData(dashboard);
      setKeyMetrics(dashboard.key_metrics?.key_metrics || {});
      setTrendingMetrics(dashboard.trending || { trending_up: [], trending_down: [] });
      setSystemHealth(dashboard.system_health || {});

    } catch (err) {
      console.error('Failed to load dashboard:', err);
      setError(err.response?.data?.detail || 'Failed to load analytics dashboard');
    } finally {
      setLoading(false);
    }
  };

  const refreshMetrics = async () => {
    setRefreshing(true);
    try {
      const token = localStorage.getItem('access_token');
      await axios.post(
        `${API_BASE_URL}/analytics/metrics/update`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      await loadDashboard();
    } catch (err) {
      console.error('Failed to refresh metrics:', err);
    } finally {
      setRefreshing(false);
    }
  };

  const loadUserAnalytics = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get(
        `${API_BASE_URL}/analytics/users`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setUserAnalytics(response.data.user_analytics);
    } catch (err) {
      console.error('Failed to load user analytics:', err);
    }
  };

  const loadChapterAnalytics = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get(
        `${API_BASE_URL}/analytics/chapters`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setChapterAnalytics(response.data.chapter_analytics);
    } catch (err) {
      console.error('Failed to load chapter analytics:', err);
    }
  };

  const loadSearchAnalytics = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get(
        `${API_BASE_URL}/analytics/search`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setSearchAnalytics(response.data.search_analytics);
    } catch (err) {
      console.error('Failed to load search analytics:', err);
    }
  };

  const loadExportAnalytics = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get(
        `${API_BASE_URL}/analytics/exports`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setExportAnalytics(response.data.export_analytics);
    } catch (err) {
      console.error('Failed to load export analytics:', err);
    }
  };

  const getTrendIcon = (trend) => {
    switch (trend) {
      case 'up':
        return <TrendingUpIcon color="success" />;
      case 'down':
        return <TrendingDownIcon color="error" />;
      case 'stable':
        return <TrendingFlatIcon color="info" />;
      default:
        return <TrendingFlatIcon color="disabled" />;
    }
  };

  const formatNumber = (num) => {
    if (num === undefined || num === null) return '0';
    return new Intl.NumberFormat().format(num);
  };

  const formatPercentage = (num) => {
    if (num === undefined || num === null) return '0%';
    return `${num >= 0 ? '+' : ''}${num.toFixed(1)}%`;
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="80vh">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box display="flex" alignItems="center" gap={2}>
          <DashboardIcon fontSize="large" color="primary" />
          <Typography variant="h4" component="h1">
            Analytics Dashboard
          </Typography>
        </Box>
        <Box display="flex" gap={2} alignItems="center">
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Time Range</InputLabel>
            <Select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              label="Time Range"
            >
              <MenuItem value="24h">Last 24 Hours</MenuItem>
              <MenuItem value="7d">Last 7 Days</MenuItem>
              <MenuItem value="30d">Last 30 Days</MenuItem>
              <MenuItem value="90d">Last 90 Days</MenuItem>
            </Select>
          </FormControl>
          <Tooltip title="Refresh metrics">
            <IconButton onClick={refreshMetrics} disabled={refreshing}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={(e, newValue) => setActiveTab(newValue)}
          variant="fullWidth"
          indicatorColor="primary"
          textColor="primary"
        >
          <Tab icon={<DashboardIcon />} label="Overview" />
          <Tab icon={<PeopleIcon />} label="Users" />
          <Tab icon={<ChapterIcon />} label="Chapters" />
          <Tab icon={<SearchIcon />} label="Search" />
          <Tab icon={<ExportIcon />} label="Exports" />
          <Tab icon={<SystemIcon />} label="System" />
        </Tabs>
      </Paper>

      {/* Overview Tab */}
      <TabPanel value={activeTab} index={0}>
        {/* Key Metrics */}
        <Typography variant="h6" gutterBottom>
          Key Metrics
        </Typography>
        <Grid container spacing={3} sx={{ mb: 4 }}>
          {Object.entries(keyMetrics).map(([key, metric]) => (
            <Grid item xs={12} sm={6} md={4} key={key}>
              <MetricCard
                title={metric.metric_name}
                value={formatNumber(metric.metric_value)}
                unit={metric.metric_unit}
                trend={metric.trend}
                changePercentage={metric.change_percentage}
                icon={getTrendIcon(metric.trend)}
              />
            </Grid>
          ))}
        </Grid>

        <Divider sx={{ my: 4 }} />

        {/* Trending Metrics */}
        <Typography variant="h6" gutterBottom>
          Trending Metrics
        </Typography>
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" gap={1} mb={2}>
                  <TrendingUpIcon color="success" />
                  <Typography variant="h6">Trending Up</Typography>
                </Box>
                {trendingMetrics.trending_up?.length > 0 ? (
                  trendingMetrics.trending_up.map((metric, index) => (
                    <Box key={index} sx={{ mb: 2 }}>
                      <Box display="flex" justifyContent="space-between" alignItems="center">
                        <Typography variant="body1">{metric.metric_name}</Typography>
                        <Chip
                          label={formatPercentage(metric.change_percentage)}
                          color="success"
                          size="small"
                        />
                      </Box>
                      <Typography variant="body2" color="text.secondary">
                        {formatNumber(metric.metric_value)}
                      </Typography>
                    </Box>
                  ))
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No trending metrics
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" gap={1} mb={2}>
                  <TrendingDownIcon color="error" />
                  <Typography variant="h6">Trending Down</Typography>
                </Box>
                {trendingMetrics.trending_down?.length > 0 ? (
                  trendingMetrics.trending_down.map((metric, index) => (
                    <Box key={index} sx={{ mb: 2 }}>
                      <Box display="flex" justifyContent="space-between" alignItems="center">
                        <Typography variant="body1">{metric.metric_name}</Typography>
                        <Chip
                          label={formatPercentage(metric.change_percentage)}
                          color="error"
                          size="small"
                        />
                      </Box>
                      <Typography variant="body2" color="text.secondary">
                        {formatNumber(metric.metric_value)}
                      </Typography>
                    </Box>
                  ))
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No trending metrics
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Divider sx={{ my: 4 }} />

        {/* System Health */}
        <Typography variant="h6" gutterBottom>
          System Health
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} sm={6} md={3}>
            <MetricCard
              title="Total Events"
              value={formatNumber(systemHealth.total_events)}
              unit="events"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <MetricCard
              title="Success Rate"
              value={systemHealth.success_rate?.toFixed(1) || '0'}
              unit="%"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <MetricCard
              title="Avg Response Time"
              value={systemHealth.avg_response_time_ms?.toFixed(0) || '0'}
              unit="ms"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <MetricCard
              title="Error Count"
              value={formatNumber(systemHealth.error_count)}
              unit="errors"
            />
          </Grid>
        </Grid>
      </TabPanel>

      {/* Users Tab */}
      <TabPanel value={activeTab} index={1}>
        <Grid container spacing={3}>
          <Grid item xs={12} sm={6} md={4}>
            <MetricCard
              title="Total Users"
              value={formatNumber(userAnalytics?.total_users?.metric_value)}
              unit="users"
              trend={userAnalytics?.total_users?.trend}
              changePercentage={userAnalytics?.total_users?.change_percentage}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={4}>
            <MetricCard
              title="Active Users (24h)"
              value={formatNumber(userAnalytics?.active_users_24h?.metric_value)}
              unit="users"
              trend={userAnalytics?.active_users_24h?.trend}
              changePercentage={userAnalytics?.active_users_24h?.change_percentage}
            />
          </Grid>
        </Grid>

        <Box mt={4}>
          <Typography variant="h6" gutterBottom>
            User Activity Timeline
          </Typography>
          {userAnalytics?.activity_timeline && (
            <ActivityChart
              data={userAnalytics.activity_timeline}
              title="User Activity"
              dataKey="event_count"
              color="#1976d2"
            />
          )}
        </Box>
      </TabPanel>

      {/* Chapters Tab */}
      <TabPanel value={activeTab} index={2}>
        <Grid container spacing={3}>
          <Grid item xs={12} sm={6} md={4}>
            <MetricCard
              title="Total Chapters"
              value={formatNumber(chapterAnalytics?.total_chapters?.metric_value)}
              unit="chapters"
              trend={chapterAnalytics?.total_chapters?.trend}
              changePercentage={chapterAnalytics?.total_chapters?.change_percentage}
            />
          </Grid>
        </Grid>

        <Box mt={4}>
          <Typography variant="h6" gutterBottom>
            Chapter Creation Timeline
          </Typography>
          {chapterAnalytics?.creation_timeline && (
            <ActivityChart
              data={chapterAnalytics.creation_timeline}
              title="Chapters Created"
              dataKey="event_count"
              color="#2e7d32"
            />
          )}
        </Box>

        <Box mt={4}>
          <Typography variant="h6" gutterBottom>
            Popular Chapters
          </Typography>
          <Card>
            <CardContent>
              {chapterAnalytics?.popular_chapters?.length > 0 ? (
                chapterAnalytics.popular_chapters.map((item, index) => (
                  <Box key={index} sx={{ mb: 2, pb: 2, borderBottom: '1px solid #e0e0e0' }}>
                    <Typography variant="body1">Chapter ID: {item.resource_id}</Typography>
                    <Box display="flex" gap={2} mt={1}>
                      <Chip label={`${formatNumber(item.view_count)} views`} size="small" />
                      <Chip label={`${formatNumber(item.unique_viewers)} viewers`} size="small" color="primary" />
                    </Box>
                  </Box>
                ))
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No data available
                </Typography>
              )}
            </CardContent>
          </Card>
        </Box>
      </TabPanel>

      {/* Search Tab */}
      <TabPanel value={activeTab} index={3}>
        <Grid container spacing={3}>
          <Grid item xs={12} sm={6} md={4}>
            <MetricCard
              title="Total Searches (7d)"
              value={formatNumber(searchAnalytics?.total_searches_7d?.metric_value)}
              unit="searches"
              trend={searchAnalytics?.total_searches_7d?.trend}
              changePercentage={searchAnalytics?.total_searches_7d?.change_percentage}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={4}>
            <MetricCard
              title="Search Count"
              value={formatNumber(searchAnalytics?.search_count)}
              unit="searches"
            />
          </Grid>
        </Grid>

        <Box mt={4}>
          <Typography variant="h6" gutterBottom>
            Search Activity Timeline
          </Typography>
          {searchAnalytics?.timeline && (
            <ActivityChart
              data={searchAnalytics.timeline}
              title="Searches"
              dataKey="event_count"
              color="#ed6c02"
            />
          )}
        </Box>
      </TabPanel>

      {/* Exports Tab */}
      <TabPanel value={activeTab} index={4}>
        <Grid container spacing={3}>
          <Grid item xs={12} sm={6} md={4}>
            <MetricCard
              title="Total Exports (30d)"
              value={formatNumber(exportAnalytics?.total_exports_30d?.metric_value)}
              unit="exports"
              trend={exportAnalytics?.total_exports_30d?.trend}
              changePercentage={exportAnalytics?.total_exports_30d?.change_percentage}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={4}>
            <MetricCard
              title="Export Count"
              value={formatNumber(exportAnalytics?.export_count)}
              unit="exports"
            />
          </Grid>
        </Grid>

        <Box mt={4}>
          <Typography variant="h6" gutterBottom>
            Export Activity Timeline
          </Typography>
          {exportAnalytics?.timeline && (
            <ActivityChart
              data={exportAnalytics.timeline}
              title="Exports"
              dataKey="event_count"
              color="#9c27b0"
            />
          )}
        </Box>
      </TabPanel>

      {/* System Tab */}
      <TabPanel value={activeTab} index={5}>
        <Typography variant="h6" gutterBottom>
          System Performance Metrics
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} sm={6} md={3}>
            <MetricCard
              title="Total Events"
              value={formatNumber(systemHealth.total_events)}
              unit="events"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <MetricCard
              title="Success Rate"
              value={systemHealth.success_rate?.toFixed(1) || '0'}
              unit="%"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <MetricCard
              title="Avg Response"
              value={systemHealth.avg_response_time_ms?.toFixed(0) || '0'}
              unit="ms"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <MetricCard
              title="P95 Response"
              value={systemHealth.p95_response_time_ms?.toFixed(0) || '0'}
              unit="ms"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <MetricCard
              title="P99 Response"
              value={systemHealth.p99_response_time_ms?.toFixed(0) || '0'}
              unit="ms"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <MetricCard
              title="Active Users"
              value={formatNumber(systemHealth.active_users)}
              unit="users"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <MetricCard
              title="Total Sessions"
              value={formatNumber(systemHealth.total_sessions)}
              unit="sessions"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <MetricCard
              title="Error Count"
              value={formatNumber(systemHealth.error_count)}
              unit="errors"
            />
          </Grid>
        </Grid>
      </TabPanel>
    </Container>
  );
}

export default Analytics;
