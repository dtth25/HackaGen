/**
 * API client for the Document-to-Study-Pack flow.
 */
import { getAuthHeaders } from "@/lib/auth";

const APP_API_BASE_URL =
  typeof window === "undefined" ? process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000" : "";

export const ENDPOINTS = {
  health: `${APP_API_BASE_URL}/api/backend/health`,
  upload: `${APP_API_BASE_URL}/api/backend/upload`,
  demoCourse: `${APP_API_BASE_URL}/api/backend/demo-course`,
  getCoursesAll: `${APP_API_BASE_URL}/api/backend/courses/all`,
  courseStatus: (courseId: string) =>
    `${APP_API_BASE_URL}/api/backend/course/${courseId}/status`,
  documentStatus: (documentId: string) =>
    `${APP_API_BASE_URL}/api/backend/documents/${documentId}/status`,
  retryDocument: (documentId: string) =>
    `${APP_API_BASE_URL}/api/backend/documents/${documentId}/retry`,
  documentSources: (documentId: string, query = "") =>
    `${APP_API_BASE_URL}/api/backend/documents/${documentId}/sources${query}`,
  deleteDocument: (documentId: string) =>
    `${APP_API_BASE_URL}/api/backend/documents/${documentId}`,
  deleteCourse: (courseId: string) =>
    `${APP_API_BASE_URL}/api/backend/course/${courseId}`,
  courseStats: (courseId: string) =>
    `${APP_API_BASE_URL}/api/backend/course/${courseId}/stats`,
  generate: (feature: GenerateFeature) =>
    `${APP_API_BASE_URL}/api/backend/generate/${feature}`,
  getBook: (courseId: string) =>
    `${APP_API_BASE_URL}/api/backend/course/${courseId}/book`,
  getStudyPack: (courseId: string) =>
    `${APP_API_BASE_URL}/api/backend/course/${courseId}/study-pack`,
  getMindmap: (courseId: string) =>
    `${APP_API_BASE_URL}/api/backend/course/${courseId}/mindmap`,
  regenerateMindmap: (courseId: string) =>
    `${APP_API_BASE_URL}/api/backend/course/${courseId}/mindmap/regenerate`,
  getFlashcardDeck: (courseId: string) =>
    `${APP_API_BASE_URL}/api/backend/course/${courseId}/flashcards`,
  regenerateFlashcardDeck: (courseId: string) =>
    `${APP_API_BASE_URL}/api/backend/course/${courseId}/flashcards/regenerate`,
  getBookPdf: (courseId: string) => assetUrl(`/api/course/${courseId}/book.pdf`),
  getSlide: (courseId: string) =>
    `${APP_API_BASE_URL}/api/backend/download/api/course/${courseId}/slide`,
  getSlidePptx: (courseId: string) => assetUrl(`/api/course/${courseId}/slide.pptx`),
  getQuiz: (courseId: string) =>
    `${APP_API_BASE_URL}/api/backend/download/api/course/${courseId}/quiz`,
  getQuizAnswerKey: (courseId: string) => assetUrl(`/api/course/${courseId}/quiz-key.pdf`),
  getVid: (courseId: string) =>
    `${APP_API_BASE_URL}/api/backend/download/api/course/${courseId}/vid`,
  getVidFile: (courseId: string) =>
    assetUrl(`/api/course/${courseId}/vid/file`),
} as const;

export function assetUrl(path?: string | null) {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  if (path.startsWith("/api/backend/download/")) return path;
  const normalized = path.replace(/^\//, "");
  return `/api/backend/download/${normalized}`;
}

export type GenerateFeature = "book" | "slide" | "quiz" | "vid";

export type VideoMode = "sixty_second" | "three_minute" | "ten_minute" | "playlist_by_chapter";

export type UserMode =
  | "student"
  | "teacher"
  | "exam_prep"
  | "self_learner"
  | "developer"
  | "researcher"
  | "enterprise_trainer";

export interface UploadResponse {
  course_id: string;
  document_id?: string;
  filename: string;
  filenames?: string[];
  file_count?: number;
  status: string;
  message: string;
}

export interface DocumentQualityReport {
  document_id?: string;
  file_type?: string;
  page_count?: number;
  text_extraction_success?: boolean;
  extracted_char_count?: number;
  average_chars_per_page?: number;
  detected_language?: string;
  is_scanned_pdf?: boolean;
  has_toc_noise?: boolean;
  has_dot_leaders?: boolean;
  has_many_page_numbers?: boolean;
  has_broken_spacing?: boolean;
  quality_score?: number;
  warnings?: string[];
  recommended_action?: "generate" | "generate_with_warning" | "needs_ocr" | "insufficient_context";
}

export interface CourseStatsResponse {
  course_id: string;
  status: string;
  has_book: boolean;
  has_book_pdf: boolean;
  has_slide: boolean;
  has_slide_pptx: boolean;
  has_quiz: boolean;
  has_quiz_answer_key: boolean;
  has_vid: boolean;
  has_mindmap: boolean;
  has_flashcards: boolean;
  total_questions?: number;
  total_slides?: number;
  num_chunks?: number;
  noisy_chunks_removed?: number;
  quality_score?: number;
  is_university_ready?: boolean;
  document_quality_report?: DocumentQualityReport;
  pdf_type?: string;
  warnings?: string[];
  recommended_action?: string;
  generated_at?: number;
}

export type DocumentProcessingStage =
  | "uploading"
  | "extracting_text"
  | "cleaning_text"
  | "chunking"
  | "embedding"
  | "storing_vectors"
  | "completed"
  | "completed_limited"
  | "failed"
  | "paused_due_to_quota"
  | "analysis_failed"
  | "extraction_failed"
  | "embedding_failed"
  | "vector_index_failed"
  | "insufficient_context";

export interface CourseStatusResponse {
  course_id: string;
  status: "pending" | "processing" | "ready" | "completed_limited" | "failed" | "paused_due_to_quota" | "unknown";
  stage?: DocumentProcessingStage;
  error?: string;
  error_code?: string;
  user_message?: string | null;
  technical_error?: string | null;
  can_retry?: boolean;
  recommended_action?: string | null;
  failure_stage?: DocumentProcessingStage | null;
  filenames?: string[];
  file_count?: number;
  progress?: number;
  progress_message?: string;
  total_processing_time?: number;
  cached_from?: string;
  preprocess_profile?: Record<string, unknown>;
  document_quality_report?: DocumentQualityReport;
}

export interface DocumentStatusResponse {
  document_id: string;
  status:
    | "extracting_text"
    | "cleaning_text"
    | "chunking"
    | "embedding"
    | "storing_vectors"
    | "completed"
    | "completed_limited"
    | "failed"
    | "paused_due_to_quota";
  stage?: DocumentProcessingStage;
  failure_stage?: DocumentProcessingStage | null;
  progress: number;
  message: string;
  error: string | null;
  user_message?: string | null;
  technical_error?: string | null;
  can_retry?: boolean;
  recommended_action?: string | null;
  error_code?: string | null;
  job_id?: string;
  job?: Record<string, unknown>;
}

export interface CourseListItem {
  course_id: string;
  status: string;
  created_at?: string | number;
  filenames?: string[];
  file_count?: number;
  error?: string;
  error_code?: string;
}

export interface CourseListResponse {
  courses: CourseListItem[];
  total: number;
}

export interface BackendHealthResponse {
  status: "ok" | "starting" | "error";
  ready: boolean;
  details: {
    upload_dir: boolean;
    output_dir: boolean;
    vector_db: boolean;
    config_loaded: boolean;
  };
  startup_duration_seconds?: number | null;
  error?: string | null;
  vector_db_provider?: string;
  vector_db_ready?: boolean;
  vector_db?: {
    provider: string;
    ready: boolean;
    collection: string;
    persist_dir: string;
    error?: string | null;
  };
}

export interface BookWorkedExample {
  title?: string;
  problem?: string;
  step_by_step_solution?: string[];
  why_each_step_matters?: string;
  common_error?: string;
  source_chunk_ids?: string[];
}

export interface BookPracticeProblem {
  difficulty?: string;
  question?: string;
  expected_answer?: string;
  hint?: string;
  solution?: string;
  source_chunk_ids?: string[];
}

export interface BookLesson {
  title: string;
  short_name?: string;
  duration?: string;
  objectives?: string[];
  core_idea?: string;
  why_it_matters?: string;
  explanation?: string;
  simple_explanation?: string;
  content?: string;
  lecture?: string;
  key_points?: string[];
  key_concepts?: Array<{ term?: string; definition?: string }>;
  example?: string;
  non_example?: string;
  common_misunderstanding?: { mistake?: string; correction?: string };
  worked_examples?: BookWorkedExample[];
  activity?: string;
  practice_problems?: BookPracticeProblem[];
  assessment?: string[];
  active_recall_questions?: string[];
  quick_check?: Array<{ question?: string; answer?: string }>;
  source_chunk_ids?: string[];
}

export interface BookChapter {
  title: string;
  description?: string;
  prerequisites?: string[];
  learning_outcomes?: string[];
  connections_to_other_chapters?: string[];
  lessons?: BookLesson[];
  sections?: BookLesson[];
}

export interface BookGlossaryItem {
  term: string;
  plain_vietnamese?: string;
  definition?: string;
}

export interface BookOutput {
  title: string;
  subtitle?: string;
  audience?: string;
  course_level?: string;
  description?: string;
  estimated_duration?: string;
  prerequisites?: string[];
  course_learning_outcomes?: string[];
  chapters: BookChapter[];
  glossary?: BookGlossaryItem[];
  quality_report?: QualityReport;
  study_pack?: Record<string, unknown>;
  generation_mode?: "full_book" | "high_yield_study_guide" | "summary_only";
  generation_status?: GenerationStatus | null;
}

export interface MindmapNode {
  id: string;
  parent_id?: string;
  title: string;
  label?: string;
  summary?: string;
  core_idea?: string;
  type?: string;
  importance?: "high" | "medium" | "low";
  keywords?: string[];
  source_chunk_ids?: string[];
  // The backend (build_mindmap_from_book / MINDMAP_GENERATION_PROMPT) stores
  // children as ID-string references into the flat `nodes` array, not
  // embedded objects — consumers must resolve them against `MindmapData.nodes`.
  children?: (MindmapNode | string)[];
}

export interface MindmapEdge {
  from: string;
  to: string;
  relation?: string;
}

export interface MindmapData {
  document_id?: string;
  title?: string;
  description?: string;
  quality_report?: QualityReport;
  root?: MindmapNode;
  nodes?: MindmapNode[];
  edges?: MindmapEdge[];
}

export interface StudyPackMindmapNode {
  id?: string;
  parent_id?: string;
  label?: string;
  title?: string;
  summary?: string;
  core_idea?: string;
  type?: string;
  importance?: "high" | "medium" | "low";
  keywords?: string[];
  source_chunk_ids?: string[];
  // Same ID-reference convention as MindmapNode.children — see the comment there.
  children?: (StudyPackMindmapNode | string)[];
}

export interface StudyPackSummaryItem {
  topic?: string;
  title?: string;
  chapter?: string;
  content?: string;
  summary?: string;
  source_chunk_ids?: string[];
}

export interface StudyPackFlashcard {
  id?: string;
  front?: string;
  back?: string;
  chapter?: string;
  card_type?: string;
  difficulty?: string;
  source_chunk_ids?: string[];
}

export interface StudyPackOutput {
  title?: string;
  summary?: StudyPackSummaryItem[];
  mindmap?: {
    title?: string;
    description?: string;
    // The backend returns the full 3-level mindmap object here (root is a node,
    // not a string) — see build_mindmap_from_book / get_study_pack in the API.
    root?: StudyPackMindmapNode;
    nodes?: StudyPackMindmapNode[];
    edges?: MindmapEdge[];
    quality_report?: QualityReport;
  };
  flashcards?: StudyPackFlashcard[];
  book?: BookOutput | null;
  quiz?: QuizQuestion[];
  readiness?: Record<string, boolean>;
  quality_scores?: Record<string, number>;
  grounding?: {
    num_chunks?: number;
    quality_score?: number;
    warnings?: string[];
  };
}

export interface StudyPackResponse {
  course_id: string;
  stats?: CourseStatsResponse;
  study_pack?: StudyPackOutput;
}

export interface SlideItem {
  title: string;
  content: string;
  slide_type?: string;
  bullets?: string[];
  key_idea?: string;
  key_message?: string;
  example?: string;
  example_or_application?: string;
  note?: string;
  common_mistake?: { mistake?: string; correction?: string };
  student_prompt?: string;
  speaker_notes?: string;
  layout_hint?: string;
  visual_type?: string;
  image_suggestion?: string;
  source_chunk_ids?: string[];
}

export interface QuizQuestion {
  id?: string;
  type?: "mcq" | "true_false" | "short_answer" | "scenario" | "code_reading";
  // Legacy field kept for backward compatibility with older saved quizzes.
  question_type?: string;
  question: string;
  options: string[];
  correct: number;
  correct_answer?: string;
  explanation: string;
  why_wrong_options_are_wrong?: string[];
  difficulty?: string;
  concept_tags?: string[];
  source_chunk_ids?: string[];
}

export interface DifficultyMix {
  easy: number;
  medium: number;
  hard: number;
}

export interface VidScene {
  title: string;
  scene_index?: number;
  scene_type?: string;
  key_message?: string;
  screen_text?: string[];
  visual_text?: string;
  visual_template?: string;
  visual_data?: Record<string, unknown>;
  animation_notes?: string;
  duration_seconds?: number;
  visual_type?: string;
  bridge?: string;
  voiceover: string;
  source_chunk_ids?: string[];
}

export interface QualityReport {
  is_university_ready: boolean;
  is_user_friendly?: boolean;
  // Mindmap's quality gate (_evaluate_mindmap_quality_gate) reports `is_usable`
  // instead of `is_university_ready` — kept optional here so both shapes fit.
  is_usable?: boolean;
  score: number;
  engagement_score?: number;
  learning_score?: number;
  visual_score?: number;
  problems?: string[];
  warnings?: string[];
  fixes_needed?: string[];
  used_chunks?: number;
  ignored_noisy_chunks?: number;
  source_chunk_ids?: string[];
  retrieved_chunks_count?: number;
  usable_chunks_count?: number;
  noisy_chunks_count?: number;
  context_quality_score?: number;
  can_generate?: boolean;
}

export interface PlaylistVideo {
  video_index?: number;
  video_id?: string;
  file_name?: string;
  full_title?: string;
  short_title?: string;
  duration_minutes?: number;
  estimated_duration_seconds?: number;
  learning_objectives?: string[];
  source_chunk_ids?: string[];
  storyboard?: VidScene[];
  scenes?: VidScene[];
  status?: "planned" | "ready" | "failed";
  url?: string | null;
  transcript?: string;
  subtitles_srt?: string;
}

export interface VidOutput {
  filename?: string | null;
  url?: string | null;
  status?: "ready" | "failed" | "running" | "pending" | "planned" | "recommendation";
  generation_status?: string;
  error?: string;
  // Present when status === "recommendation" (large document -> suggest playlist).
  message?: string;
  options?: Array<{ label: string; video_mode: VideoMode; force?: boolean }>;
  video_mode?: VideoMode;
  video_title?: string;
  duration_minutes: number;
  estimated_duration_seconds?: number;
  voiceover_status?: string;
  scenes: VidScene[];
  videos?: PlaylistVideo[];
  course_title?: string;
  playlist_title?: string;
  total_duration?: string;
  estimated_total_duration_minutes?: number;
  transcript?: string;
  subtitles_srt?: string;
  quick_quiz?: Record<string, unknown>[];
  quality_report?: QualityReport;
  renderer?: "simple_templates" | "simple_slides" | "manim";
  renderer_message?: string;
  progress_states?: string[];
  debug_log?: string;
  playlist_plan?: Record<string, unknown>[];
}

export interface GenerationStatus {
  status: "full" | "limited";
  reason: string;
  fallback_used: string | null;
}

export interface GenerateResponse {
  course_id: string;
  book?: BookOutput;
  pdf_url?: string | null;
  pptx_url?: string | null;
  answer_key_url?: string | null;
  topic?: string;
  deck_title?: string;
  total_slides?: number;
  slides?: SlideItem[];
  difficulty?: string;
  total_questions?: number;
  questions?: QuizQuestion[];
  exam_pack?: Record<string, unknown> | null;
  vid?: VidOutput;
  quality_report?: QualityReport | null;
  generation_status?: GenerationStatus | null;
}

export interface QuizResponse extends GenerateResponse {
  topic: string;
  difficulty: string;
  quiz_title?: string;
  questions: QuizQuestion[];
  total_questions: number;
  difficulty_mix?: DifficultyMix | null;
  exam_pack?: Record<string, unknown> | null;
}

export interface FlashcardItem {
  id?: string;
  front: string;
  back: string;
  card_type?: "definition" | "example" | "formula" | "misconception" | "process" | "code" | "quick_recall";
  difficulty?: string;
  concept_tags?: string[];
  source_chunk_ids?: string[];
}

export interface FlashcardDeckData {
  deck_title?: string;
  cards: FlashcardItem[];
  quality_report?: QualityReport;
  generation_status?: GenerationStatus | null;
}

export interface CourseResponse {
  course_id: string;
  book: BookOutput;
  pdf_url?: string | null;
}

export interface SourceExcerpt {
  page?: number | null;
  excerpt: string;
  filename?: string | null;
  source_chunk_id?: string | null;
}

export interface SourceGroundingResponse {
  document_id: string;
  total_source_chunks: number;
  matched_source_chunks: number;
  sources: SourceExcerpt[];
}

export const GEMINI_EMBEDDING_QUOTA_MESSAGE =
  "Đã vượt giới hạn Gemini embedding. Vui lòng chờ khoảng 1 phút rồi thử lại hoặc dùng file nhỏ hơn.";

export const VECTOR_DB_NOT_READY_MESSAGE =
  "Vector DB (Chroma) chưa sẵn sàng. Vui lòng kiểm tra CHROMA_PERSIST_DIR/cài đặt chromadb rồi khởi động lại backend.";

export function friendlyApiErrorMessage(message?: string | null, errorCode?: string | null) {
  const rawMessage = message || "Có lỗi xảy ra. Vui lòng thử lại.";
  if (
    errorCode === "EMBEDDING_QUOTA_EXCEEDED" ||
    /gemini.*embedding.*quota|quota exceeded|resource_exhausted|resourceexhausted|embed_content_free_tier_requests|429/i.test(
      rawMessage,
    )
  ) {
    return GEMINI_EMBEDDING_QUOTA_MESSAGE;
  }
  if (/backend.*khởi động|backend.*dang khoi dong|starting/i.test(rawMessage)) {
    return "Backend đang khởi động, vui lòng chờ vài giây.";
  }
  if (/backend.*chưa chạy|sai cổng|failed to fetch|econnrefused|backend down/i.test(rawMessage)) {
    return "Backend chưa chạy hoặc sai cổng.";
  }
  if (/timeout|quá lâu|timed out|abort/i.test(rawMessage)) {
    return "Backend xử lý quá lâu, vui lòng chờ preprocess hoàn tất.";
  }
  if (/chromadb|chroma.*not.*ready|vector_db.*not.*ready|vector db.*mandatory/i.test(rawMessage)) {
    return VECTOR_DB_NOT_READY_MESSAGE;
  }
  return rawMessage;
}

const RETRYABLE_STATUSES = new Set([502, 503, 504]);
const RETRY_DELAYS_MS = [1000, 2000, 4000];

interface ApiFetchOptions {
  ensureHealth?: boolean;
  retries?: number;
}

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function readPayload(response: Response) {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json().catch(() => null);
  }
  const text = await response.text().catch(() => "");
  return text ? { detail: text } : null;
}

function payloadMessage(payload: unknown, fallback: string) {
  if (payload && typeof payload === "object") {
    const record = payload as Record<string, unknown>;
    const message = record.detail ?? record.message ?? record.error;
    if (typeof message === "string" && message.trim()) return message;
  }
  return fallback;
}

async function ensureBackendHealthy(retries = 2) {
  let lastMessage = "Backend chưa chạy hoặc sai cổng.";

  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      const response = await fetch(ENDPOINTS.health, { cache: "no-store" });
      const payload = (await readPayload(response)) as BackendHealthResponse | null;

      if (response.ok && payload?.ready) return payload;

      lastMessage =
        payload?.status === "starting" || response.status === 503
          ? "Backend đang khởi động, vui lòng chờ vài giây."
          : friendlyApiErrorMessage(payloadMessage(payload, "Backend chưa sẵn sàng."));
    } catch (error) {
      lastMessage = friendlyApiErrorMessage(error instanceof Error ? error.message : String(error));
    }

    if (attempt < retries) {
      await wait(RETRY_DELAYS_MS[Math.min(attempt, RETRY_DELAYS_MS.length - 1)]);
    }
  }

  throw new Error(lastMessage);
}

export async function apiFetch(
  input: string,
  init: RequestInit = {},
  options: ApiFetchOptions = {},
): Promise<Response> {
  const ensureHealth = options.ensureHealth ?? input !== ENDPOINTS.health;
  const retries = options.retries ?? 2;

  if (ensureHealth) {
    await ensureBackendHealthy(2);
  }

  const authHeaders = getAuthHeaders();
  const mergedInit: RequestInit = {
    ...init,
    headers: { ...authHeaders, ...init.headers },
  };

  let lastError: unknown = null;
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      const response = await fetch(input, mergedInit);
      if (!RETRYABLE_STATUSES.has(response.status) || attempt === retries) {
        return response;
      }
    } catch (error) {
      lastError = error;
      if (attempt === retries) {
        const message = error instanceof Error ? error.message : "Backend chưa chạy hoặc sai cổng.";
        throw new Error(friendlyApiErrorMessage(message));
      }
    }

    await wait(RETRY_DELAYS_MS[Math.min(attempt, RETRY_DELAYS_MS.length - 1)]);
  }

  const message = lastError instanceof Error ? lastError.message : "Backend chưa chạy hoặc sai cổng.";
  throw new Error(friendlyApiErrorMessage(message));
}

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = await readPayload(response);

  if (!response.ok) {
    const message =
      payload?.detail ??
      payload?.message ??
      payload?.error ??
      `Request failed: ${response.statusText}`;
    const errorCode = payload?.error_code ?? payload?.code;
    throw new Error(friendlyApiErrorMessage(message, errorCode));
  }

  return payload as T;
}

export async function uploadFiles(files: File[]): Promise<UploadResponse> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  const response = await apiFetch(ENDPOINTS.upload, {
    method: "POST",
    body: formData,
  });

  return parseResponse<UploadResponse>(response);
}

export async function uploadFile(file: File): Promise<UploadResponse> {
  return uploadFiles([file]);
}

export async function getBackendHealth(): Promise<BackendHealthResponse> {
  const response = await apiFetch(ENDPOINTS.health, {
    cache: "no-store",
  }, { ensureHealth: false });

  return parseResponse<BackendHealthResponse>(response);
}

export async function getCourseStatus(
  courseId: string
): Promise<CourseStatusResponse> {
  const response = await apiFetch(ENDPOINTS.courseStatus(courseId), {
    cache: "no-store",
  });

  return parseResponse<CourseStatusResponse>(response);
}

export async function getDocumentStatus(
  documentId: string
): Promise<DocumentStatusResponse> {
  const response = await apiFetch(ENDPOINTS.documentStatus(documentId), {
    cache: "no-store",
  });

  return parseResponse<DocumentStatusResponse>(response);
}

export async function retryDocumentAnalysis(documentId: string): Promise<DocumentStatusResponse> {
  const response = await apiFetch(ENDPOINTS.retryDocument(documentId), {
    method: "POST",
    cache: "no-store",
  });

  return parseResponse<DocumentStatusResponse>(response);
}

export async function getDocumentSources(
  documentId: string,
  sourceChunkIds: string[] = [],
  developerMode = false,
): Promise<SourceGroundingResponse> {
  const params = new URLSearchParams();
  if (sourceChunkIds.length > 0) {
    params.set("ids", sourceChunkIds.join(","));
  }
  if (developerMode) {
    params.set("developer", "true");
  }
  const query = params.toString() ? `?${params.toString()}` : "";
  const response = await apiFetch(ENDPOINTS.documentSources(documentId, query), {
    cache: "no-store",
  });
  return parseResponse<SourceGroundingResponse>(response);
}

export async function getDemoCourse(): Promise<UploadResponse> {
  const response = await apiFetch(ENDPOINTS.demoCourse, {
    method: "GET",
    cache: "no-store",
  });
  return parseResponse<UploadResponse>(response);
}

export async function getCourseStats(courseId: string): Promise<CourseStatsResponse> {
  const response = await apiFetch(ENDPOINTS.courseStats(courseId), {
    cache: "no-store",
  });
  return parseResponse<CourseStatsResponse>(response);
}

export async function getCoursesAll(): Promise<CourseListResponse> {
  const response = await apiFetch(ENDPOINTS.getCoursesAll, {
    cache: "no-store",
  });

  return parseResponse<CourseListResponse>(response);
}

export async function getBook(courseId: string): Promise<CourseResponse> {
  const response = await apiFetch(ENDPOINTS.getBook(courseId), {
    cache: "no-store",
  });

  return parseResponse<CourseResponse>(response);
}

export const getCourse = getBook;

export async function getStudyPack(courseId: string): Promise<StudyPackResponse> {
  const response = await apiFetch(ENDPOINTS.getStudyPack(courseId), {
    cache: "no-store",
  });
  return parseResponse<StudyPackResponse>(response);
}

export async function getMindmap(courseId: string): Promise<MindmapData> {
  const response = await apiFetch(ENDPOINTS.getMindmap(courseId), {
    cache: "no-store",
  });
  return parseResponse<MindmapData>(response);
}

export async function regenerateMindmap(courseId: string): Promise<MindmapData> {
  const response = await apiFetch(ENDPOINTS.regenerateMindmap(courseId), {
    method: "POST",
    cache: "no-store",
  });
  return parseResponse<MindmapData>(response);
}

export async function getFlashcardDeck(courseId: string): Promise<FlashcardDeckData> {
  const response = await apiFetch(ENDPOINTS.getFlashcardDeck(courseId), {
    cache: "no-store",
  });
  return parseResponse<FlashcardDeckData>(response);
}

export async function regenerateFlashcardDeck(courseId: string): Promise<FlashcardDeckData> {
  const response = await apiFetch(ENDPOINTS.regenerateFlashcardDeck(courseId), {
    method: "POST",
    cache: "no-store",
  });
  return parseResponse<FlashcardDeckData>(response);
}

export async function getSlide(courseId: string): Promise<GenerateResponse> {
  const response = await apiFetch(ENDPOINTS.getSlide(courseId), {
    cache: "no-store",
  });
  return parseResponse<GenerateResponse>(response);
}

export async function getQuiz(courseId: string): Promise<GenerateResponse> {
  const response = await apiFetch(ENDPOINTS.getQuiz(courseId), {
    cache: "no-store",
  });
  return parseResponse<GenerateResponse>(response);
}

export async function getVid(courseId: string): Promise<GenerateResponse> {
  const response = await apiFetch(ENDPOINTS.getVid(courseId), {
    cache: "no-store",
  });
  return parseResponse<GenerateResponse>(response);
}

export async function generateQuiz(
  courseId: string,
  topic: string = "Kiến thức tổng quát",
  quantity: number = 10,
  difficulty: string = "medium",
  learningMode: "normal" | "high_yield" = "normal"
): Promise<QuizResponse> {
  const response = await apiFetch(ENDPOINTS.generate("quiz"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      course_id: courseId,
      topic,
      quantity,
      difficulty,
      learning_mode: learningMode,
    }),
  });

  return parseResponse<QuizResponse>(response);
}

export async function generateContent(
  feature: GenerateFeature,
  courseId: string,
  prompt: string,
  learningMode: "normal" | "high_yield" = "normal",
  options?: {
    videoRenderer?: "simple_templates" | "manim";
    allowRendererFallback?: boolean;
    difficulty?: string;
    videoMode?: VideoMode;
    topicId?: string;
    chapterId?: string;
    userMode?: UserMode;
    renderMp4?: boolean;
    force?: boolean;
  }
): Promise<GenerateResponse> {
  const topic = prompt || "tổng quan";

  const config: Record<
    GenerateFeature,
    { body: Record<string, unknown> }
  > = {
    book: {
      body: {
        course_id: courseId,
        prompt,
        target_audience: "sinh viên",
        learning_mode: learningMode,
      },
    },
    slide: {
      body: { course_id: courseId, topic, num_slides: 8, learning_mode: learningMode },
    },
    quiz: {
      body: {
        course_id: courseId,
        topic,
        quantity: 10,
        difficulty: options?.difficulty ?? "medium",
        learning_mode: learningMode,
      },
    },
    vid: {
      body: {
        course_id: courseId,
        topic,
        video_mode: options?.videoMode ?? "three_minute",
        topic_id: options?.topicId,
        chapter_id: options?.chapterId,
        user_mode: options?.userMode ?? "student",
        render_mp4: options?.renderMp4 ?? true,
        force: options?.force ?? false,
        duration_minutes: 3,
        learning_mode: learningMode,
        video_renderer: options?.videoRenderer ?? "simple_templates",
        allow_renderer_fallback: options?.allowRendererFallback ?? true,
      },
    },
  };

  const { body } = config[feature];
  const response = await apiFetch(ENDPOINTS.generate(feature), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  return parseResponse<GenerateResponse>(response);
}

/** Render one planned video from a playlist plan (playlist_by_chapter mode). */
export async function renderPlaylistVideo(courseId: string, videoIndex: number): Promise<GenerateResponse> {
  const response = await apiFetch(
    `${APP_API_BASE_URL}/api/backend/course/${encodeURIComponent(courseId)}/vid/render`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_index: videoIndex }),
    },
  );
  return parseResponse<GenerateResponse>(response);
}

export async function deleteDocument(documentId: string): Promise<{ status: string }> {
  const response = await apiFetch(ENDPOINTS.deleteDocument(documentId), {
    method: "DELETE",
  });
  return parseResponse<{ status: string }>(response);
}

export const deleteCourse = deleteDocument;

export interface GenerationReadinessReport {
  document_id: string;
  overall_quality_score: number;
  clean_chunks_count: number;
  noisy_chunks_removed: number;
  generation_readiness: Record<string, {
    status: 'ready' | 'limited' | 'not_enough_context';
    reason: string;
    recommended_fallback: string;
  }>;
  safe_outputs_available: string[];
  warnings: string[];
  recommended_actions: string[];
}

export async function getCourseReadiness(courseId: string): Promise<GenerationReadinessReport> {
  const response = await apiFetch(`${APP_API_BASE_URL}/api/backend/course/${encodeURIComponent(courseId)}/readiness`);
  return parseResponse<GenerationReadinessReport>(response);
}

export interface FallbackGenerateResponse {
  status: string;
  course_id: string;
  fallback_type: string;
  result: Record<string, unknown>;
}

export async function generateFallbackOutput(
  courseId: string,
  fallbackType: string,
  title?: string,
): Promise<FallbackGenerateResponse> {
  const response = await apiFetch(
    `${APP_API_BASE_URL}/api/backend/course/${encodeURIComponent(courseId)}/generate-fallback`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fallback_type: fallbackType, title: title || "Bản học dự phòng" }),
    },
  );
  return parseResponse<FallbackGenerateResponse>(response);
}
