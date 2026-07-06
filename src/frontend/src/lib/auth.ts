/**
 * Authentication helper library for storing JWT tokens and communicating with auth endpoints.
 */

export type RoleMode =
  | "student"
  | "teacher"
  | "self_learner"
  | "exam_prep"
  | "enterprise_trainer"
  | "researcher"
  | "developer";

export interface LearningProfile {
  role_mode: RoleMode;
  difficulty_level: "beginner" | "intermediate" | "university" | "advanced";
  learning_goal: "understand" | "exam" | "teach" | "revise" | "apply" | "onboard" | "research";
  preferred_output_style: "high_yield" | "detailed" | "visual" | "practice_based" | "academic" | "simple";
  language_style: "vietnamese_simple" | "vietnamese_academic" | "english" | "bilingual_vi_en";
  time_budget: "10_min" | "30_min" | "1_hour" | "multi_day";
  include_examples: boolean;
  include_quiz: boolean;
  include_flashcards: boolean;
  include_mindmap: boolean;
  include_common_mistakes: boolean;
}

// Vietnamese labels for onboarding/settings UI, per the product spec.
export const ROLE_MODE_LABELS_VI: Record<RoleMode, string> = {
  student: "Sinh viên",
  exam_prep: "Ôn thi",
  teacher: "Giảng viên",
  self_learner: "Người tự học",
  developer: "Lập trình / thực hành",
  enterprise_trainer: "Đào tạo nội bộ",
  researcher: "Nghiên cứu / chuyên sâu",
};

export const ROLE_MODE_DESCRIPTIONS_VI: Record<RoleMode, string> = {
  student: "Sách học súc tích, ví dụ minh họa, ôn tập chủ động (active recall).",
  exam_prep: "Điểm high-yield, các bẫy thường gặp, câu hỏi thi thử, ôn nhanh.",
  teacher: "Mục tiêu bài giảng, hoạt động lớp học, thảo luận, bài tập về nhà, rubric chấm điểm.",
  self_learner: "Giải thích đơn giản, ví von dễ hiểu, lộ trình từng bước.",
  developer: "Đọc hiểu code, cách triển khai, debug, mini-project thực hành.",
  enterprise_trainer: "Tóm tắt quy trình (SOP), checklist, quiz tuân thủ (compliance).",
  researcher: "Định nghĩa, phương pháp, giả định, giới hạn, câu hỏi mở.",
};

export const ROLE_MODES: RoleMode[] = [
  "student",
  "exam_prep",
  "teacher",
  "self_learner",
  "developer",
  "enterprise_trainer",
  "researcher",
];

export interface UserPublic {
  id: string;
  email: string;
  full_name?: string | null;
  role: "user" | "admin";
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
  last_login_at?: string | null;
  learning_profile?: LearningProfile | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserPublic;
}

const TOKEN_KEY = "agy_auth_token";
const USER_KEY = "agy_auth_user";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getStoredUser(): UserPublic | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as UserPublic;
  } catch {
    return null;
  }
}

export function setStoredUser(user: UserPublic): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function isAuthenticated(): boolean {
  return Boolean(getToken());
}

export function getAuthHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const response = await fetch("/api/backend/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Đăng nhập thất bại.");
  }

  setToken(data.access_token);
  setStoredUser(data.user);
  return data as AuthResponse;
}

export async function register(payload: {
  email: string;
  password: string;
  full_name?: string;
}): Promise<AuthResponse> {
  const response = await fetch("/api/backend/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Đăng ký thất bại.");
  }

  setToken(data.access_token);
  setStoredUser(data.user);
  return data as AuthResponse;
}

export async function logout(): Promise<void> {
  try {
    const token = getToken();
    await fetch("/api/backend/auth/logout", {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
  } catch {
    // Ignore network error on logout
  } finally {
    removeToken();
  }
}

export async function fetchCurrentUser(): Promise<UserPublic | null> {
  const token = getToken();

  try {
    const response = await fetch("/api/backend/auth/me", {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        removeToken();
      }
      return null;
    }
    const user = (await response.json()) as UserPublic;
    setStoredUser(user);
    return user;
  } catch {
    return getStoredUser();
  }
}

// Only `role_mode` is required — any other field left unset falls back to that
// role's curated default on the backend (see ROLE_MODE_DEFAULTS).
export async function updateLearningProfile(
  update: { role_mode: RoleMode } & Partial<Omit<LearningProfile, "role_mode">>
): Promise<UserPublic> {
  const token = getToken();
  const response = await fetch("/api/backend/auth/me/learning-profile", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(update),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Không thể lưu chế độ học tập.");
  }

  const user = data as UserPublic;
  setStoredUser(user);
  return user;
}
