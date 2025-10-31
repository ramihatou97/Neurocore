/**
 * Navbar Component Tests
 * Comprehensive test suite for Navbar component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import userEvent from '@testing-library/user-event'
import Navbar from '../Navbar'
import AuthContext from '../../contexts/AuthContext'

// Mock navigate function
const mockNavigate = vi.fn()

// Mock react-router-dom
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

describe('Navbar Component', () => {
  beforeEach(() => {
    mockNavigate.mockClear()
  })

  const renderNavbar = (authValue) => {
    return render(
      <BrowserRouter>
        <AuthContext.Provider value={authValue}>
          <Navbar />
        </AuthContext.Provider>
      </BrowserRouter>
    )
  }

  describe('Rendering - Unauthenticated', () => {
    const unauthContext = {
      user: null,
      isAuthenticated: false,
      logout: vi.fn(),
    }

    it('should render navbar', () => {
      renderNavbar(unauthContext)
      expect(screen.getByRole('navigation')).toBeInTheDocument()
    })

    it('should render logo', () => {
      renderNavbar(unauthContext)
      expect(screen.getByText('🧠')).toBeInTheDocument()
      expect(screen.getByText('Neurosurgery KB')).toBeInTheDocument()
    })

    it('should render login button when not authenticated', () => {
      renderNavbar(unauthContext)
      expect(screen.getByRole('link', { name: /login/i })).toBeInTheDocument()
    })

    it('should render register button when not authenticated', () => {
      renderNavbar(unauthContext)
      expect(screen.getByRole('link', { name: /register/i })).toBeInTheDocument()
    })

    it('should not render navigation links when not authenticated', () => {
      renderNavbar(unauthContext)
      expect(screen.queryByRole('link', { name: /dashboard/i })).not.toBeInTheDocument()
      expect(screen.queryByRole('link', { name: /search/i })).not.toBeInTheDocument()
      expect(screen.queryByRole('link', { name: /chapters/i })).not.toBeInTheDocument()
    })

    it('should not render logout button when not authenticated', () => {
      renderNavbar(unauthContext)
      expect(screen.queryByRole('button', { name: /logout/i })).not.toBeInTheDocument()
    })
  })

  describe('Rendering - Authenticated', () => {
    const authContext = {
      user: {
        id: '1',
        email: 'test@example.com',
        name: 'Test User',
        is_admin: false,
      },
      isAuthenticated: true,
      logout: vi.fn(),
    }

    it('should render navigation links when authenticated', () => {
      renderNavbar(authContext)
      expect(screen.getByRole('link', { name: /dashboard/i })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: /search/i })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: /chapters/i })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: /pdfs/i })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: /tasks/i })).toBeInTheDocument()
    })

    it('should display user email', () => {
      renderNavbar(authContext)
      expect(screen.getByText('test@example.com')).toBeInTheDocument()
    })

    it('should render logout button when authenticated', () => {
      renderNavbar(authContext)
      expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument()
    })

    it('should not render login/register buttons when authenticated', () => {
      renderNavbar(authContext)
      const buttons = screen.getAllByRole('button')
      const loginButton = buttons.find((btn) => btn.textContent.includes('Login'))
      const registerButton = buttons.find((btn) => btn.textContent.includes('Register'))
      expect(loginButton).toBeUndefined()
      expect(registerButton).toBeUndefined()
    })
  })

  describe('Admin-Specific Features', () => {
    it('should show analytics link for admin users', () => {
      const adminContext = {
        user: {
          id: '1',
          email: 'admin@example.com',
          is_admin: true,
        },
        isAuthenticated: true,
        logout: vi.fn(),
      }

      renderNavbar(adminContext)
      expect(screen.getByRole('link', { name: /analytics/i })).toBeInTheDocument()
    })

    it('should not show analytics link for non-admin users', () => {
      const nonAdminContext = {
        user: {
          id: '1',
          email: 'user@example.com',
          is_admin: false,
        },
        isAuthenticated: true,
        logout: vi.fn(),
      }

      renderNavbar(nonAdminContext)
      expect(screen.queryByRole('link', { name: /analytics/i })).not.toBeInTheDocument()
    })

    it('should not show analytics link when user.is_admin is undefined', () => {
      const context = {
        user: {
          id: '1',
          email: 'user@example.com',
        },
        isAuthenticated: true,
        logout: vi.fn(),
      }

      renderNavbar(context)
      expect(screen.queryByRole('link', { name: /analytics/i })).not.toBeInTheDocument()
    })
  })

  describe('User Display', () => {
    it('should display user email when available', () => {
      const context = {
        user: {
          email: 'john@example.com',
        },
        isAuthenticated: true,
        logout: vi.fn(),
      }

      renderNavbar(context)
      expect(screen.getByText('john@example.com')).toBeInTheDocument()
    })

    it('should display user name when email not available', () => {
      const context = {
        user: {
          name: 'John Doe',
        },
        isAuthenticated: true,
        logout: vi.fn(),
      }

      renderNavbar(context)
      expect(screen.getByText('John Doe')).toBeInTheDocument()
    })

    it('should display "User" as fallback', () => {
      const context = {
        user: {},
        isAuthenticated: true,
        logout: vi.fn(),
      }

      renderNavbar(context)
      expect(screen.getByText('User')).toBeInTheDocument()
    })

    it('should prefer email over name', () => {
      const context = {
        user: {
          email: 'john@example.com',
          name: 'John Doe',
        },
        isAuthenticated: true,
        logout: vi.fn(),
      }

      renderNavbar(context)
      expect(screen.getByText('john@example.com')).toBeInTheDocument()
      expect(screen.queryByText('John Doe')).not.toBeInTheDocument()
    })
  })

  describe('Navigation Links', () => {
    const authContext = {
      user: { email: 'test@example.com' },
      isAuthenticated: true,
      logout: vi.fn(),
    }

    it('should have correct href for dashboard link', () => {
      renderNavbar(authContext)
      const dashboardLink = screen.getByRole('link', { name: /dashboard/i })
      expect(dashboardLink).toHaveAttribute('href', '/dashboard')
    })

    it('should have correct href for search link', () => {
      renderNavbar(authContext)
      const searchLink = screen.getByRole('link', { name: /search/i })
      expect(searchLink).toHaveAttribute('href', '/search')
    })

    it('should have correct href for chapters link', () => {
      renderNavbar(authContext)
      const chaptersLink = screen.getByRole('link', { name: /chapters/i })
      expect(chaptersLink).toHaveAttribute('href', '/chapters')
    })

    it('should have correct href for pdfs link', () => {
      renderNavbar(authContext)
      const pdfsLink = screen.getByRole('link', { name: /pdfs/i })
      expect(pdfsLink).toHaveAttribute('href', '/pdfs')
    })

    it('should have correct href for tasks link', () => {
      renderNavbar(authContext)
      const tasksLink = screen.getByRole('link', { name: /tasks/i })
      expect(tasksLink).toHaveAttribute('href', '/tasks')
    })

    it('should have correct href for logo link', () => {
      renderNavbar(authContext)
      const nav = screen.getByRole('navigation')
      const logoLink = within(nav).getAllByRole('link')[0]
      expect(logoLink).toHaveAttribute('href', '/')
    })
  })

  describe('Logout Functionality', () => {
    it('should call logout function when logout button clicked', async () => {
      const mockLogout = vi.fn().mockResolvedValue(undefined)
      const user = userEvent.setup()

      const context = {
        user: { email: 'test@example.com' },
        isAuthenticated: true,
        logout: mockLogout,
      }

      renderNavbar(context)
      const logoutButton = screen.getByRole('button', { name: /logout/i })

      await user.click(logoutButton)

      expect(mockLogout).toHaveBeenCalledTimes(1)
    })

    it('should navigate to login page after logout', async () => {
      const mockLogout = vi.fn().mockResolvedValue(undefined)
      const user = userEvent.setup()

      const context = {
        user: { email: 'test@example.com' },
        isAuthenticated: true,
        logout: mockLogout,
      }

      renderNavbar(context)
      const logoutButton = screen.getByRole('button', { name: /logout/i })

      await user.click(logoutButton)

      // Wait for logout to complete
      await vi.waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/login')
      })
    })
  })

  describe('Styling and Layout', () => {
    it('should have navigation role', () => {
      const context = {
        user: null,
        isAuthenticated: false,
        logout: vi.fn(),
      }

      renderNavbar(context)
      const nav = screen.getByRole('navigation')
      expect(nav).toHaveClass('bg-white', 'shadow-sm', 'border-b')
    })

    it('should have responsive container', () => {
      const context = {
        user: null,
        isAuthenticated: false,
        logout: vi.fn(),
      }

      const { container } = renderNavbar(context)
      const navContainer = container.querySelector('.max-w-7xl')
      expect(navContainer).toBeInTheDocument()
    })

    it('should hide navigation links on mobile', () => {
      const context = {
        user: { email: 'test@example.com' },
        isAuthenticated: true,
        logout: vi.fn(),
      }

      const { container } = renderNavbar(context)
      const navLinks = container.querySelector('.hidden.md\\:flex')
      expect(navLinks).toBeInTheDocument()
    })
  })

  describe('Button Variants', () => {
    it('should render logout button with outline variant', () => {
      const context = {
        user: { email: 'test@example.com' },
        isAuthenticated: true,
        logout: vi.fn(),
      }

      renderNavbar(context)
      const logoutButton = screen.getByRole('button', { name: /logout/i })
      expect(logoutButton).toHaveClass('border-2', 'border-blue-600')
    })

    it('should render logout button with small size', () => {
      const context = {
        user: { email: 'test@example.com' },
        isAuthenticated: true,
        logout: vi.fn(),
      }

      renderNavbar(context)
      const logoutButton = screen.getByRole('button', { name: /logout/i })
      expect(logoutButton).toHaveClass('px-3', 'py-1.5', 'text-sm')
    })
  })

  describe('Accessibility', () => {
    it('should use semantic nav element', () => {
      const context = {
        user: null,
        isAuthenticated: false,
        logout: vi.fn(),
      }

      renderNavbar(context)
      expect(screen.getByRole('navigation')).toBeInTheDocument()
    })

    it('should have accessible links', () => {
      const context = {
        user: { email: 'test@example.com' },
        isAuthenticated: true,
        logout: vi.fn(),
      }

      renderNavbar(context)
      const links = screen.getAllByRole('link')
      expect(links.length).toBeGreaterThan(0)
      links.forEach((link) => {
        expect(link).toHaveAttribute('href')
      })
    })

    it('should have accessible logout button', () => {
      const context = {
        user: { email: 'test@example.com' },
        isAuthenticated: true,
        logout: vi.fn(),
      }

      renderNavbar(context)
      const logoutButton = screen.getByRole('button', { name: /logout/i })
      expect(logoutButton).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('should handle null user gracefully', () => {
      const context = {
        user: null,
        isAuthenticated: true,
        logout: vi.fn(),
      }

      renderNavbar(context)
      expect(screen.getByText('User')).toBeInTheDocument()
    })

    it('should handle undefined user gracefully', () => {
      const context = {
        user: undefined,
        isAuthenticated: true,
        logout: vi.fn(),
      }

      renderNavbar(context)
      expect(screen.getByText('User')).toBeInTheDocument()
    })
  })
})
