/**
 * Analytics API
 * API methods for analytics and provider performance metrics
 */

import apiClient from './client';

const analyticsAPI = {
  /**
   * Get provider overview
   */
  async getProviderOverview(days = 30) {
    const response = await apiClient.get(`/analytics/providers/overview?days=${days}`);
    return response.data;
  },

  /**
   * Get provider comparison
   */
  async getProviderComparison(taskType = null, days = 30) {
    const params = new URLSearchParams({ days });
    if (taskType) {
      params.append('task_type', taskType);
    }
    const response = await apiClient.get(`/analytics/providers/comparison?${params}`);
    return response.data;
  },

  /**
   * Get single provider performance
   */
  async getProviderPerformance(provider, days = 30) {
    const response = await apiClient.get(`/analytics/providers/${provider}/performance?days=${days}`);
    return response.data;
  },

  /**
   * Get task provider rankings
   */
  async getTaskProviderRankings(taskType, days = 30) {
    const response = await apiClient.get(`/analytics/providers/task/${taskType}?days=${days}`);
    return response.data;
  },

  /**
   * Get quality vs cost analysis
   */
  async getQualityVsCost(days = 30) {
    const response = await apiClient.get(`/analytics/providers/quality-vs-cost?days=${days}`);
    return response.data;
  },

  /**
   * Get provider errors
   */
  async getProviderErrors(provider = null, days = 30) {
    const params = new URLSearchParams({ days });
    if (provider) {
      params.append('provider', provider);
    }
    const response = await apiClient.get(`/analytics/providers/errors?${params}`);
    return response.data;
  }
};

export default analyticsAPI;
