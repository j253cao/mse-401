/**
 * Centralized API Service
 * 
 * All API calls should go through this service to:
 * - Use environment variables for base URL
 * - Centralize error handling
 * - Provide type safety
 * - Make testing/mocking easier
 */

import type {
  RecommendRequest,
  RecommendResponse,
  RandomCourseResponse,
  TranscriptParseResponse,
  ResumeRecommendResponse,
  Course,
  RecommendFilters,
} from '@/types/api';

// Get API base URL from environment variable
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Custom error class for API errors
 */
export class ApiError extends Error {
  status?: number;
  data?: unknown;

  constructor(message: string, status?: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Generic fetch wrapper with error handling
 */
async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, options);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      throw new ApiError(
        errorData?.detail || `API request failed: ${response.statusText}`,
        response.status,
        errorData
      );
    }
    
    return response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      error instanceof Error ? error.message : 'Network error occurred'
    );
  }
}

/**
 * API Service object with all endpoint methods
 */
export const api = {
  /**
   * Get course recommendations based on search queries
   */
  async recommend(
    queries: string[],
    filters?: RecommendFilters
  ): Promise<Course[]> {
    const request: RecommendRequest = { queries, filters };
    
    const response = await fetchApi<RecommendResponse>('/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    
    // Transform response to Course[] format
    const query = queries[0];
    const results = response.results[query] || [];
    
    return results.map((r) => ({
      code: r.course_code,
      title: r.title,
      description: r.description,
    }));
  },

  /**
   * Get a random course
   */
  async getRandomCourse(): Promise<Course> {
    const response = await fetchApi<RandomCourseResponse>('/random-course');
    
    return {
      code: response.course_code,
      title: response.title,
      description: response.description,
    };
  },

  /**
   * Upload resume and get course recommendations
   */
  async uploadResume(file: File): Promise<Course[]> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetchApi<ResumeRecommendResponse>('/resume-recommend', {
      method: 'POST',
      body: formData,
    });
    
    return response.map((r) => ({
      code: r.course_code,
      title: r.title,
      description: r.description,
    }));
  },

  /**
   * Parse transcript PDF and extract course history
   */
  async parseTranscript(file: File): Promise<TranscriptParseResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetchApi<TranscriptParseResponse>('/transcript-parse', {
      method: 'POST',
      body: formData,
    });
    
    if (response.error) {
      throw new ApiError(response.error);
    }
    
    return response;
  },

  /**
   * Search courses by code or title (for course picker autocomplete)
   */
  async searchCourses(q: string, limit = 20): Promise<{ code: string; title: string }[]> {
    if (!q || q.trim().length < 2) return [];
    const params = new URLSearchParams({ q: q.trim(), limit: String(limit) });
    return fetchApi<{ code: string; title: string }[]>(`/courses/search?${params}`);
  },

  /**
   * Health check endpoint
   */
  async healthCheck(): Promise<{ status: string; message: string }> {
    return fetchApi('/');
  },
};

export default api;

