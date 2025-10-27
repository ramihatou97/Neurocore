/**
 * Dashboard Page
 * Main dashboard with statistics and recent activity
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Card, LoadingSpinner, Badge, Button } from '../components';
import { chaptersAPI, pdfAPI, tasksAPI } from '../api';
import { formatRelativeTime, formatNumber } from '../utils/helpers';

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [recentChapters, setRecentChapters] = useState([]);
  const [recentPDFs, setRecentPDFs] = useState([]);
  const [activeTasks, setActiveTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [chaptersStatsData, pdfsStatsData, tasksStatsData, chaptersData, pdfsData, tasksData] = await Promise.all([
        chaptersAPI.getStats().catch(() => ({ total: 0, generated: 0, in_progress: 0 })),
        pdfAPI.getStats().catch(() => ({ total: 0, processing: 0, completed: 0 })),
        tasksAPI.getStats().catch(() => ({ total: 0, active: 0, completed: 0 })),
        chaptersAPI.getAll({ limit: 5 }).catch(() => []),
        pdfAPI.getAll({ limit: 5 }).catch(() => []),
        tasksAPI.getActive().catch(() => []),
      ]);

      setStats({
        chapters: chaptersStatsData,
        pdfs: pdfsStatsData,
        tasks: tasksStatsData,
      });
      setRecentChapters(Array.isArray(chaptersData) ? chaptersData : []);
      setRecentPDFs(Array.isArray(pdfsData) ? pdfsData : []);
      setActiveTasks(Array.isArray(tasksData) ? tasksData : []);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="xl" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-2">Welcome to your Neurosurgery Knowledge Base</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card className="bg-blue-50">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Total Chapters</p>
              <p className="text-3xl font-bold text-blue-600">{stats?.chapters?.total || 0}</p>
              <p className="text-xs text-gray-500 mt-1">{stats?.chapters?.in_progress || 0} in progress</p>
            </div>
            <div className="text-4xl">📚</div>
          </div>
        </Card>

        <Card className="bg-green-50">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Total PDFs</p>
              <p className="text-3xl font-bold text-green-600">{stats?.pdfs?.total || 0}</p>
              <p className="text-xs text-gray-500 mt-1">{stats?.pdfs?.processing || 0} processing</p>
            </div>
            <div className="text-4xl">📄</div>
          </div>
        </Card>

        <Card className="bg-purple-50">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Active Tasks</p>
              <p className="text-3xl font-bold text-purple-600">{stats?.tasks?.active || 0}</p>
              <p className="text-xs text-gray-500 mt-1">{stats?.tasks?.completed || 0} completed</p>
            </div>
            <div className="text-4xl">⚙️</div>
          </div>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
        <div className="flex flex-wrap gap-4">
          <Link to="/chapters/create">
            <Button variant="primary">Generate New Chapter</Button>
          </Link>
          <Link to="/pdfs/upload">
            <Button variant="secondary">Upload PDF</Button>
          </Link>
          <Link to="/tasks">
            <Button variant="outline">View Tasks</Button>
          </Link>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Chapters */}
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Recent Chapters</h2>
            <Link to="/chapters" className="text-blue-600 hover:text-blue-700 text-sm">
              View all →
            </Link>
          </div>
          <div className="space-y-3">
            {recentChapters.length > 0 ? (
              recentChapters.map((chapter) => (
                <Link
                  key={chapter.id}
                  to={`/chapters/${chapter.id}`}
                  className="block p-3 hover:bg-gray-50 rounded-lg transition"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">{chapter.title || 'Untitled Chapter'}</p>
                      <p className="text-sm text-gray-500 mt-1">
                        {formatRelativeTime(chapter.created_at)}
                      </p>
                    </div>
                    <Badge status={chapter.generation_status} />
                  </div>
                </Link>
              ))
            ) : (
              <p className="text-gray-500 text-center py-4">No chapters yet</p>
            )}
          </div>
        </Card>

        {/* Recent PDFs */}
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Recent PDFs</h2>
            <Link to="/pdfs" className="text-blue-600 hover:text-blue-700 text-sm">
              View all →
            </Link>
          </div>
          <div className="space-y-3">
            {recentPDFs.length > 0 ? (
              recentPDFs.map((pdf) => (
                <Link
                  key={pdf.id}
                  to={`/pdfs/${pdf.id}`}
                  className="block p-3 hover:bg-gray-50 rounded-lg transition"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">{pdf.title || pdf.filename}</p>
                      <p className="text-sm text-gray-500 mt-1">
                        {formatRelativeTime(pdf.uploaded_at)}
                      </p>
                    </div>
                    <Badge status={pdf.extraction_status} />
                  </div>
                </Link>
              ))
            ) : (
              <p className="text-gray-500 text-center py-4">No PDFs yet</p>
            )}
          </div>
        </Card>
      </div>

      {/* Active Tasks */}
      {activeTasks.length > 0 && (
        <Card className="mt-8">
          <h2 className="text-xl font-semibold mb-4">Active Tasks</h2>
          <div className="space-y-3">
            {activeTasks.map((task) => (
              <Link
                key={task.id}
                to={`/tasks/${task.id}`}
                className="block p-3 hover:bg-gray-50 rounded-lg transition"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">{task.task_type?.replace('_', ' ')}</p>
                    <p className="text-sm text-gray-500">{task.message || 'Processing...'}</p>
                  </div>
                  <Badge status={task.status} />
                </div>
              </Link>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};

export default Dashboard;
