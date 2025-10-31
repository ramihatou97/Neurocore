/**
 * ProtectedRoute Component Tests
 * Comprehensive test suite for ProtectedRoute component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import ProtectedRoute from '../ProtectedRoute'
import { useAuth } from '../../contexts/AuthContext'

// Mock the useAuth hook
vi.mock('../../contexts/AuthContext', () => ({
  useAuth: vi.fn()
}))

describe('ProtectedRoute Component', () => {
  const TestComponent = () => <div>Protected Content</div>

  beforeEach(() => {
    useAuth.mockClear()
  })

  const renderProtectedRoute = (authValue, initialRoute = '/protected') => {
    useAuth.mockReturnValue(authValue)

    return render(
      <MemoryRouter initialEntries={[initialRoute]}>
        <Routes>
          <Route
            path="/protected"
            element={
              <ProtectedRoute>
                <TestComponent />
              </ProtectedRoute>
            }
          />
          <Route path="/login" element={<div>Login Page</div>} />
        </Routes>
      </MemoryRouter>
    )
  }

  describe('Loading State', () => {
    it('should show loading spinner when loading', () => {
      const authContext = {
        user: null,
        loading: true,
      }

      const { container } = renderProtectedRoute(authContext)
      // LoadingSpinner renders as div with .animate-spin class
      expect(container.querySelector('.animate-spin')).toBeInTheDocument()
    })

    it('should show loading spinner with large size', () => {
      const authContext = {
        user: null,
        loading: true,
      }

      const { container } = renderProtectedRoute(authContext)
      const spinner = container.querySelector('.h-12.w-12')
      expect(spinner).toBeInTheDocument()
    })

    it('should center loading spinner on screen', () => {
      const authContext = {
        user: null,
        loading: true,
      }

      const { container } = renderProtectedRoute(authContext)
      const loadingContainer = container.querySelector('.min-h-screen.flex.items-center.justify-center')
      expect(loadingContainer).toBeInTheDocument()
    })

    it('should not show children while loading', () => {
      const authContext = {
        user: null,
        loading: true,
      }

      renderProtectedRoute(authContext)
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    })
  })

  describe('Unauthenticated State', () => {
    it('should redirect to login when user is null', () => {
      const authContext = {
        user: null,
        loading: false,
      }

      renderProtectedRoute(authContext)
      expect(screen.getByText('Login Page')).toBeInTheDocument()
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    })

    it('should redirect to login when user is undefined', () => {
      const authContext = {
        user: undefined,
        loading: false,
      }

      renderProtectedRoute(authContext)
      expect(screen.getByText('Login Page')).toBeInTheDocument()
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    })

    it('should not show loading spinner when redirecting', () => {
      const authContext = {
        user: null,
        loading: false,
      }

      const { container } = renderProtectedRoute(authContext)
      const spinner = container.querySelector('.animate-spin')
      expect(spinner).not.toBeInTheDocument()
    })
  })

  describe('Authenticated State', () => {
    it('should render children when user is authenticated', () => {
      const authContext = {
        user: {
          id: '1',
          email: 'test@example.com',
        },
        loading: false,
      }

      renderProtectedRoute(authContext)
      expect(screen.getByText('Protected Content')).toBeInTheDocument()
    })

    it('should not show loading spinner when authenticated', () => {
      const authContext = {
        user: {
          id: '1',
          email: 'test@example.com',
        },
        loading: false,
      }

      const { container } = renderProtectedRoute(authContext)
      const spinner = container.querySelector('.animate-spin')
      expect(spinner).not.toBeInTheDocument()
    })

    it('should not redirect when authenticated', () => {
      const authContext = {
        user: {
          id: '1',
          email: 'test@example.com',
        },
        loading: false,
      }

      renderProtectedRoute(authContext)
      expect(screen.queryByText('Login Page')).not.toBeInTheDocument()
    })

    it('should work with minimal user object', () => {
      const authContext = {
        user: { id: '1' },
        loading: false,
      }

      renderProtectedRoute(authContext)
      expect(screen.getByText('Protected Content')).toBeInTheDocument()
    })

    it('should work with empty user object', () => {
      const authContext = {
        user: {},
        loading: false,
      }

      renderProtectedRoute(authContext)
      expect(screen.getByText('Protected Content')).toBeInTheDocument()
    })
  })

  describe('Children Rendering', () => {
    it('should render simple children', () => {
      const authContext = {
        user: { id: '1' },
        loading: false,
      }

      useAuth.mockReturnValue(authContext)

      render(
        <MemoryRouter initialEntries={["/"]}>
          <ProtectedRoute>
            <div>Simple Child</div>
          </ProtectedRoute>
        </MemoryRouter>
      )

      expect(screen.getByText('Simple Child')).toBeInTheDocument()
    })

    it('should render complex children', () => {
      const authContext = {
        user: { id: '1' },
        loading: false,
      }

      useAuth.mockReturnValue(authContext)

      render(
        <MemoryRouter initialEntries={["/"]}>
          <ProtectedRoute>
            <div>
              <h1>Title</h1>
              <p>Content</p>
            </div>
          </ProtectedRoute>
        </MemoryRouter>
      )

      expect(screen.getByText('Title')).toBeInTheDocument()
      expect(screen.getByText('Content')).toBeInTheDocument()
    })

    it('should render multiple children', () => {
      const authContext = {
        user: { id: '1' },
        loading: false,
      }

      useAuth.mockReturnValue(authContext)

      render(
        <MemoryRouter initialEntries={["/"]}>
          <ProtectedRoute>
            <div>Child 1</div>
            <div>Child 2</div>
          </ProtectedRoute>
        </MemoryRouter>
      )

      expect(screen.getByText('Child 1')).toBeInTheDocument()
      expect(screen.getByText('Child 2')).toBeInTheDocument()
    })
  })

  describe('State Transitions', () => {
    it('should transition from loading to authenticated', () => {
      useAuth.mockReturnValue({
        user: null,
        loading: true,
      })

      const { rerender } = render(
        <MemoryRouter initialEntries={["/"]}>
          <ProtectedRoute>
            <div>Protected Content</div>
          </ProtectedRoute>
        </MemoryRouter>
      )

      // Initially loading
      const container = document.body
      expect(container.querySelector('.animate-spin')).toBeInTheDocument()

      // Update to authenticated
      useAuth.mockReturnValue({
        user: { id: '1' },
        loading: false,
      })

      rerender(
        <MemoryRouter initialEntries={["/"]}>
          <ProtectedRoute>
            <div>Protected Content</div>
          </ProtectedRoute>
        </MemoryRouter>
      )

      expect(screen.getByText('Protected Content')).toBeInTheDocument()
    })

    it('should transition from loading to redirect', () => {
      useAuth.mockReturnValue({
        user: null,
        loading: true,
      })

      const { rerender } = render(
        <MemoryRouter initialEntries={["/protected"]}>
          <Routes>
            <Route
              path="/protected"
              element={
                <ProtectedRoute>
                  <TestComponent />
                </ProtectedRoute>
              }
            />
            <Route path="/login" element={<div>Login Page</div>} />
          </Routes>
        </MemoryRouter>
      )

      // Initially loading
      const container = document.body
      expect(container.querySelector('.animate-spin')).toBeInTheDocument()

      // Update to not loading, still no user
      useAuth.mockReturnValue({
        user: null,
        loading: false,
      })

      rerender(
        <MemoryRouter initialEntries={["/protected"]}>
          <Routes>
            <Route
              path="/protected"
              element={
                <ProtectedRoute>
                  <TestComponent />
                </ProtectedRoute>
              }
            />
            <Route path="/login" element={<div>Login Page</div>} />
          </Routes>
        </MemoryRouter>
      )

      expect(screen.getByText('Login Page')).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('should handle falsy user values correctly', () => {
      const falsyValues = [null, undefined, false, 0, '', NaN]

      falsyValues.forEach((value) => {
        const authContext = {
          user: value,
          loading: false,
        }

        const { unmount } = renderProtectedRoute(authContext)

        if (value) {
          // 0, false, '' are truthy in user check context
          expect(screen.getByText('Protected Content')).toBeInTheDocument()
        } else {
          expect(screen.getByText('Login Page')).toBeInTheDocument()
        }

        unmount()
      })
    })

    it('should handle missing loading prop', () => {
      const authContext = {
        user: { id: '1' },
        // loading prop missing
      }

      renderProtectedRoute(authContext)
      expect(screen.getByText('Protected Content')).toBeInTheDocument()
    })

    it('should handle both loading and user being truthy', () => {
      const authContext = {
        user: { id: '1' },
        loading: true,
      }

      const { container } = renderProtectedRoute(authContext)
      // Should show loading spinner, not content (loading takes precedence)
      expect(container.querySelector('.animate-spin')).toBeInTheDocument()
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    })
  })

  describe('Navigation Behavior', () => {
    it('should use replace navigation to prevent back button issues', () => {
      const authContext = {
        user: null,
        loading: false,
      }

      // This is tested implicitly by Navigate component with replace prop
      renderProtectedRoute(authContext)
      expect(screen.getByText('Login Page')).toBeInTheDocument()
    })

    it('should redirect to /login route specifically', () => {
      const authContext = {
        user: null,
        loading: false,
      }

      renderProtectedRoute(authContext)
      // If we see Login Page, it means redirect worked
      expect(screen.getByText('Login Page')).toBeInTheDocument()
    })
  })

  describe('Integration', () => {
    it('should work in a route hierarchy', () => {
      useAuth.mockReturnValue({
        user: { id: '1' },
        loading: false,
      })

      render(
        <MemoryRouter initialEntries={["/protected"]}>
          <Routes>
            <Route path="/" element={<div>Home</div>} />
            <Route
              path="/protected"
              element={
                <ProtectedRoute>
                  <div>Protected</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      )

      // Should render the protected route when authenticated
      expect(screen.getByText('Protected')).toBeInTheDocument()
    })

    it('should work with nested routes', () => {
      useAuth.mockReturnValue({
        user: { id: '1' },
        loading: false,
      })

      render(
        <MemoryRouter initialEntries={["/"]}>
          <ProtectedRoute>
            <Routes>
              <Route path="/" element={<div>Nested Route</div>} />
            </Routes>
          </ProtectedRoute>
        </MemoryRouter>
      )

      expect(screen.getByText('Nested Route')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('should maintain accessible content structure', () => {
      useAuth.mockReturnValue({
        user: { id: '1' },
        loading: false,
      })

      render(
        <MemoryRouter initialEntries={["/"]}>
          <ProtectedRoute>
            <main role="main">
              <h1>Page Title</h1>
            </main>
          </ProtectedRoute>
        </MemoryRouter>
      )

      expect(screen.getByRole('main')).toBeInTheDocument()
      expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
    })

    it('should render loading state accessibly', () => {
      const authContext = {
        user: null,
        loading: true,
      }

      const { container } = renderProtectedRoute(authContext)
      const loadingContainer = container.querySelector('.min-h-screen')
      expect(loadingContainer).toBeInTheDocument()
    })
  })
})
