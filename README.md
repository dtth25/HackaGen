# DTTH-Hackathon-2026 AI Course Generator

Biến một hoặc nhiều tài liệu PDF, DOCX, TXT thành một **Document-to-Study-Pack**: Study Guide PDF là trung tâm, kèm quiz, mindmap, flashcards, summary và các output tùy chọn như slides/video.

## Tech Stack

| Layer | Công nghệ |
| --- | --- |
| Frontend | Next.js App Router, React 19, Tailwind CSS v4, shadcn/base-ui, lucide-react |
| Backend | FastAPI, Python 3.11+, LangChain |
| Dependency | `uv` cho backend, npm cho frontend |
| Vector DB | Chroma local persistent DB, mandatory for hackathon demo |
| Persistence | Local filesystem JSON/generated files |
| AI Model | Gemini `gemini-2.5-flash` |
| Embedding | Gemini `models/embedding-001` via LangChain batch embeddings |

## Production architecture roadmap

Mục tiêu architecture mới là giữ local/dev chạy nhẹ cho demo, nhưng tách provider để có thể nâng cấp thành production web product mà không rewrite toàn bộ codebase.

### Local/dev mode hiện tại

- Frontend: Next.js App Router trong `src/frontend`.
- Backend: FastAPI trong `src/backend`.
- Vector DB: `VECTOR_DB_PROVIDER=chroma`, lưu local tại `CHROMA_PERSIST_DIR`.
- File storage: `STORAGE_PROVIDER=local`, upload/generated files lưu trên filesystem.
- Job queue: `JOB_QUEUE_PROVIDER=inline`, chạy background bằng local thread.
- Cache: `CACHE_PROVIDER=local`, document hash/cache embedding dùng file JSON/local files.
- Database: SQLite qua `DATABASE_URL=sqlite:///./data/app.db` hoặc fallback local cũ.
- Auth: JWT bearer token + HttpOnly cookie cho local/dev; admin user management có bootstrap admin tùy env.

### Production mode sau này

- Database: chuyển `DATABASE_URL` sang Postgres để lưu users, documents, jobs, outputs, usage, metadata.
- Worker queue: thay `JOB_QUEUE_PROVIDER=inline` bằng `redis_celery`, `rq` hoặc `arq` khi triển khai worker thật.
- Cache: thay `CACHE_PROVIDER=local` bằng Redis để share cache giữa nhiều backend/worker.
- Storage: thay `STORAGE_PROVIDER=local` bằng S3 hoặc Cloudflare R2 cho uploads và generated outputs.
- Vector DB: giữ Chroma cho local/dev; thêm provider Milvus/Qdrant/pgvector phía sau interface `VectorStore`.
- Admin: xây route quản trị users, documents, failed jobs, usage và retry queue dựa trên job/document metadata.

### Provider-based extension points

- Vector store interface: `src/backend/vector_db/base.py`.
- Vector provider facade: `src/backend/vector_db/manager.py`.
- File storage interface: `src/backend/services/storage.py`.
- Job queue interface: `src/backend/services/jobs.py`.
- Cache interface: `src/backend/services/cache.py`.

### Cách switch provider

Local mặc định:

```bash
VECTOR_DB_PROVIDER=chroma
STORAGE_PROVIDER=local
JOB_QUEUE_PROVIDER=inline
CACHE_PROVIDER=local
DATABASE_URL=sqlite:///./data/app.db
```

Production provider chưa được implement sẽ báo lỗi rõ nếu chọn nhầm. Không có fallback âm thầm từ S3/Redis/Postgres về local, để tránh demo pass giả nhưng production sai.

## Public Outputs

- **Book:** View theo chương/bài và file PDF download.
- **Slide:** Viewer từng slide và file PPTX download.
- **Quiz:** MCQ tương tác, đáp án chỉ hiện khi người học yêu cầu hoặc sau khi nộp bài, kèm file key đáp án.
- **Vid:** Video học tập dạng slide + voiceover và MP4 download.

## Backend Runbook

### One-time setup

```bash
cd src/backend
uv sync --all-extras
```

Tạo environment cho Gemini:

```bash
export GOOGLE_API_KEY="your_gemini_api_key_here"
```

Trên Windows PowerShell:

```powershell
$env:GOOGLE_API_KEY="your_gemini_api_key_here"
```

### Switching Gemini model presets (Flash vs Pro)

Model routing dùng các biến `GEMINI_*_MODEL` (xem `.env.example`) để chọn model Gemini riêng cho từng loại tác vụ sinh nội dung (`GEMINI_BOOK_MODEL`, `GEMINI_SLIDE_MODEL`, `GEMINI_QUIZ_MODEL`, `GEMINI_FLASHCARD_MODEL`, `GEMINI_MINDMAP_MODEL`, `GEMINI_SUMMARY_MODEL`, `GEMINI_VIDEO_MODEL`, `GEMINI_COURSE_MODEL`, `GEMINI_QUALITY_MODEL`), với `GEMINI_DEFAULT_MODEL` rồi `GEMINI_FAST_MODEL` làm fallback nếu một biến task cụ thể chưa được set. Embeddings luôn dùng riêng `GEMINI_EMBEDDING_MODEL`.

Hai preset có sẵn: `.env.flash` (nhanh, tiết kiệm quota) và `.env.pro` (chất lượng cao hơn cho Book/Slide/Video). Copy file preset đè lên `.env` đang dùng:

Windows PowerShell (chạy tại thư mục gốc repo, hoặc `src/backend` nếu bạn giữ preset riêng cho backend):

```powershell
# Mode Flash (nhanh, tiết kiệm)
Copy-Item .env.flash .env -Force

# Mode Pro (chất lượng cao)
Copy-Item .env.pro .env -Force
```

macOS/Linux:

```bash
cp .env.flash .env   # Flash mode
cp .env.pro .env     # Pro mode
```

Khởi động lại backend sau khi đổi preset để log `[Startup Config]` in ra model đang active cho từng tác vụ.

### Every-time run

Chạy từ thư mục `src` để import path `backend.main` khớp package hiện tại:

```bash
cd src
uv run --project backend uvicorn backend.main:app --reload --port 8000
```

Backend chạy tại `http://localhost:8000`.

## Frontend Runbook

```bash
cd src/frontend
npm install
npm run dev
```

Frontend chạy tại `http://localhost:3000`. Nếu backend không chạy ở port mặc định, set `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000` cho Next.js. `BACKEND_API_BASE_URL` vẫn được hỗ trợ như alias server-side cũ.

Khi demo cho người dùng, chạy production mode để không thấy Next.js dev indicator:

```bash
cd src/frontend
npm run build
npm run start
```

## Docker Backend Option

```bash
cp .env.example .env
# Sửa .env và điền GOOGLE_API_KEY
docker compose up --build backend
```

Runtime files khi chạy Docker được mount vào `runtime/`.

## Using Chroma For Local Hackathon Demo

**Chroma is the required local/dev vector database.** It is the default provider — if
`VECTOR_DB_PROVIDER` is unset, the backend defaults to `chroma`. Chroma is used because
this app needs more than plain similarity search: persistent collections with
`document_id`/`user_id` metadata filtering, per-chunk `chunk_type`/`quality_score`
tagging, and clean per-document delete — all of which Chroma supports natively.

**FAISS is not the main vector database and is not used at all in the current provider
path.** `src/backend/vector_db/faiss_manager.py` remains in the repo only for legacy
tests/migration reference. Setting `VECTOR_DB_PROVIDER=faiss` (or `simple_dev_only`) is
normalized back to `chroma` with a warning — it is never a silent fallback. FAISS could
be wired back in later as an *optional, experimental* fallback provider, but that is not
implemented today. Future **production** vector providers (Qdrant, Milvus, or Postgres
`pgvector`) are reserved behind the same `VectorStore` interface and are also not
implemented for local/dev — selecting them reports the vector DB as not ready rather
than silently falling back to a fake store.

If Chroma is not installed or cannot initialize, `/health` returns
`vector_db.ready=false` (and legacy `vector_db_ready=false`) with a clear error, and the
backend keeps running instead of crashing — other endpoints still respond, but any
Chroma-dependent operation (upload/generate) fails with an explicit message.

Environment:

```bash
VECTOR_DB_PROVIDER=chroma
CHROMA_PERSIST_DIR=./data/chroma
CHROMA_COLLECTION_NAME=ai_course_chunks
```

`/health` response shape:

```json
{
  "status": "ok",
  "vector_db": {
    "provider": "chroma",
    "ready": true,
    "collection": "ai_course_chunks",
    "persist_dir": "./data/chroma"
  }
}
```

Install and run:

```bash
cd src/backend
uv sync --all-extras
cd ..
uv run --project backend uvicorn backend.main:app --reload --port 8000
```

Chroma data is stored under `src/data/chroma` when the backend is started from `src`. To
clear local demo vectors, stop the backend and delete that folder, or (dev/debug only —
never call this from a normal request handler) `ChromaVectorStore().reset_collection()`,
which drops and recreates the whole collection.

Duplicate-upload handling is also tied to the local Chroma path:

- File hash cache reuses an already processed document by copying existing Chroma chunks/vectors into the new `document_id` (re-tagged with the requesting user's `user_id`, not the original uploader's).
- Chunk hash cache avoids re-embedding identical chunks.
- Retrieval requires a `document_id` filter so outputs do not mix chunks from different uploaded documents; if a document has an owning `user_id`, that is filtered too.
- Every chunk stores `chunk_type` (`toc | noisy | body | definition | example | code | formula | exercise | summary`), `quality_score`, and `use_for_generation`. Generation retrieval excludes `toc`/`noisy` chunks and `use_for_generation=false` chunks by default, over-fetches, deduplicates near-identical text, and caps how many chunks come from the same page — debug/review endpoints can still request the unfiltered set.

## API Flow

1. `POST /api/upload` với multipart field **`files`** để upload một hoặc nhiều tài liệu vào cùng một `course_id`/`document_id`.
2. Legacy field **`file`** vẫn được hỗ trợ cho single-file client cũ.
3. `GET /documents/{document_id}/status` hoặc `GET /api/course/{course_id}/status` để poll đến khi `completed`/`ready`.
4. Gọi một trong 4 endpoint generation qua FastAPI.
5. Frontend render artifact; Book/Slide/Quiz/Vid đều có download tương ứng khi tạo xong.

Các route chính:
- Readiness: `/health`.
- Auth: `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/me` (also under `/api/auth/...`).
- Admin users: `/admin/users`, `/admin/users/{user_id}`, `/admin/users/{user_id}/disable|enable|make-admin|make-user|reset-password`.
- Health/management: `/api/health`, `/api/courses`, `/api/courses/all`, `DELETE /api/courses/{course_id}`.
- Upload/status: `/api/upload`, `/documents/{document_id}/status`, `/api/course/{course_id}/status`.
- Generation: `/api/generate-book`, `/api/generate-slide`, `/api/generate-quiz`, `/api/generate-vid`.
- Saved artifacts: `/api/course/{course_id}/book`, `/book.pdf`, `/slide`, `/slide.pptx`, `/quiz`, `/quiz-key.pdf`, `/vid`, `/vid/file`, `/files`, `/stats`.

## Test Gates

Backend:

```bash
cd src/backend
uv run ruff check .
uv run pytest tests
```

Frontend:

```bash
cd src/frontend
npm run lint
npm run build
```

Manual smoke trước demo:
- Upload ít nhất 2 tài liệu.
- Poll đến khi tài liệu sẵn sàng.
- Generate đủ Book, Slide, Quiz, Vid.
- Generate output mới không làm mất output cũ.
- Slide có Next/Previous và download.
- Quiz chọn đáp án được, không lộ đáp án trước submit.
- Book đọc được trong web và tải PDF được.
- Vid trả player/download MP4 hoặc lỗi rõ ràng nếu render thất bại.

## Non-Negotiable Gates

1. **Only 4 Outputs:** Public API/UI/docs chỉ có Book, Slide, Quiz, Vid.
2. **No Additional Chats:** Không có chat tự do hoặc custom prompt độc lập.
3. **No Public Source Metadata:** Public API không trả `page`, `source`, `chunk_id`, `citations`.
4. **Grounded Generation:** Output phải dựa trên retrieved chunks từ Chroma.
5. **Auth & Ownership:** Upload/generation/output APIs require an active user; regular users only access their own documents, while admins can manage users and support document access.
6. **File validation:** Chỉ chấp nhận `.pdf`, `.docx`, `.txt`, không file rỗng, không quá 50MB mỗi file.
7. **Backend-only AI:** Frontend không gọi LLM trực tiếp.
