/**
 * Section Editor Component
 * Allows inline editing of chapter sections with save and regenerate options
 */

import { useState } from 'react';
import { Button, LoadingSpinner } from './';
import { chaptersAPI } from '../api';

const SectionEditor = ({ chapterId, section, sectionNumber, onSave, onRegenerate }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [content, setContent] = useState(section.content || '');
  const [isSaving, setIsSaving] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [showRegenerateOptions, setShowRegenerateOptions] = useState(false);
  const [instructions, setInstructions] = useState('');
  const [error, setError] = useState(null);

  const handleSave = async () => {
    if (!content.trim()) {
      setError('Content cannot be empty');
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      const response = await chaptersAPI.editSection(chapterId, sectionNumber, {
        content: content
      });

      // Call parent callback
      if (onSave) {
        onSave(response);
      }

      setIsEditing(false);
    } catch (err) {
      console.error('Failed to save section:', err);
      setError(err.response?.data?.detail || 'Failed to save section');
    } finally {
      setIsSaving(false);
    }
  };

  const handleRegenerate = async () => {
    setIsRegenerating(true);
    setError(null);

    try {
      const response = await chaptersAPI.regenerateSection(chapterId, sectionNumber, {
        instructions: instructions || undefined
      });

      // Call parent callback
      if (onRegenerate) {
        onRegenerate(response);
      }

      setShowRegenerateOptions(false);
      setInstructions('');
      setContent(response.updated_content || response.new_content);
    } catch (err) {
      console.error('Failed to regenerate section:', err);
      setError(err.response?.data?.detail || 'Failed to regenerate section');
    } finally {
      setIsRegenerating(false);
    }
  };

  const handleCancel = () => {
    setContent(section.content || '');
    setIsEditing(false);
    setError(null);
  };

  return (
    <div className="section-editor border border-gray-200 rounded-lg p-6 mb-6 hover:shadow-md transition-shadow">
      {/* Section Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="text-xl font-semibold text-gray-900 mb-1">
            {section.title || `Section ${sectionNumber + 1}`}
          </h3>
          <div className="flex gap-4 text-sm text-gray-500">
            <span>{section.word_count || 0} words</span>
            {section.edited_at && (
              <span className="text-blue-600">Edited</span>
            )}
            {section.regenerated_at && (
              <span className="text-green-600">Regenerated</span>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        {!isEditing && (
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsEditing(true)}
              className="text-blue-600 hover:bg-blue-50"
            >
              ✏️ Edit
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowRegenerateOptions(!showRegenerateOptions)}
              className="text-green-600 hover:bg-green-50"
            >
              🔄 Regenerate
            </Button>
          </div>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Editing Mode */}
      {isEditing ? (
        <div className="space-y-4">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="w-full h-64 p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
            placeholder="Enter section content (HTML supported)..."
          />

          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleCancel}
              disabled={isSaving}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleSave}
              disabled={isSaving}
            >
              {isSaving ? (
                <>
                  <LoadingSpinner size="sm" className="mr-2" />
                  Saving...
                </>
              ) : (
                'Save Changes'
              )}
            </Button>
          </div>

          <div className="text-xs text-gray-500 bg-gray-50 p-3 rounded">
            <strong>Tip:</strong> You can use HTML tags for formatting. Changes will create a new version automatically.
            Cost: ~$0 (manual edit, no AI)
          </div>
        </div>
      ) : (
        <>
          {/* Content Display */}
          <div
            className="prose max-w-none"
            dangerouslySetInnerHTML={{ __html: content }}
          />

          {/* Regenerate Options Panel */}
          {showRegenerateOptions && (
            <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg space-y-3">
              <h4 className="font-medium text-green-900">AI Regeneration Options</h4>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Special Instructions (optional)
                </label>
                <textarea
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
                  rows="2"
                  placeholder="E.g., Focus more on surgical technique, add more recent studies..."
                  disabled={isRegenerating}
                />
              </div>

              <div className="flex justify-between items-center">
                <div className="text-xs text-gray-600">
                  <strong>Cost:</strong> ~$0.08 (84% savings vs full regeneration)
                  <br />
                  <strong>Time:</strong> ~10-20 seconds
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setShowRegenerateOptions(false);
                      setInstructions('');
                    }}
                    disabled={isRegenerating}
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleRegenerate}
                    disabled={isRegenerating}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    {isRegenerating ? (
                      <>
                        <LoadingSpinner size="sm" className="mr-2" />
                        Regenerating...
                      </>
                    ) : (
                      '🔄 Regenerate with AI'
                    )}
                  </Button>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default SectionEditor;
