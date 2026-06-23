# Architecture & Data Flow Design

## 1. System Topology

```
Client (Next.js App Router)
  |
  | fetch()
  v
FastAPI backend
  |
  +-- Document processing: PDF/DOCX/TXT -> LangChain Documents
  +-- Chunking: RecursiveCharacterTextSplitter
  +-- Embeddings: Gemini `models/embedding-001`
  +-- Vector store: FAISS local disk index
  +-- Generation: Gemini `gemini-2.5-flash`
  +-- Persistence: local JSON/generated files
```

## 2. Ingestion Pipeline

1. `POST /api/upload` nhận một file multipart field `file`.
2. Backend validate filename, extension, empty content và giới hạn 50MB.
3. File được lưu vào `uploads/`.
4. Backend tạo `course_id`, ghi metadata vào `questions/course_{course_id}_meta.json`.
5. Background thread parse và index tài liệu.

### Supported Files

| Type | Implementation |
|------|----------------|
| PDF | PyMuPDF (`fitz`), OCR fallback bằng pytesseract khi page không có text |
| DOCX | `python-docx` |
| TXT | built-in text read với UTF-8 ignore errors |

## 3. RAG Pipeline

```
raw documents
  -> text chunks
  -> metadata `{page, source_file, chunk_id, course_id}`
  -> Gemini embeddings
  -> FAISS index at `indices/faiss_{course_id}/`
  -> retriever top-k docs
  -> Gemini generation
  -> response + citations
```

Current chunking uses `RecursiveCharacterTextSplitter` with:
- `chunk_size=1200`
- `chunk_overlap=200`

Citation metadata is attached before indexing:
- `page`
- `source_file`
- `chunk_id`
- `course_id`

## 4. Course Management

`CourseManager` owns course lifecycle:
- Scans existing FAISS metadata files at startup.
- Lazy-loads FAISS indices on demand.
- Keeps an in-memory LRU cache of loaded courses.
- Persists course status and generated resources on local filesystem.

Course status values currently include:
- `pending`
- `ready`
- `failed`
- `unknown`

## 5. Generation Features

Generation is handled by `ResourceGenerator`, `MindmapGenerator` and `CustomProcessor`.

Supported current outputs:
- Course structure
- Summary
- Flashcards
- Quiz/questions
- Slides JSON
- Mind map JSON
- Study guide
- Podcast script/audio
- Custom prompt output

All AI generation endpoints must return citations when they produce AI content.

## 6. Storage Layout

Runtime folders are local and created by backend config when needed:

| Folder | Purpose |
|--------|---------|
| `uploads/` | Uploaded source files |
| `indices/` | FAISS indices and FAISS metadata |
| `questions/` | Course metadata, syllabus, questions |
| `guides/` | Summary and study guide markdown |
| `flashcards/` | Flashcard JSON |
| `mindmaps/` | Mind map JSON |
| `audio/` | Podcast script/audio |
| `tasks/` | Background task status |
| `custom_prompts/` | Custom prompt history |

## 7. Key Design Decisions

| Decision | Current Choice | Rationale |
|----------|----------------|-----------|
| Vector DB | FAISS local disk | Simple Hackathon setup, no external service required |
| AI provider | Gemini | Matches current code and env requirements |
| Memory | Local JSON/files | No auth/session service in v1 |
| API boundary | Frontend -> FastAPI -> LLM | Prevents client-side LLM key exposure |
| Citation | FAISS chunk metadata | Keeps AI output traceable to source document chunks |

## 8. Deprecated/Not Current

The current code does **not** use these as active stack:
- External vector service
- Zep session memory
- Claude/GPT-4o as primary model
- OpenAI embeddings as active embedding implementation
