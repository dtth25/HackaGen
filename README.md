# DTTH-Hackathon-2026 AI Course Generator

Biến tài liệu thô (PDF, DOCX, TXT) thành hệ sinh thái học tập đa phương tiện — bài học, tóm tắt, flashcards, quiz, slide, mindmap — tự động bằng AI.

## Features

| Tính năng | Mô tả |
|-----------|-------|
| 📄 Upload tài liệu | Hỗ trợ PDF, DOCX, TXT — trích xuất nội dung tự động |
| 📚 Tạo khóa học | Sinh cấu trúc khóa học gồm chương, bài học từ tài liệu |
| 📝 Tạo bài học | Từng bài học có giới thiệu, giải thích, key points, tóm tắt |
| ✂️ Tạo tóm tắt | Tóm tắt ngắn / chi tiết / danh sách ý chính |
| 🃏 Tạo flashcard | Mặt trước / mặt sau kèm trạng thái ghi nhớ |
| ❓ Tạo quiz | Trắc nghiệm có đáp án và giải thích |
| 📽️ Tạo slide | Nội dung thuyết trình có cấu trúc rõ ràng |
| 🧠 Tạo mind map | Sơ đồ tư duy hệ thống hóa kiến thức |
| 💬 Prompt tùy chỉnh | Yêu cầu AI xử lý tài liệu theo nhu cầu riêng |

## Tech Stack

| Layer | Công nghệ |
|-------|-----------|
| Frontend | Next.js 14+ (App Router), Tailwind CSS |
| Backend | FastAPI (Python 3.11+) |
| Vector DB | Milvus (RAG + Citation) |
| Memory | Zep (Session context) |
| Embedding | OpenAI text-embedding-3-small |
| Generation | Google Gemini (free tier) |

## Directory Structure

```
├── docs/                        # Tài liệu thiết kế
│   ├── PRD.md                   # Product Requirements Document
│   ├── api_contract.md          # API Contract (v1.0)
│   └── architecture_design.md   # Architecture & Data Flow
├── src/
│   ├── backend/                 # FastAPI application
│   │   ├── main.py              # Entry point
│   │   ├── services/            # Business logic
│   │   │   ├── document_processor.py  # PDF/DOCX/TXT parsing
│   │   │   ├── chunking_engine.py     # Semantic chunking
│   │   │   ├── embedding_service.py   # OpenAI embedding
│   │   │   ├── milvus_service.py      # Vector DB operations
│   │   │   ├── memory_service.py      # Zep session
│   │   │   └── llm_service.py         # Gemini generation
│   │   └── routers/             # API endpoints
│   ├── frontend/                # Next.js application
│   └── shared/                  # Shared types/constants
├── tests/                       # Test suites
├── AGENTS.md                    # Agent orchestration protocol
├── ROOT_CONTEXT.md              # Project context for AI agents
└── .env.example                 # Environment variables template
```

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (cho Milvus local)
- API keys: OpenAI (embedding) + Google Gemini (generation)

### 1. Clone & Setup Milvus

```bash
# Khởi động Milvus standalone bằng Docker
docker compose -f docker-compose.yml up -d
```

Nếu chưa có file `docker-compose.yml`, tạo mới:
```yaml
version: '3.5'
services:
  etcd:
    container_name: milvus-etcd
    image: quay.io/coreos/etcd:v3.5.5
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
      - ETCD_QUOTA_BACKEND_BYTES=4294967296
    volumes:
      - ${DOCKER_VOLUME_DIRECTORY:-.}/volumes/etcd:/etcd
  minio:
    container_name: milvus-minio
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z
    volumes:
      - ${DOCKER_VOLUME_DIRECTORY:-.}/volumes/minio:/minio_data
    command: minio server /minio_data
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
  standalone:
    container_name: milvus-standalone
    image: milvusdb/milvus:v2.3.3
    command: ["milvus", "run", "standalone"]
    ports:
      - "19530:19530"
    volumes:
      - ${DOCKER_VOLUME_DIRECTORY:-.}/volumes/milvus:/var/lib/milvus
    depends_on:
      - etcd
      - minio

networks:
  default:
    name: milvus
```

### 2. Backend Setup

```bash
cd src/backend

# Tạo virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

# Cài uv package manager
pip install uv

# Cài dependencies
uv pip install -r requirements.txt

# Copy & sửa .env
cp ../../.env.example .env
# Điền API key OpenAI và Gemini vào .env

# Chạy server
uvicorn main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd src/frontend
npm install
npm run dev
```

Mở `http://localhost:3000`

## Usage

### Ví dụ: Upload tài liệu và tạo khóa học

```bash
# 1. Upload file
curl -X POST http://localhost:8000/api/upload \
  -F "file=@tailieu.pdf"

# Response:
# {
#   "file_id": "abc123",
#   "filename": "tailieu.pdf",
#   "pages": 42,
#   "status": "success"
# }

# 2. Tạo khóa học
curl -X POST http://localhost:8000/api/generate-course \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "abc123",
    "user_prompt": "Tạo khóa học gồm 5 chương",
    "target_audience": "sinh viên đại học"
  }'

# Response:
# {
#   "course": {
#     "title": "...",
#     "chapters": [...],
#     "citations": [{"page": 3, "source": "tailieu.pdf"}]
#   }
# }
```

## API Endpoints

| Method | Endpoint | Chức năng |
|--------|----------|-----------|
| POST | `/api/upload` | Upload tài liệu (PDF/DOCX/TXT) |
| POST | `/api/generate-course` | Tạo khóa học |
| POST | `/api/generate-summary` | Tạo bản tóm tắt |
| POST | `/api/generate-flashcards` | Tạo flashcard |
| POST | `/api/generate-quiz` | Tạo quiz |
| POST | `/api/generate-slides` | Tạo nội dung slide |
| POST | `/api/generate-mindmap` | Tạo bản đồ tư duy |
| POST | `/api/custom-prompt` | Xử lý prompt tùy chỉnh |
| GET  | `/health` | Health check |

## Non-Negotiable Gates

1. **Citation-First:** Mọi output AI phải có trường `citations` trace được về chunk trong Milvus.
2. **No-Auth v1:** Không login/thanh toán — tập trung Core AI Pipeline.
3. **File validation:** Chỉ chấp nhận `.pdf`, `.docx`, `.txt`.
4. **Backend call only:** Frontend không gọi LLM trực tiếp, mọi request qua FastAPI.

## Development Workflow

Xem chi tiết tại [`AGENTS.md`](AGENTS.md) — quy trình phối hợp giữa các vai (Lead, Backend, Frontend, QA).

1. **Backend Dev** viết API spec & implementation → tạo PR
2. **Frontend Dev** tích hợp UI & kiểm tra integration → tạo PR
3. **QA Dev** chạy test suite → report kết quả
4. **Lead** review tổng thể → Approve / Request changes / Reject
5. Chỉ sau khi Lead approve, PR mới được merge

## Contributing

1. Fork repository
2. Tạo branch mới: `git checkout -b feature/ten-tinh-nang`
3. Commit message bằng tiếng Anh (theo chuẩn open-source)
4. Push và tạo Pull Request
5. Chờ Lead review và approve trước khi merge

## Roadmap

### v1.0 (Hackathon)
- [x] Upload & parse PDF/DOCX/TXT
- [x] Tạo khóa học, bài học, tóm tắt
- [x] Tạo flashcard, quiz, slide, mind map
- [x] Prompt tùy chỉnh
- [ ] Citation-First RAG pipeline hoàn chỉnh

### v2.0 (Future)
- [ ] Đăng nhập tài khoản
- [ ] Lưu lịch sử khóa học
- [ ] Export PDF / PowerPoint
- [ ] Hỗ trợ đa ngôn ngữ
- [ ] Dashboard cho giáo viên

## License

MIT License — Xem file [LICENSE](LICENSE) để biết chi tiết.

---

**Built with ❤️ by DTTH Team — Hackathon 2026**