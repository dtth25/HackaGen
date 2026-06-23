/**
 * API configuration and endpoints for backend communication.
 * Backend runs on port 8000 by default.
 */

export const API_BASE_URL = "http://localhost:8000";

export const ENDPOINTS = {
  upload: `${API_BASE_URL}/api/upload`,
  generateCourse: `${API_BASE_URL}/api/generate-course`,
  generateSummary: `${API_BASE_URL}/api/generate-summary`,
  generateFlashcards: `${API_BASE_URL}/api/generate-flashcards`,
  generateQuiz: `${API_BASE_URL}/api/generate-quiz`,
  generateSlides: `${API_BASE_URL}/api/generate-slides`,
  generateMindmap: `${API_BASE_URL}/api/generate-mindmap`,
  customPrompt: `${API_BASE_URL}/api/custom-prompt`,
  getCoursesAll: `${API_BASE_URL}/api/courses/all`,
  getCourse: (id: string) => `${API_BASE_URL}/api/course/${id}/course`,
  getCourseStatus: (id: string) => `${API_BASE_URL}/api/course/${id}/status`,
} as const;

export type Endpoint = keyof typeof ENDPOINTS;

/* ── Types ─────────────────────────────────────────────── */

/** Một bài học trong chapter */
export interface Lesson {
  title: string;
}

/** Một chapter trong course */
export interface Chapter {
  title: string;
  lessons: Lesson[];
}

/** Course detail trả về từ GET /api/course/{course_id}/course */
export interface CourseDetail {
  title: string;
  description?: string;
  chapters: Chapter[];
}

/** Response từ GET /api/course/{course_id}/course */
export interface CourseResponse {
  course_id: string;
  course: CourseDetail;
  citations?: Array<{ page: number; source: string; chunk_id: string }>;
}

/** Một item trong danh sách courses (GET /api/courses/all) */
export interface CourseListItem {
  course_id: string;
  status: string;
  pdf_path?: string;
  created_at?: string;
}

/** Response từ GET /api/courses/all */
export interface CourseListResponse {
  courses: CourseListItem[];
  total: number;
}

/* ── Fetch helpers ─────────────────────────────────────── */

/**
 * Fetch danh sách tất cả courses.
 * GET /api/courses/all
 */
export async function getCoursesAll(): Promise<CourseListResponse> {
  const response = await fetch(ENDPOINTS.getCoursesAll);
  if (!response.ok) {
    throw new Error(`Không thể lấy danh sách khóa học: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Fetch chi tiết một course (chapters + lessons).
 * GET /api/course/{course_id}/course
 */
export async function getCourse(id: string): Promise<CourseResponse> {
  const response = await fetch(ENDPOINTS.getCourse(id));
  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("NOT_FOUND");
    }
    throw new Error(`Lỗi lấy khóa học: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Upload files to backend.
 */
export async function uploadFiles(files: File[]): Promise<{ message: string }> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  const response = await fetch(ENDPOINTS.upload, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.message || `Lỗi tải lên: ${response.statusText}`);
  }

  return response.json();
}