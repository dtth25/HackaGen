/**
 * Study guide-related types
 */

import type { Citation } from "./common";

/** Request body cho POST /api/generate-study-guide */
export interface GenerateStudyGuideRequest {
  course_id: string;
}

/** Response từ POST /api/generate-study-guide */
export interface StudyGuideResponse {
  course_id: string;
  guide: string;
  filename: string;
  citations: Citation[];
}