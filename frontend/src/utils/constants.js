/**
 * Application Constants
 * Environment variables and configuration
 */

// API Configuration
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002';
export const API_VERSION = '/api/v1';
export const API_URL = `${API_BASE_URL}${API_VERSION}`;

// WebSocket Configuration
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8002';
export const WS_URL = `${WS_BASE_URL}${API_VERSION}/ws`;

// Storage Keys
export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'access_token',
  REFRESH_TOKEN: 'refresh_token',
  USER: 'user',
};

// Chapter Generation Stages
// NOTE: These names MUST match backend/utils/events.py CHAPTER_STAGE_NAMES exactly
export const CHAPTER_STAGES = {
  STAGE_1_INPUT: 'Input Validation',
  STAGE_2_CONTEXT: 'Context Building',
  STAGE_3_RESEARCH_INTERNAL: 'Internal Research',
  STAGE_4_RESEARCH_EXTERNAL: 'External Research',
  STAGE_5_PLANNING: 'Synthesis Planning',  // Fixed: was "Image Search"
  STAGE_6_GENERATION: 'Section Generation',  // Fixed: was "Content Synthesis"
  STAGE_7_IMAGES: 'Image Integration',  // Fixed: was "Outline Creation"
  STAGE_8_CITATIONS: 'Citation Network',  // Fixed: was "Draft Generation"
  STAGE_9_QA: 'Quality Assurance',  // Fixed: was "Content Enrichment"
  STAGE_10_FACT_CHECK: 'Fact Checking',  // Fixed: was "Citation Integration"
  STAGE_11_FORMATTING: 'Formatting',  // Fixed: was "Image Integration"
  STAGE_12_REVIEW: 'Review & Refinement',  // Fixed: was "Quality Assurance"
  STAGE_13_FINALIZATION: 'Finalization',  // Fixed: was "Final Formatting"
  STAGE_14_DELIVERY: 'Delivery',  // Fixed: was "Finalization"
};

// WebSocket Event Types
export const WS_EVENT_TYPES = {
  CHAPTER_STARTED: 'chapter_started',
  CHAPTER_PROGRESS: 'chapter_progress',
  CHAPTER_STAGE_UPDATE: 'chapter_stage_update',
  CHAPTER_COMPLETED: 'chapter_completed',
  CHAPTER_FAILED: 'chapter_failed',
  TASK_STARTED: 'task_started',
  TASK_PROGRESS: 'task_progress',
  TASK_COMPLETED: 'task_completed',
  TASK_FAILED: 'task_failed',
  PDF_UPLOADED: 'pdf_uploaded',
  PDF_PROCESSING: 'pdf_processing',
  PDF_TEXT_EXTRACTED: 'pdf_text_extracted',
  PDF_IMAGES_EXTRACTED: 'pdf_images_extracted',
  PDF_COMPLETED: 'pdf_completed',
  PDF_FAILED: 'pdf_failed',
};

// Task Types
export const TASK_TYPES = {
  PDF_PROCESSING: 'pdf_processing',
  IMAGE_ANALYSIS: 'image_analysis',
  EMBEDDING_GENERATION: 'embedding_generation',
  CITATION_EXTRACTION: 'citation_extraction',
};

// Task Statuses
export const TASK_STATUSES = {
  PENDING: 'pending',
  RUNNING: 'running',
  COMPLETED: 'completed',
  FAILED: 'failed',
};

// PDF Processing Statuses
export const PDF_STATUSES = {
  UPLOADED: 'uploaded',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed',
};

// Chapter Generation Statuses
export const CHAPTER_STATUSES = {
  DRAFT: 'draft',
  IN_PROGRESS: 'in_progress',
  GENERATED: 'generated',
  REVIEWED: 'reviewed',
  PUBLISHED: 'published',
  ARCHIVED: 'archived',
  FAILED: 'failed',
};

// Chapter Types
export const CHAPTER_TYPES = {
  OVERVIEW: 'overview',
  DETAILED: 'detailed',
  CLINICAL: 'clinical',
  RESEARCH: 'research',
};

// Pagination
export const DEFAULT_PAGE_SIZE = 20;
export const PAGE_SIZES = [10, 20, 50, 100];

// File Upload
export const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
export const ALLOWED_FILE_TYPES = ['.pdf'];

// Timeouts
export const API_TIMEOUT = 30000; // 30 seconds
export const WS_RECONNECT_DELAY = 3000; // 3 seconds
export const WS_HEARTBEAT_INTERVAL = 30000; // 30 seconds

// Routes
export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  DASHBOARD: '/dashboard',
  PDFS: '/pdfs',
  PDF_UPLOAD: '/pdfs/upload',
  PDF_DETAIL: '/pdfs/:id',
  CHAPTERS: '/chapters',
  CHAPTER_CREATE: '/chapters/create',
  CHAPTER_DETAIL: '/chapters/:id',
  CHAPTER_EDIT: '/chapters/:id/edit',
  TASKS: '/tasks',
  TASK_DETAIL: '/tasks/:id',
  PROFILE: '/profile',
  SETTINGS: '/settings',
};
