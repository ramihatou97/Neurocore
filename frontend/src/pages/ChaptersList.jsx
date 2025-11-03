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
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deletingChapterId, setDeletingChapterId] = useState(null);
  const [deleting, setDeleting] = useState(false);

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

  const handleDeleteClick = (e, chapterId) => {
    e.preventDefault();
    e.stopPropagation();
    setDeletingChapterId(chapterId);
    setShowDeleteConfirm(true);
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await chaptersAPI.delete(deletingChapterId);
      setShowDeleteConfirm(false);
      loadChapters(); // Refresh the list
    } catch (error) {
      console.error('Failed to delete chapter:', error);
      alert('Failed to delete chapter: ' + (error.response?.data?.detail || error.message));
    } finally {
      setDeleting(false);
      setDeletingChapterId(null);
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
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>{formatRelativeTime(chapter.created_at)}</span>
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={(e) => handleDeleteClick(e, chapter.id)}
                    className="text-xs px-2 py-1"
                  >
                    🗑️
                  </Button>
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

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && deletingChapterId && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <Card className="max-w-md w-full">
            <h2 className="text-xl font-bold text-gray-900 mb-3">Delete Chapter?</h2>
            <p className="text-gray-700 mb-4">
              Are you sure you want to delete this chapter? This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <Button
                variant="outline"
                onClick={() => {
                  setShowDeleteConfirm(false);
                  setDeletingChapterId(null);
                }}
                disabled={deleting}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                onClick={handleDelete}
                disabled={deleting}
              >
                {deleting ? 'Deleting...' : 'Delete Chapter'}
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};

export default ChaptersList;
