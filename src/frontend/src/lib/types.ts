// ============================================================
// Auth Types
// ============================================================

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: "user" | "admin";
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string;
}

// ============================================================
// Course Types
// ============================================================

export interface CourseListItem {
  course_id: string;
  status: string;
  created_at?: string;
  filenames?: string[];
  file_count?: number;
  error?: string;
}

export interface CoursesResponse {
  courses: CourseListItem[];
  total: number;
}

export interface CourseStatusResponse {
  course_id: string;
  status: string;
  progress?: number;
  filename?: string;
  filenames?: string[];
  file_count?: number;
  created_at?: string;
  quality_score?: number;
  has_book?: boolean;
  has_slide?: boolean;
  has_quiz?: boolean;
  has_vid?: boolean;
  has_mindmap?: boolean;
  has_flashcards?: boolean;
  error?: string;
}

// ============================================================
// Upload Types
// ============================================================

export interface UploadResponse {
  course_id: string;
  document_id: string;
  filename: string;
  filenames: string[];
  file_count: number;
  status: string;
  message: string;
}

// ============================================================
// Study Pack Types (for future use)
// ============================================================

export interface StudyPackStats {
  course_id: string;
  status: string;
  has_book: boolean;
  has_book_pdf: boolean;
  has_slide: boolean;
  has_slide_pptx: boolean;
  has_quiz: boolean;
  has_quiz_answer_key: boolean;
  has_vid: boolean;
  has_mindmap: boolean;
  has_flashcards: boolean;
  quality_score?: number;
  num_chunks?: number;
}

export interface StudyPackResponse {
  course_id: string;
  stats: StudyPackStats;
  study_pack: {
    title: string;
    summary?: Array<{ topic: string; chapter: string; content: string }>;
    readiness?: Record<string, boolean>;
    quality_scores?: Record<string, number>;
    grounding?: {
      num_chunks: number;
      quality_score: number;
      warnings: string[];
    };
  };
}

// ============================================================
// API Error Types
// ============================================================

export interface ApiError {
  detail: string;
}

// ============================================================
// Component Prop Types
// ============================================================

export type CourseStatus = "processing" | "ready" | "error";

export function normalizeCourseStatus(status: string): CourseStatus {
  const s = status.toLowerCase();
  if (s === "ready" || s === "completed") return "ready";
  if (s === "error" || s === "failed") return "error";
  return "processing";
}
