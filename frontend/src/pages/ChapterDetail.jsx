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
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
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

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await chaptersAPI.delete(id);
      navigate('/chapters');
    } catch (error) {
      console.error('Failed to delete chapter:', error);
      alert('Failed to delete chapter: ' + (error.response?.data?.detail || error.message));
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
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
              <Button
                variant="danger"
                size="sm"
                onClick={() => setShowDeleteConfirm(true)}
              >
                🗑️ Delete
              </Button>
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
            <div className="bg-blue-50 p-4 rounded-lg mb-4">
              {/* Overall Quality Score - Prominent Display */}
              <div className="flex items-center justify-between mb-4 pb-4 border-b border-blue-200">
                <div>
                  <h3 className="text-sm font-semibold text-blue-900 mb-1">Overall Quality Score</h3>
                  <p className="text-xs text-blue-700">Average of depth, coverage, currency, and evidence scores</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <div className="text-3xl font-bold text-blue-900">
                      {(chapter.quality_scores.overall * 100).toFixed(1)}%
                    </div>
                  </div>
                  <Badge className={`text-sm py-1 px-3 ${
                    chapter.quality_scores.rating === 'Excellent' ? 'bg-green-100 text-green-800 border-green-300' :
                    chapter.quality_scores.rating === 'Good' ? 'bg-blue-100 text-blue-800 border-blue-300' :
                    chapter.quality_scores.rating === 'Fair' ? 'bg-yellow-100 text-yellow-800 border-yellow-300' :
                    'bg-red-100 text-red-800 border-red-300'
                  }`}>
                    {chapter.quality_scores.rating}
                  </Badge>
                </div>
              </div>

              {/* Individual Score Breakdown */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
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
            </div>
          )}

          {/* Generation Confidence - Phase 22 Part 4 */}
          {chapter.generation_confidence && (
            <div className="relative group bg-gradient-to-r from-indigo-50 to-purple-50 p-4 rounded-lg mb-4 border border-indigo-200">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-indigo-900 mb-1 flex items-center gap-2">
                    <span>Generation Confidence</span>
                    <span className="text-xs text-indigo-600 font-normal">ℹ️ Hover for details</span>
                  </h3>
                  <p className="text-xs text-indigo-700">
                    AI-powered quality assurance across generation pipeline
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <div className="text-3xl font-bold text-indigo-900">
                      {(chapter.generation_confidence.overall * 100).toFixed(1)}%
                    </div>
                  </div>
                  <Badge className={`text-sm py-1 px-3 ${
                    chapter.generation_confidence.rating === 'Very High' ? 'bg-green-100 text-green-800 border-green-300' :
                    chapter.generation_confidence.rating === 'High' ? 'bg-blue-100 text-blue-800 border-blue-300' :
                    chapter.generation_confidence.rating === 'Moderate' ? 'bg-yellow-100 text-yellow-800 border-yellow-300' :
                    'bg-red-100 text-red-800 border-red-300'
                  }`}>
                    {chapter.generation_confidence.rating}
                  </Badge>
                </div>
              </div>

              {/* Hover Breakdown Tooltip */}
              <div className="invisible group-hover:visible absolute left-0 right-0 top-full mt-2 bg-white rounded-lg shadow-xl border border-indigo-300 p-4 z-10 transition-all duration-200">
                <div className="text-xs font-semibold text-gray-900 mb-3 border-b pb-2">
                  Confidence Breakdown
                </div>
                <div className="space-y-3">
                  {/* Analysis Confidence */}
                  {chapter.generation_confidence.breakdown.components.analysis && (
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex-1">
                        <div className="font-medium text-gray-900">Topic Analysis</div>
                        <div className="text-gray-600">
                          {chapter.generation_confidence.breakdown.components.analysis.description}
                        </div>
                      </div>
                      <div className="ml-4 text-right">
                        <div className="font-bold text-indigo-900">
                          {(chapter.generation_confidence.breakdown.components.analysis.score * 100).toFixed(1)}%
                        </div>
                        <div className="text-gray-500">
                          Weight: {(chapter.generation_confidence.breakdown.components.analysis.weight * 100).toFixed(0)}%
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Research Confidence */}
                  {chapter.generation_confidence.breakdown.components.research && (
                    <div className="flex items-center justify-between text-xs border-t pt-2">
                      <div className="flex-1">
                        <div className="font-medium text-gray-900">Research Quality</div>
                        <div className="text-gray-600">
                          {chapter.generation_confidence.breakdown.components.research.description}
                        </div>
                      </div>
                      <div className="ml-4 text-right">
                        <div className="font-bold text-indigo-900">
                          {(chapter.generation_confidence.breakdown.components.research.score * 100).toFixed(1)}%
                        </div>
                        <div className="text-gray-500">
                          Weight: {(chapter.generation_confidence.breakdown.components.research.weight * 100).toFixed(0)}%
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Fact-Check Confidence */}
                  {chapter.generation_confidence.breakdown.components.fact_check && (
                    <div className="flex items-center justify-between text-xs border-t pt-2">
                      <div className="flex-1">
                        <div className="font-medium text-gray-900">Medical Accuracy</div>
                        <div className="text-gray-600">
                          {chapter.generation_confidence.breakdown.components.fact_check.description}
                        </div>
                      </div>
                      <div className="ml-4 text-right">
                        <div className="font-bold text-indigo-900">
                          {(chapter.generation_confidence.breakdown.components.fact_check.score * 100).toFixed(1)}%
                        </div>
                        <div className="text-gray-500">
                          Weight: {(chapter.generation_confidence.breakdown.components.fact_check.weight * 100).toFixed(0)}%
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Formula Explanation */}
                <div className="mt-3 pt-3 border-t text-xs text-gray-600">
                  <span className="font-medium">Formula:</span> Overall = (Analysis × 20%) + (Research × 30%) + (Fact-Check × 50%)
                </div>
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

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <Card className="max-w-md w-full">
            <h2 className="text-xl font-bold text-gray-900 mb-3">Delete Chapter?</h2>
            <p className="text-gray-700 mb-4">
              Are you sure you want to delete "{chapter.title}"? This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <Button
                variant="outline"
                onClick={() => setShowDeleteConfirm(false)}
                disabled={deleting}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                onClick={handleDelete}
                disabled={deleting}
              >
                {deleting ? 'Deleting...' : 'Delete Chapter'}
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};

export default ChapterDetail;
