/**
 * Mock API Client for Testing
 * Provides mock implementations of all API methods
 */

import { vi } from 'vitest'

export const mockApiClient = {
  // Auth endpoints
  auth: {
    login: vi.fn().mockResolvedValue({
      data: {
        access_token: 'mock-token',
        user: {
          id: '1',
          email: 'test@example.com',
          full_name: 'Test User',
        },
      },
    }),
    register: vi.fn().mockResolvedValue({
      data: {
        access_token: 'mock-token',
        user: {
          id: '1',
          email: 'test@example.com',
          full_name: 'Test User',
        },
      },
    }),
    logout: vi.fn().mockResolvedValue({ data: { message: 'Logged out' } }),
    getCurrentUser: vi.fn().mockResolvedValue({
      data: {
        id: '1',
        email: 'test@example.com',
        full_name: 'Test User',
      },
    }),
  },

  // PDF endpoints
  pdfs: {
    list: vi.fn().mockResolvedValue({
      data: [
        {
          id: 'pdf-1',
          filename: 'test.pdf',
          title: 'Test PDF',
          indexing_status: 'completed',
          total_pages: 10,
        },
      ],
    }),
    get: vi.fn().mockResolvedValue({
      data: {
        id: 'pdf-1',
        filename: 'test.pdf',
        title: 'Test PDF',
        indexing_status: 'completed',
        total_pages: 10,
      },
    }),
    upload: vi.fn().mockResolvedValue({
      data: {
        id: 'pdf-1',
        filename: 'test.pdf',
        indexing_status: 'uploaded',
      },
    }),
    delete: vi.fn().mockResolvedValue({ data: { message: 'Deleted' } }),
  },

  // Chapter endpoints
  chapters: {
    list: vi.fn().mockResolvedValue({
      data: [
        {
          id: 'chapter-1',
          title: 'Test Chapter',
          topic: 'Neurosurgery',
          status: 'completed',
          quality_score: 0.95,
        },
      ],
    }),
    get: vi.fn().mockResolvedValue({
      data: {
        id: 'chapter-1',
        title: 'Test Chapter',
        topic: 'Neurosurgery',
        status: 'completed',
        content: {
          sections: [
            {
              title: 'Introduction',
              content: 'Test content',
            },
          ],
        },
        quality_score: 0.95,
      },
    }),
    create: vi.fn().mockResolvedValue({
      data: {
        id: 'chapter-1',
        title: 'Test Chapter',
        status: 'generating',
      },
    }),
    delete: vi.fn().mockResolvedValue({ data: { message: 'Deleted' } }),
  },

  // Search endpoints
  search: {
    semantic: vi.fn().mockResolvedValue({
      data: {
        results: [
          {
            id: '1',
            type: 'chapter',
            title: 'Test Result',
            content: 'Test content',
            similarity_score: 0.9,
          },
        ],
      },
    }),
    hybrid: vi.fn().mockResolvedValue({
      data: {
        results: [
          {
            id: '1',
            type: 'chapter',
            title: 'Test Result',
            content: 'Test content',
            score: 0.9,
          },
        ],
      },
    }),
  },

  // Analytics endpoints
  analytics: {
    getOverview: vi.fn().mockResolvedValue({
      data: {
        total_pdfs: 10,
        total_chapters: 5,
        total_searches: 100,
      },
    }),
    getChapterQuality: vi.fn().mockResolvedValue({
      data: [
        {
          chapter_id: 'chapter-1',
          quality_score: 0.95,
        },
      ],
    }),
  },
}

/**
 * Reset all mock functions
 */
export function resetMocks() {
  Object.values(mockApiClient).forEach((module) => {
    Object.values(module).forEach((fn) => {
      if (fn.mockClear) {
        fn.mockClear()
      }
    })
  })
}

/**
 * Mock API error
 */
export function mockApiError(endpoint, error = { message: 'API Error', status: 500 }) {
  endpoint.mockRejectedValueOnce(error)
}

export default mockApiClient
