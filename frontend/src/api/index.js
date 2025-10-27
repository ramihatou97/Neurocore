/**
 * API Module
 * Central export for all API services
 */

import authAPI from './auth';
import pdfAPI from './pdfs';
import chaptersAPI from './chapters';
import tasksAPI from './tasks';
import apiClient from './client';

export {
  authAPI,
  pdfAPI,
  chaptersAPI,
  tasksAPI,
  apiClient,
};

export default {
  auth: authAPI,
  pdfs: pdfAPI,
  chapters: chaptersAPI,
  tasks: tasksAPI,
  client: apiClient,
};
