/**
 * Textbook API Service
 * Handles textbook upload, chapter management, and embedding progress
 * Phase 5: Chapter-Level Vector Search Upload Infrastructure
 */

import apiClient from './client';

const textbookAPI = {
  /**
   * Upload single textbook PDF
   * POST /textbooks/upload
   *
   * @param {File} file - PDF file to upload
   * @param {Function} onUploadProgress - Progress callback (percent)
   * @returns {Promise<UploadResponse>}
   */
  upload: async (file, onUploadProgress) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post('/textbooks/upload', formData, {
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
   * Batch upload multiple textbook PDFs
   * POST /textbooks/batch-upload
   *
   * @param {File[]} files - Array of PDF files (max 50)
   * @param {Function} onBatchProgress - Overall progress callback
   * @returns {Promise<BatchUploadResponse>}
   */
  batchUpload: async (files, onBatchProgress) => {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    const response = await apiClient.post('/textbooks/batch-upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: onBatchProgress ? (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onBatchProgress(percentCompleted);
      } : undefined,
    });

    return response.data;
  },

  /**
   * Get upload/processing progress for a book
   * GET /textbooks/upload-progress/:bookId
   *
   * @param {string} bookId - Book UUID
   * @returns {Promise<UploadProgressResponse>}
   */
  getUploadProgress: async (bookId) => {
    const response = await apiClient.get(`/textbooks/upload-progress/${bookId}`);
    return response.data;
  },

  /**
   * Get library statistics
   * GET /textbooks/library-stats
   *
   * @returns {Promise<LibraryStatsResponse>}
   */
  getLibraryStats: async () => {
    const response = await apiClient.get('/textbooks/library-stats');
    return response.data;
  },

  /**
   * Get all textbooks
   * GET /textbooks/books
   *
   * @param {Object} params - Query parameters (skip, limit, filter, sort)
   * @returns {Promise<BookResponse[]>}
   */
  listBooks: async (params = {}) => {
    const response = await apiClient.get('/textbooks/books', { params });
    return response.data;
  },

  /**
   * Get textbook by ID
   * GET /textbooks/books/:bookId
   *
   * @param {string} bookId - Book UUID
   * @returns {Promise<BookResponse>}
   */
  getBook: async (bookId) => {
    const response = await apiClient.get(`/textbooks/books/${bookId}`);
    return response.data;
  },

  /**
   * Update book title
   * PATCH /textbooks/books/:bookId/title
   *
   * @param {string} bookId - Book UUID
   * @param {Object} data - {title: string}
   * @returns {Promise<BookResponse>}
   */
  updateBookTitle: async (bookId, data) => {
    const response = await apiClient.patch(`/textbooks/books/${bookId}/title`, data);
    return response.data;
  },

  /**
   * Get chapters for a textbook
   * GET /textbooks/books/:bookId/chapters
   *
   * @param {string} bookId - Book UUID
   * @returns {Promise<ChapterResponse[]>}
   */
  getBookChapters: async (bookId) => {
    const response = await apiClient.get(`/textbooks/books/${bookId}/chapters`);
    return response.data;
  },

  /**
   * Get chapter by ID
   * GET /textbooks/chapters/:chapterId
   *
   * @param {string} chapterId - Chapter UUID
   * @returns {Promise<ChapterResponse>}
   */
  getChapter: async (chapterId) => {
    const response = await apiClient.get(`/textbooks/chapters/${chapterId}`);
    return response.data;
  },

  /**
   * Get chapter embedding vector
   * GET /textbooks/chapters/:chapterId/embedding
   *
   * @param {string} chapterId - Chapter UUID
   * @returns {Promise<{embedding: number[], embedding_preview: number[], has_embedding: boolean}>}
   */
  getChapterEmbedding: async (chapterId) => {
    const response = await apiClient.get(`/textbooks/chapters/${chapterId}/embedding`);
    return response.data;
  },

  /**
   * Get similar chapters
   * GET /textbooks/chapters/:chapterId/similar
   *
   * @param {string} chapterId - Chapter UUID
   * @param {number} limit - Number of similar chapters to return (default: 5)
   * @returns {Promise<{similar_chapters: Array}>}
   */
  getSimilarChapters: async (chapterId, limit = 5) => {
    const response = await apiClient.get(`/textbooks/chapters/${chapterId}/similar`, {
      params: { limit }
    });
    return response.data;
  },

  /**
   * Delete textbook
   * DELETE /textbooks/books/:bookId
   *
   * @param {string} bookId - Book UUID
   * @returns {Promise<{message: string}>}
   */
  deleteBook: async (bookId) => {
    const response = await apiClient.delete(`/textbooks/books/${bookId}`);
    return response.data;
  },

  /**
   * Delete chapter
   * DELETE /textbooks/chapters/:chapterId
   *
   * @param {string} chapterId - Chapter UUID
   * @returns {Promise<{message: string}>}
   */
  deleteChapter: async (chapterId) => {
    const response = await apiClient.delete(`/textbooks/chapters/${chapterId}`);
    return response.data;
  },

  /**
   * Search textbooks and chapters
   * POST /textbooks/search
   *
   * @param {Object} query - Search query parameters
   * @returns {Promise<SearchResults>}
   */
  search: async (query) => {
    const response = await apiClient.post('/textbooks/search', query);
    return response.data;
  },
};

export default textbookAPI;
