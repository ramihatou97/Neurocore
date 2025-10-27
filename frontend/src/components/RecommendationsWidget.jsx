/**
 * RecommendationsWidget Component
 * Display personalized content recommendations
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Card from './Card';
import LoadingSpinner from './LoadingSpinner';
import Alert from './Alert';
import Badge from './Badge';

const RecommendationsWidget = ({
  algorithm = 'hybrid',
  sourceType = null,
  sourceId = null,
  limit = 5,
  title = 'Recommended for You',
  onInteraction = null
}) => {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchRecommendations();
  }, [algorithm, sourceType, sourceId, limit]);

  const fetchRecommendations = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams({
        algorithm,
        limit: limit.toString()
      });

      if (sourceType) params.append('source_type', sourceType);
      if (sourceId) params.append('source_id', sourceId);

      const response = await fetch(
        `/api/v1/ai/recommendations?${params.toString()}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch recommendations');
      }

      const data = await response.json();
      setRecommendations(data.recommendations || []);
    } catch (err) {
      console.error('Error fetching recommendations:', err);
      setError('Failed to load recommendations');
    } finally {
      setLoading(false);
    }
  };

  const handleClick = async (recommendation) => {
    // Track interaction
    try {
      const token = localStorage.getItem('token');
      await fetch('/api/v1/ai/recommendations/interaction', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          interaction_type: 'view',
          content_type: recommendation.type,
          content_id: recommendation.id
        })
      });

      if (onInteraction) {
        onInteraction(recommendation);
      }
    } catch (err) {
      console.error('Error tracking interaction:', err);
    }
  };

  const getContentLink = (item) => {
    if (item.type === 'chapter') {
      return `/chapters/${item.id}`;
    } else if (item.type === 'pdf') {
      return `/pdfs/${item.id}`;
    }
    return '#';
  };

  const getContentIcon = (type) => {
    if (type === 'chapter') {
      return '📄';
    } else if (type === 'pdf') {
      return '📕';
    }
    return '📚';
  };

  if (loading) {
    return (
      <Card className="p-4">
        <div className="flex items-center justify-center py-8">
          <LoadingSpinner size="md" />
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-4">
        <Alert type="error">{error}</Alert>
      </Card>
    );
  }

  if (recommendations.length === 0) {
    return (
      <Card className="p-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">{title}</h3>
        <p className="text-sm text-gray-600">
          No recommendations available yet. Keep exploring content to get personalized suggestions!
        </p>
      </Card>
    );
  }

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        <Badge variant="primary" className="text-xs">
          {algorithm}
        </Badge>
      </div>

      <div className="space-y-3">
        {recommendations.map((item) => (
          <Link
            key={item.id}
            to={getContentLink(item)}
            onClick={() => handleClick(item)}
            className="block group"
          >
            <div className="flex items-start gap-3 p-3 rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition-all">
              <span className="text-2xl flex-shrink-0">
                {getContentIcon(item.type)}
              </span>
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-medium text-gray-900 group-hover:text-blue-600 truncate">
                  {item.title}
                </h4>
                {item.author && (
                  <p className="text-xs text-gray-600 mt-1">
                    by {item.author}
                  </p>
                )}
                {item.summary && (
                  <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                    {item.summary}
                  </p>
                )}
                <div className="flex items-center gap-2 mt-2">
                  <Badge variant="default" className="text-xs">
                    {item.type}
                  </Badge>
                  {item.relevance_score && (
                    <span className="text-xs text-gray-500">
                      {Math.round(item.relevance_score * 100)}% match
                    </span>
                  )}
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>

      {sourceType && sourceId && (
        <button
          onClick={fetchRecommendations}
          className="w-full mt-3 text-sm text-blue-600 hover:text-blue-700 font-medium"
        >
          Refresh Recommendations
        </button>
      )}
    </Card>
  );
};

export default RecommendationsWidget;
