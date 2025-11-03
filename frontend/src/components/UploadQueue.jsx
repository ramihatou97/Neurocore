/**
 * UploadQueue Component
 * Manages multiple file uploads with queue visualization
 * Coordinates parallel uploads and provides overall progress
 */

import { useState, useCallback } from 'react';
import UploadProgressCard from './UploadProgressCard';
import Button from './Button';

const UploadQueue = ({
  files,
  onClearQueue,
  onUploadComplete
}) => {
  const [completedUploads, setCompletedUploads] = useState([]);
  const [failedUploads, setFailedUploads] = useState([]);

  /**
   * Handle individual upload completion
   */
  const handleUploadComplete = useCallback((bookId) => {
    setCompletedUploads(prev => [...prev, bookId]);
  }, []);

  /**
   * Handle processing completion for individual file
   */
  const handleProcessingComplete = useCallback((bookId) => {
    // Additional completion logic if needed
  }, []);

  /**
   * Handle upload error
   */
  const handleError = useCallback((filename, error) => {
    setFailedUploads(prev => [...prev, { filename, error }]);
  }, []);

  /**
   * Handle cancel for individual file
   */
  const handleCancel = useCallback((filename) => {
    // Individual file cancelled
  }, []);

  /**
   * Calculate overall progress
   */
  const getOverallProgress = () => {
    if (files.length === 0) return 0;
    return Math.round((completedUploads.length / files.length) * 100);
  };

  /**
   * Check if all uploads are complete
   */
  const allComplete = completedUploads.length === files.length;

  if (files.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      {/* Queue Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            Upload Queue
            <span className="ml-2 text-sm font-normal text-gray-600">
              ({completedUploads.length}/{files.length} complete)
            </span>
          </h3>
          {failedUploads.length > 0 && (
            <p className="text-sm text-red-600 mt-1">
              {failedUploads.length} upload{failedUploads.length > 1 ? 's' : ''} failed
            </p>
          )}
        </div>

        <div className="flex gap-2">
          {allComplete && onUploadComplete && (
            <Button
              variant="success"
              size="sm"
              onClick={() => onUploadComplete(completedUploads)}
            >
              View Library
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={onClearQueue}
          >
            Clear Queue
          </Button>
        </div>
      </div>

      {/* Overall Progress Bar */}
      {!allComplete && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">
              Overall Progress
            </span>
            <span className="text-sm text-gray-600">
              {getOverallProgress()}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${getOverallProgress()}%` }}
            />
          </div>
        </div>
      )}

      {/* Upload Progress Cards */}
      <div className="space-y-3">
        {files.map((file, index) => (
          <UploadProgressCard
            key={`${file.name}-${index}`}
            file={file}
            onUploadComplete={handleUploadComplete}
            onProcessingComplete={handleProcessingComplete}
            onError={handleError}
            onCancel={handleCancel}
          />
        ))}
      </div>

      {/* Success Summary */}
      {allComplete && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-green-800 font-medium flex items-center gap-2">
            <span className="text-xl">✓</span>
            <span>
              All {files.length} file{files.length > 1 ? 's' : ''} uploaded successfully!
            </span>
          </p>
          {failedUploads.length === 0 && (
            <p className="text-sm text-green-700 mt-1">
              Your textbooks are being indexed and will be available for search shortly.
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default UploadQueue;
