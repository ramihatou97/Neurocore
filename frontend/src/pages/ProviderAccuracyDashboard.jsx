/**
 * Provider Accuracy Dashboard
 * Compares AI provider performance, quality, and costs
 */

import { useState, useEffect } from 'react';
import { Card, LoadingSpinner, Badge } from '../components';
import { analyticsAPI } from '../api';
import {
  BarChart, Bar, LineChart, Line, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  Cell, PieChart, Pie
} from 'recharts';

const COLORS = {
  claude: '#8B5CF6',  // Purple
  gpt4o: '#10B981',   // Green
  gemini: '#3B82F6'   // Blue
};

const ProviderAccuracyDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);
  const [overview, setOverview] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [qualityCost, setQualityCost] = useState(null);
  const [errors, setErrors] = useState(null);

  useEffect(() => {
    loadDashboardData();
  }, [days]);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      // Load all provider analytics data
      const [overviewData, comparisonData, qualityCostData, errorsData] = await Promise.all([
        analyticsAPI.getProviderOverview(days),
        analyticsAPI.getProviderComparison(null, days),
        analyticsAPI.getQualityVsCost(days),
        analyticsAPI.getProviderErrors(null, days)
      ]);

      setOverview(overviewData);
      setComparison(comparisonData);
      setQualityCost(qualityCostData);
      setErrors(errorsData);
    } catch (error) {
      console.error('Failed to load provider analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner />
      </div>
    );
  }

  if (!overview || !comparison) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Card>
          <div className="text-center py-12">
            <p className="text-gray-500">No provider analytics data available yet.</p>
            <p className="text-sm text-gray-400 mt-2">
              Provider metrics will appear here once AI tasks are performed.
            </p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">AI Provider Performance</h1>
          <p className="mt-1 text-sm text-gray-500">
            Compare Claude, GPT-4o, and Gemini across quality, cost, and reliability
          </p>
        </div>

        {/* Time Range Selector */}
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {overview.success_rates?.map(provider => (
          <Card key={provider.provider}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 capitalize">{provider.provider}</p>
                <p className="mt-2 text-3xl font-semibold" style={{ color: COLORS[provider.provider] }}>
                  {provider.success_rate_pct}%
                </p>
                <p className="mt-1 text-xs text-gray-500">
                  {provider.successful_requests} / {provider.total_requests} requests
                </p>
              </div>
              <div className="p-3 rounded-full" style={{ backgroundColor: `${COLORS[provider.provider]}20` }}>
                <svg className="w-8 h-8" style={{ color: COLORS[provider.provider] }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Provider Comparison Table */}
      <Card>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Provider Comparison by Task</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Provider
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Task
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Requests
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Success Rate
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Avg Quality
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Avg Cost
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Response Time
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {comparison.comparison?.map((row, idx) => (
                <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Badge color={COLORS[row.provider]} variant="subtle">
                      {row.provider}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {row.task_type.replace(/_/g, ' ')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {row.total_requests}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`text-sm font-medium ${
                      row.success_rate_pct >= 95 ? 'text-green-600' :
                      row.success_rate_pct >= 80 ? 'text-yellow-600' :
                      'text-red-600'
                    }`}>
                      {row.success_rate_pct}%
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {row.avg_quality_score ? (
                      <span>{(row.avg_quality_score * 100).toFixed(1)}%</span>
                    ) : (
                      <span className="text-gray-400">N/A</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    ${row.avg_cost_usd?.toFixed(4) || '0.0000'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {row.avg_response_time_ms ? `${row.avg_response_time_ms}ms` : 'N/A'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Quality vs Cost Scatter Plot */}
      {qualityCost && qualityCost.cost_efficiency?.length > 0 && (
        <Card>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Quality vs Cost Efficiency</h2>
          <p className="text-sm text-gray-500 mb-4">
            Higher quality per dollar = better value. Hover over points for details.
          </p>
          <ResponsiveContainer width="100%" height={400}>
            <ScatterChart margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                type="number"
                dataKey="avg_cost_usd"
                name="Average Cost"
                unit=" USD"
                label={{ value: 'Cost per Request ($)', position: 'bottom' }}
              />
              <YAxis
                type="number"
                dataKey="avg_quality"
                name="Quality Score"
                label={{ value: 'Quality Score', angle: -90, position: 'left' }}
                domain={[0, 1]}
              />
              <Tooltip
                cursor={{ strokeDasharray: '3 3' }}
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="bg-white p-3 border border-gray-200 rounded shadow-lg">
                        <p className="font-semibold capitalize">{data.provider}</p>
                        <p className="text-sm">{data.task_type.replace(/_/g, ' ')}</p>
                        <p className="text-sm">Quality: {(data.avg_quality * 100).toFixed(1)}%</p>
                        <p className="text-sm">Cost: ${data.avg_cost_usd.toFixed(4)}</p>
                        <p className="text-sm font-semibold">
                          Efficiency: {data.quality_per_dollar.toFixed(2)}
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Legend />
              {Object.keys(COLORS).map(provider => {
                const providerData = qualityCost.cost_efficiency.filter(d => d.provider === provider);
                return (
                  <Scatter
                    key={provider}
                    name={provider}
                    data={providerData}
                    fill={COLORS[provider]}
                  />
                );
              })}
            </ScatterChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* Success Rate Comparison */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Success Rate Bar Chart */}
        <Card>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Success Rates</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={overview.success_rates}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="provider" />
              <YAxis label={{ value: 'Success Rate (%)', angle: -90, position: 'left' }} />
              <Tooltip />
              <Bar dataKey="success_rate_pct" name="Success Rate">
                {overview.success_rates?.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[entry.provider]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* Fallback Statistics */}
        {overview.fallback_statistics && (
          <Card>
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Fallback Usage</h2>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Total Requests</span>
                <span className="text-2xl font-bold text-gray-900">
                  {overview.fallback_statistics.total_requests}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Fallback Requests</span>
                <span className="text-2xl font-bold text-orange-600">
                  {overview.fallback_statistics.fallback_requests}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Fallback Rate</span>
                <span className="text-2xl font-bold text-orange-600">
                  {overview.fallback_statistics.fallback_rate_pct}%
                </span>
              </div>

              {overview.fallback_statistics.fallback_breakdown?.length > 0 && (
                <div className="mt-4 pt-4 border-t">
                  <h3 className="text-sm font-medium text-gray-700 mb-2">Fallback Breakdown</h3>
                  <div className="space-y-2">
                    {overview.fallback_statistics.fallback_breakdown.map((fb, idx) => (
                      <div key={idx} className="flex justify-between text-sm">
                        <span className="text-gray-600">
                          {fb.original_provider} → {fb.fallback_provider}
                        </span>
                        <span className="font-medium text-gray-900">{fb.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Card>
        )}
      </div>

      {/* Error Breakdown */}
      {errors && errors.error_breakdown?.length > 0 && (
        <Card>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Error Analysis</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Provider
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Error Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Count
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {errors.error_breakdown.map((error, idx) => (
                  <tr key={idx}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Badge color={COLORS[error.provider]} variant="subtle">
                        {error.provider}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {error.error_type}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {error.count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Cost Efficiency Ranking */}
      {comparison.cost_efficiency?.length > 0 && (
        <Card>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Cost Efficiency Rankings</h2>
          <p className="text-sm text-gray-500 mb-4">
            Quality per dollar (higher is better)
          </p>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart
              data={comparison.cost_efficiency.slice(0, 10)}
              layout="vertical"
              margin={{ left: 100 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" label={{ value: 'Quality per Dollar', position: 'bottom' }} />
              <YAxis
                dataKey="task_type"
                type="category"
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => value.replace(/_/g, ' ')}
              />
              <Tooltip />
              <Bar dataKey="quality_per_dollar" name="Efficiency Score">
                {comparison.cost_efficiency.slice(0, 10).map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[entry.provider]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}
    </div>
  );
};

export default ProviderAccuracyDashboard;
