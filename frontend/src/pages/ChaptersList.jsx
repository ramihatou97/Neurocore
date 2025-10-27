/**
 * Chapters List Page
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Card, LoadingSpinner, Badge, Button } from '../components';
import { chaptersAPI } from '../api';
import { formatRelativeTime } from '../utils/helpers';

const ChaptersList = () => {
  const [chapters, setChapters] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadChapters();
  }, []);

  const loadChapters = async () => {
    try {
      const data = await chaptersAPI.getAll();
      setChapters(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Failed to load chapters:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="flex justify-center py-12"><LoadingSpinner size="lg" /></div>;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Chapters</h1>
        <Link to="/chapters/create">
          <Button variant="primary">Generate New Chapter</Button>
        </Link>
      </div>

      {chapters.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {chapters.map((chapter) => (
            <Link key={chapter.id} to={`/chapters/${chapter.id}`}>
              <Card hover padding="md">
                <div className="mb-3">
                  <Badge status={chapter.generation_status} />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {chapter.title || 'Untitled Chapter'}
                </h3>
                <p className="text-sm text-gray-600 mb-4 line-clamp-2">
                  {chapter.summary || 'No summary available'}
                </p>
                <div className="text-xs text-gray-500">
                  {formatRelativeTime(chapter.created_at)}
                </div>
              </Card>
            </Link>
          ))}
        </div>
      ) : (
        <Card className="text-center py-12">
          <p className="text-gray-600 mb-4">No chapters yet</p>
          <Link to="/chapters/create">
            <Button variant="primary">Generate Your First Chapter</Button>
          </Link>
        </Card>
      )}
    </div>
  );
};

export default ChaptersList;
