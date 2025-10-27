/**
 * QAInterface Component
 * AI-powered Q&A interface using RAG over knowledge base
 */

import { useState, useEffect, useRef } from 'react';
import Card from './Card';
import Button from './Button';
import Input from './Input';
import LoadingSpinner from './LoadingSpinner';
import Alert from './Alert';
import Badge from './Badge';

const QAInterface = ({
  sessionId = null,
  onSessionStart = null,
  showHistory = true,
  autoFocus = false
}) => {
  const [question, setQuestion] = useState('');
  const [conversation, setConversation] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentSessionId, setCurrentSessionId] = useState(sessionId);
  const [history, setHistory] = useState([]);
  const [showHistorySidebar, setShowHistorySidebar] = useState(false);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus]);

  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  useEffect(() => {
    if (showHistory) {
      fetchHistory();
    }
  }, [showHistory]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchHistory = async () => {
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams({ limit: '10' });
      if (currentSessionId) {
        params.append('session_id', currentSessionId);
      }

      const response = await fetch(
        `/api/v1/ai/qa/history?${params.toString()}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (response.ok) {
        const data = await response.json();
        setHistory(data.history || []);
      }
    } catch (err) {
      console.error('Error fetching history:', err);
    }
  };

  const handleAskQuestion = async (e) => {
    e.preventDefault();

    if (!question.trim()) {
      return;
    }

    const userQuestion = question.trim();
    setQuestion('');
    setError(null);
    setLoading(true);

    // Add user question to conversation
    setConversation(prev => [...prev, {
      type: 'question',
      text: userQuestion,
      timestamp: new Date()
    }]);

    try {
      const token = localStorage.getItem('token');

      // Generate session ID if not exists
      let session = currentSessionId;
      if (!session) {
        session = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        setCurrentSessionId(session);
        if (onSessionStart) {
          onSessionStart(session);
        }
      }

      const response = await fetch('/api/v1/ai/qa/ask', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          question: userQuestion,
          session_id: session,
          max_context_docs: 5
        })
      });

      if (!response.ok) {
        throw new Error('Failed to get answer');
      }

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      // Add answer to conversation
      setConversation(prev => [...prev, {
        type: 'answer',
        text: data.answer,
        confidence: data.confidence,
        sources: data.sources || [],
        id: data.id,
        timestamp: new Date()
      }]);

      // Refresh history
      if (showHistory) {
        fetchHistory();
      }
    } catch (err) {
      console.error('Error asking question:', err);
      setError(err.message || 'Failed to get answer. Please try again.');

      // Remove the last question since it failed
      setConversation(prev => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (qaId, helpful) => {
    try {
      const token = localStorage.getItem('token');
      await fetch(`/api/v1/ai/qa/${qaId}/feedback`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          was_helpful: helpful
        })
      });

      // Update conversation to reflect feedback
      setConversation(prev => prev.map(msg =>
        msg.id === qaId ? { ...msg, feedback: helpful } : msg
      ));
    } catch (err) {
      console.error('Error submitting feedback:', err);
    }
  };

  const loadHistoryItem = (item) => {
    setConversation([
      {
        type: 'question',
        text: item.question,
        timestamp: new Date(item.asked_at)
      },
      {
        type: 'answer',
        text: item.answer,
        confidence: item.confidence,
        sources: item.sources || [],
        id: item.id,
        timestamp: new Date(item.asked_at)
      }
    ]);
    setShowHistorySidebar(false);
  };

  const clearConversation = () => {
    setConversation([]);
    setCurrentSessionId(null);
    setError(null);
  };

  return (
    <div className="flex gap-4 h-full">
      {/* Main Q&A Interface */}
      <div className="flex-1">
        <Card className="flex flex-col h-full">
          {/* Header */}
          <div className="p-4 border-b border-gray-200 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                Ask the Knowledge Base
              </h3>
              <p className="text-xs text-gray-600 mt-1">
                AI-powered answers using RAG over neurosurgery content
              </p>
            </div>
            <div className="flex items-center gap-2">
              {showHistory && (
                <Button
                  onClick={() => setShowHistorySidebar(!showHistorySidebar)}
                  variant="ghost"
                  size="sm"
                >
                  History
                </Button>
              )}
              {conversation.length > 0 && (
                <Button
                  onClick={clearConversation}
                  variant="ghost"
                  size="sm"
                >
                  Clear
                </Button>
              )}
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {conversation.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center max-w-md">
                  <div className="text-6xl mb-4">💬</div>
                  <h4 className="text-lg font-medium text-gray-900 mb-2">
                    Ask me anything about neurosurgery
                  </h4>
                  <p className="text-sm text-gray-600">
                    I&apos;ll search through the knowledge base and provide accurate answers based on the available content.
                  </p>
                  <div className="mt-4 space-y-2 text-sm text-gray-600 text-left">
                    <p className="font-medium">Example questions:</p>
                    <ul className="list-disc list-inside space-y-1">
                      <li>What are the indications for craniotomy?</li>
                      <li>Explain the management of subdural hematoma</li>
                      <li>What imaging is needed for spinal cord compression?</li>
                    </ul>
                  </div>
                </div>
              </div>
            ) : (
              <>
                {conversation.map((msg, index) => (
                  <div
                    key={index}
                    className={`flex ${msg.type === 'question' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-3xl ${
                        msg.type === 'question'
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-900'
                      } rounded-lg p-4`}
                    >
                      {msg.type === 'question' ? (
                        <p className="text-sm">{msg.text}</p>
                      ) : (
                        <div className="space-y-3">
                          <div className="prose prose-sm max-w-none">
                            <p>{msg.text}</p>
                          </div>

                          {/* Confidence Score */}
                          {msg.confidence !== undefined && (
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-gray-600">Confidence:</span>
                              <Badge variant={msg.confidence > 0.7 ? 'success' : 'warning'}>
                                {Math.round(msg.confidence * 100)}%
                              </Badge>
                            </div>
                          )}

                          {/* Sources */}
                          {msg.sources && msg.sources.length > 0 && (
                            <div className="border-t border-gray-200 pt-2 mt-2">
                              <p className="text-xs font-medium text-gray-700 mb-1">
                                Sources ({msg.sources.length}):
                              </p>
                              <div className="space-y-1">
                                {msg.sources.slice(0, 3).map((source, i) => (
                                  <div key={i} className="text-xs text-gray-600">
                                    📄 {source.title}
                                    {source.similarity && (
                                      <span className="ml-1 text-gray-500">
                                        ({Math.round(source.similarity * 100)}% match)
                                      </span>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Feedback */}
                          {msg.id && msg.feedback === undefined && (
                            <div className="flex items-center gap-2 pt-2 border-t border-gray-200">
                              <span className="text-xs text-gray-600">Was this helpful?</span>
                              <button
                                onClick={() => handleFeedback(msg.id, true)}
                                className="text-xs px-2 py-1 rounded bg-green-100 text-green-700 hover:bg-green-200"
                              >
                                👍 Yes
                              </button>
                              <button
                                onClick={() => handleFeedback(msg.id, false)}
                                className="text-xs px-2 py-1 rounded bg-red-100 text-red-700 hover:bg-red-200"
                              >
                                👎 No
                              </button>
                            </div>
                          )}

                          {msg.feedback !== undefined && (
                            <div className="text-xs text-gray-600 pt-2 border-t border-gray-200">
                              Thanks for your feedback! {msg.feedback ? '👍' : '👎'}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-gray-100 rounded-lg p-4">
                      <LoadingSpinner size="sm" />
                      <span className="ml-2 text-sm text-gray-600">Thinking...</span>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Error */}
          {error && (
            <div className="px-4 pb-2">
              <Alert type="error" onClose={() => setError(null)}>
                {error}
              </Alert>
            </div>
          )}

          {/* Input */}
          <form onSubmit={handleAskQuestion} className="p-4 border-t border-gray-200">
            <div className="flex gap-2">
              <Input
                ref={inputRef}
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask a question about neurosurgery..."
                disabled={loading}
                className="flex-1"
              />
              <Button type="submit" disabled={loading || !question.trim()}>
                {loading ? <LoadingSpinner size="xs" /> : 'Ask'}
              </Button>
            </div>
          </form>
        </Card>
      </div>

      {/* History Sidebar */}
      {showHistorySidebar && showHistory && (
        <div className="w-80">
          <Card className="p-4 h-full overflow-y-auto">
            <h4 className="text-sm font-semibold text-gray-900 mb-3">Recent Questions</h4>
            {history.length === 0 ? (
              <p className="text-sm text-gray-600">No history yet</p>
            ) : (
              <div className="space-y-2">
                {history.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => loadHistoryItem(item)}
                    className="w-full text-left p-3 rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition-all"
                  >
                    <p className="text-sm font-medium text-gray-900 line-clamp-2">
                      {item.question}
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      {item.confidence && (
                        <Badge variant="default" className="text-xs">
                          {Math.round(item.confidence * 100)}%
                        </Badge>
                      )}
                      {item.was_helpful !== null && (
                        <span className="text-xs">
                          {item.was_helpful ? '👍' : '👎'}
                        </span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
};

export default QAInterface;
