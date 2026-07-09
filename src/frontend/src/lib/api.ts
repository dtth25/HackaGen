import { getAuthHeaders, removeToken, getToken } from "@/lib/auth";
import type {
  AuthResponse,
  LoginRequest,
  RegisterRequest,
  CoursesResponse,
  CourseStatusResponse,
  UploadResponse,
  StudyPackResponse,
  User,
  GenerateResponse,
  BookArtifactStatus,
  SlideArtifactStatus,
  QuizArtifactStatus,
  VidOutput,
} from "@/lib/types";

// Base URL for the FastAPI backend. Prefer the documented public env vars;
// fall back to the conventional local/dev backend port.
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:8000";

// ============================================================
// Core Fetch Wrapper
// ============================================================

async function apiFetch<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const headers: Record<string, string> = {
    ...getAuthHeaders(),
    ...((init?.headers as Record<string, string>) || {}),
  };

  if (!(init?.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });

  if (response.status === 401) {
    removeToken();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new Error("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.");
  }

  if (response.status === 403) {
    throw new Error("Bạn không có quyền truy cập tài nguyên này.");
  }

  if (!response.ok) {
    let message = "Đã xảy ra lỗi. Vui lòng thử lại.";
    try {
      const errorBody = await response.json();
      if (errorBody.detail) {
        message =
          typeof errorBody.detail === "string"
            ? errorBody.detail
            : JSON.stringify(errorBody.detail);
      }
    } catch {
      // Use default message
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

// ============================================================
// Auth API
// ============================================================

export async function apiLogin(data: LoginRequest): Promise<AuthResponse> {
  return apiFetch<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function apiRegister(
  data: RegisterRequest
): Promise<AuthResponse> {
  return apiFetch<AuthResponse>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function apiLogout(): Promise<void> {
  try {
    await apiFetch<{ detail: string }>("/api/auth/logout", {
      method: "POST",
    });
  } catch {
    // Ignore network errors on logout
  }
}

export async function apiGetCurrentUser(): Promise<User> {
  return apiFetch<User>("/api/auth/me");
}

// ============================================================
// Course API
// ============================================================

export async function apiGetCourses(): Promise<CoursesResponse> {
  return apiFetch<CoursesResponse>("/api/courses/all");
}

export async function apiGetCourseStatus(
  courseId: string
): Promise<CourseStatusResponse> {
  return apiFetch<CourseStatusResponse>(`/api/course/${courseId}/status`);
}

export async function apiDeleteCourse(courseId: string): Promise<void> {
  await apiFetch<{ status: string }>(`/api/courses/${courseId}`, {
    method: "DELETE",
  });
}

export async function apiRenameCourse(
  courseId: string,
  name: string
): Promise<void> {
  await apiFetch<{ id: string }>(`/api/courses/${courseId}`, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });
}

// ============================================================
// Upload API
// ============================================================

export async function apiUploadFiles(
  files: File[],
  onProgress?: (percent: number) => void
): Promise<UploadResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  if (onProgress) {
    return new Promise<UploadResponse>((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${API_BASE}/api/upload`);

      const headers = getAuthHeaders();
      Object.entries(headers).forEach(([key, value]) => {
        xhr.setRequestHeader(key, value);
      });
      xhr.withCredentials = true;

      xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      });

      xhr.addEventListener("load", () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText) as UploadResponse);
        } else if (xhr.status === 401) {
          removeToken();
          window.location.href = "/login";
          reject(new Error("Phiên đăng nhập đã hết hạn."));
        } else {
          try {
            const err = JSON.parse(xhr.responseText);
            reject(new Error(err.detail || "Upload thất bại."));
          } catch {
            reject(new Error("Upload thất bại. Vui lòng thử lại."));
          }
        }
      });

      xhr.addEventListener("error", () => {
        reject(new Error("Lỗi kết nối. Vui lòng kiểm tra backend."));
      });

      xhr.send(formData);
    });
  }

  return apiFetch<UploadResponse>("/api/upload", {
    method: "POST",
    body: formData,
  });
}

// ============================================================
// Study Pack API (for future use)
// ============================================================

export async function apiGetStudyPack(
  courseId: string
): Promise<StudyPackResponse> {
  return apiFetch<StudyPackResponse>(`/api/course/${courseId}/study-pack`);
}

// ============================================================
// Generation & Artifact API
// ============================================================

export async function apiGenerateBook(
  courseId: string,
  params?: Record<string, unknown>
): Promise<GenerateResponse> {
  return apiFetch<GenerateResponse>("/api/generate-book", {
    method: "POST",
    body: JSON.stringify({ course_id: courseId, ...(params || {}) }),
  });
}

export async function apiGenerateSlide(
  courseId: string,
  params?: Record<string, unknown>
): Promise<GenerateResponse> {
  return apiFetch<GenerateResponse>("/api/generate-slide", {
    method: "POST",
    body: JSON.stringify({ course_id: courseId, ...(params || {}) }),
  });
}

export async function apiGenerateQuiz(
  courseId: string,
  params?: Record<string, unknown>
): Promise<GenerateResponse> {
  return apiFetch<GenerateResponse>("/api/generate-quiz", {
    method: "POST",
    body: JSON.stringify({ course_id: courseId, ...(params || {}) }),
  });
}

export async function apiGenerateVid(
  courseId: string,
  params?: Record<string, unknown>
): Promise<GenerateResponse> {
  return apiFetch<GenerateResponse>("/api/generate-vid", {
    method: "POST",
    body: JSON.stringify({ course_id: courseId, ...(params || {}) }),
  });
}

export async function apiGetBook(courseId: string): Promise<BookArtifactStatus> {
  return apiFetch<BookArtifactStatus>(`/api/course/${courseId}/book`);
}

export async function apiGetSlide(courseId: string): Promise<SlideArtifactStatus> {
  return apiFetch<SlideArtifactStatus>(`/api/course/${courseId}/slide`);
}

export async function apiGetQuiz(courseId: string): Promise<QuizArtifactStatus> {
  return apiFetch<QuizArtifactStatus>(`/api/course/${courseId}/quiz`);
}

export async function apiGetVid(courseId: string): Promise<VidOutput | null> {
  return apiFetch<VidOutput | null>(`/api/course/${courseId}/vid`);
}

// ============================================================
// Download Helpers
// ============================================================

export function getDownloadBookUrl(courseId: string): string {
  const token = getToken();
  const suffix = token ? `?token=${encodeURIComponent(token)}` : "";
  return `${API_BASE}/api/course/${courseId}/book.pdf${suffix}`;
}

export function getDownloadSlideUrl(courseId: string): string {
  const token = getToken();
  const suffix = token ? `?token=${encodeURIComponent(token)}` : "";
  return `${API_BASE}/api/course/${courseId}/slide.pptx${suffix}`;
}

export function getDownloadSlidePdfUrl(courseId: string): string {
  const token = getToken();
  const suffix = token ? `?token=${encodeURIComponent(token)}` : "";
  return `${API_BASE}/api/course/${courseId}/slide.pdf${suffix}`;
}

export function getDownloadQuizKeyUrl(courseId: string): string {
  const token = getToken();
  const suffix = token ? `?token=${encodeURIComponent(token)}` : "";
  return `${API_BASE}/api/course/${courseId}/quiz-key.pdf${suffix}`;
}

export function getDownloadVidUrl(courseId: string): string {
  const token = getToken();
  const suffix = token ? `?token=${encodeURIComponent(token)}` : "";
  return `${API_BASE}/api/course/${courseId}/vid/file${suffix}`;
}

export const getBookPdfUrl = getDownloadBookUrl;
export const getSlidePptxUrl = getDownloadSlideUrl;
export const getQuizKeyPdfUrl = getDownloadQuizKeyUrl;
export const getVidFileUrl = getDownloadVidUrl;

export function getSlideImageUrl(courseId: string, slideNum: number): string {
  const token = getToken();
  const suffix = token ? `?token=${encodeURIComponent(token)}` : "";
  return `${API_BASE}/api/course/${courseId}/slide-images/${slideNum}${suffix}`;
}
