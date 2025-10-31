/**
 * Source Adder Component
 * Allows users to add additional research sources to a chapter
 */

import { useState } from 'react';
import { Button, LoadingSpinner } from './';
import { chaptersAPI } from '../api';

const SourceAdder = ({ chapterId, onSourcesAdded }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Form state
  const [pdfIds, setPdfIds] = useState('');
  const [dois, setDois] = useState('');
  const [pubmedIds, setPubmedIds] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    // Parse inputs (comma or newline separated)
    const parsePdfIds = pdfIds
      .split(/[,\n]/)
      .map(id => id.trim())
      .filter(id => id.length > 0);

    const parseDois = dois
      .split(/[,\n]/)
      .map(doi => doi.trim())
      .filter(doi => doi.length > 0);

    const parsePubmedIds = pubmedIds
      .split(/[,\n]/)
      .map(id => id.trim())
      .filter(id => id.length > 0);

    if (parsePdfIds.length === 0 && parseDois.length === 0 && parsePubmedIds.length === 0) {
      setError('Please provide at least one source');
      setLoading(false);
      return;
    }

    try {
      const response = await chaptersAPI.addSources(chapterId, {
        pdf_ids: parsePdfIds.length > 0 ? parsePdfIds : undefined,
        external_dois: parseDois.length > 0 ? parseDois : undefined,
        pubmed_ids: parsePubmedIds.length > 0 ? parsePubmedIds : undefined
      });

      setSuccess(`Added ${response.sources_added} sources. Total: ${response.total_sources}`);

      // Reset form
      setPdfIds('');
      setDois('');
      setPubmedIds('');

      // Call parent callback
      if (onSourcesAdded) {
        onSourcesAdded(response);
      }

      // Auto-close after 2 seconds
      setTimeout(() => {
        setIsOpen(false);
        setSuccess(null);
      }, 2000);

    } catch (err) {
      console.error('Failed to add sources:', err);
      setError(err.response?.data?.detail || 'Failed to add sources');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    setPdfIds('');
    setDois('');
    setPubmedIds('');
    setError(null);
    setSuccess(null);
    setIsOpen(false);
  };

  if (!isOpen) {
    return (
      <Button
        variant="outline"
        size="sm"
        onClick={() => setIsOpen(true)}
        className="text-purple-600 hover:bg-purple-50"
      >
        📚 Add Research Sources
      </Button>
    );
  }

  return (
    <div className="border border-purple-200 rounded-lg p-6 bg-purple-50">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Add Research Sources
      </h3>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
          {error}
        </div>
      )}

      {success && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-md text-green-700 text-sm">
          ✓ {success}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Internal PDF IDs */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Internal PDF IDs
            <span className="text-gray-500 font-normal ml-2">(comma or newline separated)</span>
          </label>
          <textarea
            value={pdfIds}
            onChange={(e) => setPdfIds(e.target.value)}
            className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:border-purple-500 text-sm font-mono"
            rows="3"
            placeholder="123e4567-e89b-12d3-a456-426614174000&#10;abc123..."
            disabled={loading}
          />
          <p className="text-xs text-gray-500 mt-1">
            PDFs from your indexed library
          </p>
        </div>

        {/* External DOIs */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            External DOIs
            <span className="text-gray-500 font-normal ml-2">(comma or newline separated)</span>
          </label>
          <textarea
            value={dois}
            onChange={(e) => setDois(e.target.value)}
            className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:border-purple-500 text-sm font-mono"
            rows="3"
            placeholder="10.1234/example&#10;10.5678/another"
            disabled={loading}
          />
          <p className="text-xs text-gray-500 mt-1">
            Digital Object Identifiers for external papers
          </p>
        </div>

        {/* PubMed IDs */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            PubMed IDs (PMIDs)
            <span className="text-gray-500 font-normal ml-2">(comma or newline separated)</span>
          </label>
          <textarea
            value={pubmedIds}
            onChange={(e) => setPubmedIds(e.target.value)}
            className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:border-purple-500 text-sm font-mono"
            rows="3"
            placeholder="12345678&#10;87654321"
            disabled={loading}
          />
          <p className="text-xs text-gray-500 mt-1">
            PubMed article identifiers
          </p>
        </div>

        {/* Info Box */}
        <div className="bg-blue-50 border border-blue-200 rounded-md p-3 text-sm text-blue-800">
          <strong>Note:</strong> These sources will be available when regenerating sections or the entire chapter.
          They will be integrated into the research data automatically.
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end gap-2 pt-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleCancel}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            size="sm"
            disabled={loading}
            className="bg-purple-600 hover:bg-purple-700"
          >
            {loading ? (
              <>
                <LoadingSpinner size="sm" className="mr-2" />
                Adding...
              </>
            ) : (
              '📚 Add Sources'
            )}
          </Button>
        </div>
      </form>
    </div>
  );
};

export default SourceAdder;
