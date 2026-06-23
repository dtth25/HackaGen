/**
 * Course-related types
 */

import type { Citation } from "./common";

/** Một bài học trong chapter */
export interface Lesson {
  title: string;
}

/** Một chapter trong course */
export interface Chapter {
  title: string;
  lessons: Lesson[];
}

/** Course detail */
export interface CourseDetail {
  title: string;
  description?: string;
  chapters: Chapter[];
}

/** Response từ GET /api/course/{course_id}/course */
export interface CourseResponse {
  course_id: string;
  course: CourseDetail;
  citations?: Citation[];
}

/** Một item trong danh sách courses (GET /api/courses/all) */
export interface CourseListItem {
  course_id: string;
  status: string;
  pdf_path?: string;
  created_at?: string;
}

/** Response từ GET /api/courses/all */
export interface CourseListResponse {
  courses: CourseListItem[];
  total: number;
}

/** Request body cho POST /api/generate-course */
export interface GenerateCourseRequest {
  file_id: string;
  user_prompt?: string;
}

/** Response từ POST /api/generate-course */
export interface GenerateCourseResponse {
  course_title: string;
  chapters: Array<{ id: number; title: string; lessons: string[] }>;
  total_slides: number;
  citations: Citation[];
}