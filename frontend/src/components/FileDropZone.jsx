/**
 * FileDropZone Component
 * Drag-and-drop file upload zone with validation
 * Supports single and multi-file uploads with size/type validation
 */

import { useState, useCallback } from 'react';
import Card from './Card';
import Alert from './Alert';

const FileDropZone = ({
  onFilesSelected,
  maxFiles = 50,
  maxSizeMB = 100,
  accept = '.pdf',
  multiple = true,
  disabled = false
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState('');

  /**
   * Validate files against size and type constraints
   */
  const validateFiles = useCallback((files) => {
    const validFiles = [];
    const errors = [];

    for (const file of files) {
      // Type validation
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        errors.push(`${file.name}: Only PDF files are supported`);
        continue;
      }

      // Size validation
      const sizeMB = file.size / (1024 * 1024);
      if (sizeMB > maxSizeMB) {
        errors.push(`${file.name}: Exceeds ${maxSizeMB}MB limit (${sizeMB.toFixed(1)}MB)`);
        continue;
      }

      validFiles.push(file);
    }

    // Max files validation
    if (validFiles.length > maxFiles) {
      errors.push(`Maximum ${maxFiles} files allowed per batch`);
      return {
        validFiles: validFiles.slice(0, maxFiles),
        errors
      };
    }

    return { validFiles, errors };
  }, [maxFiles, maxSizeMB]);

  /**
   * Handle file drop event
   */
  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();

    if (disabled) return;

    setIsDragging(false);
    setError('');

    const files = Array.from(e.dataTransfer.files);
    const { validFiles, errors } = validateFiles(files);

    if (errors.length > 0) {
      setError(errors.join('; '));
    }

    if (validFiles.length > 0) {
      onFilesSelected(validFiles);
    }
  }, [disabled, validateFiles, onFilesSelected]);

  /**
   * Handle file input change
   */
  const handleFileInput = useCallback((e) => {
    if (disabled) return;

    setError('');

    const files = Array.from(e.target.files);
    const { validFiles, errors } = validateFiles(files);

    if (errors.length > 0) {
      setError(errors.join('; '));
    }

    if (validFiles.length > 0) {
      onFilesSelected(validFiles);
    }

    // Reset input to allow re-upload of same file
    e.target.value = '';
  }, [disabled, validateFiles, onFilesSelected]);

  /**
   * Handle drag events
   */
  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) {
      setIsDragging(true);
    }
  }, [disabled]);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  return (
    <div>
      {error && (
        <Alert
          type="error"
          message={error}
          onClose={() => setError('')}
          className="mb-4"
        />
      )}

      <div
        className={`
          border-2 border-dashed rounded-lg transition-all
          ${isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-blue-400'
          }
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={handleFileInput}
          disabled={disabled}
          className="hidden"
          id="file-upload-input"
        />

        <label
          htmlFor="file-upload-input"
          className={`
            block text-center py-12 px-6
            ${disabled ? 'cursor-not-allowed' : 'cursor-pointer'}
          `}
        >
          <div className="text-6xl mb-4">
            {isDragging ? '📥' : '📚'}
          </div>

          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            {isDragging ? 'Drop files here' : 'Drag & Drop PDFs Here'}
          </h3>

          <p className="text-gray-600 mb-2">
            or click to browse your files
          </p>

          <div className="text-sm text-gray-500 space-y-1">
            <p>Supported: PDF files only (max {maxSizeMB}MB per file)</p>
            {multiple && (
              <p>Batch Upload: Up to {maxFiles} files at once</p>
            )}
          </div>
        </label>
      </div>
    </div>
  );
};

export default FileDropZone;
