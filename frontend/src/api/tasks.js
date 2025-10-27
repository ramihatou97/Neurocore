/**
 * Tasks API Service
 * Handles background task monitoring and management
 */

import apiClient from './client';

const tasksAPI = {
  /**
   * Get all tasks for current user
   * GET /tasks
   */
  getAll: async (params = {}) => {
    const response = await apiClient.get('/tasks', { params });
    return response.data;
  },

  /**
   * Get task by ID
   * GET /tasks/:id
   */
  getById: async (id) => {
    const response = await apiClient.get(`/tasks/${id}`);
    return response.data;
  },

  /**
   * Get task status
   * GET /tasks/:id/status
   */
  getStatus: async (id) => {
    const response = await apiClient.get(`/tasks/${id}/status`);
    return response.data;
  },

  /**
   * Get task progress
   * GET /tasks/:id/progress
   */
  getProgress: async (id) => {
    const response = await apiClient.get(`/tasks/${id}/progress`);
    return response.data;
  },

  /**
   * Cancel task
   * POST /tasks/:id/cancel
   */
  cancel: async (id) => {
    const response = await apiClient.post(`/tasks/${id}/cancel`);
    return response.data;
  },

  /**
   * Retry failed task
   * POST /tasks/:id/retry
   */
  retry: async (id) => {
    const response = await apiClient.post(`/tasks/${id}/retry`);
    return response.data;
  },

  /**
   * Get tasks by entity
   * GET /tasks/entity/:entity_type/:entity_id
   */
  getByEntity: async (entityType, entityId) => {
    const response = await apiClient.get(`/tasks/entity/${entityType}/${entityId}`);
    return response.data;
  },

  /**
   * Get active tasks
   * GET /tasks/active
   */
  getActive: async () => {
    const response = await apiClient.get('/tasks/active');
    return response.data;
  },

  /**
   * Get task statistics
   * GET /tasks/stats
   */
  getStats: async () => {
    const response = await apiClient.get('/tasks/stats');
    return response.data;
  },

  /**
   * Delete task
   * DELETE /tasks/:id
   */
  delete: async (id) => {
    const response = await apiClient.delete(`/tasks/${id}`);
    return response.data;
  },
};

export default tasksAPI;
