/**
 * UploadProgressCard Component
 * Real-time upload and processing progress for individual file
 * Shows upload progress, processing stages, and embedding generation
 */

import { useState, useEffect } from 'react';
import Card from './Card';
import ProgressBar from './ProgressBar';
import Badge from './Badge';
import Button from './Button';
import { textbookAPI } from '../api';

const UploadProgressCard = ({
  file,
  onUploadComplete,
  onProcessingComplete,
  onError,
  onCancel
}) => {
  const [status, setStatus] = useState('queued'); // queued, uploading, processing, completed, failed, cancelled
  const [uploadProgress, setUploadProgress] = useState(0);
  const [bookId, setBookId] = useState(null);
  const [processingData, setProcessingData] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  // Upload file when component mounts
  useEffect(() => {
    if (status === 'queued') {
      uploadFile();
    }
  }, [status]);

  // Poll processing progress
  useEffect(() => {
    if (status === 'processing' && bookId) {
      const interval = setInterval(() => {
        fetchProgress();
      }, 3000); // Poll every 3 seconds

      return () => clearInterval(interval);
    }
  }, [status, bookId]);

  /**
   * Upload file to backend
   */
  const uploadFile = async () => {
    setStatus('uploading');
    try {
      const response = await textbookAPI.upload(file, setUploadProgress);

      setBookId(response.book_id);
      setStatus('processing');
      setProcessingData({
        bookId: response.book_id,
        chaptersCreated: response.chapters_created,
        totalPages: response.total_pages,
        pdfType: response.pdf_type,
        embeddingTasksQueued: response.embedding_tasks_queued
      });

      if (onUploadComplete) {
        onUploadComplete(response.book_id);
      }
    } catch (error) {
      setStatus('failed');
      const message = error.response?.data?.detail || error.message || 'Upload failed';
      setErrorMessage(message);
      if (onError) {
        onError(file.name, message);
      }
    }
  };

  /**
   * Fetch processing progress from backend
   */
  const fetchProgress = async () => {
    try {
      const progress = await textbookAPI.getUploadProgress(bookId);

      setProcessingData(prev => ({
        ...prev,
        ...progress
      }));

      // Check if processing is complete
      if (progress.embedding_progress_percent >= 100) {
        setStatus('completed');
        if (onProcessingComplete) {
          onProcessingComplete(bookId);
        }
      }
    } catch (error) {
      console.error('Failed to fetch progress:', error);
    }
  };

  /**
   * Handle cancel action
   */
  const handleCancel = () => {
    setStatus('cancelled');
    if (onCancel) {
      onCancel(file.name);
    }
  };

  /**
   * Retry failed upload
   */
  const handleRetry = () => {
    setStatus('queued');
    setError

Message('');
    setUploadProgress(0);
    setBookId(null);
    setProcessingData(null);
  };

  /**
   * Get status badge configuration
   */
  const getStatusBadge = () => {
    const statusMap = {
      queued: { variant: 'default', text: 'Queued' },
      uploading: { variant: 'primary', text: 'Uploading' },
      processing: { variant: 'primary', text: 'Processing' },
      completed: { variant: 'success', text: 'Completed' },
      failed: { variant: 'danger', text: 'Failed' },
      cancelled: { variant: 'default', text: 'Cancelled' }
    };
    const config = statusMap[status];
    return <Badge variant={config.variant}>{config.text}</Badge>;
  };

  /**
   * Format file size
   */
  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  /**
   * Get PDF type display text
   */
  const getPdfTypeText = (type) => {
    const typeMap = {
      textbook: 'Textbook',
      standalone_chapter: 'Standalone Chapter',
      research_paper: 'Research Paper'
    };
    return typeMap[type] || type;
  };

  return (
    <Card className="mb-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-2xl">📖</span>
            <h4 className="font-semibold text-gray-900 truncate max-w-md" title={file.name}>
              {file.name}
            </h4>
            {getStatusBadge()}
          </div>

          <div className="text-sm text-gray-600 space-y-1">
            <p>
              {formatFileSize(file.size)}
              {processingData && ` • ${processingData.totalPages} pages`}
              {processingData && ` • ${processingData.chaptersCreated} chapters`}
              {processingData?.pdfType && ` • ${getPdfTypeText(processingData.pdfType)}`}
            </p>
          </div>
        </div>

        <div className="flex gap-2 ml-4">
          {status === 'failed' && (
            <Button
              variant="primary"
              size="sm"
              onClick={handleRetry}
            >
              Retry
            </Button>
          )}
          {(status === 'queued' || status === 'uploading' || status === 'processing') && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleCancel}
            >
              Cancel
            </Button>
          )}
        </div>
      </div>

      {/* Upload Progress */}
      {status === 'uploading' && (
        <div>
          <p className="text-sm text-gray-700 mb-2">Uploading file...</p>
          <ProgressBar progress={uploadProgress} size="md" />
        </div>
      )}

      {/* Processing Progress */}
      {status === 'processing' && processingData && (
        <div>
          <p className="text-sm text-gray-700 mb-2">
            Generating embeddings...
            {processingData.estimated_completion_minutes &&
              ` (~${processingData.estimated_completion_minutes} min remaining)`
            }
          </p>
          <ProgressBar
            progress={processingData.embedding_progress_percent || 0}
            size="md"
          />
          <p className="text-xs text-gray-500 mt-1">
            {processingData.chapters_with_embeddings || 0} /
            {processingData.total_chapters || processingData.chaptersCreated} chapters indexed
          </p>

          {/* Processing stages */}
          <div className="mt-3 text-xs space-y-1">
            <div className="flex items-center gap-2 text-green-600">
              <span>✓</span>
              <span>PDF Uploaded</span>
            </div>
            <div className="flex items-center gap-2 text-green-600">
              <span>✓</span>
              <span>Classified as {getPdfTypeText(processingData.pdfType)}</span>
            </div>
            <div className="flex items-center gap-2 text-green-600">
              <span>✓</span>
              <span>{processingData.chaptersCreated} Chapters Detected</span>
            </div>
            <div className="flex items-center gap-2 text-blue-600">
              <span>⚙</span>
              <span>Generating Embeddings ({processingData.chapters_with_embeddings || 0}/{processingData.chaptersCreated})</span>
            </div>
          </div>
        </div>
      )}

      {/* Completion Message */}
      {status === 'completed' && processingData && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3">
          <p className="text-sm text-green-800 flex items-center gap-2">
            <span>✓</span>
            <span>
              Successfully indexed {processingData.chaptersCreated} chapters
            </span>
          </p>
        </div>
      )}

      {/* Error Message */}
      {status === 'failed' && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
          <p className="text-sm text-red-800 flex items-center gap-2">
            <span>✕</span>
            <span>{errorMessage || 'Upload failed. Please try again.'}</span>
          </p>
        </div>
      )}

      {/* Cancelled Message */}
      {status === 'cancelled' && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
          <p className="text-sm text-gray-700">
            Upload cancelled
          </p>
        </div>
      )}
    </Card>
  );
};

export default UploadProgressCard;
