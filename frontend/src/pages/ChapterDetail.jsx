/**
 * Chapter Detail Page
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, LoadingSpinner, Badge, Button } from '../components';
import { chaptersAPI } from '../api';
import { formatDate } from '../utils/helpers';

const ChapterDetail = () => {
  const { id } = useParams();
  const [chapter, setChapter] = useState(null);
  const [loading, setLoading] = useState(true);
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

  if (loading) return <div className="flex justify-center py-12"><LoadingSpinner size="lg" /></div>;
  if (!chapter) return <div className="text-center py-12">Chapter not found</div>;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <Button variant="outline" size="sm" onClick={() => navigate('/chapters')} className="mb-4">
        ← Back to Chapters
      </Button>

      <Card>
        <div className="mb-6">
          <div className="flex items-start justify-between mb-4">
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-gray-900 mb-2">{chapter.title}</h1>
              <p className="text-gray-600">{chapter.summary}</p>
            </div>
            <Badge status={chapter.generation_status} />
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm text-gray-600 bg-gray-50 p-4 rounded-lg">
            <div>
              <span className="font-medium">Created:</span> {formatDate(chapter.created_at)}
            </div>
            <div>
              <span className="font-medium">Type:</span> {chapter.chapter_type || 'N/A'}
            </div>
            <div>
              <span className="font-medium">Word Count:</span> {chapter.word_count || 0}
            </div>
            <div>
              <span className="font-medium">Sections:</span> {chapter.section_count || 0}
            </div>
          </div>
        </div>

        <div className="prose max-w-none">
          <div dangerouslySetInnerHTML={{ __html: chapter.content || '<p>No content available</p>' }} />
        </div>
      </Card>
    </div>
  );
};

export default ChapterDetail;
