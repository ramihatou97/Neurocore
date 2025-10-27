/**
 * TagDisplay Component
 * Display and manage AI-generated tags on content
 */

import { useState, useEffect } from 'react';
import Badge from './Badge';
import Button from './Button';
import LoadingSpinner from './LoadingSpinner';
import Alert from './Alert';

const TagDisplay = ({
  contentType,
  contentId,
  contentText = '',
  contentTitle = '',
  showAutoTag = true,
  onTagsUpdated = null
}) => {
  const [tags, setTags] = useState([]);
  const [suggestedTags, setSuggestedTags] = useState([]);
  const [loading, setLoading] = useState(false);
  const [autoTagging, setAutoTagging] = useState(false);
  const [error, setError] = useState(null);
  const [showSuggestions, setShowSuggestions] = useState(false);

  // Fetch existing tags on mount
  useEffect(() => {
    if (contentType && contentId) {
      fetchTags();
    }
  }, [contentType, contentId]);

  const fetchTags = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(
        `/api/v1/ai/content/${contentType}/${contentId}/tags`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch tags');
      }

      const data = await response.json();
      setTags(data.tags || []);
    } catch (err) {
      console.error('Error fetching tags:', err);
      setError('Failed to load tags');
    } finally {
      setLoading(false);
    }
  };

  const handleAutoTag = async () => {
    if (!contentText) {
      setError('No content available for auto-tagging');
      return;
    }

    setAutoTagging(true);
    setError(null);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/v1/ai/tags/auto-tag', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          content_type: contentType,
          content_id: contentId,
          content_text: contentText,
          content_title: contentTitle,
          max_tags: 5,
          min_confidence: 0.6
        })
      });

      if (!response.ok) {
        throw new Error('Auto-tagging failed');
      }

      const data = await response.json();
      if (data.success) {
        setTags(data.tags);
        if (onTagsUpdated) {
          onTagsUpdated(data.tags);
        }
      }
    } catch (err) {
      console.error('Error auto-tagging:', err);
      setError('Auto-tagging failed. Please try again.');
    } finally {
      setAutoTagging(false);
    }
  };

  const handleGetSuggestions = async () => {
    if (!contentText) {
      setError('No content available for suggestions');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(
        `/api/v1/ai/tags/suggest?text=${encodeURIComponent(contentText.substring(0, 1000))}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (!response.ok) {
        throw new Error('Failed to get suggestions');
      }

      const data = await response.json();
      setSuggestedTags(data.suggestions || []);
      setShowSuggestions(true);
    } catch (err) {
      console.error('Error getting suggestions:', err);
      setError('Failed to get tag suggestions');
    } finally {
      setLoading(false);
    }
  };

  const handleAddTag = async (tagName) => {
    setError(null);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/v1/ai/tags/add', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          content_type: contentType,
          content_id: contentId,
          tag_name: tagName
        })
      });

      if (!response.ok) {
        throw new Error('Failed to add tag');
      }

      // Refresh tags
      await fetchTags();
      if (onTagsUpdated) {
        onTagsUpdated(tags);
      }
    } catch (err) {
      console.error('Error adding tag:', err);
      setError('Failed to add tag');
    }
  };

  const handleRemoveTag = async (tagId) => {
    setError(null);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(
        `/api/v1/ai/tags/${tagId}/remove/${contentType}/${contentId}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (!response.ok) {
        throw new Error('Failed to remove tag');
      }

      // Update local state
      setTags(tags.filter(t => t.id !== tagId));
      if (onTagsUpdated) {
        onTagsUpdated(tags.filter(t => t.id !== tagId));
      }
    } catch (err) {
      console.error('Error removing tag:', err);
      setError('Failed to remove tag');
    }
  };

  if (loading && tags.length === 0) {
    return (
      <div className="flex items-center gap-2">
        <LoadingSpinner size="sm" />
        <span className="text-sm text-gray-600">Loading tags...</span>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {error && (
        <Alert type="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Current Tags */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-medium text-gray-700">Tags</h4>
          {showAutoTag && (
            <Button
              onClick={handleAutoTag}
              disabled={autoTagging || !contentText}
              variant="secondary"
              size="sm"
            >
              {autoTagging ? (
                <>
                  <LoadingSpinner size="xs" />
                  <span className="ml-2">Auto-Tagging...</span>
                </>
              ) : (
                'Auto-Tag'
              )}
            </Button>
          )}
        </div>

        {tags.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {tags.map((tag) => (
              <div key={tag.id} className="group relative">
                <Badge variant="primary" className="pr-6">
                  {tag.name}
                  {tag.confidence && (
                    <span className="ml-1 text-xs opacity-70">
                      ({Math.round(tag.confidence * 100)}%)
                    </span>
                  )}
                </Badge>
                <button
                  onClick={() => handleRemoveTag(tag.id)}
                  className="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity"
                  title="Remove tag"
                >
                  <span className="text-blue-600 hover:text-blue-800 text-sm">×</span>
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500">
            No tags yet. Click &quot;Auto-Tag&quot; to generate tags automatically.
          </p>
        )}
      </div>

      {/* Tag Suggestions */}
      {contentText && (
        <div className="pt-2 border-t">
          <Button
            onClick={handleGetSuggestions}
            disabled={loading}
            variant="ghost"
            size="sm"
          >
            {loading ? 'Getting suggestions...' : 'Get Tag Suggestions'}
          </Button>

          {showSuggestions && suggestedTags.length > 0 && (
            <div className="mt-2 space-y-2">
              <p className="text-xs text-gray-600">Suggested tags (click to add):</p>
              <div className="flex flex-wrap gap-2">
                {suggestedTags.map((suggestion, index) => (
                  <button
                    key={index}
                    onClick={() => {
                      handleAddTag(suggestion.name);
                      setSuggestedTags(suggestedTags.filter((_, i) => i !== index));
                    }}
                    className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors cursor-pointer"
                  >
                    + {suggestion.name}
                    {suggestion.confidence && (
                      <span className="ml-1 text-xs opacity-70">
                        ({Math.round(suggestion.confidence * 100)}%)
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TagDisplay;
