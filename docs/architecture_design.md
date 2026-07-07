# Architecture Design

## 1. System Overview

```text
Frontend (Next.js)
  -> FastAPI Backend (Auth Layer: Bearer JWT + HttpOnly Cookie)
  -> Document Processor
  -> VectorStore Provider (Chroma Local DB by default, FAISS legacy reference)
  -> ResourceGenerator
  -> Local Generated Artifacts
```

Public product surface là **Document-to-Study-Pack** với Study Pack Dashboard kết nối 4 direct generation endpoints (Book/Study Guide, Slide, Quiz, Vid) cùng các course-scoped outputs trong Study Pack:
- Study Guide PDF (Book)
- Mindmap (3-level interactive, course-scoped)
- Quiz
- Flashcards (course-scoped)
- High-yield summary (course-scoped)
- Slide & Vid (output trực tiếp bổ sung)

## 2. Upload & Indexing Flow

1. Frontend gửi `POST /api/upload` với multipart field `files` cho một hoặc nhiều tài liệu.
2. Backend vẫn hỗ trợ legacy field `file` cho single-file client cũ.
3. Backend validate extension, empty file và size <= 50MB mỗi file.
4. Backend lưu files vào `uploads/{course_id}/`, tạo `course_id`, ghi metadata vào `questions/course_{course_id}_meta.json`.
5. Background thread parse text từng tài liệu bằng document processor.
6. Text được chunk, embed bằng Gemini embeddings và lưu vào Chroma collection `ai_course_chunks` theo `course_id`.
7. Khi index sẵn sàng, status chuyển thành `ready`.

## 3. Generation Flow

```text
course_id
  -> load configured vectorstore
  -> retrieve top-k chunks from the full corpus
  -> clean internal extraction markers
  -> prompt Gemini
  -> normalize/fallback
  -> save artifact
  -> return public response
```

Resource generation nằm trong `ResourceGenerator`:
- `generate_book`
- `generate_slides_v2`
- `generate_quiz_v2`
- `generate_vid`
- `generate_mindmap` / `build_mindmap_from_book` (course-scoped trong Study Pack)

Vector metadata vẫn được giữ nội bộ cho retrieval/debug/ownership filtering, nhưng public generation response policy là "không trả raw metadata" (không lộ page, source, chunk_id, citations).

### 3.1 Mindmap Generation Flow

Mindmap không được tạo trực tiếp từ raw chunks. Pipeline ưu tiên theo thứ tự:

```text
clean chunks (context_cleaner)
  -> book plan / teaching notes (đã lưu, hoặc tạo mới)
  -> build_mindmap_from_book (3-level: chapter -> lesson -> concept/formula/example/warning/exercise)
  -> quality gate (_evaluate_mindmap_quality_gate)
  -> mindmap JSON (root/nodes/edges/quality_report)
  -> frontend render (InteractiveMindmapCanvas, lazy-loaded)
```

- `GET /api/course/{course_id}/mindmap`: trả mindmap đã lưu, hoặc build từ book plan (không gọi LLM).
- `POST /api/course/{course_id}/mindmap/regenerate`: thử LLM generation từ clean chunks (`MINDMAP_GENERATION_PROMPT`) trước, fallback về book plan, rồi fallback về shallow mindmap (`generate_fallback_shallow_mindmap`) khi context không đủ.
- Quality gate reject/hạ điểm khi phát hiện: `Contents`/`Mục lục`, dot leaders, số trang thô làm tiêu đề, debug markers (`BẮT ĐẦU DỮ LIỆU`, `KẾT THÚC DỮ LIỆU`, `MÃ ĐỊNH DANH TRANG`, `NỘI DUNG:`), generic filler (`Ý chính`, `Ghi nhớ ý chính`), hoặc node quan trọng thiếu `source_chunk_ids`.
- Frontend: `/mindmap/[id]` dynamic-imports `InteractiveMindmapCanvas` với `ssr:false` (không load lên dashboard chính) để giữ nhẹ cho máy 8GB RAM; không dùng thư viện graph nặng (d3/react-flow/cytoscape) — cây được vẽ bằng CSS/flexbox thuần với zoom/pan, search, filter theo `type`/`importance`, expand/collapse, panel chi tiết node, và export JSON/PNG.

## 4. Backend Modules

| Module | Responsibility |
| --- | --- |
| `backend.main` | FastAPI routes, validation, response shape |
| `backend.services.course_gen` | Course lifecycle, lazy loading, LRU cache |
| `backend.services.doc_processor` | PDF/DOCX/TXT extraction |
| `backend.services.resource_gen` | Book, Mindmap, Slide, Quiz, Vid generation and artifact export |
| `backend.services.mindmap_manager` | Course-scoped 3-level mindmap generation, quality gate, fallback handling |
| `backend.services.flashcards_manager` | Course-scoped flashcard deck assembly and regeneration |
| `backend.vector_db.manager` | Provider selection for Chroma/FAISS |
| `backend.vector_db.chroma_store` | Chroma create/load/list/drop and retrieval |
| `backend.vector_db.faiss_manager` | Legacy FAISS create/load/list/drop |
| `backend.core.prompts` | Prompt templates for 4 outputs |
| `backend.core.config` | Paths, model factories, utility helpers |

## 5. Local Storage

| Path | Purpose |
| --- | --- |
| `uploads/{course_id}/` | Original uploaded files for one corpus |
| `data/chroma/` | Chroma persistent local DB |
| `indices/chroma_{course_id}.json` | Chroma preprocessing metadata |
| `indices/faiss_{course_id}/` | Legacy FAISS index when `VECTOR_DB_PROVIDER=faiss` |
| `indices/faiss_{course_id}.json` | Legacy FAISS metadata |
| `questions/course_{course_id}_meta.json` | Course lifecycle metadata |
| `questions/course_{course_id}_questions.json` | Quiz JSON |
| `questions/course_{course_id}_answer_key.pdf` | Quiz answer key PDF |
| `books/course_{course_id}_book.json` | Book JSON |
| `books/course_{course_id}_book.pdf` | Book PDF |
| `mindmaps/course_{course_id}_mindmap.json` | Mindmap JSON (root/nodes/edges/quality_report) |
| `flashcards/course_{course_id}_flashcards.json` | Flashcards JSON deck |
| `slides/course_{course_id}_slides.json` | Slide JSON |
| `slides/course_{course_id}_slides.pptx` | Slide PPTX |
| `videos/course_{course_id}/vid.json` | Vid metadata |
| `videos/course_{course_id}/vid.mp4` | Vid MP4 |

## 6. Architecture Decisions

| Decision | Choice | Reason |
| --- | --- | --- |
| Public outputs | Book, Slide, Quiz, Vid | Hackathon scope rõ, ít phân tán |
| Multi-document | One `course_id` per uploaded corpus | User cần tạo học liệu từ nhiều tài liệu cùng lúc |
| AI boundary | Frontend -> FastAPI -> LLM | Không expose API key ở client |
| Retrieval | Chroma local default, FAISS legacy | Dễ chạy demo, không cần Milvus/external vector DB |
| Artifact export | Book PDF, Slide PPTX, Quiz key PDF, Vid MP4 | File tải xuống khớp đúng 4 output public |
| Public metadata | Không trả page/source/chunk | Product mới không hiển thị raw source metadata trong generation response |
| Auth | Auth v2 đã có (JWT Bearer + HttpOnly Cookie `agy_session`) | Bảo mật API, phân định ownership tài liệu/output giữa regular user và admin |
