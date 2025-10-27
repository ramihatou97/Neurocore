/**
 * Chapters API Service
 * Handles chapter generation, management, and viewing
 */

import apiClient from './client';

const chaptersAPI = {
  /**
   * Generate new chapter
   * POST /chapters/generate
   */
  generate: async (chapterData) => {
    const response = await apiClient.post('/chapters/generate', chapterData);
    return response.data;
  },

  /**
   * Get all chapters for current user
   * GET /chapters
   */
  getAll: async (params = {}) => {
    const response = await apiClient.get('/chapters', { params });
    return response.data;
  },

  /**
   * Get chapter by ID
   * GET /chapters/:id
   */
  getById: async (id) => {
    const response = await apiClient.get(`/chapters/${id}`);
    return response.data;
  },

  /**
   * Get chapter generation status
   * GET /chapters/:id/status
   */
  getStatus: async (id) => {
    const response = await apiClient.get(`/chapters/${id}/status`);
    return response.data;
  },

  /**
   * Update chapter content
   * PUT /chapters/:id
   */
  update: async (id, chapterData) => {
    const response = await apiClient.put(`/chapters/${id}`, chapterData);
    return response.data;
  },

  /**
   * Delete chapter
   * DELETE /chapters/:id
   */
  delete: async (id) => {
    const response = await apiClient.delete(`/chapters/${id}`);
    return response.data;
  },

  /**
   * Get chapter sections
   * GET /chapters/:id/sections
   */
  getSections: async (id) => {
    const response = await apiClient.get(`/chapters/${id}/sections`);
    return response.data;
  },

  /**
   * Get chapter images
   * GET /chapters/:id/images
   */
  getImages: async (id) => {
    const response = await apiClient.get(`/chapters/${id}/images`);
    return response.data;
  },

  /**
   * Get chapter citations
   * GET /chapters/:id/citations
   */
  getCitations: async (id) => {
    const response = await apiClient.get(`/chapters/${id}/citations`);
    return response.data;
  },

  /**
   * Get chapter quality scores
   * GET /chapters/:id/quality
   */
  getQuality: async (id) => {
    const response = await apiClient.get(`/chapters/${id}/quality`);
    return response.data;
  },

  /**
   * Publish chapter
   * POST /chapters/:id/publish
   */
  publish: async (id) => {
    const response = await apiClient.post(`/chapters/${id}/publish`);
    return response.data;
  },

  /**
   * Archive chapter
   * POST /chapters/:id/archive
   */
  archive: async (id) => {
    const response = await apiClient.post(`/chapters/${id}/archive`);
    return response.data;
  },

  /**
   * Regenerate chapter
   * POST /chapters/:id/regenerate
   */
  regenerate: async (id, options = {}) => {
    const response = await apiClient.post(`/chapters/${id}/regenerate`, options);
    return response.data;
  },

  /**
   * Get chapter versions
   * GET /chapters/:id/versions
   */
  getVersions: async (id) => {
    const response = await apiClient.get(`/chapters/${id}/versions`);
    return response.data;
  },

  /**
   * Create chapter version
   * POST /chapters/:id/versions
   */
  createVersion: async (id, versionData) => {
    const response = await apiClient.post(`/chapters/${id}/versions`, versionData);
    return response.data;
  },

  /**
   * Search chapters
   * POST /chapters/search
   */
  search: async (query) => {
    const response = await apiClient.post('/chapters/search', { query });
    return response.data;
  },

  /**
   * Get chapter statistics
   * GET /chapters/stats
   */
  getStats: async () => {
    const response = await apiClient.get('/chapters/stats');
    return response.data;
  },

  /**
   * Export chapter as PDF
   * GET /chapters/:id/export/pdf
   */
  exportPDF: async (id) => {
    const response = await apiClient.get(`/chapters/${id}/export/pdf`, {
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * Export chapter as Markdown
   * GET /chapters/:id/export/markdown
   */
  exportMarkdown: async (id) => {
    const response = await apiClient.get(`/chapters/${id}/export/markdown`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

export default chaptersAPI;
