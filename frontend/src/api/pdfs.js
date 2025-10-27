/**
 * PDF API Service
 * Handles PDF upload, management, and processing
 */

import apiClient from './client';

const pdfAPI = {
  /**
   * Upload PDF file
   * POST /pdfs/upload
   */
  upload: async (file, onUploadProgress) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post('/pdfs/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: onUploadProgress ? (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onUploadProgress(percentCompleted);
      } : undefined,
    });

    return response.data;
  },

  /**
   * Get all PDFs for current user
   * GET /pdfs
   */
  getAll: async (params = {}) => {
    const response = await apiClient.get('/pdfs', { params });
    return response.data;
  },

  /**
   * Get PDF by ID
   * GET /pdfs/:id
   */
  getById: async (id) => {
    const response = await apiClient.get(`/pdfs/${id}`);
    return response.data;
  },

  /**
   * Get PDF processing status
   * GET /pdfs/:id/status
   */
  getStatus: async (id) => {
    const response = await apiClient.get(`/pdfs/${id}/status`);
    return response.data;
  },

  /**
   * Get PDF images
   * GET /pdfs/:id/images
   */
  getImages: async (id) => {
    const response = await apiClient.get(`/pdfs/${id}/images`);
    return response.data;
  },

  /**
   * Get PDF extracted text
   * GET /pdfs/:id/text
   */
  getText: async (id) => {
    const response = await apiClient.get(`/pdfs/${id}/text`);
    return response.data;
  },

  /**
   * Get PDF citations
   * GET /pdfs/:id/citations
   */
  getCitations: async (id) => {
    const response = await apiClient.get(`/pdfs/${id}/citations`);
    return response.data;
  },

  /**
   * Reprocess PDF
   * POST /pdfs/:id/reprocess
   */
  reprocess: async (id) => {
    const response = await apiClient.post(`/pdfs/${id}/reprocess`);
    return response.data;
  },

  /**
   * Delete PDF
   * DELETE /pdfs/:id
   */
  delete: async (id) => {
    const response = await apiClient.delete(`/pdfs/${id}`);
    return response.data;
  },

  /**
   * Search PDFs
   * POST /pdfs/search
   */
  search: async (query) => {
    const response = await apiClient.post('/pdfs/search', { query });
    return response.data;
  },

  /**
   * Get PDF statistics
   * GET /pdfs/stats
   */
  getStats: async () => {
    const response = await apiClient.get('/pdfs/stats');
    return response.data;
  },
};

export default pdfAPI;
