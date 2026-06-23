/**
 * Flashcard-related types
 */

import type { Citation } from "./common";

/** Một flashcard */
export interface Flashcard {
  id?: string;
  question: string;
  answer: string;
  citations?: Citation[];
}

/** Request body cho POST /api/generate-flashcards */
export interface GenerateFlashcardsRequest {
  course_id: string;
  count?: number;
}

/** Response từ POST /api/generate-flashcards */
export interface GenerateFlashcardsResponse {
  course_id: string;
  flashcards: Flashcard[];
  citations?: Citation[];
}

/** Response từ GET /api/course/{course_id}/flashcards */
export interface GetFlashcardsResponse {
  course_id: string;
  flashcards: Flashcard[];
}