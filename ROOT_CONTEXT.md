# Project Context: AI Course Generator

## 1. Product Soul
- **Mục tiêu:** Biến tài liệu thô (PDF, DOCX, TXT) thành một **Document-to-Study-Pack** có Study Guide/Book làm trung tâm, kèm Mindmap, Quiz, Flashcards, Summary và các output trình bày Slide/Vid.
- **Giá trị cốt lõi:** Tự động hệ thống hóa kiến thức thành artifact học tập có thể đọc, trình chiếu, luyện tập, ôn tập nhanh và xem dạng video.
- **Đối tượng:** Học sinh, giáo viên, người tự học và nhóm làm nội dung đào tạo.

## 2. Mandatory Tech Stack
- **Frontend:** Next.js App Router, React 19, Tailwind CSS v4, shadcn/base-ui, lucide-react.
- **Backend:** FastAPI, Python 3.11+, LangChain, dependency management bằng `uv`.
- **Vector DB:** Chroma local persistent DB là provider bắt buộc cho local/dev. Dữ liệu mặc định ở `data/chroma/`, collection `ai_course_chunks`. FAISS chỉ còn là legacy reference/test path.
- **Persistence:** Local filesystem JSON/generated files: `books/`, `slides/`, `questions/`, `videos/`, `mindmaps/`, `flashcards/`.
- **Auth:** JWT bearer token + HttpOnly cookie (`agy_session`); user ownership cho document/output, admin routes cho quản trị.
- **AI Models:** Google Gemini qua LangChain Google GenAI. Model routing dùng `GEMINI_*_MODEL`; embeddings dùng `GEMINI_EMBEDDING_MODEL` hoặc legacy `EMBEDDING_MODEL`.

## 3. Guiding Principles & Constraints
- **Connected Study Pack:** Public product là dashboard học tập kết nối, không phải tập hợp output rời rạc.
- **Four Direct Generation Endpoints:** Chỉ có 4 endpoint sinh output trực tiếp: Book, Slide, Quiz, Vid. Mindmap/Flashcards/Summary là thành phần course-scoped của Study Pack.
- **No Additional Chats:** Không có chat tự do hoặc custom prompt độc lập.
- **No Raw Public Source Metadata:** Không trả raw/internal `source`, `chunk_id`, `citations` hoặc debug markers trong generation responses. `source_chunk_ids` được giữ để grounding; source panel có thể hiển thị `page` + excerpt sạch.
- **Grounded Generation:** Nội dung AI phải dựa trên retrieved chunks từ Chroma/local index sau khi lọc noisy/TOC/debug text.
- **Backend-only AI calls:** Frontend không gọi LLM trực tiếp; mọi AI flow đi qua FastAPI.
- **Auth & Ownership:** Upload/generation/output/delete cần active user, trừ health/demo public được đánh dấu rõ.

## 4. Core Pipeline

```text
[Auth: JWT/Cookie] -> [Upload] -> [Parse] -> [Clean/Chunk] -> [Embed] -> [Chroma] -> [Retrieve] -> [Generate/Assemble]
        |               |          |             |             |          |             |              |
        |               |          |             |             |          |             |              +-- Study Pack Dashboard
        |               |          |             |             |          |             |              +-- Book (Study Guide PDF)
        |               |          |             |             |          |             |              +-- Slide (PPTX)
        |               |          |             |             |          |             |              +-- Quiz (Answer Key PDF)
        |               |          |             |             |          |             |              +-- Vid (MP4)
        v               v          v             v             v          v             v
     user_id       document_id  raw_text    clean chunks   vectors   local DB       top_k
```

## 5. Non-Negotiable Gates
1. **Upload validation** - chỉ chấp nhận `.pdf`, `.docx`, `.txt`, không file rỗng, không quá 50MB.
2. **Connected Study Pack** - Study Guide/Book, Mindmap, Quiz, Flashcards, Summary, readiness/quality/grounding phải xuất phát từ cùng nguồn cấu trúc.
3. **No additional chats** - không merge chat tự do, custom prompt độc lập hoặc legacy standalone generators.
4. **No raw public metadata leak** - không lộ raw `source`, `chunk_id`, `citations` hoặc debug markers trong generation responses; `source_chunk_ids` và source excerpt policy theo API contract.
5. **Backend-only AI** - tất cả LLM/embedding calls phải nằm ở backend.
6. **Auth & ownership** - protected APIs yêu cầu active user; regular user chỉ truy cập document/output của mình.
7. **Backend dùng `uv`** để quản lý Python dependencies.
