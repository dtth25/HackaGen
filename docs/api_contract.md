# API Contract

Contract này bám theo routes hiện tại trong `src/backend/main.py`.

Product surface hiện tại là **Document-to-Study-Pack**: user upload tài liệu và xem một dashboard học tập kết nối 4 học liệu cốt lõi: Book (Study Guide PDF), Slide, Quiz, Vid và grounding. Public generation endpoints là **Book/Study Guide, Slide, Quiz, Vid**.

## 1. Health & Management

### Auth & Admin

Auth supports Bearer JWT and an HttpOnly cookie named `agy_session` for browser flows. Upload, dashboard, generation, output, job, and delete endpoints require an active user unless explicitly marked as health or public demo.

- `POST /auth/register` / `POST /api/auth/register`: create a user. Email is lowercased and unique. Password is hashed with bcrypt. Default role is `user`.
- `POST /auth/login` / `POST /api/auth/login`: return `{ access_token, token_type, user }` and set the auth cookie.
- `POST /auth/logout` / `POST /api/auth/logout`: clear the auth cookie.
- `GET /auth/me` / `GET /api/auth/me`: return the current public user profile. Response never contains `password_hash`.
- Admin endpoints require `require_admin`: `GET /admin/users`, `GET /admin/users/{user_id}`, `PATCH /admin/users/{user_id}`, `POST /admin/users/{user_id}/disable`, `POST /admin/users/{user_id}/enable`, `POST /admin/users/{user_id}/make-admin`, `POST /admin/users/{user_id}/make-user`, `DELETE /admin/users/{user_id}`, `POST /admin/users/{user_id}/reset-password`.
- Disabled users cannot login/use protected APIs; backend prevents deleting, disabling, or demoting the last active admin.
- First admin bootstrap uses `CREATE_DEFAULT_ADMIN=true`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, and only creates an admin if no admin exists. The password is never logged.

- `GET /health`: readiness endpoint cho frontend proxy. Không gọi Gemini warm-up. Response gồm `status`, `ready`, `details.upload_dir`, `details.output_dir`, `details.vector_db`, `details.config_loaded`, `vector_db_provider`, `vector_db_ready`, `chroma_persist_dir`, `chroma_collection_name`, `startup_duration_seconds`, `error`. Với `VECTOR_DB_PROVIDER=chroma`, nếu Chroma thiếu hoặc không initialize được thì `vector_db_ready=false` và không fallback sang simple/local store.
- Health response có thể kèm `storage_provider`, `storage_ready`, `job_queue_provider`, `job_queue_ready`, `cache_provider`, `cache_ready` để chuẩn bị production provider switch.
- `GET /api/health`: trả trạng thái backend và danh sách `course_id`.
- `GET /api/courses`: trả danh sách `course_id` đã đăng ký.
- `GET /api/courses/all`: trả danh sách course kèm metadata local.
- `DELETE /api/courses/{course_id}`: xóa course khỏi cache, generated files và vector DB.
- `DELETE /api/documents/{document_id}` hoặc `DELETE /documents/{document_id}`: xóa document, upload file, vector entries, generated outputs và cache hash do ứng dụng quản lý khi có thể. Endpoint yêu cầu user sở hữu document, trừ admin.

## 2. Upload & Status

### `POST /api/upload`

Input: `multipart/form-data`.

Supported fields:
- `files`: một hoặc nhiều file PDF, DOCX, TXT.
- `file`: legacy single-file field, vẫn được hỗ trợ để tránh vỡ client cũ.

Validation:
- filename required.
- extension phải là `.pdf`, `.docx`, `.txt`.
- file không rỗng.
- mỗi file size <= 50MB.

Response:

```json
{
  "course_id": "abc123def456",
  "document_id": "abc123def456",
  "filename": "2 files",
  "filenames": ["intro.pdf", "exercise.docx"],
  "file_count": 2,
  "status": "processing",
  "message": "Đã nhận 2 file và đang phân tích tài liệu. ID tài liệu: abc123def456"
}
```

### `GET /api/course/{course_id}/status`

```json
{
  "course_id": "abc123def456",
  "status": "ready",
  "stage": "completed",
  "progress": 100,
  "progress_message": "Hoàn thành!",
  "filenames": ["intro.pdf", "exercise.docx"],
  "file_count": 2,
  "total_processing_time": 18.4
}
```

Possible statuses: `pending`, `processing`, `ready`, `completed_limited`, `failed`, `paused_due_to_quota`, `unknown`.
Possible preprocessing stages: `uploading`, `extracting_text`, `cleaning_text`, `chunking`, `embedding`, `storing_vectors`, `completed`, `completed_limited`, `failed`, `paused_due_to_quota`, `analysis_failed`, `extraction_failed`, `embedding_failed`, `vector_index_failed`, `insufficient_context`.
When available, response may include `preprocess_profile` with file size, page count, extracted character count, chunk count, embedding request count, cache hits/misses, retry count, throttle sleep time, and per-step timings.
If preprocessing fails because Gemini embedding quota is exhausted, response includes `error_code: "EMBEDDING_QUOTA_EXCEEDED"` and a public `error` message that asks the user to wait, retry with a smaller file, enable billing, or switch embedding provider.

### `GET /documents/{document_id}/status`

Stable polling endpoint for upload/preprocess progress. `document_id` currently equals `course_id`.

```json
{
  "document_id": "abc123def456",
  "status": "embedding",
  "stage": "embedding",
  "failure_stage": null,
  "progress": 56,
  "message": "Đang tạo embedding và kiểm soát quota...",
  "error": null,
  "user_message": null,
  "technical_error": null,
  "can_retry": false,
  "recommended_action": null,
  "error_code": null
}
```

Possible statuses: `extracting_text`, `cleaning_text`, `chunking`, `embedding`, `storing_vectors`, `completed`, `completed_limited`, `failed`, `paused_due_to_quota`.

When preprocessing fails, the endpoint stores and returns structured failure details:

```json
{
  "document_id": "abc123def456",
  "status": "failed",
  "stage": "extraction_failed",
  "failure_stage": "extraction_failed",
  "progress": 0,
  "message": "PDF này có vẻ là bản scan/ảnh hoặc không có lớp text đủ rõ.",
  "error": "PDF này có vẻ là bản scan/ảnh hoặc không có lớp text đủ rõ.",
  "user_message": "PDF này có vẻ là bản scan/ảnh hoặc không có lớp text đủ rõ.",
  "technical_error": "ValueError: ...",
  "can_retry": true,
  "recommended_action": "upload_clearer_pdf",
  "error_code": "PDF_TEXT_EXTRACTION_FAILED"
}
```

`technical_error` is for developer/debug UI only; do not show it inline to normal users.

### `POST /documents/{document_id}/retry`

Retries preprocessing from the saved upload file without requiring a new upload. `POST /api/documents/{document_id}/retry` is also available.

```json
{
  "document_id": "abc123def456",
  "status": "processing",
  "stage": "extracting_text",
  "progress": 0,
  "message": "Đang chạy lại phân tích tài liệu...",
  "job_id": "..."
}
```

### `GET /documents/{document_id}/sources`

Stable source-grounding endpoint for UI panels. `GET /api/documents/{document_id}/sources` is also available.

Query:
- `ids`: optional comma-separated `source_chunk_ids` generated by Study Pack outputs.
- `developer`: optional boolean. Defaults to `false`; when `true` and the requester is admin, response may include internal `source_chunk_id` for debugging.

Public response hides internal chunk ids by default and returns clean excerpts only:

```json
{
  "document_id": "abc123def456",
  "total_source_chunks": 12,
  "matched_source_chunks": 2,
  "sources": [
    {
      "page": 3,
      "excerpt": "Short cleaned source excerpt..."
    }
  ]
}
```

The frontend should show `page` and `excerpt` to users. `source_chunk_id` must only be displayed when developer mode is explicitly enabled.

### `GET /api/jobs/{job_id}`

Local/dev job metadata endpoint. Hiện tại dùng inline local thread queue; schema giữ tương thích để sau này chuyển sang Postgres + Redis worker.

```json
{
  "id": "uuid",
  "document_id": "abc123def456",
  "user_id": "uuid optional",
  "job_type": "preprocess",
  "status": "queued",
  "progress": 0,
  "message": "Queued",
  "error": null,
  "created_at": 0,
  "updated_at": 0,
  "completed_at": null
}
```

## 3. Generation

Tất cả generation endpoints yêu cầu course ở trạng thái `ready`. Response public không trả `page`, `source`, `chunk_id` hoặc `citations`.

### `POST /api/generate-book`

Request:

```json
{
  "course_id": "abc123def456",
  "user_prompt": "Tập trung vào phần nhập môn",
  "target_audience": "sinh viên"
}
```

Response:

```json
{
  "course_id": "abc123def456",
  "book": {
    "title": "string",
    "description": "string",
    "estimated_duration": "3-5 giờ",
    "chapters": []
  },
  "pdf_url": "/api/course/abc123def456/book.pdf"
}
```

### `POST /api/generate-slide`

Request:

```json
{
  "course_id": "abc123def456",
  "topic": "Cơ học",
  "num_slides": 8
}
```

Response fields: `course_id`, `topic`, `total_slides`, `slides`, `pptx_url`.

`slides[]` public fields:
- `slide_number`: sequential slide number.
- `title`: slide title.
- `layout_type` (optional): `default`, `two_column`, or `quote`.
- `bullet_points`: concise bullet points on the slide.
- `source_chunk_ids`: internal grounding chunk ids (not shown raw to end users).

Note: teaching/speaker notes and graphic-design hints are intentionally NOT part of the slide output — slides are rendered as clean 16:9 artifacts with no meta-instruction text.

### `POST /api/generate-quiz`

Request:

```json
{
  "course_id": "abc123def456",
  "topic": "Cơ học",
  "quantity": 10,
  "difficulty": "medium"
}
```

Response fields: `course_id`, `topic`, `difficulty`, `total_questions`, `questions`, `answer_key_url`.

`questions[]` public fields:
- `question_type` (optional): `concept`, `application`, `formula`, `scenario`, or similar.
- `question`: question text.
- `options`: answer options.
- `correct`: zero-based index for internal UI scoring and answer-key export.
- `explanation`: teaching explanation, shown only after user review/submission in UI.
- `difficulty` (optional): normalized difficulty label.

### `POST /api/generate-vid`

Request:

```json
{
  "course_id": "abc123def456",
  "topic": "tổng quan",
  "duration_minutes": 3,
  "learning_mode": "normal",
  "video_renderer": "simple_templates",
  "allow_renderer_fallback": true
}
```

Optional:
- `learning_mode`: `normal` hoặc `high_yield`.
- `video_renderer`: `simple_templates` hoặc `manim`. `simple_slides` cũ vẫn được backend nhận như alias tương thích. Nếu `manim` chưa khả dụng và `allow_renderer_fallback = true`, backend fallback sang renderer thường và trả `vid.renderer_message`.
- `allow_renderer_fallback`: mặc định `true`.

Response fields: `course_id`, `vid`. Khi tạo thành công, `vid.status = "ready"` và `vid.url` trỏ tới `/api/course/{course_id}/vid/file`. Khi render lỗi hoặc storyboard không đạt quality gate, `vid.status = "failed"` và có lỗi thân thiện trong `vid.error`.

`vid.scenes[]` public fields: `scene_index`, `scene_type`, `title`, `key_message`, `screen_text`, `voiceover`, `visual_template`, `visual_data`, `duration_seconds`, `animation_notes`, `source_chunk_ids`.

Metadata video có thể gồm: `quality_report`, `transcript`, `subtitles_srt`, `quick_quiz`, `videos`, `playlist_plan`, `progress_states`, `renderer`, `renderer_message`, `debug_log`. `debug_log` là log rút gọn, không trả full FFmpeg stderr.

## 4. Saved Artifacts

- `GET /api/course/{course_id}/book`
- `GET /api/course/{course_id}/book.pdf`
- `GET /api/course/{course_id}/slide`
- `GET /api/course/{course_id}/slide.pptx`
- `GET /api/course/{course_id}/slide.pdf`
- `GET /api/course/{course_id}/quiz`
- `GET /api/course/{course_id}/quiz-key.pdf`
- `GET /api/course/{course_id}/vid`
- `GET /api/course/{course_id}/vid/file`
- `GET /api/course/{course_id}/files`
- `GET /api/course/{course_id}/stats`
- `GET /api/course/{course_id}/study-pack`

### `GET /api/course/{course_id}/study-pack`

Returns the connected document dashboard. This endpoint does not create a separate AI output; it reads saved Study Guide/book, slide, quiz, vid and course stats, then derives dashboard-ready readiness and quality scores from the same structured source.

```json
{
  "course_id": "abc123def456",
  "stats": {},
  "study_pack": {
    "title": "string",
    "book": {},
    "slides": [],
    "quiz": [],
    "vid": {},
    "readiness": {
      "study_guide_pdf": true,
      "slides": true,
      "quiz": true,
      "vid": true
    },
    "quality_scores": {
      "study_guide_pdf": 90,
      "slides": 88,
      "quiz": 92,
      "vid": 89
    },
    "grounding": {
      "num_chunks": 120,
      "quality_score": 85,
      "warnings": []
    }
  }
}
```

## 5. Deprecated Surface

Các route output cũ không còn là public API và phải trả 404 nếu gọi:
- `/api/chat`
- `/api/custom-prompt`
- `/api/generate-course`
- `/api/generate-summary`
- `/api/generate-flashcards`
- `/api/generate-mindmap`
- `/api/generate-podcast/{course_id}`
- `/api/generate-study-guide/{course_id}`
- mọi async generation route cũ
