/**
 * Tasks List Page
 */

import { useState, useEffect } from 'react';
import { Card, LoadingSpinner, Badge, ProgressBar } from '../components';
import { tasksAPI } from '../api';
import { formatRelativeTime } from '../utils/helpers';

const TasksList = () => {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTasks();
    const interval = setInterval(loadTasks, 5000); // Refresh every 5s
    return () => clearInterval(interval);
  }, []);

  const loadTasks = async () => {
    try {
      const data = await tasksAPI.getAll();
      setTasks(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Failed to load tasks:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="flex justify-center py-12"><LoadingSpinner size="lg" /></div>;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Background Tasks</h1>

      {tasks.length > 0 ? (
        <div className="space-y-4">
          {tasks.map((task) => (
            <Card key={task.id}>
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-semibold text-gray-900">
                      {task.task_type?.replace('_', ' ').toUpperCase()}
                    </h3>
                    <Badge status={task.status} />
                  </div>
                  <p className="text-sm text-gray-600 mb-2">{task.message || 'Processing...'}</p>
                  <div className="text-xs text-gray-500">
                    Started {formatRelativeTime(task.created_at)}
                  </div>
                </div>
              </div>

              {(task.status === 'running' || task.status === 'processing') && task.progress != null && (
                <div>
                  <div className="flex items-center justify-between mb-2 text-sm">
                    <span className="text-gray-600">
                      Step {task.current_step || 0}/{task.total_steps || 0}
                    </span>
                    <span className="text-gray-600">{task.progress}%</span>
                  </div>
                  <ProgressBar progress={task.progress} showPercentage={false} />
                </div>
              )}
            </Card>
          ))}
        </div>
      ) : (
        <Card className="text-center py-12">
          <p className="text-gray-600">No tasks</p>
        </Card>
      )}
    </div>
  );
};

export default TasksList;
