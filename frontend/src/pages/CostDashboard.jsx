/**
 * Cost Dashboard - Analytics and tracking for chapter generation costs
 * Phase 22 Part 6B Implementation
 */

import { useState, useEffect } from 'react';
import { Card, LoadingSpinner, Badge } from '../components';
import { chaptersAPI } from '../api';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

const CostDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [chapters, setChapters] = useState([]);
  const [analytics, setAnalytics] = useState(null);

  useEffect(() => {
    loadCostData();
  }, []);

  const loadCostData = async () => {
    try {
      // Fetch all chapters to calculate cost analytics
      const data = await chaptersAPI.list();
      setChapters(data);

      // Calculate analytics
      const analytics = calculateAnalytics(data);
      setAnalytics(analytics);
    } catch (error) {
      console.error('Failed to load cost data:', error);
    } finally {
      setLoading(false);
    }
  };

  const calculateAnalytics = (chapters) => {
    // Filter chapters with cost data
    const chaptersWithCost = chapters.filter(c => c.generation_cost_usd);

    if (chaptersWithCost.length === 0) {
      return null;
    }

    // Total spending
    const totalSpent = chaptersWithCost.reduce((sum, c) => sum + c.generation_cost_usd, 0);

    // Average cost
    const avgCost = totalSpent / chaptersWithCost.length;

    // Cost by chapter type
    const costByType = {};
    chaptersWithCost.forEach(c => {
      const type = c.chapter_type || 'unknown';
      if (!costByType[type]) {
        costByType[type] = { total: 0, count: 0, chapters: [] };
      }
      costByType[type].total += c.generation_cost_usd;
      costByType[type].count += 1;
      costByType[type].chapters.push(c);
    });

    // Most expensive chapters
    const sortedByCost = [...chaptersWithCost].sort((a, b) => b.generation_cost_usd - a.generation_cost_usd);
    const mostExpensive = sortedByCost.slice(0, 5);

    // Monthly spending (group by month)
    const monthlyData = {};
    chaptersWithCost.forEach(c => {
      const date = new Date(c.created_at);
      const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      if (!monthlyData[monthKey]) {
        monthlyData[monthKey] = { month: monthKey, cost: 0, count: 0 };
      }
      monthlyData[monthKey].cost += c.generation_cost_usd;
      monthlyData[monthKey].count += 1;
    });

    const monthlySpending = Object.values(monthlyData).sort((a, b) => a.month.localeCompare(b.month));

    // Cost distribution (chart data)
    const typeChartData = Object.entries(costByType).map(([type, data]) => ({
      type: type.replace(/_/g, ' '),
      avgCost: data.total / data.count,
      totalCost: data.total,
      count: data.count
    }));

    return {
      totalSpent,
      avgCost,
      totalChapters: chaptersWithCost.length,
      costByType,
      mostExpensive,
      monthlySpending,
      typeChartData
    };
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 4
    }).format(value);
  };

  const formatMonth = (monthKey) => {
    const [year, month] = monthKey.split('-');
    const date = new Date(year, parseInt(month) - 1);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Card>
          <div className="text-center py-12">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">No Cost Data Available</h2>
            <p className="text-gray-600">
              Generate some chapters to see cost analytics and tracking.
            </p>
          </div>
        </Card>
      </div>
    );
  }

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D'];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Cost Analytics Dashboard</h1>
        <p className="text-gray-600">
          Track and analyze chapter generation costs across your knowledge base
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {/* Total Spending */}
        <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 mb-1">Total Spending</p>
              <p className="text-3xl font-bold text-blue-900">
                {formatCurrency(analytics.totalSpent)}
              </p>
            </div>
            <div className="text-4xl text-blue-500">💰</div>
          </div>
          <div className="mt-4 text-sm text-gray-600">
            Across {analytics.totalChapters} chapters
          </div>
        </Card>

        {/* Average Cost */}
        <Card className="bg-gradient-to-r from-green-50 to-emerald-50 border-green-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 mb-1">Average Cost</p>
              <p className="text-3xl font-bold text-green-900">
                {formatCurrency(analytics.avgCost)}
              </p>
            </div>
            <div className="text-4xl text-green-500">📊</div>
          </div>
          <div className="mt-4 text-sm text-gray-600">
            Per chapter generation
          </div>
        </Card>

        {/* Most Expensive */}
        <Card className="bg-gradient-to-r from-purple-50 to-pink-50 border-purple-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 mb-1">Highest Cost</p>
              <p className="text-3xl font-bold text-purple-900">
                {formatCurrency(analytics.mostExpensive[0]?.generation_cost_usd || 0)}
              </p>
            </div>
            <div className="text-4xl text-purple-500">🏆</div>
          </div>
          <div className="mt-4 text-sm text-gray-600">
            {analytics.mostExpensive[0]?.title?.substring(0, 30)}...
          </div>
        </Card>
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Monthly Spending Trend */}
        <Card>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Monthly Spending Trend</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={analytics.monthlySpending}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="month"
                tickFormatter={formatMonth}
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis tickFormatter={(value) => `$${value.toFixed(2)}`} />
              <Tooltip
                formatter={(value) => formatCurrency(value)}
                labelFormatter={formatMonth}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="cost"
                stroke="#8884d8"
                strokeWidth={2}
                name="Total Cost"
                dot={{ r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
          <div className="mt-4 text-sm text-gray-600 text-center">
            Total chapters generated: {analytics.monthlySpending.reduce((sum, m) => sum + m.count, 0)}
          </div>
        </Card>

        {/* Cost by Chapter Type */}
        <Card>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Average Cost by Chapter Type</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={analytics.typeChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="type"
                angle={-45}
                textAnchor="end"
                height={100}
              />
              <YAxis tickFormatter={(value) => `$${value.toFixed(2)}`} />
              <Tooltip
                formatter={(value) => formatCurrency(value)}
              />
              <Legend />
              <Bar dataKey="avgCost" fill="#82ca9d" name="Average Cost">
                {analytics.typeChartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Total Cost Distribution by Type */}
        <Card>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Total Spending by Type</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={analytics.typeChartData}
                dataKey="totalCost"
                nameKey="type"
                cx="50%"
                cy="50%"
                outerRadius={100}
                label={(entry) => `${entry.type}: ${formatCurrency(entry.totalCost)}`}
              >
                {analytics.typeChartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => formatCurrency(value)} />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        {/* Chapter Count by Type */}
        <Card>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Chapters by Type</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={analytics.typeChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="type"
                angle={-45}
                textAnchor="end"
                height={100}
              />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="count" fill="#8884d8" name="Chapter Count">
                {analytics.typeChartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Most Expensive Chapters Table */}
      <Card>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Most Expensive Chapters</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Rank
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Title
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Sections
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Words
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Cost
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Cost/Word
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {analytics.mostExpensive.map((chapter, index) => (
                <tr key={chapter.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      {index === 0 && <span className="text-2xl mr-2">🥇</span>}
                      {index === 1 && <span className="text-2xl mr-2">🥈</span>}
                      {index === 2 && <span className="text-2xl mr-2">🥉</span>}
                      <span className="text-sm font-medium text-gray-900">#{index + 1}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">{chapter.title}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Badge className="bg-blue-100 text-blue-800">
                      {chapter.chapter_type?.replace(/_/g, ' ') || 'N/A'}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {chapter.total_sections || 0}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {chapter.total_words || chapter.word_count || 0}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm font-semibold text-green-600">
                      {formatCurrency(chapter.generation_cost_usd)}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatCurrency(
                      chapter.generation_cost_usd / (chapter.total_words || chapter.word_count || 1)
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Cost Breakdown by Type Table */}
      <Card className="mt-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Cost Summary by Chapter Type</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Chapter Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Count
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Total Cost
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Average Cost
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  % of Total
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {analytics.typeChartData.map((item, index) => (
                <tr key={index} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm font-medium text-gray-900 capitalize">{item.type}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {item.count}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm font-semibold text-blue-600">
                      {formatCurrency(item.totalCost)}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm font-semibold text-green-600">
                      {formatCurrency(item.avgCost)}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {((item.totalCost / analytics.totalSpent) * 100).toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};

export default CostDashboard;
