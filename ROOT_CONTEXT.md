# Project Context: AI Course Generator

## 1. Product Soul (Tóm lược PRD)
- **Mục tiêu:** Biến tài liệu thô (PDF, DOCX, TXT) thành hệ sinh thái học tập đa phương tiện.
- **Giá trị cốt lõi:** Tiết kiệm thời gian đọc hiểu và hệ thống hóa kiến thức tự động.
- **Đối tượng:** Học sinh, giáo viên, người tự học.

## 2. Mandatory Tech Stack (Chốt theo code hiện tại)
- **Frontend:** Next.js 16.x App Router, React 19, Tailwind CSS v4, shadcn/base-ui, lucide-react.
- **Backend:** FastAPI, Python 3.11+, LangChain, dependency management bằng `uv`.
- **Vector DB:** FAISS local disk-based. Mỗi course lưu index tại `indices/faiss_{course_id}/` và metadata tại `indices/faiss_{course_id}.json`.
- **Memory Layer:** Local filesystem metadata/JSON. Chưa có Zep hoặc external session memory.
- **AI Models:** Google Gemini qua LangChain Google GenAI: `gemini-2.5-flash` cho LLM và `models/embedding-001` cho batch embeddings.

## 3. Guiding Principles & Constraints
- **Citation-First:** Mọi nội dung AI sinh ra phải kèm `citations` gồm `{page, source, chunk_id}`.
- **Traceability:** Citation phải trace được về metadata của chunk trong FAISS/local index.
- **No-Auth v1:** Không làm đăng nhập, thanh toán hoặc phân quyền trong phiên bản Hackathon.
- **Backend-only AI calls:** Frontend không gọi LLM trực tiếp; mọi AI flow đi qua FastAPI.
- **Agentic Workflow:** AI hỗ trợ viết code, con người/Lead giữ vai trò giám sát và thẩm định logic.

## 4. Core Pipeline (Theo code hiện tại)

```
[Upload] -> [Parse] -> [Chunk] -> [Embed] -> [FAISS] -> [Retrieve] -> [RAG] -> [Generate]
   |          |          |          |          |           |           |         |
   |          |          |          |          |           |           |         +-- Course
   |          |          |          |          |           |           |             Summary
   |          |          |          |          |           |           |             Flashcards
   |          |          |          |          |           |           |             Quiz
   |          |          |          |          |           |           |             Slides
   |          |          |          |          |           |           |             Mindmap
   v          v          v          v          v           v           v
 course_id  raw_text   chunks     vectors   local index  top_k      Gemini prompt
                                             + metadata             + citations
```

## 5. Non-Negotiable Gates (Tóm tắt cho agents)
1. **Mọi upload input phải validate format** - chỉ chấp nhận `.pdf`, `.docx`, `.txt`.
2. **Mọi output AI phải có trường `citations`** - mỗi citation phải trace được về chunk metadata trong FAISS/local index.
3. **Không được gọi LLM trực tiếp từ Frontend** - tất cả qua FastAPI.
4. **Backend chỉ dùng `uv`** để quản lý Python dependencies.
5. **Không thêm Auth/Payment trong v1** - tập trung Core AI Pipeline.
