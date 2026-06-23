/**
 * API configuration and endpoints for backend communication.
 * Backend runs on port 8000 by default.
 */

export const API_BASE_URL = "http://localhost:8001";

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

import type {
  Lesson,
  Chapter,
  CourseDetail,
  CourseResponse,
  CourseListItem,
  CourseListResponse,
  GenerateCourseRequest,
  GenerateCourseResponse,
  QuizQuestion,
  QuizResponse,
  GenerateQuizRequest,
  Flashcard,
  GenerateFlashcardsRequest,
  GenerateFlashcardsResponse,
  GetFlashcardsResponse,
  MindmapNode,
  Mindmap,
  GenerateMindmapRequest,
  MindmapResponse,
  PromptType,
  CustomPromptRequest,
  CustomPromptResponse,
  CustomPromptHistoryItem,
  CustomPromptHistoryResponse,
  GenerateStudyGuideRequest,
  StudyGuideResponse,
  SyllabusItem,
  GenerateSyllabusRequest,
  SyllabusResponse,
  PodcastScriptItem,
  GeneratePodcastRequest,
  PodcastScriptResponse,
  TaskStatus,
  TaskType,
  TaskResponse,
  TaskPollResponse,
  Citation,
  UploadResponse,
  CourseStats,
  CourseFiles,
} from "@/shared/types";

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
 * Generate course từ file đã upload.
 * POST /api/generate-course
 */
export async function generateCourse(
  fileId: string,
  userPrompt?: string
): Promise<GenerateCourseResponse> {
  const response = await fetch(ENDPOINTS.generateCourse, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      file_id: fileId,
      user_prompt: userPrompt,
    }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => null);
    throw new Error(
      err?.message || `Lỗi tạo khóa học: ${response.statusText}`
    );
  }

  return response.json();
}

/**
 * Generate quiz từ course.
 * POST /api/generate-quiz
 */
export async function generateQuiz(
  courseId: string,
  topic: string = "Kiến thức tổng quát",
  quantity: number = 10,
  difficulty: string = "medium"
): Promise<QuizResponse> {
  const requestBody: GenerateQuizRequest = {
    course_id: courseId,
    topic,
    quantity,
    difficulty,
  };

  const response = await fetch(ENDPOINTS.generateQuiz, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => null);
    throw new Error(err?.message || `Lỗi tạo quiz: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Upload files to backend.
 * POST /api/upload
 * Response: { file_id: string, pages: number, status: string }
 */
export async function uploadFiles(files: File[]): Promise<UploadResponse> {
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