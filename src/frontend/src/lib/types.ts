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
  name?: string;
  status: string;
  created_at?: string;
  filenames?: string[];
  file_count?: number;
  error?: string;
  name_pending?: boolean;
}

export interface CoursesResponse {
  courses: CourseListItem[];
  total: number;
}

export interface CourseStatusResponse {
  course_id: string;
  name?: string;
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
  error?: string;
  name_pending?: boolean;
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
// Generation & Artifact Types
// ============================================================

export interface GenerateRequest {
  course_id?: string;
  [key: string]: unknown;
}

export interface GenerateResponse {
  course_id: string;
  status?: string;
  message?: string;
  estimated_time?: string;
  regen_used?: number;
  regen_max?: number;
}

export interface BookSection {
  title: string;
  content: string;
}

export interface BookChapter {
  chapter_title: string;
  introduction?: string;
  objectives?: string[];
  sections: BookSection[];
  key_points?: string[];
  review_questions?: string[];
  source_chunk_ids?: string[];
}

export interface BookOutput {
  title: string;
  summary: string;
  preface?: string;
  chapters: BookChapter[];
  description?: string;
  estimated_duration?: string;
}

export interface BookArtifactStatus {
  status: "empty" | "processing" | "ready" | "error";
  error?: string | null;
  progress?: number | null;
  data: BookOutput | null;
  regen_used?: number;
  regen_max?: number;
}

export interface SlideItem {
  slide_number?: number;
  title: string;
  key_idea?: string;
  content?: string | string[];
  bullet_points?: string[];
  example?: string;
  layout_hint?: string;
  layout_type?: string;
  source_chunk_ids?: string[];
}

export interface SlidesOutput {
  title: string;
  slides: SlideItem[];
  total_slides?: number;
}

export interface SlideArtifactStatus {
  status: "empty" | "processing" | "ready" | "error";
  error?: string | null;
  progress?: number | null;
  data: SlidesOutput | null;
  regen_used?: number;
  regen_max?: number;
}

export interface QuizOption {
  key?: string;
  text?: string;
}

export interface QuizQuestion {
  question_number?: number;
  question_text?: string;
  question?: string;
  options: (string | QuizOption)[];
  correct_answer?: string;
  correct?: number | string;
  explanation?: string;
  difficulty?: string;
  question_type?: string;
  source_chunk_ids?: string[];
}

export interface QuizOutput {
  title: string;
  questions: QuizQuestion[];
  total_questions?: number;
}

export interface QuizArtifactStatus {
  status: "empty" | "processing" | "ready" | "error";
  error?: string | null;
  progress?: number | null;
  data: QuizQuestion[] | null;
  regen_used?: number;
  regen_max?: number;
}

export interface VidScene {
  scene_number: number;
  title: string;
  on_screen_text?: string;
  narration: string;
  duration_seconds: number;
}

export interface VidOutput {
  title: string;
  total_duration_seconds?: number;
  scenes: VidScene[];
}

export interface VidArtifactStatus {
  status: "empty" | "processing" | "ready" | "error";
  error?: string | null;
  progress?: number | null;
  data: VidOutput | null;
  regen_used?: number;
  regen_max?: number;
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
  quality_score?: number;
  num_chunks?: number;
}

export interface StudyPackResponse {
  course_id: string;
  stats: StudyPackStats;
  study_pack: {
    title: string;
    book?: BookOutput;
    quiz?: QuizQuestion[];
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
