/**
 * PDFs List Page
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Card, LoadingSpinner, Badge, Button } from '../components';
import { pdfAPI } from '../api';
import { formatRelativeTime, formatFileSize } from '../utils/helpers';

const PDFsList = () => {
  const [pdfs, setPdfs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPDFs();
  }, []);

  const loadPDFs = async () => {
    try {
      const data = await pdfAPI.getAll();
      setPdfs(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Failed to load PDFs:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="flex justify-center py-12"><LoadingSpinner size="lg" /></div>;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold text-gray-900">PDF Library</h1>
        <Link to="/pdfs/upload">
          <Button variant="primary">Upload PDF</Button>
        </Link>
      </div>

      {pdfs.length > 0 ? (
        <div className="space-y-4">
          {pdfs.map((pdf) => (
            <Card key={pdf.id} hover>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-2xl">📄</span>
                    <h3 className="text-lg font-semibold text-gray-900">
                      {pdf.title || pdf.filename}
                    </h3>
                    <Badge status={pdf.extraction_status} />
                  </div>
                  <div className="flex gap-6 text-sm text-gray-600">
                    <span>{formatRelativeTime(pdf.uploaded_at)}</span>
                    <span>{pdf.page_count || 0} pages</span>
                    <span>{formatFileSize(pdf.file_size)}</span>
                  </div>
                </div>
                <Link to={`/pdfs/${pdf.id}`}>
                  <Button variant="outline" size="sm">View Details</Button>
                </Link>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="text-center py-12">
          <p className="text-gray-600 mb-4">No PDFs uploaded yet</p>
          <Link to="/pdfs/upload">
            <Button variant="primary">Upload Your First PDF</Button>
          </Link>
        </Card>
      )}
    </div>
  );
};

export default PDFsList;
