/**
 * TextbookUpload Page
 * Main interface for uploading textbooks with drag-and-drop support
 * Handles single and batch uploads with real-time progress tracking
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import FileDropZone from '../components/FileDropZone';
import UploadQueue from '../components/UploadQueue';
import Alert from '../components/Alert';

const TextbookUpload = () => {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [showSuccess, setShowSuccess] = useState(false);
  const navigate = useNavigate();

  /**
   * Handle files selected from drop zone
   */
  const handleFilesSelected = (files) => {
    setSelectedFiles(prev => [...prev, ...files]);
    setShowSuccess(false);
  };

  /**
   * Clear upload queue
   */
  const handleClearQueue = () => {
    setSelectedFiles([]);
    setShowSuccess(false);
  };

  /**
   * Handle upload completion
   */
  const handleUploadComplete = (bookIds) => {
    setShowSuccess(true);
    // Optionally clear queue after success
    // setTimeout(() => {
    //   setSelectedFiles([]);
    // }, 3000);
  };

  /**
   * Navigate to library
   */
  const handleViewLibrary = () => {
    navigate('/textbooks');
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Upload Textbooks
          </h1>
          <p className="text-gray-600">
            Upload neurosurgery textbooks for automatic chapter detection and semantic indexing
          </p>
        </div>

        {/* Success Alert */}
        {showSuccess && (
          <Alert
            type="success"
            message="All textbooks uploaded successfully! Embeddings are being generated."
            onClose={() => setShowSuccess(false)}
            className="mb-6"
          />
        )}

        {/* Upload Information */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <h3 className="text-sm font-semibold text-blue-900 mb-2">
            What happens after upload:
          </h3>
          <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
            <li>PDF classification (textbook/chapter/paper)</li>
            <li>Automatic chapter detection using TOC, patterns, and headings</li>
            <li>Content extraction per chapter</li>
            <li>Embedding generation (1536-dim vectors) for semantic search</li>
            <li>Duplicate detection across your library (&gt;95% similarity)</li>
          </ul>
        </div>

        {/* File Drop Zone */}
        {selectedFiles.length === 0 && (
          <FileDropZone
            onFilesSelected={handleFilesSelected}
            maxFiles={50}
            maxSizeMB={100}
            multiple={true}
          />
        )}

        {/* Upload Queue */}
        {selectedFiles.length > 0 && (
          <div className="mt-6">
            <UploadQueue
              files={selectedFiles}
              onClearQueue={handleClearQueue}
              onUploadComplete={handleUploadComplete}
            />

            {/* Add More Files Button */}
            {selectedFiles.length < 50 && (
              <div className="mt-6">
                <FileDropZone
                  onFilesSelected={handleFilesSelected}
                  maxFiles={50 - selectedFiles.length}
                  maxSizeMB={100}
                  multiple={true}
                />
              </div>
            )}
          </div>
        )}

        {/* Processing Information */}
        <div className="mt-8 bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Upload Guidelines
          </h3>

          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium text-gray-900 mb-2">File Requirements</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Format: PDF only</li>
                <li>• Max size: 100MB per file</li>
                <li>• Batch limit: 50 files at once</li>
                <li>• Max pages: 1000 per PDF</li>
              </ul>
            </div>

            <div>
              <h4 className="font-medium text-gray-900 mb-2">Processing Time</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Upload: &lt;1 minute per file</li>
                <li>• Chapter detection: &lt;1 minute</li>
                <li>• Embedding generation: ~6 seconds per chapter</li>
                <li>• 25-chapter textbook: ~2.5 minutes total</li>
              </ul>
            </div>

            <div>
              <h4 className="font-medium text-gray-900 mb-2">Chapter Detection</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Table of Contents parsing (90% confidence)</li>
                <li>• Pattern matching (80% confidence)</li>
                <li>• Heading analysis (60% confidence)</li>
                <li>• Automatic fallback if needed</li>
              </ul>
            </div>

            <div>
              <h4 className="font-medium text-gray-900 mb-2">Cost Estimate</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Average chapter: ~$0.0009</li>
                <li>• 100-chapter textbook: ~$0.09</li>
                <li>• 1000-chapter library: ~$0.90</li>
                <li>• Model: text-embedding-3-large (1536 dims)</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="mt-6 flex justify-between items-center">
          <button
            onClick={handleViewLibrary}
            className="text-blue-600 hover:text-blue-700 font-medium text-sm"
          >
            ← View Library
          </button>

          <div className="text-sm text-gray-500">
            Need help? Check the{' '}
            <a href="#" className="text-blue-600 hover:text-blue-700">
              documentation
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TextbookUpload;
