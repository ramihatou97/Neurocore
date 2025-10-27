/**
 * PDF Upload Page
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Button, Alert, ProgressBar } from '../components';
import { pdfAPI } from '../api';

const PDFUpload = () => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      if (selectedFile.type !== 'application/pdf') {
        setError('Please select a PDF file');
        return;
      }
      if (selectedFile.size > 50 * 1024 * 1024) {
        setError('File size must be less than 50MB');
        return;
      }
      setFile(selectedFile);
      setError('');
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file');
      return;
    }

    try {
      setUploading(true);
      setError('');
      const response = await pdfAPI.upload(file, setUploadProgress);
      setTimeout(() => {
        navigate(`/pdfs/${response.pdf_id}`);
      }, 1000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed');
      setUploading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Upload PDF</h1>
        <p className="text-gray-600 mt-2">Upload neurosurgery literature for processing</p>
      </div>

      <Card>
        {error && <Alert type="error" message={error} onClose={() => setError('')} className="mb-4" />}

        <div className="space-y-6">
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              disabled={uploading}
              className="hidden"
              id="file-upload"
            />
            <label htmlFor="file-upload" className="cursor-pointer">
              <div className="text-4xl mb-4">📄</div>
              <p className="text-gray-700 font-medium mb-1">
                {file ? file.name : 'Click to select PDF'}
              </p>
              <p className="text-sm text-gray-500">Maximum size: 50MB</p>
            </label>
          </div>

          {uploading && (
            <div>
              <p className="text-sm text-gray-700 mb-2">Uploading...</p>
              <ProgressBar progress={uploadProgress} />
            </div>
          )}

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="font-medium text-blue-900 mb-2">Processing Pipeline</h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• Text extraction from all pages</li>
              <li>• Image extraction and analysis</li>
              <li>• Citation detection and linking</li>
              <li>• Vector embedding generation</li>
            </ul>
          </div>

          <div className="flex gap-4">
            <Button
              onClick={handleUpload}
              disabled={!file || uploading}
              loading={uploading}
              fullWidth
            >
              {uploading ? 'Uploading...' : 'Upload PDF'}
            </Button>
            <Button
              variant="outline"
              onClick={() => navigate('/pdfs')}
              disabled={uploading}
            >
              Cancel
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default PDFUpload;
