/**
 * Custom prompt-related types
 */

import type { Citation } from "./common";

/** Loại prompt */
export type PromptType = "TABLE" | "LIST" | "EXPLAIN" | "JSON" | "CODE";

/** Request body cho POST /api/custom-prompt */
export interface CustomPromptRequest {
  course_id: string;
  prompt: string;
}

/** Response từ POST /api/custom-prompt */
export interface CustomPromptResponse {
  course_id: string;
  prompt: string;
  prompt_type: PromptType;
  result: string;
  citations: Citation[];
}

/** Item trong lịch sử custom prompt */
export interface CustomPromptHistoryItem {
  filename: string;
  prompt: string;
  prompt_type: PromptType;
  created_at: string;
}

/** Response từ GET /api/course/{course_id}/custom-prompts */
export interface CustomPromptHistoryResponse {
  course_id: string;
  custom_prompts: CustomPromptHistoryItem[];
  total: number;
}