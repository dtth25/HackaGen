import { getAuthHeaders, removeToken } from "@/lib/auth";
import type {
  AuthResponse,
  LoginRequest,
  RegisterRequest,
  CoursesResponse,
  CourseStatusResponse,
  UploadResponse,
  StudyPackResponse,
  User,
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
