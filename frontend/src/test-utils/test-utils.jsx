/**
 * Test Utilities for React Testing Library
 * Provides custom render functions with all necessary providers
 */

import { render } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import { AuthProvider } from '../contexts/AuthContext'

// Create default MUI theme for tests
const theme = createTheme()

/**
 * Custom render function that wraps components with all providers
 * @param {React.ReactElement} ui - Component to render
 * @param {Object} options - Additional options
 * @param {Object} options.initialEntries - Initial router entries
 * @param {Object} options.authValue - Mock auth context value
 * @returns {Object} - Render result with additional utilities
 */
export function renderWithProviders(ui, {
  initialEntries = ['/'],
  authValue = {
    user: null,
    token: null,
    login: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
    isAuthenticated: false,
    isLoading: false,
  },
  ...renderOptions
} = {}) {

  function Wrapper({ children }) {
    return (
      <BrowserRouter>
        <ThemeProvider theme={theme}>
          <AuthProvider value={authValue}>
            {children}
          </AuthProvider>
        </ThemeProvider>
      </BrowserRouter>
    )
  }

  return {
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
    // Add custom utilities if needed
  }
}

/**
 * Render with only Router (no auth)
 */
export function renderWithRouter(ui, { initialEntries = ['/'], ...renderOptions } = {}) {
  function Wrapper({ children }) {
    return (
      <BrowserRouter>
        <ThemeProvider theme={theme}>
          {children}
        </ThemeProvider>
      </BrowserRouter>
    )
  }

  return render(ui, { wrapper: Wrapper, ...renderOptions })
}

/**
 * Render with only Theme (no router, no auth)
 */
export function renderWithTheme(ui, renderOptions = {}) {
  function Wrapper({ children }) {
    return <ThemeProvider theme={theme}>{children}</ThemeProvider>
  }

  return render(ui, { wrapper: Wrapper, ...renderOptions })
}

// Re-export everything from React Testing Library
export * from '@testing-library/react'
export { default as userEvent } from '@testing-library/user-event'
