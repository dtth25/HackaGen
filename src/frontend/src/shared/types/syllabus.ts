/**
 * Syllabus-related types
 */

import type { Citation } from "./common";

/** Một item trong syllabus */
export interface SyllabusItem {
  title: string;
  description: string;
  duration: string;
}

/** Request body cho POST /api/generate-syllabus */
export interface GenerateSyllabusRequest {
  course_id: string;
}

/** Response từ POST /api/generate-syllabus */
export interface SyllabusResponse {
  course_id: string;
  syllabus: SyllabusItem[];
  citations: Citation[];
}