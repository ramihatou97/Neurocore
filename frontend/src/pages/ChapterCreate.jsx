/**
 * Chapter Create Page
 * Generate new chapter with real-time progress updates via WebSocket
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Input, Button, Alert, ProgressBar } from '../components';
import { chaptersAPI } from '../api';
import { useChapterWebSocket } from '../hooks/useWebSocket';
import { CHAPTER_STAGES, CHAPTER_TYPES } from '../utils/constants';

const ChapterCreate = () => {
  const [topic, setTopic] = useState('');
  const [chapterType, setChapterType] = useState('detailed');
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const [chapterId, setChapterId] = useState(null);
  const [progress, setProgress] = useState({
    stage: '',
    stageNumber: 0,
    totalStages: 14,
    progress_percent: 0,
    message: '',
  });

  const navigate = useNavigate();

  // WebSocket connection for real-time updates
  const { isConnected } = useChapterWebSocket(chapterId, {
    onMessage: (data) => {
      console.log('WebSocket message:', data);

      if (data.event === 'chapter_progress') {
        setProgress({
          stage: data.data.stage_name || data.data.stage,
          stageNumber: data.data.stage_number,
          totalStages: data.data.total_stages || 14,
          progress_percent: data.data.progress_percent,
          message: data.data.message,
        });
      } else if (data.event === 'chapter_completed') {
        setGenerating(false);
        setTimeout(() => {
          navigate(`/chapters/${chapterId}`);
        }, 2000);
      } else if (data.event === 'chapter_failed') {
        setError(data.data.error_message || 'Chapter generation failed');
        setGenerating(false);
      }
    },
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!topic.trim()) {
      setError('Please enter a topic');
      return;
    }

    try {
      setGenerating(true);
      const response = await chaptersAPI.generate({
        topic: topic.trim(),
        chapter_type: chapterType,
      });

      setChapterId(response.chapter_id);
      setProgress({
        stage: 'Starting generation...',
        stageNumber: 0,
        totalStages: 14,
        progress_percent: 0,
        message: 'Initializing chapter generation',
      });
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start chapter generation');
      setGenerating(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Generate New Chapter</h1>
        <p className="text-gray-600 mt-2">
          Create AI-powered neurosurgery chapters with real-time generation
        </p>
      </div>

      <Card>
        {!generating ? (
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && <Alert type="error" message={error} onClose={() => setError('')} />}

            <Input
              label="Chapter Topic"
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g., Glioblastoma Treatment Approaches"
              required
            />

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Chapter Type
              </label>
              <select
                value={chapterType}
                onChange={(e) => setChapterType(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="overview">Overview - High-level summary</option>
                <option value="detailed">Detailed - Comprehensive analysis</option>
                <option value="clinical">Clinical - Practice-focused</option>
                <option value="research">Research - Evidence-based</option>
              </select>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="font-medium text-blue-900 mb-2">14-Stage Generation Process</h3>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>• Input validation and context building</li>
                <li>• Internal & external research</li>
                <li>• Image search and synthesis</li>
                <li>• Content drafting and enrichment</li>
                <li>• Citation & image integration</li>
                <li>• Quality assurance and formatting</li>
              </ul>
            </div>

            <Button type="submit" fullWidth size="lg">
              Start Generation
            </Button>
          </form>
        ) : (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-2xl font-semibold text-gray-900 mb-2">
                Generating Chapter...
              </h2>
              <p className="text-gray-600">
                WebSocket: {isConnected ? '✓ Connected' : '⏳ Connecting...'}
              </p>
            </div>

            <div className="bg-gray-50 rounded-lg p-6 space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">
                    Stage {progress.stageNumber}/{progress.totalStages}
                  </span>
                  <span className="text-sm font-medium text-blue-600">
                    {progress.stage}
                  </span>
                </div>
                <ProgressBar progress={progress.progress_percent} />
              </div>

              <div className="text-sm text-gray-600">
                {progress.message || 'Processing...'}
              </div>

              {/* Stage Timeline */}
              <div className="mt-6 space-y-2">
                <p className="text-xs font-medium text-gray-700 mb-3">Generation Stages:</p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {Object.entries(CHAPTER_STAGES).map(([key, name], index) => {
                    const stageNum = index + 1;
                    const isActive = stageNum === progress.stageNumber;
                    const isComplete = stageNum < progress.stageNumber;

                    return (
                      <div
                        key={key}
                        className={`px-2 py-1 rounded ${
                          isActive
                            ? 'bg-blue-600 text-white font-medium'
                            : isComplete
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {isComplete && '✓ '}
                        {stageNum}. {name}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            <Alert
              type="info"
              message="Chapter generation typically takes 2-5 minutes. You can navigate away and check progress later."
            />
          </div>
        )}
      </Card>
    </div>
  );
};

export default ChapterCreate;
