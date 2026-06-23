/**
 * Common types used across the application
 */

/** Citation metadata attached to AI-generated content */
export interface Citation {
  page: number;
  source: string;
  chunk_id: string;
}

/** Response from file upload endpoint */
export interface UploadResponse {
  file_id: string;
  pages: number;
  status: string;
}

/** Course statistics */
export interface CourseStats {
  course_id: string;
  status: string;
  generated_at: string;
  total_questions: number;
  total_flashcards: number;
  total_slides: number;
  has_course: boolean;
  has_summary: boolean;
  has_study_guide: boolean;
  has_mindmap: boolean;
  has_podcast: boolean;
}

/** Files generated for a course */
export interface CourseFiles {
  course_id: string;
  files: {
    course?: string;
    summary?: string;
    flashcards?: string;
    questions?: string;
    slides?: string[];
    mindmap?: string;
    guides?: string[];
    audio?: string[];
  };
}

/** Generic API error response */
export interface ApiError {
  message: string;
  status?: number;
}