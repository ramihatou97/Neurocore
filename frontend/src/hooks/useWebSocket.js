/**
 * useWebSocket Hook
 * React hook for WebSocket connections with auto-cleanup
 */

import { useEffect, useState, useCallback } from 'react';
import websocketClient from '../services/websocket';

/**
 * Hook for chapter WebSocket connection
 */
export const useChapterWebSocket = (chapterId, handlers = {}) => {
  const [status, setStatus] = useState('disconnected');
  const [lastMessage, setLastMessage] = useState(null);

  useEffect(() => {
    if (!chapterId) return;

    // Connect to chapter WebSocket
    const ws = websocketClient.connectToChapter(chapterId, {
      onOpen: () => {
        setStatus('connected');
        handlers.onOpen?.();
      },
      onMessage: (data) => {
        setLastMessage(data);
        handlers.onMessage?.(data);
      },
      onError: (error) => {
        setStatus('error');
        handlers.onError?.(error);
      },
      onClose: () => {
        setStatus('closed');
        handlers.onClose?.();
      },
    });

    // Update status
    setStatus(websocketClient.getStatus(`chapter:${chapterId}`));

    // Cleanup on unmount
    return () => {
      websocketClient.disconnect(`chapter:${chapterId}`);
    };
  }, [chapterId]);

  const send = useCallback((message) => {
    return websocketClient.send(`chapter:${chapterId}`, message);
  }, [chapterId]);

  return {
    status,
    lastMessage,
    send,
    isConnected: status === 'connected',
  };
};

/**
 * Hook for task WebSocket connection
 */
export const useTaskWebSocket = (taskId, handlers = {}) => {
  const [status, setStatus] = useState('disconnected');
  const [lastMessage, setLastMessage] = useState(null);

  useEffect(() => {
    if (!taskId) return;

    // Connect to task WebSocket
    const ws = websocketClient.connectToTask(taskId, {
      onOpen: () => {
        setStatus('connected');
        handlers.onOpen?.();
      },
      onMessage: (data) => {
        setLastMessage(data);
        handlers.onMessage?.(data);
      },
      onError: (error) => {
        setStatus('error');
        handlers.onError?.(error);
      },
      onClose: () => {
        setStatus('closed');
        handlers.onClose?.();
      },
    });

    // Update status
    setStatus(websocketClient.getStatus(`task:${taskId}`));

    // Cleanup on unmount
    return () => {
      websocketClient.disconnect(`task:${taskId}`);
    };
  }, [taskId]);

  const send = useCallback((message) => {
    return websocketClient.send(`task:${taskId}`, message);
  }, [taskId]);

  return {
    status,
    lastMessage,
    send,
    isConnected: status === 'connected',
  };
};

/**
 * Hook for notifications WebSocket connection
 */
export const useNotificationsWebSocket = (handlers = {}) => {
  const [status, setStatus] = useState('disconnected');
  const [lastMessage, setLastMessage] = useState(null);

  useEffect(() => {
    // Connect to notifications WebSocket
    const ws = websocketClient.connectToNotifications({
      onOpen: () => {
        setStatus('connected');
        handlers.onOpen?.();
      },
      onMessage: (data) => {
        setLastMessage(data);
        handlers.onMessage?.(data);
      },
      onError: (error) => {
        setStatus('error');
        handlers.onError?.(error);
      },
      onClose: () => {
        setStatus('closed');
        handlers.onClose?.();
      },
    });

    // Update status
    setStatus(websocketClient.getStatus('notifications'));

    // Cleanup on unmount
    return () => {
      websocketClient.disconnect('notifications');
    };
  }, []);

  const send = useCallback((message) => {
    return websocketClient.send('notifications', message);
  }, []);

  return {
    status,
    lastMessage,
    send,
    isConnected: status === 'connected',
  };
};

/**
 * Hook for WebSocket event subscription
 */
export const useWebSocketEvent = (eventType, handler) => {
  useEffect(() => {
    // Subscribe to event
    const unsubscribe = websocketClient.on(eventType, handler);

    // Cleanup on unmount
    return () => {
      unsubscribe();
    };
  }, [eventType, handler]);
};

export default {
  useChapterWebSocket,
  useTaskWebSocket,
  useNotificationsWebSocket,
  useWebSocketEvent,
};
