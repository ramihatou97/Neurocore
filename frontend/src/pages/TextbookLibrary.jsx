/**
 * TextbookLibrary Page
 * Browse uploaded textbooks with chapter-level details and embedding status
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { textbookAPI } from '../api';
import Card from '../components/Card';
import Button from '../components/Button';
import Badge from '../components/Badge';
import LoadingSpinner from '../components/LoadingSpinner';
import Alert from '../components/Alert';
import BookTitleEditor from '../components/BookTitleEditor';

const TextbookLibrary = () => {
  const [books, setBooks] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedBooks, setExpandedBooks] = useState({});
  const navigate = useNavigate();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [booksData, statsData] = await Promise.all([
        textbookAPI.listBooks(),
        textbookAPI.getLibraryStats()
      ]);
      setBooks(booksData);
      setStats(statsData);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load library');
    } finally {
      setLoading(false);
    }
  };

  const toggleBookExpansion = (bookId) => {
    setExpandedBooks(prev => ({
      ...prev,
      [bookId]: !prev[bookId]
    }));
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <LoadingSpinner size="xl" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Textbook Library
            </h1>
            <p className="text-gray-600">
              Browse your neurosurgery textbook collection
            </p>
          </div>
          <Button
            variant="primary"
            onClick={() => navigate('/textbooks/upload')}
          >
            📚 Upload Textbooks
          </Button>
        </div>

        {/* Error Alert */}
        {error && (
          <Alert
            type="error"
            message={error}
            onClose={() => setError('')}
            className="mb-6"
          />
        )}

        {/* Statistics Overview */}
        {stats && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <Card className="text-center">
              <div className="text-3xl mb-2">📚</div>
              <div className="text-2xl font-bold text-gray-900">
                {stats.total_books}
              </div>
              <div className="text-sm text-gray-600">Books</div>
            </Card>

            <Card className="text-center">
              <div className="text-3xl mb-2">📄</div>
              <div className="text-2xl font-bold text-gray-900">
                {stats.total_chapters}
              </div>
              <div className="text-sm text-gray-600">Chapters</div>
            </Card>

            <Card className="text-center">
              <div className="text-3xl mb-2">🔹</div>
              <div className="text-2xl font-bold text-gray-900">
                {stats.embedding_progress_percent.toFixed(0)}%
              </div>
              <div className="text-sm text-gray-600">Indexed</div>
            </Card>

            <Card className="text-center">
              <div className="text-3xl mb-2">💾</div>
              <div className="text-2xl font-bold text-gray-900">
                {stats.storage_gb.toFixed(2)} GB
              </div>
              <div className="text-sm text-gray-600">Storage</div>
            </Card>
          </div>
        )}

        {/* Books List */}
        {books.length === 0 ? (
          <Card className="text-center py-12">
            <div className="text-6xl mb-4">📚</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              No textbooks yet
            </h3>
            <p className="text-gray-600 mb-6">
              Upload your first textbook to get started with semantic search
            </p>
            <Button
              variant="primary"
              onClick={() => navigate('/textbooks/upload')}
            >
              Upload Textbook
            </Button>
          </Card>
        ) : (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Books ({books.length})
            </h2>

            {books.map(book => (
              <BookCard
                key={book.id}
                book={book}
                expanded={expandedBooks[book.id]}
                onToggle={() => toggleBookExpansion(book.id)}
                formatDate={formatDate}
                formatFileSize={formatFileSize}
                onBookDeleted={loadData}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// Book Card Component
const BookCard = ({ book, expanded, onToggle, formatDate, formatFileSize, onBookDeleted }) => {
  const navigate = useNavigate();
  const [currentBook, setCurrentBook] = useState(book);
  const [chapters, setChapters] = useState([]);
  const [loadingChapters, setLoadingChapters] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Update local book state when prop changes
  useEffect(() => {
    setCurrentBook(book);
  }, [book]);

  useEffect(() => {
    if (expanded && chapters.length === 0) {
      loadChapters();
    }
  }, [expanded]);

  const loadChapters = async () => {
    try {
      setLoadingChapters(true);
      const chaptersData = await textbookAPI.getBookChapters(currentBook.id);
      setChapters(chaptersData);
    } catch (err) {
      console.error('Failed to load chapters:', err);
    } finally {
      setLoadingChapters(false);
    }
  };

  const handleTitleUpdated = (updatedBook) => {
    // Update local state with new book data
    setCurrentBook(updatedBook);
    // Also notify parent to refresh if needed
    if (onBookDeleted) {
      // Reuse the callback name even though it's for refresh
      onBookDeleted();
    }
  };

  const handleDelete = async () => {
    try {
      setDeleting(true);
      await textbookAPI.deleteBook(currentBook.id);
      onBookDeleted();
    } catch (err) {
      console.error('Failed to delete book:', err);
      alert('Failed to delete book: ' + (err.response?.data?.detail || err.message));
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  const getStatusBadge = (status) => {
    const statusMap = {
      completed: { variant: 'success', text: 'Complete' },
      processing: { variant: 'primary', text: 'Processing' },
      failed: { variant: 'danger', text: 'Failed' },
      uploaded: { variant: 'default', text: 'Uploaded' }
    };
    const config = statusMap[status] || { variant: 'default', text: status };
    return <Badge variant={config.variant}>{config.text}</Badge>;
  };

  return (
    <>
      <Card className="hover:shadow-md transition-shadow">
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <button
                onClick={onToggle}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <span className="text-xl">{expanded ? '▼' : '▶'}</span>
              </button>
              <h3 className="text-lg font-semibold text-gray-900">
                {currentBook.title}
              </h3>
              {getStatusBadge(currentBook.processing_status)}
            </div>

            <div className="ml-8 text-sm text-gray-700 space-y-1">
              {currentBook.authors && (
                <p className="text-gray-900">Authors: {Array.isArray(currentBook.authors) ? currentBook.authors.join(', ') : currentBook.authors}</p>
              )}
              <p className="text-gray-900">
                {currentBook.total_pages} pages • {currentBook.total_chapters} chapters
                {currentBook.file_size_bytes && ` • ${formatFileSize(currentBook.file_size_bytes)}`}
              </p>
              <p className="text-gray-900">Uploaded: {formatDate(currentBook.uploaded_at)}</p>
            </div>
          </div>

          <div className="flex gap-2">
            <BookTitleEditor
              book={currentBook}
              onTitleUpdated={handleTitleUpdated}
            />
            <Button
              variant="danger"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                setShowDeleteConfirm(true);
              }}
              disabled={deleting}
            >
              🗑️ Delete
            </Button>
          </div>
        </div>

      {/* Chapters List */}
      {expanded && (
        <div className="ml-8 mt-4 border-t pt-4">
          {loadingChapters ? (
            <div className="text-center py-4">
              <LoadingSpinner size="sm" />
            </div>
          ) : chapters.length > 0 ? (
            <div className="space-y-2">
              <h4 className="font-medium text-gray-900 mb-3">Chapters:</h4>
              {chapters.map(chapter => (
                <div
                  key={chapter.id}
                  className="bg-gray-50 rounded-lg p-3 text-sm hover:bg-gray-100 transition-colors cursor-pointer"
                  onClick={() => navigate(`/textbooks/chapters/${chapter.id}`)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        {chapter.chapter_number && (
                          <span className="font-medium text-gray-900">
                            Ch {chapter.chapter_number}:
                          </span>
                        )}
                        <span className="text-gray-900 font-medium">{chapter.chapter_title}</span>
                      </div>
                      <div className="text-xs text-gray-700 space-y-1">
                        <p className="text-gray-900">
                          Pages {chapter.start_page}-{chapter.end_page} • {chapter.word_count} words
                        </p>
                        {chapter.detection_method && (
                          <p className="text-gray-900">
                            Detection: {chapter.detection_method} ({(chapter.detection_confidence * 100).toFixed(0)}%)
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="ml-4 flex flex-col items-end gap-1">
                      {chapter.has_embedding ? (
                        <Badge variant="success">✓ Indexed</Badge>
                      ) : (
                        <Badge variant="default">Pending</Badge>
                      )}
                      {chapter.is_duplicate && (
                        <Badge variant="warning">Duplicate</Badge>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-700 text-sm">No chapters found</p>
          )}
        </div>
      )}
    </Card>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="max-w-md w-full mx-4">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">
              Delete Book?
            </h3>
            <p className="text-gray-900 mb-6">
              Are you sure you want to delete "{currentBook.title}"? This will permanently delete the book and all {currentBook.total_chapters} chapters. This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <Button
                variant="outline"
                onClick={() => setShowDeleteConfirm(false)}
                disabled={deleting}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                onClick={handleDelete}
                disabled={deleting}
              >
                {deleting ? 'Deleting...' : 'Delete Book'}
              </Button>
            </div>
          </Card>
        </div>
      )}
    </>
  );
};

export default TextbookLibrary;
