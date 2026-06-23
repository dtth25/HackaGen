/**
 * Mindmap-related types
 */

import type { Citation } from "./common";

/** Node trong mind map */
export interface MindmapNode {
  title: string;
  children?: MindmapNode[];
}

/** Mindmap structure */
export interface Mindmap {
  central_topic: string;
  branches: MindmapNode[];
}

/** Request body cho POST /api/generate-mindmap */
export interface GenerateMindmapRequest {
  course_id: string;
  max_depth?: number;
}

/** Response từ POST /api/generate-mindmap */
export interface MindmapResponse {
  course_id: string;
  mindmap: Mindmap;
  citations: Citation[];
}