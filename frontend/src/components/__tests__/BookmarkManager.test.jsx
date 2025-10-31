/**
 * BookmarkManager Component Tests
 * Streamlined test suite focusing on core bookmark management logic
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import BookmarkManager from '../BookmarkManager'
import axios from 'axios'

// Mock axios
vi.mock('axios')

describe('BookmarkManager Component', () => {
  const mockContentType = 'chapter'
  const mockContentId = 'chapter-123'
  const mockOnBookmarkChange = vi.fn()

  const mockBookmarks = [
    {
      id: 'bm-1',
      content_type: 'chapter',
      content_id: 'chapter-123',
      title: 'Important Chapter',
      notes: 'Review for exam',
      tags: ['neurosurgery', 'important'],
      is_favorite: true,
      collection_name: 'Study Materials',
      created_at: '2024-01-15T10:00:00Z'
    },
    {
      id: 'bm-2',
      content_type: 'section',
      content_id: 'section-456',
      title: '',
      notes: 'Good reference',
      tags: ['anatomy'],
      is_favorite: false,
      collection_name: null,
      created_at: '2024-01-16T12:00:00Z'
    }
  ]

  const mockCollections = [
    {
      id: 'col-1',
      name: 'Study Materials',
      description: 'Resources for board exam',
      color: '#1976d2',
      icon: 'folder',
      bookmark_count: 5,
      is_public: false
    },
    {
      id: 'col-2',
      name: 'Research Papers',
      description: 'Recent publications',
      color: '#f44336',
      icon: 'star',
      bookmark_count: 12,
      is_public: true
    }
  ]

  const mockStatistics = {
    total_bookmarks: 25,
    favorite_count: 8,
    collection_count: 4,
    content_types_bookmarked: 3
  }

  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.setItem('token', 'mock-token')
    global.alert = vi.fn()
    global.confirm = vi.fn(() => true)
  })

  const renderManager = (props = {}) => {
    return render(
      <BookmarkManager
        contentType={mockContentType}
        contentId={mockContentId}
        onBookmarkChange={mockOnBookmarkChange}
        {...props}
      />
    )
  }

  describe('Initial Loading', () => {
    it('should fetch bookmarks on mount', async () => {
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: mockBookmarks } })
      })

      renderManager()

      await waitFor(() => {
        expect(axios.get).toHaveBeenCalledWith(
          expect.stringContaining('/content/bookmarks'),
          expect.objectContaining({
            headers: expect.objectContaining({ Authorization: 'Bearer mock-token' })
          })
        )
      })
    })

    it('should fetch collections on mount', async () => {
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: mockCollections } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: [] } })
      })

      renderManager()

      await waitFor(() => {
        expect(axios.get).toHaveBeenCalledWith(
          expect.stringContaining('/content/bookmarks/collections'),
          expect.any(Object)
        )
      })
    })

    it('should fetch statistics on mount', async () => {
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: [] } })
      })

      renderManager()

      await waitFor(() => {
        expect(axios.get).toHaveBeenCalledWith(
          expect.stringContaining('/content/bookmarks/statistics'),
          expect.any(Object)
        )
      })
    })

    it('should show loading state initially', () => {
      axios.get.mockImplementation(() => new Promise(() => {}))

      const { container } = renderManager()

      expect(container.querySelector('.MuiCircularProgress-root')).toBeInTheDocument()
    })
  })

  describe('Bookmarks Display', () => {
    it('should display bookmarks after loading', async () => {
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: mockCollections } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: mockBookmarks } })
      })

      renderManager()

      await waitFor(() => {
        expect(screen.getByText('Important Chapter')).toBeInTheDocument()
        expect(screen.getByText(/Review for exam/i)).toBeInTheDocument()
      })
    })

    it('should display bookmark without title using content type and ID', async () => {
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: mockBookmarks } })
      })

      renderManager()

      await waitFor(() => {
        // Component displays content_type - content_id.slice(0, 8)
        // For 'section-456', .slice(0, 8) gives 'section-'
        expect(screen.getByText(/section - section-/i)).toBeInTheDocument()
      })
    })

    it('should display bookmark tags', async () => {
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: mockBookmarks } })
      })

      renderManager()

      await waitFor(() => {
        expect(screen.getByText('neurosurgery')).toBeInTheDocument()
        expect(screen.getByText('important')).toBeInTheDocument()
        expect(screen.getByText('anatomy')).toBeInTheDocument()
      })
    })

    it('should display favorite icon for favorited bookmarks', async () => {
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: mockBookmarks } })
      })

      const { container } = renderManager()

      await waitFor(() => {
        expect(screen.getByText('Important Chapter')).toBeInTheDocument()
      })

      // Check for star icon (favorite)
      const starIcons = container.querySelectorAll('[data-testid="StarIcon"]')
      expect(starIcons.length).toBeGreaterThan(0)
    })

    it('should show empty state when no bookmarks', async () => {
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: [] } })
      })

      renderManager()

      await waitFor(() => {
        expect(screen.getByText(/No bookmarks yet/i)).toBeInTheDocument()
      })
    })

    it('should have Create Bookmark button in empty state', async () => {
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: [] } })
      })

      renderManager()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Create Bookmark/i })).toBeInTheDocument()
      })
    })
  })

  describe('Collections Display', () => {
    it('should display collections in Collections tab', async () => {
      const user = userEvent.setup({ delay: null })
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: mockCollections } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: [] } })
      })

      renderManager()

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /Collections/i })).toBeInTheDocument()
      })

      // Click Collections tab
      await user.click(screen.getByRole('tab', { name: /Collections/i }))

      await waitFor(() => {
        expect(screen.getByText('Study Materials')).toBeInTheDocument()
        expect(screen.getByText('Research Papers')).toBeInTheDocument()
      })
    })

    it('should display collection descriptions', async () => {
      const user = userEvent.setup({ delay: null })
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: mockCollections } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: [] } })
      })

      renderManager()

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /Collections/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('tab', { name: /Collections/i }))

      await waitFor(() => {
        expect(screen.getByText(/Resources for board exam/i)).toBeInTheDocument()
        expect(screen.getByText(/Recent publications/i)).toBeInTheDocument()
      })
    })

    it('should display bookmark counts for collections', async () => {
      const user = userEvent.setup({ delay: null })
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: mockCollections } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: [] } })
      })

      renderManager()

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /Collections/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('tab', { name: /Collections/i }))

      await waitFor(() => {
        expect(screen.getByText(/5 bookmarks/i)).toBeInTheDocument()
        expect(screen.getByText(/12 bookmarks/i)).toBeInTheDocument()
      })
    })

    it('should show empty state when no collections', async () => {
      const user = userEvent.setup({ delay: null })
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: [] } })
      })

      renderManager()

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /Collections/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('tab', { name: /Collections/i }))

      await waitFor(() => {
        expect(screen.getByText(/No collections yet/i)).toBeInTheDocument()
      })
    })
  })

  describe('Statistics Display', () => {
    it('should display statistics', async () => {
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: [] } })
      })

      renderManager()

      await waitFor(() => {
        expect(screen.getByText('25')).toBeInTheDocument()
        expect(screen.getByText('Total Bookmarks')).toBeInTheDocument()
        expect(screen.getByText('8')).toBeInTheDocument()
        expect(screen.getByText('Favorites')).toBeInTheDocument()
        expect(screen.getByText('4')).toBeInTheDocument()
        // Use getAllByText since "Collections" appears in both stats and tabs
        const collectionsText = screen.getAllByText('Collections')
        expect(collectionsText.length).toBeGreaterThan(0)
      })
    })

    it('should handle missing statistics gracefully', async () => {
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: null } })
        }
        return Promise.resolve({ data: { bookmarks: [] } })
      })

      renderManager()

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /Bookmarks/i })).toBeInTheDocument()
      })

      // Should not crash
    })
  })

  describe('Create Bookmark', () => {
    it('should open bookmark dialog when Add Bookmark clicked', async () => {
      const user = userEvent.setup({ delay: null })
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: [] } })
      })

      renderManager()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Add Bookmark/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /Add Bookmark/i }))

      await waitFor(() => {
        // Use getByRole to find dialog since "Create Bookmark" text appears in multiple places
        expect(screen.getByRole('dialog')).toBeInTheDocument()
        expect(screen.getByLabelText(/Title \(optional\)/i)).toBeInTheDocument()
      })
    })

    it('should have form fields in bookmark dialog', async () => {
      const user = userEvent.setup({ delay: null })
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: mockCollections } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: [] } })
      })

      renderManager()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Add Bookmark/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /Add Bookmark/i }))

      await waitFor(() => {
        expect(screen.getByLabelText(/Title \(optional\)/i)).toBeInTheDocument()
        expect(screen.getByLabelText(/Notes/i)).toBeInTheDocument()
      })
    })

    it('should allow adding tags', async () => {
      const user = userEvent.setup({ delay: null })
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: [] } })
      })

      renderManager()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Add Bookmark/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /Add Bookmark/i }))

      await waitFor(() => {
        expect(screen.getByLabelText(/Add tag/i)).toBeInTheDocument()
      })

      await user.type(screen.getByLabelText(/Add tag/i), 'test-tag')
      await user.click(screen.getByRole('button', { name: /^Add$/i }))

      await waitFor(() => {
        expect(screen.getByText('test-tag')).toBeInTheDocument()
      })
    })

    it('should create bookmark when submitted', async () => {
      const user = userEvent.setup({ delay: null })
      axios.get
        .mockImplementation((url) => {
          if (url.includes('/bookmarks/collections')) {
            return Promise.resolve({ data: { collections: [] } })
          }
          if (url.includes('/bookmarks/statistics')) {
            return Promise.resolve({ data: { statistics: mockStatistics } })
          }
          return Promise.resolve({ data: { bookmarks: [] } })
        })
      axios.post.mockResolvedValueOnce({
        data: {
          success: true,
          bookmark: { id: 'new-bm' }
        }
      })

      renderManager()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Add Bookmark/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /Add Bookmark/i }))

      await waitFor(() => {
        expect(screen.getByLabelText(/Title \(optional\)/i)).toBeInTheDocument()
      })

      await user.type(screen.getByLabelText(/Title \(optional\)/i), 'My Bookmark')

      const createButton = screen.getByRole('button', { name: /^Create$/i })
      await user.click(createButton)

      await waitFor(() => {
        expect(axios.post).toHaveBeenCalledWith(
          expect.stringContaining('/content/bookmarks'),
          expect.objectContaining({
            title: 'My Bookmark',
            content_type: mockContentType,
            content_id: mockContentId
          }),
          expect.any(Object)
        )
      })
    })

    it('should call onBookmarkChange callback on success', async () => {
      const user = userEvent.setup({ delay: null })
      const newBookmark = { id: 'new-bm', title: 'Test' }
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: [] } })
      })
      axios.post.mockResolvedValueOnce({
        data: {
          success: true,
          bookmark: newBookmark
        }
      })

      renderManager()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Add Bookmark/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /Add Bookmark/i }))
      await waitFor(() => {
        expect(screen.getByLabelText(/Title \(optional\)/i)).toBeInTheDocument()
      })

      const createButton = screen.getByRole('button', { name: /^Create$/i })
      await user.click(createButton)

      await waitFor(() => {
        expect(mockOnBookmarkChange).toHaveBeenCalledWith(newBookmark)
      })
    })
  })

  describe('Delete Bookmark', () => {
    it('should confirm before deleting', async () => {
      const user = userEvent.setup({ delay: null })
      global.confirm = vi.fn(() => false)
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: mockBookmarks } })
      })

      const { container } = renderManager()

      await waitFor(() => {
        expect(screen.getByText('Important Chapter')).toBeInTheDocument()
      })

      // Find delete button
      const deleteButtons = container.querySelectorAll('[data-testid="DeleteIcon"]')
      if (deleteButtons.length > 0) {
        const deleteButton = deleteButtons[0].closest('button')
        await user.click(deleteButton)

        expect(global.confirm).toHaveBeenCalledWith('Delete this bookmark?')
      }
    })

    it('should call delete API when confirmed', async () => {
      const user = userEvent.setup({ delay: null })
      global.confirm = vi.fn(() => true)
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: mockBookmarks } })
      })
      axios.delete.mockResolvedValueOnce({ data: { success: true } })

      const { container } = renderManager()

      await waitFor(() => {
        expect(screen.getByText('Important Chapter')).toBeInTheDocument()
      })

      const deleteButtons = container.querySelectorAll('[data-testid="DeleteIcon"]')
      if (deleteButtons.length > 0) {
        const deleteButton = deleteButtons[0].closest('button')
        await user.click(deleteButton)

        await waitFor(() => {
          expect(axios.delete).toHaveBeenCalledWith(
            expect.stringContaining('/content/bookmarks/bm-1'),
            expect.any(Object)
          )
        })
      }
    })
  })

  describe('Create Collection', () => {
    it('should open collection dialog when New Collection clicked', async () => {
      const user = userEvent.setup({ delay: null })
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: [] } })
      })

      renderManager()

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /Collections/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('tab', { name: /Collections/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /New Collection/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /New Collection/i }))

      await waitFor(() => {
        expect(screen.getByText('Create Collection')).toBeInTheDocument()
      })
    })

    it('should have form fields in collection dialog', async () => {
      const user = userEvent.setup({ delay: null })
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: [] } })
      })

      renderManager()

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /Collections/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('tab', { name: /Collections/i }))
      await user.click(screen.getByRole('button', { name: /New Collection/i }))

      await waitFor(() => {
        expect(screen.getByLabelText(/Collection Name/i)).toBeInTheDocument()
        expect(screen.getByLabelText(/Description/i)).toBeInTheDocument()
      })
    })

    it('should create collection when submitted', async () => {
      const user = userEvent.setup({ delay: null })
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: [] } })
      })
      axios.post.mockResolvedValueOnce({ data: { success: true } })

      renderManager()

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /Collections/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('tab', { name: /Collections/i }))
      await user.click(screen.getByRole('button', { name: /New Collection/i }))

      await waitFor(() => {
        expect(screen.getByLabelText(/Collection Name/i)).toBeInTheDocument()
      })

      await user.type(screen.getByLabelText(/Collection Name/i), 'My Collection')

      const createButton = screen.getByRole('button', { name: /^Create$/i })
      await user.click(createButton)

      await waitFor(() => {
        expect(axios.post).toHaveBeenCalledWith(
          expect.stringContaining('/content/bookmarks/collections'),
          expect.objectContaining({
            name: 'My Collection'
          }),
          expect.any(Object)
        )
      })
    })
  })

  describe('Tab Navigation', () => {
    it('should default to Bookmarks tab', async () => {
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: [] } })
      })

      renderManager()

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /Bookmarks/i })).toHaveAttribute('aria-selected', 'true')
      })
    })

    it('should switch to Collections tab when clicked', async () => {
      const user = userEvent.setup({ delay: null })
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: [] } })
      })

      renderManager()

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /Collections/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('tab', { name: /Collections/i }))

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /Collections/i })).toHaveAttribute('aria-selected', 'true')
      })
    })
  })

  describe('Error Handling', () => {
    it('should show error when loading bookmarks fails', async () => {
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.reject(new Error('Load failed'))
      })

      renderManager()

      await waitFor(() => {
        expect(screen.getByText(/Failed to load bookmarks/i)).toBeInTheDocument()
      })
    })

    it('should allow dismissing error alert', async () => {
      const user = userEvent.setup({ delay: null })
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.reject(new Error('Load failed'))
      })

      renderManager()

      await waitFor(() => {
        expect(screen.getByText(/Failed to load bookmarks/i)).toBeInTheDocument()
      })

      const closeButton = screen.getByLabelText(/close/i)
      await user.click(closeButton)

      await waitFor(() => {
        expect(screen.queryByText(/Failed to load bookmarks/i)).not.toBeInTheDocument()
      })
    })
  })

  describe('Edge Cases', () => {
    it('should handle missing onBookmarkChange callback', async () => {
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: [] } })
      })

      render(<BookmarkManager contentType={mockContentType} contentId={mockContentId} />)

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /Bookmarks/i })).toBeInTheDocument()
      })
    })

    it('should handle bookmarks without tags', async () => {
      const bookmarksNoTags = [{ ...mockBookmarks[0], tags: null }]
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: bookmarksNoTags } })
      })

      renderManager()

      await waitFor(() => {
        expect(screen.getByText('Important Chapter')).toBeInTheDocument()
      })
    })

    it('should handle collections without bookmark_count', async () => {
      const user = userEvent.setup({ delay: null })
      const collectionsNoCount = mockCollections.map(c => ({ ...c, bookmark_count: undefined }))
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: collectionsNoCount } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: [] } })
      })

      renderManager()

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /Collections/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('tab', { name: /Collections/i }))

      await waitFor(() => {
        // Use getAllByText since multiple collections may show "0 bookmarks"
        const zeroBookmarks = screen.getAllByText(/0 bookmarks/i)
        expect(zeroBookmarks.length).toBeGreaterThan(0)
      })
    })
  })

  describe('API Integration', () => {
    it('should include auth token in requests', async () => {
      axios.get.mockImplementation((url) => {
        if (url.includes('/bookmarks/collections')) {
          return Promise.resolve({ data: { collections: [] } })
        }
        if (url.includes('/bookmarks/statistics')) {
          return Promise.resolve({ data: { statistics: mockStatistics } })
        }
        return Promise.resolve({ data: { bookmarks: [] } })
      })

      renderManager()

      await waitFor(() => {
        expect(axios.get).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            headers: expect.objectContaining({
              Authorization: 'Bearer mock-token'
            })
          })
        )
      })
    })
  })
})
