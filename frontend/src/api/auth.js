/**
 * Authentication API Service
 * Handles user authentication, registration, and token management
 */

import apiClient from './client';

const authAPI = {
  /**
   * Register new user
   * POST /auth/register
   */
  register: async (userData) => {
    const response = await apiClient.post('/auth/register', userData);
    return response.data;
  },

  /**
   * Login user
   * POST /auth/login
   */
  login: async (credentials) => {
    const response = await apiClient.post('/auth/login', credentials);
    return response.data;
  },

  /**
   * Get current user info
   * GET /auth/me
   */
  getCurrentUser: async () => {
    const response = await apiClient.get('/auth/me');
    return response.data;
  },

  /**
   * Update user profile
   * PUT /auth/profile
   */
  updateProfile: async (userData) => {
    const response = await apiClient.put('/auth/profile', userData);
    return response.data;
  },

  /**
   * Change password
   * POST /auth/change-password
   */
  changePassword: async (passwordData) => {
    const response = await apiClient.post('/auth/change-password', passwordData);
    return response.data;
  },

  /**
   * Logout (client-side only - clear tokens)
   */
  logout: () => {
    // Backend doesn't have logout endpoint (stateless JWT)
    // Just clear local storage
    return Promise.resolve();
  },
};

export default authAPI;
