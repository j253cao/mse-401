/**
 * API Type Definitions
 */

// Course types
export interface ContributingProgram {
  name: string;
  type: "option" | "minor";
}

export interface Course {
  code: string;
  title: string;
  description?: string;
  score?: number;
  contributing_programs?: ContributingProgram[];
  prereqs?: string | null;
  coreqs?: string | null;
  antireqs?: string | null;
}

export interface CourseRecommendation {
  rank: number;
  course_code: string;
  title: string;
  description: string;
  score: number;
  contributing_programs?: ContributingProgram[];
  prereqs?: string | null;
  coreqs?: string | null;
  antireqs?: string | null;
}

// Request types
export interface RecommendFilters {
  include_undergrad?: boolean;
  include_grad?: boolean;
  department?: string[];
  completed_courses?: string[];
  ignore_dependencies?: boolean;
  options?: string[];
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
  contributing_programs?: ContributingProgram[];
  prereqs?: string | null;
  coreqs?: string | null;
  antireqs?: string | null;
}

export interface OptionsAndMinorsResponse {
  options: { name: string }[];
  minors: { name: string }[];
}

export interface HighValueCoursesResponse {
  courses: CourseRecommendation[];
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

// Program and term selection (items 1 & 2)
export type IncomingLevel = "1A" | "1B" | "2A" | "2B" | "3A" | "3B" | "4A" | "4B";

export interface StoredProfile {
  programCode: string;
  incomingLevel: IncomingLevel;
  completedCourses?: string[];
  startingTerm?: {
    season: "Fall" | "Winter" | "Spring";
    year: number;
  };
}

