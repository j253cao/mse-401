/**
 * API Type Definitions
 */

// Course types
export interface Course {
  code: string;
  title: string;
  description?: string;
}

export interface CourseRecommendation {
  rank: number;
  course_code: string;
  title: string;
  description: string;
  score: number;
}

// Request types
export interface RecommendFilters {
  include_undergrad?: boolean;
  include_grad?: boolean;
  department?: string[];
  completed_courses?: string[];
}

export interface RecommendRequest {
  queries: string[];
  filters?: RecommendFilters;
}

// Response types
export interface RecommendResponse {
  results: Record<string, CourseRecommendation[]>;
}

export interface RandomCourseResponse {
  course_code: string;
  title: string;
  description: string;
}

export interface TermSummary {
  term_id: number;
  term_name: string;
  level: string;
  courses: string[];
}

export interface LatestTerm {
  term_id: number;
  term_name: string;
  level: string;
  courses: string[];
}

export interface TranscriptParseResponse {
  courses: string[];
  latest_term: LatestTerm | null;
  program: string;
  student_number: number;
  term_summaries: TermSummary[];
  error?: string;
}

export interface ResumeRecommendResponse extends Array<CourseRecommendation> {}

// Student profile types (used in context)
export interface StudentProfile {
  program: string;
  studentNumber: number;
  latestTerm: LatestTerm | null;
}

