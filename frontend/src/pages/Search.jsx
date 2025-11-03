/**
 * Search Page
 * Simple search interface using Tailwind CSS
 */

import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Card, Button, Input, LoadingSpinner, Badge, Alert } from '../components';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002/api/v1';

function Search() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  // Search state
  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searched, setSearched] = useState(false);

  // Execute search on mount if query exists
  useEffect(() => {
    const initialQuery = searchParams.get('q');
    if (initialQuery) {
      setQuery(initialQuery);
      executeSearch(initialQuery);
    }
  }, []);

  const executeSearch = async (searchQuery) => {
    if (!searchQuery.trim()) {
      setError('Please enter a search query');
      return;
    }

    setLoading(true);
    setError('');
    setSearched(true);

    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${API_BASE_URL}/search/semantic`,
        {
          query: searchQuery,
          limit: 20
        },
        {
          headers: {
            Authorization: `Bearer ${token}`
          }
        }
      );

      setResults(response.data.results || []);
    } catch (err) {
      console.error('Search error:', err);
      setError(err.response?.data?.detail || 'Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    setSearchParams({ q: query });
    executeSearch(query);
  };

  const handleResultClick = (result) => {
    if (result.chapter_id) {
      navigate(`/chapters/${result.chapter_id}`);
    }
  };

  const getResultTypeColor = (type) => {
    switch (type) {
      case 'textbook_chapter':
        return 'bg-blue-100 text-blue-800';
      case 'standalone_chapter':
        return 'bg-green-100 text-green-800';
      case 'research_paper':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-3">
            🔍 Semantic Search
          </h1>
          <p className="text-lg text-gray-600">
            Search through your neurosurgery knowledge base using AI-powered semantic search
          </p>
        </div>

        {/* Search Form */}
        <Card className="mb-8">
          <form onSubmit={handleSearch} className="space-y-4">
            <div className="flex gap-3">
              <div className="flex-1">
                <Input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search for concepts, procedures, techniques..."
                  className="w-full text-lg"
                  disabled={loading}
                />
              </div>
              <Button
                type="submit"
                variant="primary"
                size="lg"
                disabled={loading || !query.trim()}
              >
                {loading ? 'Searching...' : 'Search'}
              </Button>
            </div>

            <p className="text-sm text-gray-600">
              💡 Tip: Search uses semantic similarity to find relevant content, even if exact keywords don't match
            </p>
          </form>
        </Card>

        {/* Error Alert */}
        {error && (
          <Alert
            type="error"
            message={error}
            onClose={() => setError('')}
            className="mb-6"
          />
        )}

        {/* Loading State */}
        {loading && (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="xl" />
          </div>
        )}

        {/* Results */}
        {!loading && searched && (
          <>
            {/* Results Header */}
            <div className="mb-4">
              <h2 className="text-xl font-semibold text-gray-900">
                {results.length > 0 ? (
                  <>Found {results.length} result{results.length !== 1 ? 's' : ''}</>
                ) : (
                  'No results found'
                )}
              </h2>
              {results.length === 0 && (
                <p className="text-gray-600 mt-2">
                  Try different keywords or broader search terms
                </p>
              )}
            </div>

            {/* Results List */}
            <div className="space-y-4">
              {results.map((result, index) => (
                <Card
                  key={result.chapter_id || index}
                  className="hover:shadow-lg transition-shadow cursor-pointer"
                  onClick={() => handleResultClick(result)}
                >
                  <div className="space-y-3">
                    {/* Result Header */}
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="text-lg font-semibold text-gray-900 mb-1">
                          {result.chapter_title || 'Untitled'}
                        </h3>
                        {result.chapter_number && (
                          <p className="text-sm text-gray-600">
                            Chapter {result.chapter_number}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 ml-4">
                        {/* Similarity Score */}
                        <div className="text-right">
                          <div className="text-2xl font-bold text-blue-600">
                            {(result.similarity_score * 100).toFixed(0)}%
                          </div>
                          <div className="text-xs text-gray-600">similarity</div>
                        </div>
                        {/* Source Type Badge */}
                        {result.source_type && (
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getResultTypeColor(result.source_type)}`}>
                            {result.source_type.replace(/_/g, ' ')}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Content Preview */}
                    {result.content_preview && (
                      <p className="text-gray-700 text-sm line-clamp-3">
                        {result.content_preview}
                      </p>
                    )}

                    {/* Metadata */}
                    <div className="flex items-center gap-4 text-sm text-gray-600">
                      {result.word_count && (
                        <span>📝 {result.word_count.toLocaleString()} words</span>
                      )}
                      {result.page_count && (
                        <span>📄 {result.page_count} pages</span>
                      )}
                      {result.has_images && (
                        <span>🖼️ Contains images</span>
                      )}
                    </div>

                    {/* Highlight/Context (if available) */}
                    {result.highlight && (
                      <div className="bg-yellow-50 border-l-4 border-yellow-400 p-3 rounded">
                        <p className="text-sm text-gray-800">
                          <span className="font-semibold">Relevant excerpt: </span>
                          {result.highlight}
                        </p>
                      </div>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          </>
        )}

        {/* Empty State (no search yet) */}
        {!searched && !loading && (
          <Card className="text-center py-16">
            <div className="text-6xl mb-4">🔍</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              Start Your Search
            </h3>
            <p className="text-gray-600 max-w-md mx-auto">
              Enter keywords, concepts, or questions to search through your neurosurgery knowledge base using semantic similarity
            </p>
          </Card>
        )}
      </div>
    </div>
  );
}

export default Search;
