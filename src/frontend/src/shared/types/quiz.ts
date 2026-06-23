/**
 * Quiz-related types
 */

import type { Citation } from "./common";

/** Một câu hỏi trong quiz */
export interface QuizQuestion {
  question: string;
  options: string[];
  correct: number;
  explanation: string;
}

/** Request body cho POST /api/generate-quiz */
export interface GenerateQuizRequest {
  course_id: string;
  topic?: string;
  quantity?: number;
  difficulty?: string;
}

/** Response từ POST /api/generate-quiz */
export interface QuizResponse {
  course_id: string;
  topic: string;
  difficulty: string;
  questions: QuizQuestion[];
  total_questions: number;
  citations?: Citation[];
}