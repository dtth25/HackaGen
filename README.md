# DTTH-Hackathon-2026 AI Course Generator

AI Course Generator biến một hoặc nhiều tài liệu `.pdf`, `.docx`, `.txt` thành một **Document-to-Study-Pack**: Study Guide/Book là trung tâm, kèm Mindmap, Quiz, Flashcards, High-yield Summary, Slide và Vid.

Code hiện tại là source of truth. README này mô tả đúng flow đang chạy trong repo: Chroma local, Auth v2, FastAPI backend, Next.js frontend và các generated artifacts lưu trên filesystem local.

## Tech Stack

| Layer | Công nghệ |
| --- | --- |
| Frontend | Next.js App Router, React 19, Tailwind CSS v4, shadcn/base-ui, lucide-react |
| Backend | FastAPI, Python 3.11+, LangChain |
| Dependency | `uv` cho backend, npm cho frontend |
| Vector DB | Chroma local persistent DB, bắt buộc cho local/dev demo |
| Persistence | Local filesystem JSON/generated files |
| Auth | JWT bearer token + HttpOnly cookie, user ownership, admin routes |
| AI Model | Gemini, mặc định `gemini-2.5-flash` qua model routing |
| Embedding | Gemini embedding qua LangChain batch embeddings |

## Product Surface

- **Study Pack Dashboard:** View tổng hợp từ cùng một document/course: Study Guide/Book, Mindmap, Quiz, Flashcards, Summary, readiness, quality scores và grounding.
- **Book / Study Guide:** View theo chương/bài và file PDF download.
- **Mindmap:** Sơ đồ 3-level interactive, có endpoint get/regenerate theo course.
- **Quiz:** MCQ tương tác; đáp án/explanation chỉ hiện khi người học review hoặc submit; có answer-key PDF.
- **Flashcards:** Deck ôn tập từ book plan/saved deck hoặc regenerate theo course.
- **Summary:** High-yield summary trong Study Pack, không có legacy standalone generate endpoint.
- **Slide:** Viewer từng slide và file PPTX download.
- **Vid:** Video dạng slide + voiceover, metadata JSON và MP4 download hoặc lỗi render rõ ràng.

Book, Slide, Quiz và Vid là 4 endpoint generation trực tiếp. Mindmap, Flashcards và Summary là thành phần Study Pack/course-scoped, không phải chat/custom prompt tự do.

## Prerequisites

Cài các công cụ sau trước khi setup từ máy sạch:

- Python 3.11+.
- `uv`.
- Node.js 20+ và npm.
- Gemini API key (`GOOGLE_API_KEY`).
- Windows: cài **Microsoft C++ Build Tools** với workload "Desktop development with C++". Chroma phụ thuộc `chroma-hnswlib`; trên một số máy Windows package này phải build native wheel và sẽ fail nếu thiếu C++ toolchain.
- Docker Desktop nếu muốn chạy backend bằng Docker.

Kiểm tra nhanh:

```bash
python --version
uv --version
node --version
npm --version
```

## Environment Setup

Tạo file env ở root repo:

Windows PowerShell:

```powershell
Copy-Item .env.example .env -Force
```

macOS/Linux:

```bash
cp .env.example .env
```

Sửa `.env` và điền ít nhất:

```bash
GOOGLE_API_KEY=your_gemini_api_key_here
JWT_SECRET=change-this-dev-secret
VECTOR_DB_PROVIDER=chroma
CHROMA_PERSIST_DIR=./data/chroma
CHROMA_COLLECTION_NAME=ai_course_chunks
DATABASE_URL=sqlite:///./data/app.db
```

Nếu muốn bootstrap admin local/dev:

```bash
CREATE_DEFAULT_ADMIN=true
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-this-password
```

Preset model có sẵn dưới dạng file example. Copy preset rồi sửa key/secrets nếu cần:

Windows PowerShell:

```powershell
# Flash mode: nhanh, tiết kiệm quota
Copy-Item .env.flash.example .env -Force

# Pro mode: chất lượng cao hơn cho một số tác vụ
Copy-Item .env.pro.example .env -Force
```

macOS/Linux:

```bash
cp .env.flash.example .env
cp .env.pro.example .env
```

Backend tự load `.env` từ root repo, `src/`, hoặc `src/backend/`. Khởi động lại backend sau khi đổi env để log `[Startup Config]` hiển thị model đang active.

## Backend Runbook

One-time setup:

```bash
cd src/backend
uv sync --all-extras
```

Chạy backend từ thư mục `src` để import path `backend.main` khớp package hiện tại:

```bash
cd ..
uv run --project backend uvicorn backend.main:app --reload --port 8000
```

Backend chạy tại `http://127.0.0.1:8000`.

Kiểm tra readiness:

```bash
curl http://127.0.0.1:8000/health
```

Nếu `/health` trả `vector_db.ready=false`, kiểm tra lại `chromadb`, `CHROMA_PERSIST_DIR` và C++ Build Tools trên Windows. Backend vẫn có thể trả health, nhưng upload/generate sẽ fail cho tới khi Chroma ready.

## Frontend Runbook

One-time setup:

```bash
cd src/frontend
npm install
```

Run dev:

```bash
npm run dev
```

Frontend chạy tại `http://localhost:3000`.

Frontend gọi backend qua Next.js proxy `/api/backend/*`. Nếu backend không chạy ở `http://127.0.0.1:8000`, set biến server-side cho frontend:

```bash
BACKEND_API_BASE_URL=http://127.0.0.1:8001
```

`NEXT_PUBLIC_API_BASE_URL` vẫn được hỗ trợ như alias cũ, nhưng `BACKEND_API_BASE_URL` là biến nên dùng cho proxy hiện tại.

Demo production mode để không thấy Next.js dev indicator:

```bash
npm run build
npm run start
```

## First User Flow

1. Mở `http://localhost:3000/register` để tạo user, hoặc bật `CREATE_DEFAULT_ADMIN=true` rồi đăng nhập admin.
2. Upload một hoặc nhiều file `.pdf`, `.docx`, `.txt`.
3. Poll status đến khi document/course `completed` hoặc `ready`.
4. Mở dashboard Study Pack hoặc generate Book, Slide, Quiz, Vid.
5. Kiểm tra download: Book PDF, Slide PPTX, Quiz answer-key PDF, Vid MP4 nếu render thành công.

## Docker Backend Option

```bash
cp .env.example .env
# Sửa .env và điền GOOGLE_API_KEY/JWT_SECRET
docker compose up --build backend
```

Runtime files khi chạy Docker được mount vào `runtime/`. Docker compose hiện chỉ chạy backend; frontend vẫn chạy bằng npm ở `src/frontend`.

## Local Architecture

Local/dev mode hiện tại:

- Frontend: Next.js App Router trong `src/frontend`.
- Backend: FastAPI trong `src/backend`.
- Vector DB: `VECTOR_DB_PROVIDER=chroma`, lưu local tại `CHROMA_PERSIST_DIR`.
- File storage: `STORAGE_PROVIDER=local`, upload/generated files lưu trên filesystem.
- Job queue: `JOB_QUEUE_PROVIDER=inline`, chạy background bằng local thread.
- Cache: `CACHE_PROVIDER=local`, document hash/cache embedding dùng file JSON/local files.
- Database: SQLite qua `DATABASE_URL`.
- Auth: Bearer JWT + HttpOnly cookie; protected APIs require active user.

Provider extension points:

- Vector store interface: `src/backend/vector_db/base.py`.
- Vector provider facade: `src/backend/vector_db/manager.py`.
- File storage interface: `src/backend/services/storage.py`.
- Job queue interface: `src/backend/services/jobs.py`.
- Cache interface: `src/backend/services/cache.py`.

Production providers như Postgres, Redis worker/cache, S3/R2 storage, Qdrant/Milvus/pgvector chỉ là hướng mở rộng. Nếu chọn provider chưa implement, backend phải báo lỗi rõ, không fallback âm thầm sang local.

## Chroma Notes

Chroma là vector database bắt buộc cho local/dev. Nếu `VECTOR_DB_PROVIDER` unset, backend mặc định dùng `chroma`.

FAISS không phải provider chính trong flow hiện tại. `src/backend/vector_db/faiss_manager.py` còn trong repo cho legacy tests/migration reference. Setting `VECTOR_DB_PROVIDER=faiss` hoặc `simple_dev_only` được normalize về `chroma` với warning.

Chroma được dùng vì app cần:

- Persistent collection local.
- Filter theo `document_id` và `user_id`.
- Metadata `chunk_type`, `quality_score`, `use_for_generation`.
- Delete/copy document chunks cho ownership và duplicate-upload cache.

Data mặc định nằm dưới `src/data/chroma` nếu backend start từ `src`. Muốn clear demo vectors thì stop backend rồi xóa folder đó.

## API Flow

Các route chính:

- Readiness: `GET /health`.
- Auth: `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/me` và alias `/api/auth/...`.
- Admin users: `/admin/users`, `/admin/users/{user_id}`, `/admin/users/{user_id}/disable|enable|make-admin|make-user|reset-password`.
- Upload/status: `POST /api/upload`, `GET /documents/{document_id}/status`, `GET /api/course/{course_id}/status`.
- Source grounding: `GET /documents/{document_id}/sources`, alias `/api/documents/{document_id}/sources`.
- Direct generation: `POST /api/generate-book`, `/api/generate-slide`, `/api/generate-quiz`, `/api/generate-vid`.
- Study Pack/course outputs: `/api/course/{course_id}/study-pack`, `/mindmap`, `/mindmap/regenerate`, `/flashcards`, `/flashcards/regenerate`, `/readiness`, `/stats`.
- Saved artifacts: `/api/course/{course_id}/book`, `/book.pdf`, `/slide`, `/slide.pptx`, `/quiz`, `/quiz-key.pdf`, `/vid`, `/vid/file`, `/files`.
- Delete: `DELETE /api/courses/{course_id}`, `DELETE /api/documents/{document_id}`, `DELETE /documents/{document_id}`.

Upload dùng multipart field `files` cho multi-document. Legacy field `file` vẫn được hỗ trợ cho single-file client cũ.

## Security & Metadata Policy

- Frontend không gọi Gemini/LLM trực tiếp. Mọi AI call đi qua FastAPI.
- Upload/generation/output/delete yêu cầu active user, trừ health/demo public routes được đánh dấu rõ.
- User thường chỉ truy cập document/output của mình; admin có quyền quản trị/hỗ trợ.
- Generation response không được lộ raw/internal `source`, `chunk_id`, `citations` hoặc debug markers.
- `source_chunk_ids` được giữ trong artifact metadata để UI truy vấn grounding.
- Source panel có thể hiển thị `page` + excerpt sạch; `source_chunk_id` chỉ hiện khi developer mode bật và requester là admin.

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

- Register/login thành công.
- Upload ít nhất 2 tài liệu.
- Poll đến khi tài liệu sẵn sàng.
- Dashboard Study Pack hiển thị Book, Mindmap, Quiz, Flashcards, Summary/readiness/grounding.
- Generate đủ Book, Slide, Quiz, Vid.
- Generate output mới không làm mất output cũ.
- Slide có Next/Previous và PPTX download.
- Quiz chọn đáp án được, không lộ đáp án/explanation trước submit/review.
- Book đọc được trong web và tải PDF được.
- Vid trả player/download MP4 hoặc lỗi rõ ràng nếu render thất bại.
- User A không truy cập được document/output của User B; admin có thể hỗ trợ/quản trị.

## Non-Negotiable Gates

1. **Connected Study Pack:** Study Guide/Book, Mindmap, Quiz, Flashcards, Summary, readiness/quality/grounding phải xuất phát từ cùng nguồn cấu trúc.
2. **Four Direct Generation Endpoints:** Book, Slide, Quiz, Vid là các endpoint generation trực tiếp; Mindmap/Flashcards/Summary là course-scoped Study Pack components.
3. **No Additional Chats:** Không có chat tự do hoặc custom prompt độc lập ngoài hệ sinh thái Study Pack.
4. **No Raw Public Source Metadata:** Generation response không lộ raw/internal `source`, `chunk_id`, `citations` hoặc debug markers; `source_chunk_ids` và source excerpt/page display theo API contract.
5. **Grounded Generation:** Output phải dựa trên retrieved chunks từ Chroma/local index sau khi lọc noisy/TOC/debug text.
6. **Auth & Ownership:** Protected APIs require active user; regular users only access their own documents/outputs, admins can manage/support.
7. **File Validation:** Chỉ chấp nhận `.pdf`, `.docx`, `.txt`, không file rỗng, không quá 50MB mỗi file.
8. **Backend-only AI:** Frontend không gọi LLM/Gemini trực tiếp.
9. **Code Style:** Backend Ruff-compatible, Frontend ESLint/build không lỗi.
