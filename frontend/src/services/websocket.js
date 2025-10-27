/**
 * WebSocket Client Service
 * Handles real-time WebSocket connections for chapter and task updates
 */

import { WS_URL, STORAGE_KEYS, WS_RECONNECT_DELAY, WS_HEARTBEAT_INTERVAL } from '../utils/constants';

class WebSocketClient {
  constructor() {
    this.connections = new Map(); // Map of connection_id -> WebSocket
    this.eventHandlers = new Map(); // Map of event_type -> Set of handlers
    this.reconnectAttempts = new Map(); // Map of connection_id -> attempt count
    this.heartbeatIntervals = new Map(); // Map of connection_id -> interval
  }

  /**
   * Connect to chapter WebSocket
   */
  connectToChapter(chapterId, handlers = {}) {
    const connectionId = `chapter:${chapterId}`;
    return this._connect(connectionId, `/chapters/${chapterId}`, handlers);
  }

  /**
   * Connect to task WebSocket
   */
  connectToTask(taskId, handlers = {}) {
    const connectionId = `task:${taskId}`;
    return this._connect(connectionId, `/tasks/${taskId}`, handlers);
  }

  /**
   * Connect to notifications WebSocket
   */
  connectToNotifications(handlers = {}) {
    const connectionId = 'notifications';
    return this._connect(connectionId, '/notifications', handlers);
  }

  /**
   * Internal connect method
   */
  _connect(connectionId, path, handlers = {}) {
    // If already connected, return existing connection
    if (this.connections.has(connectionId)) {
      console.log(`WebSocket already connected: ${connectionId}`);
      return this.connections.get(connectionId);
    }

    // Get auth token
    const token = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
    if (!token) {
      console.error('No auth token found for WebSocket connection');
      return null;
    }

    // Build WebSocket URL with token
    const wsUrl = `${WS_URL}${path}?token=${token}`;

    try {
      // Create WebSocket connection
      const ws = new WebSocket(wsUrl);

      // Setup event handlers
      ws.onopen = () => {
        console.log(`WebSocket connected: ${connectionId}`);
        this.reconnectAttempts.set(connectionId, 0);

        // Start heartbeat
        this._startHeartbeat(connectionId, ws);

        // Call custom onOpen handler
        if (handlers.onOpen) {
          handlers.onOpen();
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log(`WebSocket message received on ${connectionId}:`, data);

          // Handle heartbeat pong
          if (data.type === 'pong') {
            return;
          }

          // Call custom onMessage handler
          if (handlers.onMessage) {
            handlers.onMessage(data);
          }

          // Call event-specific handlers
          if (data.event) {
            this._callEventHandlers(data.event, data);
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error(`WebSocket error on ${connectionId}:`, error);

        // Call custom onError handler
        if (handlers.onError) {
          handlers.onError(error);
        }
      };

      ws.onclose = (event) => {
        console.log(`WebSocket closed: ${connectionId}, code: ${event.code}`);

        // Stop heartbeat
        this._stopHeartbeat(connectionId);

        // Remove from connections
        this.connections.delete(connectionId);

        // Call custom onClose handler
        if (handlers.onClose) {
          handlers.onClose(event);
        }

        // Attempt reconnection if not a normal closure
        if (event.code !== 1000 && event.code !== 1001) {
          this._attemptReconnect(connectionId, path, handlers);
        }
      };

      // Store connection
      this.connections.set(connectionId, ws);

      return ws;
    } catch (error) {
      console.error(`Failed to create WebSocket connection for ${connectionId}:`, error);
      return null;
    }
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect(connectionId) {
    const ws = this.connections.get(connectionId);
    if (ws) {
      this._stopHeartbeat(connectionId);
      ws.close(1000, 'Client disconnect');
      this.connections.delete(connectionId);
      console.log(`WebSocket disconnected: ${connectionId}`);
    }
  }

  /**
   * Disconnect all connections
   */
  disconnectAll() {
    this.connections.forEach((ws, connectionId) => {
      this.disconnect(connectionId);
    });
  }

  /**
   * Send message to WebSocket
   */
  send(connectionId, message) {
    const ws = this.connections.get(connectionId);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message));
      return true;
    }
    console.warn(`Cannot send message, WebSocket not open: ${connectionId}`);
    return false;
  }

  /**
   * Register event handler
   */
  on(eventType, handler) {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, new Set());
    }
    this.eventHandlers.get(eventType).add(handler);

    // Return unsubscribe function
    return () => {
      this.off(eventType, handler);
    };
  }

  /**
   * Unregister event handler
   */
  off(eventType, handler) {
    const handlers = this.eventHandlers.get(eventType);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  /**
   * Call registered event handlers
   */
  _callEventHandlers(eventType, data) {
    const handlers = this.eventHandlers.get(eventType);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(data);
        } catch (error) {
          console.error(`Error in event handler for ${eventType}:`, error);
        }
      });
    }
  }

  /**
   * Start heartbeat for connection
   */
  _startHeartbeat(connectionId, ws) {
    const interval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }));
      } else {
        this._stopHeartbeat(connectionId);
      }
    }, WS_HEARTBEAT_INTERVAL);

    this.heartbeatIntervals.set(connectionId, interval);
  }

  /**
   * Stop heartbeat for connection
   */
  _stopHeartbeat(connectionId) {
    const interval = this.heartbeatIntervals.get(connectionId);
    if (interval) {
      clearInterval(interval);
      this.heartbeatIntervals.delete(connectionId);
    }
  }

  /**
   * Attempt to reconnect
   */
  _attemptReconnect(connectionId, path, handlers) {
    const attempts = this.reconnectAttempts.get(connectionId) || 0;
    const maxAttempts = 5;

    if (attempts >= maxAttempts) {
      console.log(`Max reconnection attempts reached for ${connectionId}`);
      return;
    }

    this.reconnectAttempts.set(connectionId, attempts + 1);

    console.log(`Attempting to reconnect ${connectionId} (attempt ${attempts + 1}/${maxAttempts})...`);

    setTimeout(() => {
      this._connect(connectionId, path, handlers);
    }, WS_RECONNECT_DELAY * (attempts + 1)); // Exponential backoff
  }

  /**
   * Get connection status
   */
  getStatus(connectionId) {
    const ws = this.connections.get(connectionId);
    if (!ws) return 'disconnected';

    switch (ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting';
      case WebSocket.OPEN:
        return 'connected';
      case WebSocket.CLOSING:
        return 'closing';
      case WebSocket.CLOSED:
        return 'closed';
      default:
        return 'unknown';
    }
  }

  /**
   * Check if connected
   */
  isConnected(connectionId) {
    return this.getStatus(connectionId) === 'connected';
  }
}

// Create singleton instance
const websocketClient = new WebSocketClient();

export default websocketClient;
