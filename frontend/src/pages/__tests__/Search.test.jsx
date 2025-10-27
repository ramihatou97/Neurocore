/**
 * Tests for Search Component
 * Tests search functionality, suggestions, filters, and results display
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import axios from 'axios';
import Search from '../Search';

// Mock axios
jest.mock('axios');

// Mock react-router-dom hooks
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
  useSearchParams: () => [new URLSearchParams(), jest.fn()],
}));

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(() => 'mock-token'),
  setItem: jest.fn(),
  clear: jest.fn(),
};
global.localStorage = localStorageMock;

describe('Search Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const renderSearch = () => {
    return render(
      <BrowserRouter>
        <Search />
      </BrowserRouter>
    );
  };

  describe('Rendering', () => {
    test('renders search page with all elements', () => {
      renderSearch();

      expect(screen.getByText(/Advanced Search/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/brain tumor classification/i)).toBeInTheDocument();
      expect(screen.getByText(/Search Type/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Search/i })).toBeInTheDocument();
    });

    test('renders search stats banner', async () => {
      axios.get.mockResolvedValueOnce({
        data: {
          pdfs: { total: 100, with_embeddings: 80, coverage: 80 },
          chapters: { total: 50, with_embeddings: 45, coverage: 90 },
          images: { total: 200, with_embeddings: 180, coverage: 90 },
        },
      });

      renderSearch();

      await waitFor(() => {
        expect(screen.getByText(/PDFs Indexed/i)).toBeInTheDocument();
        expect(screen.getByText(/Chapters Indexed/i)).toBeInTheDocument();
        expect(screen.getByText(/Images Indexed/i)).toBeInTheDocument();
      });
    });

    test('renders empty state when no query', () => {
      renderSearch();

      expect(screen.getByText(/Start Your Search/i)).toBeInTheDocument();
      expect(screen.getByText(/Try searching for:/i)).toBeInTheDocument();
    });
  });

  describe('Search Functionality', () => {
    test('performs search on form submit', async () => {
      axios.post.mockResolvedValueOnce({
        data: {
          query: 'brain tumor',
          search_type: 'hybrid',
          total: 2,
          results: [
            {
              id: 'pdf-123',
              type: 'pdf',
              title: 'Brain Tumor Classification',
              authors: 'Dr. Smith',
              score: 0.85,
              year: 2024,
            },
            {
              id: 'chapter-456',
              type: 'chapter',
              title: 'Surgical Techniques',
              summary: 'Guide to surgical approaches',
              score: 0.75,
            },
          ],
          filters_applied: {},
        },
      });

      renderSearch();

      const searchInput = screen.getByPlaceholderText(/brain tumor classification/i);
      const searchButton = screen.getByRole('button', { name: /Search/i });

      fireEvent.change(searchInput, { target: { value: 'brain tumor' } });
      fireEvent.click(searchButton);

      await waitFor(() => {
        expect(axios.post).toHaveBeenCalledWith(
          expect.stringContaining('/search'),
          expect.objectContaining({
            query: 'brain tumor',
            search_type: 'hybrid',
          }),
          expect.any(Object)
        );
      });

      await waitFor(() => {
        expect(screen.getByText('Brain Tumor Classification')).toBeInTheDocument();
        expect(screen.getByText('Surgical Techniques')).toBeInTheDocument();
      });
    });

    test('shows error on search failure', async () => {
      axios.post.mockRejectedValueOnce({
        response: { data: { detail: 'Search failed' } },
      });

      renderSearch();

      const searchInput = screen.getByPlaceholderText(/brain tumor classification/i);
      const searchButton = screen.getByRole('button', { name: /Search/i });

      fireEvent.change(searchInput, { target: { value: 'test' } });
      fireEvent.click(searchButton);

      await waitFor(() => {
        expect(screen.getByText(/Search failed/i)).toBeInTheDocument();
      });
    });

    test('disables search button when query is empty', () => {
      renderSearch();

      const searchButton = screen.getByRole('button', { name: /Search/i });
      expect(searchButton).toBeDisabled();
    });

    test('changes search type', async () => {
      axios.post.mockResolvedValueOnce({
        data: {
          query: 'test',
          search_type: 'semantic',
          total: 0,
          results: [],
          filters_applied: {},
        },
      });

      renderSearch();

      const searchInput = screen.getByPlaceholderText(/brain tumor classification/i);
      fireEvent.change(searchInput, { target: { value: 'test' } });

      // Open search type selector and select semantic
      const searchTypeSelect = screen.getByLabelText(/Search Type/i);
      fireEvent.mouseDown(searchTypeSelect);

      const semanticOption = await screen.findByText(/Semantic \(AI\)/i);
      fireEvent.click(semanticOption);

      const searchButton = screen.getByRole('button', { name: /Search/i });
      fireEvent.click(searchButton);

      await waitFor(() => {
        expect(axios.post).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            search_type: 'semantic',
          }),
          expect.any(Object)
        );
      });
    });
  });

  describe('Suggestions and Autocomplete', () => {
    test('fetches suggestions on query input', async () => {
      axios.get.mockResolvedValueOnce({
        data: {
          query: 'brain',
          suggestions: [
            'brain tumor classification',
            'brain tumor types',
            'brain surgery techniques',
          ],
          count: 3,
        },
      });

      renderSearch();

      const searchInput = screen.getByPlaceholderText(/brain tumor classification/i);
      fireEvent.change(searchInput, { target: { value: 'brain' } });

      await waitFor(
        () => {
          expect(axios.get).toHaveBeenCalledWith(
            expect.stringContaining('/search/suggestions'),
            expect.any(Object)
          );
        },
        { timeout: 500 }
      );
    });

    test('selects suggestion on click', async () => {
      axios.get.mockResolvedValueOnce({
        data: {
          suggestions: ['brain tumor classification'],
        },
      });

      axios.post.mockResolvedValueOnce({
        data: {
          query: 'brain tumor classification',
          total: 0,
          results: [],
        },
      });

      renderSearch();

      const searchInput = screen.getByPlaceholderText(/brain tumor classification/i);
      fireEvent.change(searchInput, { target: { value: 'brain' } });

      await waitFor(() => {
        const suggestion = screen.getByText('brain tumor classification');
        fireEvent.click(suggestion);
      });

      expect(searchInput.value).toBe('brain tumor classification');
    });
  });

  describe('Filters', () => {
    test('shows filters when filter button clicked', () => {
      renderSearch();

      const filterButton = screen.getByRole('button', { name: /Advanced Filters/i });
      fireEvent.click(filterButton);

      expect(screen.getByLabelText(/Content Type/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Date Range/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Min Similarity/i)).toBeInTheDocument();
    });

    test('applies content type filter', async () => {
      axios.post.mockResolvedValueOnce({
        data: {
          query: 'test',
          total: 0,
          results: [],
          filters_applied: { content_type: 'pdf' },
        },
      });

      renderSearch();

      // Open filters
      const filterButton = screen.getByRole('button', { name: /Advanced Filters/i });
      fireEvent.click(filterButton);

      // Select PDF only
      const contentTypeSelect = screen.getByLabelText(/Content Type/i);
      fireEvent.mouseDown(contentTypeSelect);

      const pdfOption = await screen.findByText(/PDFs Only/i);
      fireEvent.click(pdfOption);

      // Perform search
      const searchInput = screen.getByPlaceholderText(/brain tumor classification/i);
      fireEvent.change(searchInput, { target: { value: 'test' } });

      const searchButton = screen.getByRole('button', { name: /Search/i });
      fireEvent.click(searchButton);

      await waitFor(() => {
        expect(axios.post).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            filters: expect.objectContaining({
              content_type: 'pdf',
            }),
          }),
          expect.any(Object)
        );
      });
    });

    test('clears filters', () => {
      renderSearch();

      // Open filters
      const filterButton = screen.getByRole('button', { name: /Advanced Filters/i });
      fireEvent.click(filterButton);

      // Clear filters
      const clearButton = screen.getByRole('button', { name: /Clear Filters/i });
      fireEvent.click(clearButton);

      // Filters should be reset to defaults
      expect(screen.getByLabelText(/Content Type/i)).toHaveValue('all');
    });
  });

  describe('Results Display', () => {
    test('displays PDF results correctly', async () => {
      axios.post.mockResolvedValueOnce({
        data: {
          query: 'test',
          total: 1,
          results: [
            {
              id: 'pdf-123',
              type: 'pdf',
              title: 'Test PDF',
              authors: 'Dr. Smith',
              year: 2024,
              journal: 'Test Journal',
              score: 0.85,
            },
          ],
        },
      });

      renderSearch();

      const searchInput = screen.getByPlaceholderText(/brain tumor classification/i);
      fireEvent.change(searchInput, { target: { value: 'test' } });

      const searchButton = screen.getByRole('button', { name: /Search/i });
      fireEvent.click(searchButton);

      await waitFor(() => {
        expect(screen.getByText('Test PDF')).toBeInTheDocument();
        expect(screen.getByText('Dr. Smith')).toBeInTheDocument();
        expect(screen.getByText('2024')).toBeInTheDocument();
        expect(screen.getByText(/Relevance: 85.0%/i)).toBeInTheDocument();
      });
    });

    test('displays chapter results correctly', async () => {
      axios.post.mockResolvedValueOnce({
        data: {
          query: 'test',
          total: 1,
          results: [
            {
              id: 'chapter-123',
              type: 'chapter',
              title: 'Test Chapter',
              summary: 'This is a test chapter summary',
              score: 0.75,
            },
          ],
        },
      });

      renderSearch();

      const searchInput = screen.getByPlaceholderText(/brain tumor classification/i);
      fireEvent.change(searchInput, { target: { value: 'test' } });

      const searchButton = screen.getByRole('button', { name: /Search/i });
      fireEvent.click(searchButton);

      await waitFor(() => {
        expect(screen.getByText('Test Chapter')).toBeInTheDocument();
        expect(screen.getByText(/This is a test chapter summary/i)).toBeInTheDocument();
        expect(screen.getByText(/Relevance: 75.0%/i)).toBeInTheDocument();
      });
    });

    test('shows no results message', async () => {
      axios.post.mockResolvedValueOnce({
        data: {
          query: 'nonexistent',
          total: 0,
          results: [],
        },
      });

      renderSearch();

      const searchInput = screen.getByPlaceholderText(/brain tumor classification/i);
      fireEvent.change(searchInput, { target: { value: 'nonexistent' } });

      const searchButton = screen.getByRole('button', { name: /Search/i });
      fireEvent.click(searchButton);

      await waitFor(() => {
        expect(screen.getByText(/No results found/i)).toBeInTheDocument();
      });
    });

    test('navigates to PDF detail on result click', async () => {
      axios.post.mockResolvedValueOnce({
        data: {
          query: 'test',
          total: 1,
          results: [
            {
              id: 'pdf-123',
              type: 'pdf',
              title: 'Test PDF',
              score: 0.85,
            },
          ],
        },
      });

      renderSearch();

      const searchInput = screen.getByPlaceholderText(/brain tumor classification/i);
      fireEvent.change(searchInput, { target: { value: 'test' } });

      const searchButton = screen.getByRole('button', { name: /Search/i });
      fireEvent.click(searchButton);

      await waitFor(() => {
        const result = screen.getByText('Test PDF');
        fireEvent.click(result);
      });

      expect(mockNavigate).toHaveBeenCalledWith('/pdfs/pdf-123');
    });
  });

  describe('Pagination', () => {
    test('shows pagination controls when results exceed page size', async () => {
      axios.post.mockResolvedValueOnce({
        data: {
          query: 'test',
          total: 50,
          results: Array.from({ length: 20 }, (_, i) => ({
            id: `pdf-${i}`,
            type: 'pdf',
            title: `PDF ${i}`,
            score: 0.8,
          })),
        },
      });

      renderSearch();

      const searchInput = screen.getByPlaceholderText(/brain tumor classification/i);
      fireEvent.change(searchInput, { target: { value: 'test' } });

      const searchButton = screen.getByRole('button', { name: /Search/i });
      fireEvent.click(searchButton);

      await waitFor(() => {
        expect(screen.getByText(/Page 1 of 3/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Next/i })).toBeInTheDocument();
      });
    });

    test('loads next page on pagination click', async () => {
      // First page
      axios.post.mockResolvedValueOnce({
        data: {
          query: 'test',
          total: 50,
          results: Array.from({ length: 20 }, (_, i) => ({
            id: `pdf-${i}`,
            type: 'pdf',
            title: `PDF ${i}`,
            score: 0.8,
          })),
        },
      });

      // Second page
      axios.post.mockResolvedValueOnce({
        data: {
          query: 'test',
          total: 50,
          results: Array.from({ length: 20 }, (_, i) => ({
            id: `pdf-${i + 20}`,
            type: 'pdf',
            title: `PDF ${i + 20}`,
            score: 0.7,
          })),
        },
      });

      renderSearch();

      const searchInput = screen.getByPlaceholderText(/brain tumor classification/i);
      fireEvent.change(searchInput, { target: { value: 'test' } });

      const searchButton = screen.getByRole('button', { name: /Search/i });
      fireEvent.click(searchButton);

      await waitFor(() => {
        expect(screen.getByText('PDF 0')).toBeInTheDocument();
      });

      const nextButton = screen.getByRole('button', { name: /Next/i });
      fireEvent.click(nextButton);

      await waitFor(() => {
        expect(axios.post).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            offset: 20,
          }),
          expect.any(Object)
        );
      });
    });
  });

  describe('Quick Search Chips', () => {
    test('clicking quick search chip performs search', async () => {
      axios.post.mockResolvedValueOnce({
        data: {
          query: 'brain tumor classification',
          total: 0,
          results: [],
        },
      });

      renderSearch();

      const chip = screen.getByText('brain tumor classification');
      fireEvent.click(chip);

      await waitFor(() => {
        expect(axios.post).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            query: 'brain tumor classification',
          }),
          expect.any(Object)
        );
      });
    });
  });
});
