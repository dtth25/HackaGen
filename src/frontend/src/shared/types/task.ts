/**
 * Task-related types for async operations
 */

/** Trạng thái của task */
export type TaskStatus = "processing" | "completed" | "failed";

/** Loại task */
export type TaskType =
  | "course"
  | "summary"
  | "flashcards"
  | "quiz"
  | "slides"
  | "mindmap"
  | "custom_prompt";

/** Response từ POST async endpoints */
export interface TaskResponse {
  task_id: string;
  status: TaskStatus;
}

/** Response từ GET /api/task/{task_id} */
export interface TaskPollResponse {
  task_id: string;
  status: TaskStatus;
  task_type: TaskType;
  course_id: string;
  created_at: string;
  updated_at: string;
  elapsed_seconds: number;
  result?: unknown;
  error?: string;
}