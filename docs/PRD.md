# Product Requirements Document: AI Course Generator

## 1. Product Soul
- **Mục tiêu:** Biến tài liệu thô (PDF, DOCX, TXT) thành nội dung học tập có cấu trúc: khóa học, tóm tắt, flashcards, quiz, slides, mind map, study guide, podcast script và custom prompt.
- **Giá trị cốt lõi:** Giảm thời gian đọc hiểu, tự động hệ thống hóa kiến thức và luôn giữ khả năng kiểm chứng bằng citation.
- **Đối tượng:** Học sinh, giáo viên, người tự học và nhóm làm nội dung đào tạo.

## 2. Current Source of Truth
Code hiện tại là source of truth cho project. Các tài liệu phải bám theo implementation hiện có:
- **Frontend:** Next.js App Router, Tailwind CSS, shadcn/base-ui, lucide-react.
- **Backend:** FastAPI, Python 3.11+, LangChain, `uv`.
- **Vector DB:** FAISS local disk-based.
- **Persistence/Memory:** Local filesystem JSON và generated files.
- **AI:** Gemini `gemini-2.5-flash` và batch embeddings bằng `models/embedding-001`.

## 3. Core User Flow
1. User upload một file `.pdf`, `.docx` hoặc `.txt`.
2. Backend validate file, lưu file, tạo `course_id`, xử lý tài liệu ở background.
3. Backend parse text, chunk tài liệu, gắn metadata citation, tạo embeddings và lưu FAISS index.
4. User poll `/api/course/{course_id}/status` đến khi `ready`.
5. User gọi các endpoint AI qua FastAPI để tạo course/summary/flashcards/quiz/slides/mindmap/custom output.
6. Mọi AI response phải trả về `citations`.

## 4. Non-Negotiable Constraints
- **Citation-First:** AI output phải có `citations: [{page, source, chunk_id}]`.
- **Traceability:** Nội dung AI phải dựa trên retrieved chunks và trace được về FAISS metadata.
- **No-Auth v1:** Không đăng nhập, thanh toán hoặc phân quyền trong Hackathon version.
- **Backend-only AI:** Frontend không gọi Gemini/LLM trực tiếp.
- **File validation:** `/api/upload` chỉ nhận `.pdf`, `.docx`, `.txt`, không nhận file rỗng hoặc file quá 50MB.

## 5. Known Implementation Notes
- API upload hiện nhận **một file** bằng multipart field `file`.
- Frontend hiện có gap integration: upload UI đang gửi field `files` nhiều file, chưa khớp backend.
- Một số docs cũ từng nhắc Milvus/Zep/Claude/GPT-4o; các stack đó không còn là implementation hiện tại.
