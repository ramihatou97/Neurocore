/**
 * Chapter Detail Page with Section Editing
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, LoadingSpinner, Badge, Button, SectionEditor, SourceAdder, GapAnalysisPanel } from '../components';
import { chaptersAPI } from '../api';
import { formatDate } from '../utils/helpers';

const ChapterDetail = () => {
  const { id } = useParams();
  const [chapter, setChapter] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editMode, setEditMode] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    loadChapter();
  }, [id]);

  const loadChapter = async () => {
    try {
      const data = await chaptersAPI.getById(id);
      setChapter(data);
    } catch (error) {
      console.error('Failed to load chapter:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSectionSave = (response) => {
    console.log('Section saved:', response);
    // Reload chapter to get updated version
    loadChapter();
  };

  const handleSectionRegenerate = (response) => {
    console.log('Section regenerated:', response);
    // Reload chapter to get updated content
    loadChapter();
  };

  const handleSourcesAdded = (response) => {
    console.log('Sources added:', response);
    // Could show a success toast here
  };

  if (loading) return <div className="flex justify-center py-12"><LoadingSpinner size="lg" /></div>;
  if (!chapter) return <div className="text-center py-12">Chapter not found</div>;

  // Parse sections from chapter data
  const sections = chapter.sections || [];
  const hasSections = sections && sections.length > 0;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <Button variant="outline" size="sm" onClick={() => navigate('/chapters')} className="mb-4">
        ← Back to Chapters
      </Button>

      <Card>
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-start justify-between mb-4">
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-gray-900 mb-2">{chapter.title}</h1>
              {chapter.summary && (
                <p className="text-gray-600">{chapter.summary}</p>
              )}
            </div>
            <div className="flex gap-2 items-start">
              <Badge status={chapter.generation_status} />
              {chapter.version && (
                <Badge className="bg-purple-100 text-purple-800">
                  v{chapter.version}
                </Badge>
              )}
            </div>
          </div>

          {/* Metadata Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600 bg-gray-50 p-4 rounded-lg mb-4">
            <div>
              <span className="font-medium">Created:</span> {formatDate(chapter.created_at)}
            </div>
            <div>
              <span className="font-medium">Type:</span> {chapter.chapter_type || 'N/A'}
            </div>
            <div>
              <span className="font-medium">Words:</span> {chapter.total_words || chapter.word_count || 0}
            </div>
            <div>
              <span className="font-medium">Sections:</span> {chapter.total_sections || sections.length || 0}
            </div>
          </div>

          {/* Quality Scores */}
          {chapter.quality_scores && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm bg-blue-50 p-4 rounded-lg mb-4">
              <div>
                <span className="font-medium text-blue-900">Depth:</span>{' '}
                <span className="text-blue-700">{(chapter.quality_scores.depth * 100).toFixed(1)}%</span>
              </div>
              <div>
                <span className="font-medium text-blue-900">Coverage:</span>{' '}
                <span className="text-blue-700">{(chapter.quality_scores.coverage * 100).toFixed(1)}%</span>
              </div>
              <div>
                <span className="font-medium text-blue-900">Currency:</span>{' '}
                <span className="text-blue-700">{(chapter.quality_scores.currency * 100).toFixed(1)}%</span>
              </div>
              <div>
                <span className="font-medium text-blue-900">Evidence:</span>{' '}
                <span className="text-blue-700">{(chapter.quality_scores.evidence * 100).toFixed(1)}%</span>
              </div>
            </div>
          )}

          {/* Gap Analysis Panel - Phase 2 Week 5 */}
          {chapter.generation_status === 'completed' && (
            <div className="mb-4">
              <GapAnalysisPanel chapterId={id} initialData={chapter.gap_analysis_summary} />
            </div>
          )}

          {/* Action Bar */}
          <div className="flex gap-2 items-center justify-between border-t border-b border-gray-200 py-3">
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setEditMode(!editMode)}
                className={editMode ? 'bg-blue-50 text-blue-700' : ''}
              >
                {editMode ? '📖 View Mode' : '✏️ Edit Mode'}
              </Button>
              <SourceAdder chapterId={id} onSourcesAdded={handleSourcesAdded} />
            </div>
            <div className="text-xs text-gray-500">
              {editMode ? 'Edit individual sections below' : 'Enable edit mode to modify sections'}
            </div>
          </div>
        </div>

        {/* Content Display */}
        {hasSections && editMode ? (
          /* Section-by-Section Editing */
          <div className="space-y-6">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <h3 className="font-semibold text-blue-900 mb-1">✏️ Section Editing Mode</h3>
              <p className="text-sm text-blue-700">
                Edit sections individually or use AI to regenerate them. All changes create new versions automatically.
              </p>
            </div>

            {sections.map((section, index) => (
              <SectionEditor
                key={index}
                chapterId={id}
                section={section}
                sectionNumber={index}
                onSave={handleSectionSave}
                onRegenerate={handleSectionRegenerate}
              />
            ))}
          </div>
        ) : hasSections ? (
          /* Read-Only View by Sections */
          <div className="space-y-8">
            {sections.map((section, index) => (
              <div key={index} className="border-b border-gray-200 pb-6 last:border-b-0">
                <h2 className="text-2xl font-semibold text-gray-900 mb-3">
                  {section.title || `Section ${index + 1}`}
                </h2>
                <div
                  className="prose max-w-none"
                  dangerouslySetInnerHTML={{ __html: section.content || '<p>No content</p>' }}
                />
                {section.word_count && (
                  <div className="mt-3 text-sm text-gray-500">
                    {section.word_count} words
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          /* Fallback for chapters without sections array */
          <div className="prose max-w-none">
            <div dangerouslySetInnerHTML={{ __html: chapter.content || '<p>No content available</p>' }} />
          </div>
        )}

        {/* Footer Info */}
        {chapter.generation_cost_usd && (
          <div className="mt-8 pt-6 border-t border-gray-200 text-sm text-gray-500">
            Generation cost: ${chapter.generation_cost_usd.toFixed(4)}
          </div>
        )}
      </Card>
    </div>
  );
};

export default ChapterDetail;
