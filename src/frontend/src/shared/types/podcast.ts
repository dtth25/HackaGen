/**
 * Podcast-related types
 */

import type { Citation } from "./common";

/** Một đoạn trong podcast script */
export interface PodcastScriptItem {
  speaker: "host" | "expert";
  text: string;
}

/** Request body cho POST /api/generate-podcast */
export interface GeneratePodcastRequest {
  course_id: string;
}

/** Response từ POST /api/generate-podcast */
export interface PodcastScriptResponse {
  course_id: string;
  script: PodcastScriptItem[];
  estimated_duration: string;
  citations: Citation[];
}