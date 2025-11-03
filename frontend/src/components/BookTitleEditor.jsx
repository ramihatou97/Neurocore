/**
 * BookTitleEditor Component
 * Modal dialog for editing book titles with validation and quick-fill suggestions
 */

import { useState } from 'react';
import { XMarkIcon, PencilIcon } from '@heroicons/react/24/outline';
import Card from './Card';
import Button from './Button';
import { textbookAPI } from '../api';

const BookTitleEditor = ({ book, onTitleUpdated }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [title, setTitle] = useState(book.title);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Show prominent button for books that need title editing
  const needsTitle = book.title === "Untitled Book - Please Edit"
    || /^[0-9a-f]{8}-[0-9a-f]{4}/.test(book.title);

  // Common neurosurgery textbook patterns
  const suggestions = [
    "Youmans Neurological Surgery Vol. ",
    "Handbook of Neurosurgery - ",
    "Atlas of Neurosurgical Techniques - ",
    "Principles of Neurosurgery - ",
    "Operative Neurosurgical Techniques - ",
    "Schmidek & Sweet - ",
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const response = await textbookAPI.updateBookTitle(book.id, { title: title.trim() });

      // Call parent callback with updated book data
      onTitleUpdated(response);

      // Close modal
      setIsOpen(false);

      // Success notification (optional - could use a toast library)
      console.log('Book title updated successfully');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update title');
    } finally {
      setIsLoading(false);
    }
  };

  const handleOpen = () => {
    setTitle(book.title);
    setError(null);
    setIsOpen(true);
  };

  const handleClose = () => {
    if (!isLoading) {
      setIsOpen(false);
      setTitle(book.title);
      setError(null);
    }
  };

  return (
    <>
      {/* Edit Button */}
      <Button
        variant={needsTitle ? "warning" : "outline"}
        size="sm"
        onClick={handleOpen}
      >
        <PencilIcon className="h-4 w-4 inline mr-1" />
        {needsTitle ? 'Edit Title (Required)' : 'Edit Title'}
      </Button>

      {/* Modal Overlay */}
      {isOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              {/* Header */}
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-900">
                  Edit Book Title
                </h2>
                <button
                  onClick={handleClose}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                  disabled={isLoading}
                >
                  <XMarkIcon className="h-6 w-6" />
                </button>
              </div>

              {/* Original Title (if exists) */}
              {book.original_title && (
                <div className="mb-4 p-3 bg-gray-50 rounded-md border border-gray-200">
                  <p className="text-xs font-medium text-gray-600 mb-1">
                    Original Title:
                  </p>
                  <p className="text-sm text-gray-800 font-mono break-words">
                    {book.original_title}
                  </p>
                  {book.title_edited_at && (
                    <p className="text-xs text-gray-500 mt-1">
                      Last edited: {new Date(book.title_edited_at).toLocaleString()}
                    </p>
                  )}
                </div>
              )}

              {/* Form */}
              <form onSubmit={handleSubmit}>
                {/* Title Input */}
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    New Title *
                  </label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="e.g., Youmans Neurological Surgery Vol. 1"
                    maxLength={500}
                    required
                    autoFocus
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    {title.length}/500 characters
                  </p>
                </div>

                {/* Quick-Fill Suggestions */}
                <div className="mb-4">
                  <p className="text-xs font-medium text-gray-600 mb-2">
                    Quick-fill suggestions:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {suggestions.map((suggestion, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => setTitle(suggestion)}
                        className="px-2 py-1 text-xs bg-blue-50 text-blue-700 rounded hover:bg-blue-100 transition-colors"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Error Display */}
                {error && (
                  <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
                    <p className="text-sm text-red-800">{error}</p>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex justify-end gap-3">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleClose}
                    disabled={isLoading}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    variant="primary"
                    disabled={isLoading || !title.trim() || title.trim() === "Untitled Book - Please Edit"}
                  >
                    {isLoading ? 'Saving...' : 'Save Title'}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default BookTitleEditor;
