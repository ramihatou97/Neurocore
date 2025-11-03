/**
 * TextbookChapterDetail Page
 * Detailed view of a chapter with embedding visualization and similarity analysis
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { textbookAPI } from '../api';
import Card from '../components/Card';
import Button from '../components/Button';
import Badge from '../components/Badge';
import LoadingSpinner from '../components/LoadingSpinner';
import Alert from '../components/Alert';
import EmbeddingHeatmap from '../components/EmbeddingHeatmap';
import EmbeddingStatsChart from '../components/EmbeddingStatsChart';

const TextbookChapterDetail = () => {
  const { chapterId } = useParams();
  const navigate = useNavigate();

  // State
  const [chapter, setChapter] = useState(null);
  const [embedding, setEmbedding] = useState(null);
  const [similarChapters, setSimilarChapters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showFullEmbedding, setShowFullEmbedding] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    loadChapterData();
  }, [chapterId]);

  const loadChapterData = async () => {
    try {
      setLoading(true);
      setError('');

      // Load chapter details, embedding, and similar chapters in parallel
      const [chapterData, embeddingData] = await Promise.all([
        textbookAPI.getChapter(chapterId),
        textbookAPI.getChapterEmbedding(chapterId).catch(() => null)
      ]);

      setChapter(chapterData);
      setEmbedding(embeddingData);

      // Load similar chapters if embedding exists
      if (embeddingData && embeddingData.has_embedding) {
        const similarData = await textbookAPI.getSimilarChapters(chapterId, 10);
        setSimilarChapters(similarData.similar_chapters || []);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load chapter details');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    try {
      setDeleting(true);
      await textbookAPI.deleteChapter(chapterId);
      navigate('/textbooks', {
        state: { message: 'Chapter deleted successfully' }
      });
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete chapter');
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  const getSimilarityColor = (score) => {
    if (score >= 0.95) return 'bg-red-100 text-red-800';
    if (score >= 0.85) return 'bg-orange-100 text-orange-800';
    if (score >= 0.75) return 'bg-yellow-100 text-yellow-800';
    if (score >= 0.65) return 'bg-blue-100 text-blue-800';
    return 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <LoadingSpinner size="xl" />
      </div>
    );
  }

  if (!chapter) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <Alert type="error" message="Chapter not found" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-6">
          <Button
            variant="outline"
            onClick={() => navigate('/textbooks')}
            className="mb-4"
          >
            ← Back to Library
          </Button>

          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                {chapter.chapter_title}
              </h1>
              {chapter.chapter_number && (
                <p className="text-lg text-gray-700">
                  Chapter {chapter.chapter_number}
                </p>
              )}
            </div>
            <Button
              variant="danger"
              onClick={() => setShowDeleteConfirm(true)}
              disabled={deleting}
            >
              🗑️ Delete Chapter
            </Button>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <Alert
            type="error"
            message={error}
            onClose={() => setError('')}
            className="mb-6"
          />
        )}

        {/* Chapter Metadata */}
        <Card className="mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Chapter Information</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-gray-600">Source Type</p>
              <p className="text-base font-medium text-gray-900">{chapter.source_type}</p>
            </div>
            {chapter.start_page && (
              <div>
                <p className="text-sm text-gray-600">Pages</p>
                <p className="text-base font-medium text-gray-900">
                  {chapter.start_page}-{chapter.end_page} ({chapter.page_count} pages)
                </p>
              </div>
            )}
            <div>
              <p className="text-sm text-gray-600">Word Count</p>
              <p className="text-base font-medium text-gray-900">{chapter.word_count?.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Images</p>
              <p className="text-base font-medium text-gray-900">{chapter.image_count} images</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Quality Score</p>
              <p className="text-base font-medium text-gray-900">{(chapter.quality_score * 100).toFixed(0)}%</p>
            </div>
            {chapter.detection_method && (
              <div>
                <p className="text-sm text-gray-600">Detection Method</p>
                <p className="text-base font-medium text-gray-900">
                  {chapter.detection_method} ({(chapter.detection_confidence * 100).toFixed(0)}%)
                </p>
              </div>
            )}
            <div>
              <p className="text-sm text-gray-600">Embedding Status</p>
              <div>
                {chapter.has_embedding ? (
                  <Badge variant="success">✓ Indexed</Badge>
                ) : (
                  <Badge variant="default">Pending</Badge>
                )}
              </div>
            </div>
            <div>
              <p className="text-sm text-gray-600">Duplicate Status</p>
              <div>
                {chapter.is_duplicate ? (
                  <Badge variant="warning">Duplicate</Badge>
                ) : (
                  <Badge variant="success">Unique</Badge>
                )}
              </div>
            </div>
          </div>
        </Card>

        {/* Chapter Content - Issue #1 Fix */}
        {chapter.extracted_text && (
          <Card className="mb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Chapter Content</h2>
            <div className="prose max-w-none">
              <div className="bg-white rounded-lg p-6 border border-gray-200">
                <pre className="whitespace-pre-wrap font-sans text-sm text-gray-900 leading-relaxed">
                  {chapter.extracted_text}
                </pre>
              </div>
            </div>
            <div className="mt-4 text-sm text-gray-600">
              {chapter.word_count?.toLocaleString()} words • {chapter.page_count} pages
              {chapter.book_title && ` • From: ${chapter.book_title}`}
            </div>
          </Card>
        )}

        {/* Embedding Source Context - Issue #3 Enhancement */}
        {chapter.has_embedding && (
          <Card className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">
              Embedded Content Context
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              Natural language labels showing what text was embedded for vector search
            </p>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 space-y-3">
              <div>
                <p className="text-xs font-medium text-blue-900 mb-1">Source</p>
                <p className="text-sm text-blue-800">
                  {chapter.book_title ? `${chapter.book_title} - ` : ''}
                  {chapter.chapter_title}
                  {chapter.chapter_number ? ` (Chapter ${chapter.chapter_number})` : ''}
                </p>
              </div>
              {(chapter.start_page && chapter.end_page) && (
                <div>
                  <p className="text-xs font-medium text-blue-900 mb-1">Page Range</p>
                  <p className="text-sm text-blue-800">
                    Pages {chapter.start_page}-{chapter.end_page} ({chapter.page_count} pages)
                  </p>
                </div>
              )}
              <div>
                <p className="text-xs font-medium text-blue-900 mb-1">Content Size</p>
                <p className="text-sm text-blue-800">
                  {chapter.word_count?.toLocaleString()} words
                </p>
              </div>
              {chapter.extracted_text_preview && (
                <div>
                  <p className="text-xs font-medium text-blue-900 mb-1">Text Preview (First 500 chars)</p>
                  <p className="text-sm text-blue-800 italic leading-relaxed">
                    "{chapter.extracted_text_preview}"
                  </p>
                </div>
              )}
              <div>
                <p className="text-xs font-medium text-blue-900 mb-1">Embedding Model</p>
                <p className="text-sm text-blue-800">
                  {chapter.embedding_model || 'text-embedding-3-large'} (1536 dimensions)
                </p>
              </div>
              {chapter.embedding_generated_at && (
                <div>
                  <p className="text-xs font-medium text-blue-900 mb-1">Generated At</p>
                  <p className="text-sm text-blue-800">
                    {new Date(chapter.embedding_generated_at).toLocaleString()}
                  </p>
                </div>
              )}
            </div>
            <p className="mt-3 text-xs text-gray-500">
              💡 This context helps you understand what text is being searched when using vector similarity
            </p>
          </Card>
        )}

        {/* Embedding Visualization */}
        {embedding && embedding.has_embedding && (
          <>
            {/* Embedding Preview */}
            <Card className="mb-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Embedding Vector Preview
              </h2>
              <p className="text-sm text-gray-600 mb-4">
                1536-dimensional vector generated by OpenAI text-embedding-3-large
              </p>

              {/* First 20 dimensions */}
              <div className="mb-4">
                <p className="text-sm font-medium text-gray-900 mb-2">
                  First 20 dimensions:
                </p>
                <div className="bg-gray-50 rounded-lg p-4 font-mono text-xs overflow-x-auto">
                  <div className="flex flex-wrap gap-2">
                    {embedding.embedding_preview?.map((value, index) => (
                      <span
                        key={index}
                        className="px-2 py-1 bg-white rounded border border-gray-200 text-gray-900"
                      >
                        [{index}]: {value.toFixed(6)}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Embedding Statistics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <div>
                  <p className="text-sm text-gray-600">Dimensions</p>
                  <p className="text-lg font-medium text-gray-900">{embedding.embedding_dimensions}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Min Value</p>
                  <p className="text-lg font-medium text-gray-900">
                    {Math.min(...embedding.embedding).toFixed(6)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Max Value</p>
                  <p className="text-lg font-medium text-gray-900">
                    {Math.max(...embedding.embedding).toFixed(6)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Mean Value</p>
                  <p className="text-lg font-medium text-gray-900">
                    {(embedding.embedding.reduce((a, b) => a + b, 0) / embedding.embedding.length).toFixed(6)}
                  </p>
                </div>
              </div>

              {/* Full Embedding Toggle */}
              <Button
                variant="outline"
                onClick={() => setShowFullEmbedding(!showFullEmbedding)}
                className="w-full"
              >
                {showFullEmbedding ? '▲ Hide' : '▼ Show'} Full Embedding Vector (1536 dimensions)
              </Button>

              {showFullEmbedding && (
                <div className="mt-4 bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-medium text-gray-900">Complete Vector Data (JSON)</p>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        navigator.clipboard.writeText(JSON.stringify(embedding.embedding, null, 2));
                        alert('Embedding vector copied to clipboard!');
                      }}
                    >
                      📋 Copy JSON
                    </Button>
                  </div>
                  <pre className="bg-white rounded border border-gray-200 p-4 overflow-x-auto text-xs font-mono text-gray-900 max-h-96 overflow-y-auto">
                    {JSON.stringify(embedding.embedding, null, 2)}
                  </pre>
                </div>
              )}

              {/* Statistical Analysis */}
              <div className="mt-6 pt-6 border-t border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900 mb-3">
                  Statistical Analysis
                </h3>
                <p className="text-sm text-gray-600 mb-4">
                  Statistical distribution of embedding values across all dimensions.
                  Shows the frequency and spread of values.
                </p>
                <EmbeddingStatsChart embedding={embedding.embedding} />
              </div>

              {/* Visual Heatmap */}
              <div className="mt-6 pt-6 border-t border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900 mb-3">
                  Visual Heatmap
                </h3>
                <p className="text-sm text-gray-600 mb-4">
                  Color-coded visualization of all 1536 dimensions. Each cell represents one dimension:
                  blue indicates negative values, red indicates positive values, and white is near zero.
                  Hover over cells to see exact values.
                </p>
                <EmbeddingHeatmap embedding={embedding.embedding} />
              </div>
            </Card>

            {/* Similar Chapters */}
            {similarChapters.length > 0 && (
              <Card className="mb-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                  Similar Chapters
                </h2>
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                  <p className="text-sm text-blue-900 mb-2">
                    <strong>What is similarity?</strong> Similarity scores are calculated using cosine similarity
                    between embedding vectors. This measures how semantically related the content is.
                  </p>
                  <div className="text-xs text-blue-800 space-y-1">
                    <p>• <strong>95%+:</strong> Very high similarity - likely covers the same surgical techniques, anatomical regions, or clinical scenarios</p>
                    <p>• <strong>85-95%:</strong> High similarity - related topics with overlapping concepts (e.g., different approaches to same condition)</p>
                    <p>• <strong>75-85%:</strong> Moderate similarity - shares some key concepts but different focus areas</p>
                    <p>• <strong>60-75%:</strong> Low similarity - limited overlap, possibly related subspecialty or adjacent anatomy</p>
                  </div>
                </div>

                <div className="space-y-3">
                  {similarChapters.map((similar, index) => (
                    <div
                      key={similar.id}
                      className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer"
                      onClick={() => navigate(`/textbooks/chapters/${similar.id}`)}
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-1">
                          <span className="text-sm font-medium text-gray-500">#{index + 1}</span>
                          <h3 className="text-base font-medium text-gray-900">
                            {similar.chapter_title}
                          </h3>
                          {similar.is_duplicate && (
                            <Badge variant="warning">Duplicate</Badge>
                          )}
                        </div>
                        {similar.chapter_number && (
                          <p className="text-sm text-gray-600 ml-10">
                            Chapter {similar.chapter_number}
                          </p>
                        )}
                      </div>
                      <div className="ml-4">
                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${getSimilarityColor(similar.similarity_score)}`}>
                          {(similar.similarity_score * 100).toFixed(1)}% similar
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </>
        )}

        {/* No Embedding Message */}
        {(!embedding || !embedding.has_embedding) && (
          <Card>
            <div className="text-center py-8">
              <div className="text-4xl mb-3">⏳</div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Embedding Generation Pending
              </h3>
              <p className="text-gray-600">
                This chapter is being processed. Embeddings will be available shortly.
              </p>
            </div>
          </Card>
        )}

        {/* Delete Confirmation Modal */}
        {showDeleteConfirm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <Card className="max-w-md w-full mx-4">
              <h3 className="text-xl font-semibold text-gray-900 mb-4">
                Delete Chapter?
              </h3>
              <p className="text-gray-700 mb-6">
                Are you sure you want to delete "{chapter.chapter_title}"? This action cannot be undone and will also delete all associated chunks.
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
    </div>
  );
};

export default TextbookChapterDetail;
