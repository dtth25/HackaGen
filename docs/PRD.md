# Product Requirements Document: HackaGen

## 1. Product Soul
- **Mục tiêu:** Biến một hoặc nhiều tài liệu PDF, DOCX, TXT thành một **Document-to-Study-Pack** kết nối 4 học liệu cốt lõi: Book (Study Guide PDF), Slide, Quiz và Vid.
- **Giá trị cốt lõi:** Giảm thời gian đọc hiểu và tự động hệ thống hóa kiến thức thành artifact học tập có thể đọc, trình chiếu, luyện tập và xem dạng video.
- **Đối tượng:** Học sinh, giáo viên, người tự học và nhóm làm nội dung đào tạo.

## 2. Current Source of Truth
Code hiện tại là source of truth cho project. Các tài liệu phải bám theo implementation hiện có:
- **Frontend:** Next.js App Router, React 19, Tailwind CSS v4, shadcn/base-ui, lucide-react.
- **Backend:** FastAPI, Python 3.11+, LangChain, dependency management bằng `uv`.
- **Vector DB:** Chroma local persistent DB là provider bắt buộc cho local/dev hackathon demo. FAISS chỉ còn là legacy reference/test path, không phải provider chính.
- **Persistence:** Local filesystem JSON/generated files: `books/`, `slides/`, `questions/`, `videos/`, cùng Chroma data trong `data/chroma/`.
- **AI:** OpenRouter-only. Runtime ưu tiên `openrouter/free`, sau đó fallback sang model paid cho quota, provider hoặc schema failure; embedding dùng model OpenRouter đã cấu hình.
- **Auth:** Auth v2 đã có trong code: Bearer JWT + HttpOnly cookie (`agy_session`), user ownership cho upload/generation/output, admin endpoints cho quản trị user.

## 3. Core User Flow
1. User đăng ký/đăng nhập, trừ các route health/demo public được đánh dấu rõ.
2. User upload một hoặc nhiều file `.pdf`, `.docx` hoặc `.txt`.
3. Backend validate từng file, lưu file, tạo `course_id`/`document_id`, xử lý cả bộ tài liệu ở background.
4. Backend parse text, clean/chunk tài liệu, tạo embeddings và lưu vào Chroma collection theo `document_id` và `user_id`.
5. User poll `/documents/{document_id}/status` hoặc `/api/course/{course_id}/status` đến khi `completed`/`ready`.
6. User mở Study Pack Dashboard hoặc gọi một trong 4 generation endpoint trực tiếp: Book, Slide, Quiz, Vid.
7. Frontend hiển thị artifact trong workspace; tạo output mới không làm mất output cũ.
8. User có thể tải Book PDF, Slide PPTX, Quiz answer-key PDF và Vid MP4 khi artifact đã tạo xong.

## 4. Non-Negotiable Constraints
- **Connected Study Pack:** Public product là dashboard học tập kết nối gồm Book (Study Guide PDF), Slide, Quiz, Vid, grounding/readiness và quality scores.
- **Four Direct Generation Endpoints:** Các endpoint sinh output trực tiếp và duy nhất là Book, Slide, Quiz, Vid.
- **No Additional Chats:** Không có chat tự do, custom prompt độc lập hoặc legacy output rời rạc ngoài hệ sinh thái Study Pack.
- **No Raw Public Source Metadata:** Public generation responses không trả raw/internal `page`, `source`, `chunk_id`, `citations` hoặc debug markers. `source_chunk_ids` được giữ cho grounding, và source panel có thể hiển thị `page` + excerpt sạch theo API contract.
- **Grounded Generation:** Output AI phải dựa trên chunks truy xuất từ Chroma/local vector index, sau bước lọc noisy/TOC/debug text.
- **Backend-only AI:** Frontend không gọi LLM trực tiếp; mọi AI flow đi qua FastAPI.
- **Auth & Ownership:** Upload/generation/output/delete yêu cầu active user; user thường chỉ thấy tài liệu của mình, admin có quyền quản trị/hỗ trợ.
- **File validation:** `/api/upload` chỉ nhận `.pdf`, `.docx`, `.txt`, không nhận file rỗng hoặc file quá 50MB mỗi file.

## 5. Public Product Surface
- **Study Pack Dashboard:** Tổng hợp Book (Study Guide PDF), Slide, Quiz, Vid, readiness, quality scores và grounding từ cùng một nguồn cấu trúc.
- **Book / Study Guide:** View theo chương/bài trên UI và file PDF tải xuống (endpoint sinh output trực tiếp `/api/generate-book`).
- **Slide:** Viewer từng slide và file PPTX tải xuống (endpoint sinh output trực tiếp `/api/generate-slide`).
- **Quiz:** Bộ câu hỏi MCQ tương tác (endpoint sinh output trực tiếp `/api/generate-quiz`); không hiện đáp án trước khi user nộp bài/review; có answer-key PDF tải xuống.
- **Vid:** Video dạng slide + voiceover, metadata JSON và MP4 tải xuống (endpoint sinh output trực tiếp `/api/generate-vid`); nếu render video lỗi phải trả trạng thái lỗi rõ ràng.

## 6. Known Implementation Notes
- API upload ưu tiên multipart field `files` cho multi-document; legacy field `file` vẫn được hỗ trợ.
- `course_id` hiện cũng là `document_id` cho flow local/dev.
- Chroma metadata vẫn được giữ nội bộ để retrieval/debug/ownership filtering. Không lộ raw metadata trong generation response.
- Các route legacy như `/api/chat`, `/api/custom-prompt`, `/api/generate-course`, `/api/generate-summary`, `/api/generate-flashcards`, `/api/generate-mindmap`, `/api/generate-podcast/{course_id}`, `/api/generate-study-guide/{course_id}` cùng mọi async generation route cũ phải trả về 404.
- Demo cho người dùng nên chạy production frontend bằng `npm run build && npm run start` để tránh Next.js dev indicator.
