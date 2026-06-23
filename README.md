# DTTH-Hackathon-2026 AI Course Generator

Biến tài liệu thô (PDF, DOCX, TXT) thành nội dung học tập đa phương tiện: khóa học, tóm tắt, flashcards, quiz, slides, mind map, study guide, podcast script và custom prompt.

## Tech Stack Hiện Tại

| Layer | Công nghệ |
|-------|-----------|
| Frontend | Next.js App Router, React 19, Tailwind CSS v4, shadcn/base-ui, lucide-react |
| Backend | FastAPI, Python 3.11+, LangChain |
| Dependency | `uv` cho backend, npm cho frontend |
| Vector DB | FAISS local disk-based |
| Persistence | Local filesystem JSON/generated files |
| AI Model | Gemini `gemini-2.5-flash` |
| Embedding | Gemini `models/embedding-001` via LangChain batch embeddings |

## Cấu Trúc Thư Mục

```
├── docs/
│   ├── PRD.md
│   ├── api_contract.md
│   └── architecture_design.md
├── src/
│   ├── backend/
│   │   ├── main.py
│   │   ├── core/
│   │   ├── services/
│   │   └── vector_db/
│   └── frontend/
│       ├── src/app/
│       ├── src/components/
│       └── src/lib/
├── AGENTS.md
├── ROOT_CONTEXT.md
├── docker-compose.yml
└── .env.example
```

## Backend Runbook

### One-time setup

```bash
cd src/backend
uv sync --all-extras
```

Tạo environment cho Gemini:

```bash
# Option A: shell environment
export GOOGLE_API_KEY="your_gemini_api_key_here"

# Option B: từ repo root, tạo file được code hiện tại đọc khi chạy từ src/
cp .env.example src/api_key.env
```

Trên Windows PowerShell:

```powershell
$env:GOOGLE_API_KEY="your_gemini_api_key_here"
```

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

Frontend chạy tại `http://localhost:3000`.

## Docker Backend Option

Docker chỉ là tùy chọn chạy backend. FAISS chạy local trong container, không cần Milvus/etcd/minio.

```bash
cp .env.example .env
# Sửa .env và điền GOOGLE_API_KEY
docker compose up --build backend
```

Runtime files khi chạy Docker được mount vào `runtime/`.

## API Flow Hiện Tại

1. `POST /api/upload` với multipart field **`file`** để tạo `course_id`.
2. `GET /api/course/{course_id}/status` để poll đến khi `ready`.
3. Gọi các endpoint generation/chat qua FastAPI.
4. Mọi response AI phải có `citations`.

Các route chính:
- Health/management: `/api/health`, `/api/courses`, `/api/courses/all`, `DELETE /api/courses/{course_id}`.
- Upload/status: `/api/upload`, `/api/course/{course_id}/status`.
- AI sync: `/api/chat`, `/api/generate-course`, `/api/generate-summary`, `/api/generate-flashcards`, `/api/generate-quiz`, `/api/generate-slides`, `/api/generate-mindmap`, `/api/custom-prompt`.
- AI async: `/api/generate-course-async`, `/api/generate-summary-async`, `/api/generate-flashcards-async`, `/api/generate-quiz-async`, `/api/generate-slides-async`, `/api/generate-mindmap-async`, `/api/custom-prompt-async/{course_id}`.
- Saved content: `/api/course/{course_id}/summary`, `/flashcards`, `/questions`, `/slides`, `/mindmap`, `/study-guide`, `/audio`, `/files`, `/stats`.

## Known Integration Gaps

- Frontend upload UI hiện gửi field `files` nhiều file, trong khi backend `/api/upload` nhận một field `file`.
- Một số trang frontend chi tiết như `/course/[id]`, `/quiz/[id]`, `/flashcards/[id]`, `/slides/[id]` vẫn là placeholder.
- `src/frontend/src/app/layout.tsx` đang có duplicate imports cần dọn trong PR frontend riêng.
- Chưa có test suite source-level trong repo.

## Non-Negotiable Gates

1. **Citation-First:** Mọi output AI phải có `citations: [{page, source, chunk_id}]`.
2. **Traceability:** Citation phải trace được về chunk metadata trong FAISS/local index.
3. **No-Auth v1:** Không login/thanh toán/phân quyền trong Hackathon version.
4. **File validation:** Chỉ chấp nhận `.pdf`, `.docx`, `.txt`.
5. **Backend-only AI:** Frontend không gọi LLM trực tiếp.
