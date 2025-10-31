import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    // Test environment
    environment: 'jsdom',

    // Setup files
    setupFiles: ['./src/test-utils/setup.js'],

    // Globals
    globals: true,

    // Coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'src/test-utils/',
        '**/*.config.js',
        '**/*.test.{js,jsx}',
        '**/main.jsx',
        'dist/',
        'coverage/',
      ],
      // Coverage thresholds - targeting 80%
      statements: 80,
      branches: 80,
      functions: 80,
      lines: 80,
    },

    // Test file patterns
    include: [
      '**/*.{test,spec}.{js,jsx}',
      '**/__tests__/**/*.{js,jsx}'
    ],

    // Exclude patterns
    exclude: [
      'node_modules',
      'dist',
      '.idea',
      '.git',
      '.cache',
      'coverage'
    ],

    // Test timeout
    testTimeout: 10000,

    // Hook timeout
    hookTimeout: 10000,

    // Reporters
    reporters: ['verbose'],

    // Watch mode settings
    watch: false,

    // Clear mocks between tests
    clearMocks: true,

    // Restore mocks between tests
    restoreMocks: true,

    // Mock reset
    mockReset: true,
  },

  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@pages': path.resolve(__dirname, './src/pages'),
      '@contexts': path.resolve(__dirname, './src/contexts'),
      '@api': path.resolve(__dirname, './src/api'),
      '@services': path.resolve(__dirname, './src/services'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@utils': path.resolve(__dirname, './src/utils'),
    }
  }
})
