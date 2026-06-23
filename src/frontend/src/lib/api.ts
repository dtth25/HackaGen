/**
 * API configuration and endpoints for backend communication.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const ENDPOINTS = {
  upload: `${API_BASE_URL}/api/upload`,
  courseStatus: (courseId: string) =>
    `${API_BASE_URL}/api/course/${courseId}/status`,
  generateCourse: `${API_BASE_URL}/api/generate-course`,
  generateSummary: `${API_BASE_URL}/api/generate-summary`,
  generateFlashcards: `${API_BASE_URL}/api/generate-flashcards`,
  generateQuiz: `${API_BASE_URL}/api/generate-quiz`,
  generateSlides: `${API_BASE_URL}/api/generate-slides`,
  generateMindmap: `${API_BASE_URL}/api/generate-mindmap`,
  customPrompt: `${API_BASE_URL}/api/custom-prompt`,
} as const;

export type Citation = {
  page?: number | string;
  source?: string;
  chunk_id?: number | string;
};

export type UploadResponse = {
  course_id: string;
  filename: string;
  status: string;
  message: string;
};

export type CourseStatusResponse = {
  course_id: string;
  status: "pending" | "processing" | "ready" | "failed" | "unknown";
  error?: string;
};

export type GenerateFeature =
  | "course"
  | "summary"
  | "flashcards"
  | "quiz"
  | "slides"
  | "mindmap"
  | "custom";

export type GenerateResponse = Record<string, unknown> & {
  citations?: Citation[];
};

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const detail =
      typeof payload?.detail === "string"
        ? payload.detail
        : typeof payload?.message === "string"
          ? payload.message
          : `Request failed: ${response.statusText}`;
    throw new Error(detail);
  }

  return payload as T;
}

export async function uploadFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(ENDPOINTS.upload, {
    method: "POST",
    body: formData,
  });

  return parseResponse<UploadResponse>(response);
}

export async function getCourseStatus(
  courseId: string
): Promise<CourseStatusResponse> {
  const response = await fetch(ENDPOINTS.courseStatus(courseId), {
    cache: "no-store",
  });

  return parseResponse<CourseStatusResponse>(response);
}

export async function generateContent(
  feature: GenerateFeature,
  courseId: string,
  prompt: string
): Promise<GenerateResponse> {
  const topic = prompt || "tổng quan";

  const config: Record<
    GenerateFeature,
    { endpoint: string; body: Record<string, unknown> }
  > = {
    course: {
      endpoint: ENDPOINTS.generateCourse,
      body: {
        course_id: courseId,
        user_prompt: prompt,
        target_audience: "sinh viên",
      },
    },
    summary: {
      endpoint: ENDPOINTS.generateSummary,
      body: { course_id: courseId, type: "detailed" },
    },
    flashcards: {
      endpoint: ENDPOINTS.generateFlashcards,
      body: { course_id: courseId, count: 8 },
    },
    quiz: {
      endpoint: ENDPOINTS.generateQuiz,
      body: {
        course_id: courseId,
        topic,
        quantity: 10,
        difficulty: "medium",
      },
    },
    slides: {
      endpoint: ENDPOINTS.generateSlides,
      body: { course_id: courseId, topic, num_slides: 8 },
    },
    mindmap: {
      endpoint: ENDPOINTS.generateMindmap,
      body: { course_id: courseId, max_depth: 3 },
    },
    custom: {
      endpoint: ENDPOINTS.customPrompt,
      body: { course_id: courseId, prompt: topic },
    },
  };

  const { endpoint, body } = config[feature];
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  return parseResponse<GenerateResponse>(response);
}
