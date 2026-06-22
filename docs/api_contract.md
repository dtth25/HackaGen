# API Contract (v1.0)

## 1. Document Ingestion
- **POST `/api/upload`**
  - Input: `file: MultipartFile`
  - Output: `{"file_id": "uuid", "pages": 20, "status": "processed"}`

## 2. Course Generation
- **POST `/api/generate-course`**
  - Input: `{"file_id": "uuid", "user_prompt": "string"}`
  - Output: 
    ```json
    {
      "course_title": "string",
      "chapters": [
        { "id": 1, "title": "string", "lessons": ["string"] }
      ]
    }
  ],
  "total_slides": 10,
  "citations": [
    {"page": 5, "source": "tailieu.pdf", "chunk_id": "chunk_15"}
  ]
}
```

---

### 4.6. Generate Mind Map

Tạo bản đồ tư duy dạng cây từ nội dung tài liệu. Mind map được tổ chức theo cấu trúc **node** đệ quy với các trường `name` và `children`.

```
POST /api/generate-mindmap
```

**Request Body** (`GenerateMindmapRequest`):
```json
{
  "course_id": "abc123",
  "max_depth": 3
}
```


| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| course_id | string | required | ID của course |
| max_depth | integer | 2-5, optional, default 3 | Độ sâu tối đa của mind map |


**Response** (`MindmapResponse`):
```json
{
  "course_id": "abc123",
  "mindmap": {
    "central_topic": "Vật lý đại cương",
    "branches": [
      {
        "title": "Cơ học",
        "children": [
          {"title": "Động lực học", "children": []},
          {"title": "Công và năng lượng", "children": []}
        ]
      },
      {
        "title": "Nhiệt học",
        "children": []
      }
    ]
  },
  "citations": [
    {"page": 3, "source": "tailieu.pdf", "chunk_id": "chunk_10"},
    {"page": 20, "source": "tailieu.pdf", "chunk_id": "chunk_50"}
  ]
}
```


---

### 4.7. Custom Prompt 

Xử lý prompt tùy chỉnh của người dùng với hệ thống prompt 3 lớp:
1. **CORE**: System prompt cốt định (chống ảo giác, kiểm soát ngôn ngữ, độ dài)
2. **FORMAT**: Tự động phân loại prompt → 5 format: TABLE, LIST, EXPLAIN, JSON, CODE
3. **FEW-SHOT**: 4 ví dụ mẫu giúp LLM hiểu đúng format đầu ra

```
POST /api/custom-prompt
```

**Request Body** (`CustomPromptRequest`):
```json
{
  "course_id": "abc123",
  "prompt": "Tóm tắt tài liệu này trong 5 ý chính dành cho học sinh cấp 3"
}
```

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| course_id | string | required | ID của course |
| prompt | string | 1-2000 ký tự, required | Yêu cầu xử lý tùy chỉnh |

**Response** (`CustomPromptResponse`):
```json
{
  "course_id": "abc123",
  "prompt": "Tóm tắt tài liệu này trong 5 ý chính dành cho học sinh cấp 3",
  "prompt_type": "LIST",
  "result": "- Ý chính 1: ...\n- Ý chính 2: ...\n- Ý chính 3: ...\n- Ý chính 4: ...\n- Ý chính 5: ...",
  "citations": [
    {"page": 1, "source": "tailieu.pdf", "chunk_id": "chunk_1"},
    {"page": 3, "source": "tailieu.pdf", "chunk_id": "chunk_9"}
  ]
}
```

**Cơ chế phân loại prompt tự động**:

| Loại | Từ khóa kích hoạt | Format output | Temperature |
|------|-------------------|---------------|-------------|
| `TABLE` | "bảng", "so sánh", "đối chiếu", "thống kê", "tổng hợp" | Markdown table | 0.1 |
| `LIST` | "danh sách", "liệt kê", "các bước", "quy trình", "các ý chính" | Ordered/Unordered list | 0.2 |
| `EXPLAIN` | (default) — "giải thích", "phân tích", "trình bày" | Markdown sections | 0.3 |
| `JSON` | "json", "cấu trúc dữ liệu", "machine-readable", "parse" | Raw JSON array/object | 0.1 |
| `CODE` | "code", "ví dụ code", "implementation", "chạy thử" | Code block with language | 0.2 |

**Xử lý prompt mơ hồ**: Nếu prompt không rõ ràng, AI tự chọn format EXPLAIN và kết thúc câu trả lời bằng gợi ý: *"> 💡 Bạn có muốn tôi trình bày theo một format khác (bảng, danh sách, tóm tắt ngắn) không?"*

**Status Codes**:
- `200`: OK
- `404`: Không tìm thấy course
- `500`: Lỗi xử lý

**Lưu kết quả**: Mỗi lần chạy thành công sẽ lưu cặp file vào `custom_prompts/course_{id}/{timestamp}.json` và `.md`.

---

### 4.8. Generate Study Guide (Bonus)

```
POST /api/generate-study-guide
```

**Request Body** (`GenerateStudyGuideRequest`):
```json
{
  "course_id": "abc123"
}
```

**Response** (`StudyGuideResponse`):
```json
{
  "course_id": "abc123",
  "guide": "# Hướng dẫn ôn tập\n\n## Chương 1...",
  "filename": "study_guide_abc123.md",
  "citations": [
    {"page": 1, "source": "tailieu.pdf", "chunk_id": "chunk_1"}
  ]
}
```

---

### 4.9. Generate Syllabus (Bonus)

```
POST /api/generate-syllabus
```

**Request Body** (`GenerateSyllabusRequest`):
```json
{
  "course_id": "abc123"
}
```

**Response** (`SyllabusResponse`):
```json
{
  "course_id": "abc123",
  "syllabus": [
    {"title": "Chương 1", "description": "...", "duration": "2 buổi"},
    {"title": "Chương 2", "description": "...", "duration": "3 buổi"}
  ],
  "citations": [
    {"page": 1, "source": "tailieu.pdf", "chunk_id": "chunk_1"}
  ]
}
```

---

### 4.10. Generate Podcast Script (Bonus)

```
POST /api/generate-podcast
```

**Request Body** (`GeneratePodcastRequest`):
```json
{
  "course_id": "abc123"
}
```

**Response** (`PodcastScriptResponse`):
```json
{
  "course_id": "abc123",
  "script": [
    {"speaker": "host", "text": "Xin chào..."},
    {"speaker": "expert", "text": "Hôm nay chúng ta..."}
  ],
  "estimated_duration": "15 phút",
  "citations": [
    {"page": 1, "source": "tailieu.pdf", "chunk_id": "chunk_1"}
  ]
}
```

---

## 5. Generate Resources (Async)

Các endpoints bất đồng bộ — trả về `task_id` để polling. Phù hợp cho dữ liệu lớn, tránh timeout.

**Các async endpoints**:

| Method | Endpoint | Task Type |
|--------|----------|-----------|
| POST | `/api/generate-course-async` | course |
| POST | `/api/generate-summary-async` | summary |
| POST | `/api/generate-flashcards-async` | flashcards |
| POST | `/api/generate-quiz-async` | quiz |
| POST | `/api/generate-slides-async` | slides |
| POST | `/api/generate-mindmap-async` | mindmap |
| POST | `/api/custom-prompt-async` | custom_prompt |

**Request Body**: Giống hệt sync version tương ứng.

**Response** (`TaskResponse`):
```json
{
  "task_id": "task_abc123",
  "status": "processing"
}
```

---

## 6. Task Polling

Poll trạng thái của một background task.

```
GET /api/task/{task_id}
```

**Response** (`TaskPollResponse`):
```json
// Khi đang xử lý
{
  "task_id": "task_abc123",
  "status": "processing",
  "task_type": "flashcards",
  "course_id": "abc123",
  "created_at": "2025-01-01 12:00:00",
  "updated_at": "2025-01-01 12:02:00",
  "elapsed_seconds": 120,
  "result": null
}

// Khi hoàn thành
{
  "task_id": "task_abc123",
  "status": "completed",
  "task_type": "flashcards",
  "course_id": "abc123",
  "created_at": "2025-01-01 12:00:00",
  "updated_at": "2025-01-01 12:05:00",
  "elapsed_seconds": 300,
  "result": [
    {"question": "...", "answer": "..."}
  ]
}
```

**Các trạng thái**: `processing` → `completed` | `failed`

Khi `status = "failed"`, response có thêm field `error`:
```json
{
  "task_id": "task_abc123",
  "status": "failed",
  "error": "Course 'abc' chưa sẵn sàng.",
  ...
}
```

---

## 7. Get Saved Content

Truy xuất nội dung đã được generate từ trước (đã lưu vào ổ đĩa).

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/course/{course_id}/course` | Lấy khóa học đã lưu |
| GET | `/api/course/{course_id}/summary` | Lấy summary đã lưu |
| GET | `/api/course/{course_id}/flashcards` | Lấy flashcards đã lưu |
| GET | `/api/course/{course_id}/questions` | Lấy questions đã lưu |
| GET | `/api/course/{course_id}/slides` | Lấy slides đã lưu |
| GET | `/api/course/{course_id}/mindmap` | Lấy mind map đã lưu |
| GET | `/api/course/{course_id}/study-guide` | Lấy study guide |
| GET | `/api/course/{course_id}/syllabus` | Lấy syllabus đã lưu |
| GET | `/api/course/{course_id}/audio` | Lấy podcast script |
| GET | `/api/course/{course_id}/custom-prompts` | Lấy lịch sử custom prompt |
| GET | `/api/course/{course_id}/files` | List tất cả files đã generate |
| GET | `/api/course/{course_id}/stats` | Thống kê course |

**Status Codes**: `404` nếu chưa có nội dung tương ứng.

### 7.1. List All Course Files

```
GET /api/course/{course_id}/files
```

**Response**:
```json
{
  "course_id": "abc123",
  "files": {
    "course": "courses/course_abc123/course.json",
    "summary": "courses/course_abc123/summary.json",
    "flashcards": "flashcards/course_abc123_flashcards.json",
    "questions": "questions/course_abc123_questions.json",
    "slides": ["slides_chuong_1.json"],
    "mindmap": "mindmaps/course_abc123_mindmap.json",
    "guides": ["study_guide.md"],
    "audio": ["podcast_script.json"]
  }
}
```

### 7.2. Get Course Stats

```
GET /api/course/{course_id}/stats
```

**Response**:
```json
{
  "course_id": "abc123",
  "status": "ready",
  "generated_at": "2025-01-01 12:05:00",
  "total_questions": 20,
  "total_flashcards": 15,
  "total_slides": 10,
  "has_course": true,
  "has_summary": true,
  "has_study_guide": true,
  "has_mindmap": false,
  "has_podcast": true
}
```

### 7.3. List Custom Prompt History

```
GET /api/course/{course_id}/custom-prompts
```

**Response**:
```json
{
  "course_id": "abc123",
  "custom_prompts": [
    {
      "filename": "20260622_212020.json",
      "prompt": "Tóm tắt tài liệu này trong 5 ý chính",
      "prompt_type": "LIST",
      "created_at": "2026-06-22T21:20:20"
    },
    {
      "filename": "20260622_213659.json",
      "prompt": "So sánh cơ học cổ điển và lượng tử",
      "prompt_type": "TABLE",
      "created_at": "2026-06-22T21:36:59"
    }
  ],
  "total": 2
}
```

---

## 8. Tổng hợp Endpoints

### 8.1. Health & Management (4)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/health` | Health check |
| GET | `/api/courses` | List course IDs |
| GET | `/api/courses/all` | List courses + metadata |
| DELETE | `/api/courses/{course_id}` | Xóa course |

### 8.2. Upload (2)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/upload` | Upload file, tạo course |
| GET | `/api/course/{course_id}/status` | Check processing status |

### 8.3. Chat (1)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/chat` | Chat với course (RAG) |

### 8.4. Generate — Sync (10)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/generate-course` | Tạo khóa học |
| POST | `/api/generate-summary` | Tạo tóm tắt |
| POST | `/api/generate-flashcards` | Tạo flashcards |
| POST | `/api/generate-quiz` | Tạo câu hỏi MCQ |
| POST | `/api/generate-slides` | Tạo slides |
| POST | `/api/generate-mindmap` | Tạo mind map |
| POST | `/api/custom-prompt` | Xử lý prompt tùy chỉnh |
| POST | `/api/generate-study-guide` | Tạo study guide |
| POST | `/api/generate-syllabus` | Tạo syllabus |
| POST | `/api/generate-podcast` | Tạo podcast script |

### 8.5. Generate — Async (7)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/generate-course-async` | Course background |
| POST | `/api/generate-summary-async` | Summary background |
| POST | `/api/generate-flashcards-async` | Flashcards background |
| POST | `/api/generate-quiz-async` | Quiz background |
| POST | `/api/generate-slides-async` | Slides background |
| POST | `/api/generate-mindmap-async` | Mind map background |
| POST | `/api/custom-prompt-async` | Custom prompt background |

### 8.6. Task (1)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/task/{task_id}` | Poll task status |

### 8.7. Get Saved Content (11)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/course/{course_id}/course` | Lấy course đã lưu |
| GET | `/api/course/{course_id}/summary` | Lấy summary đã lưu |
| GET | `/api/course/{course_id}/flashcards` | Lấy flashcards |
| GET | `/api/course/{course_id}/questions` | Lấy questions |
| GET | `/api/course/{course_id}/slides` | Lấy slides |
| GET | `/api/course/{course_id}/mindmap` | Lấy mind map |
| GET | `/api/course/{course_id}/study-guide` | Lấy study guide |
| GET | `/api/course/{course_id}/syllabus` | Lấy syllabus |
| GET | `/api/course/{course_id}/audio` | Lấy podcast script |
| GET | `/api/course/{course_id}/custom-prompts` | Lấy lịch sử custom prompt |
| GET | `/api/course/{course_id}/files` | List tất cả files |
| GET | `/api/course/{course_id}/stats` | Thống kê course |

**Tổng cộng**: **37 endpoints** (4 + 2 + 1 + 10 + 7 + 1 + 12).

---

## 9. Flow khuyến nghị cho Frontend

### 9.1. Upload & tạo course

```
POST /api/upload (file)
  → nhận course_id + status: "processing"
  → GET /api/course/{course_id}/status (poll mỗi 2s)
  → status: "ready" → có thể chat & generate
```

### 9.2. Generate nội dung

```
Option A (sync — nhanh, dữ liệu nhỏ):
  POST /api/generate-flashcards (body: {course_id, count})
  → nhận kết quả ngay + citations

Option B (async — tránh timeout cho dữ liệu lớn):
  POST /api/generate-flashcards-async (body: {course_id, count})
  → nhận task_id
  → GET /api/task/{task_id} (poll mỗi 2-3s)
  → status: "completed" → lấy result từ task
```

### 9.3. Lấy lại nội dung cũ

```
GET /api/course/{course_id}/flashcards
GET /api/course/{course_id}/questions
GET /api/course/{course_id}/summary
...
```

### 9.4. Xóa course

```
DELETE /api/courses/{course_id}
