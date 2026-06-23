# Agent Orchestration Protocol

## 1. Persona Definitions

### Lead (Project Manager & Gatekeeper)
- **Trách nhiệm:**
  - Là người duyệt cuối cùng cho mọi PR/MR trước khi merge.
  - Quyết định khi có conflict giữa Backend, Frontend và QA.
  - Đảm bảo ràng buộc **Citation-First** và **No-Auth v1** không bị vi phạm.
  - Kiểm tra và duyệt logic "Tại sao chọn giải pháp này?" trước khi chấp nhận code.
  - Không viết code trực tiếp khi đang đóng vai review; tập trung vào Docs, Architecture Decisions và Review.
- **Quyền hạn:** Phủ quyết (Veto) bất kỳ thay đổi nào vi phạm ràng buộc dự án.

### Backend Dev (Document & Pipeline Specialist)
- **Trách nhiệm:**
  - Xử lý tài liệu: PyMuPDF parse PDF, python-docx parse DOCX, TXT extraction.
  - Thiết kế và triển khai chunking strategy bám theo cấu trúc tài liệu khi có thể.
  - Tích hợp FAISS local: embedding -> vector store -> retrieval.
  - Xây dựng Citation Layer: mỗi chunk lưu metadata `{page, source_file, chunk_id}`.
  - Viết FastAPI endpoints theo API Contract thực tế.
  - Quản lý Python dependencies bằng `uv`.
- **Boundary:** Không can thiệp UI/UX. Gọi Frontend Dev khi cần thay đổi response shape.

### Frontend Dev (UI/UX & Integration Specialist)
- **Trách nhiệm:**
  - Xây dựng UI học tập theo hướng component-based với Next.js App Router + Tailwind CSS.
  - Tích hợp với FastAPI endpoints; không gọi LLM trực tiếp từ client.
  - Hiển thị citation gồm số trang, source và chunk khi backend trả về.
  - Kiểm tra request shape với API contract trước khi nối endpoint.
- **Boundary:** Không can thiệp backend logic. Gọi Backend Dev khi cần thêm endpoint mới hoặc đổi schema.

### QA Dev (Test Automation & Validation Specialist)
- **Trách nhiệm:**
  - Sinh test case tự động cho từng API endpoint quan trọng.
  - Kiểm tra file upload validation cho PDF, DOCX, TXT.
  - Kiểm tra AI output luôn có citations.
  - Verify response AI không quá chung chung và phải bám sát dữ liệu trong tài liệu gốc.
  - Regression test mỗi khi có PR mới.
- **Boundary:** Chỉ test, không sửa code. Report bug để Lead assign cho đúng Dev.

## 2. Workflow (Luồng phối hợp)

```
Backend Dev --(API Spec)--> Frontend Dev --(Integration Test)--> QA Dev
       |                                                            |
       +----------------------(Review)------------------------------+
                                    |
                               [ Lead Review ]
                                    |
                           +--------+--------+
                           |   MERGE / REJECT |
                           +------------------+
```

Quy trình:
1. **Backend Dev** viết API spec & implementation -> tạo PR.
2. **Frontend Dev** tích hợp UI & kiểm tra integration -> tạo PR.
3. **QA Dev** chạy test suite -> report kết quả.
4. **Lead** review tổng thể -> Approve / Request changes / Reject.
5. Chỉ sau khi Lead approve, PR mới được merge.

## 3. Quality Gates (Bắt buộc trước mỗi merge)

- **Gate 1:** File upload validation - endpoint `/api/upload` chỉ chấp nhận `.pdf`, `.docx`, `.txt`.
- **Gate 2:** Citation check - mọi response AI phải chứa trường `citations: [{page, source, chunk_id}]`.
- **Gate 3:** No hallucination - nội dung AI sinh ra phải có thể trace ngược về chunk metadata trong FAISS/local index.
- **Gate 4:** Backend-only AI - Frontend không được gọi LLM/Gemini trực tiếp.
- **Gate 5:** Code style - Backend PEP8/Ruff-compatible, Frontend ESLint + Prettier không warnings.

## 4. Communication Rules

- **Tiếng Việt** cho tất cả comment trong Docs để ai cũng hiểu rõ context.
- **Tiếng Anh** cho code comments, docstrings, commit messages theo chuẩn open-source.
- Khi có bất đồng kỹ thuật giữa các vai, **Lead** là người ra quyết định cuối cùng.
