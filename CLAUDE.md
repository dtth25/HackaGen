# CLAUDE.md — HackaGen

> Auto-load mỗi session. Giữ NGẮN — đây là nguồn context duy nhất. Runbook chi tiết ở [`README.md`](./README.md).

## North star
NotebookLM-clone, **chỉ** nhận Docs (`.pdf/.docx/.txt`) → xuất **Study Pack** kết nối: **Book** (Study Guide PDF), **Slide** (PPTX), **Quiz** (answer-key PDF), **Vid** (MP4). Thẩm mỹ chuẩn GAFAM/NotebookLM — sạch, kỷ luật, **no AI slop**.

## Stack (cách run đầy đủ: README.md)
- **FE**: Next.js App Router (⚠️ bản mới nhiều breaking change — đọc `node_modules/next/dist/docs/` trước khi code Next), React 19, Tailwind v4 (CSS-first, token trong `globals.css` qua `@theme inline`), shadcn/base-ui, lucide. Dev: `npm run dev` trong `src/frontend`.
- **BE**: FastAPI, Python 3.11+, LangChain, deps bằng `uv`. Chạy từ `src/backend/`: `uv run --project . uvicorn main:app --reload --port 8000` (không cd lên `src` — `pyproject.toml` không có `[build-system]` nên `app.*` chỉ resolve đúng cwd).
- **Vector DB**: Chroma local (`data/chroma/`, collection `ai_course_chunks`). FAISS chỉ là legacy.
- **AI**: OpenRouter-only. Mỗi call thử `openrouter/free` một lần, rồi fallback âm thầm sang model paid khi quota/provider/schema lỗi; frontend không biết nhà cung cấp.
- **Auth**: JWT bearer + HttpOnly cookie `agy_session`; user ownership + admin routes.

## Product invariants — "done" = KHÔNG vi phạm mấy điều này
1. **Connected Study Pack**: Book/Slide/Quiz/Vid + readiness/quality/grounding cùng 1 nguồn cấu trúc.
2. **4 generation endpoints duy nhất**: `/api/generate-{book,slide,quiz,vid}`. Không thêm generator lẻ.
3. **No additional chats**: không chat tự do / custom prompt độc lập.
4. **No raw metadata leak**: response không lộ raw `source`/`chunk_id`/`citations`/debug. `source_chunk_ids` giữ cho grounding; source panel chỉ `page` + excerpt sạch.
5. **Grounded**: output dựa trên retrieved chunks sau khi lọc noise/TOC.
6. **Backend-only AI**: FE không gọi LLM trực tiếp; mọi AI flow qua FastAPI.
7. **Auth & Ownership**: protected API cần active user; user thường chỉ thấy của mình, admin quản trị.
8. **Upload**: chỉ `.pdf/.docx/.txt`, không rỗng, ≤ 50MB/file.

## Integration rules load-bearing (đừng phá)
- **Download có auth**: mọi URL tải (PDF/PPTX/MP4…) phải kèm `?token=<jwt>`; `deps.py get_current_user` đọc token từ `query_params`. KHÔNG dùng `<a download>` trực tiếp tới API.
- **Polling**: resource ở `processing` → FE tự poll 3–5s tới `ready`/`error` rồi dừng, không cần reload.
- **Image-based slides**: mỗi slide render PNG/JPEG (ReportLab→PyMuPDF); viewer chỉ phát mảng ảnh; PPTX/PDF nhúng chính bức ảnh đó → không lệch font.
- **Expand/Collapse**: mọi tab học liệu có nút Mở rộng/Thu gọn viewport.

## Design system (TÁI DÙNG, đừng bịa class mới)
- **Elevation**: `shadow-[var(--shadow-xs|sm|md)]` (đừng dùng ring / shadow-lg rời rạc).
- **Motion**: `--duration-fast` (150ms) / `--duration-base` (200ms), `--ease-standard`.
- **Accent**: `#2454c4` (light) / `#7aa6f0` (dark).
- **`stage-*` tokens**: khu trình chiếu slide — **cố tình LUÔN tối** bất kể theme (như video player), KHÔNG phải bug.
- **Layout**: `CONTAINER_WIDE` / `CONTAINER_NARROW` (`src/frontend/src/lib/layout.ts`).
- **States dùng chung**: `EmptyState` / `ErrorState` (`components/ui/`). `EmptyState` có prop `expandable` (bật cho coming-soon, tắt cho CTA thật).

## Reality (2026-07) — đừng nhầm
- Cả bốn artifact đều là pipeline thật. Mỗi feature có tối đa ba phiên bản, cache nội trang và thao tác đổi tên/xóa; tạo mới không làm mất bản cũ.
- FE đang **mixed** `@radix-ui/*` (accordion/progress/radio-group/separator) + `@base-ui/react` (còn lại) — chưa hợp nhất (deferred).

## How we work — Lead + Claude, không team giả
- Chỉ 2 vai: **Lead** = người quyết định; **tôi** = kỹ sư. Bỏ mọi persona Backend/Frontend/QA Dev.
- **Definition of Done** (tôi tự enforce, KHÔNG để Lead là người bắt bug):
  1. `npm run lint` + `npm run build` (FE) / `ruff check` + `pytest` (BE) sạch.
  2. Preview verify **state thật** (preview_* tools) — không chỉ "compile được".
  3. Nói rõ cái gì **chưa** verify được (thiếu key/data…) — không giả vờ đã test đủ.
- **Token discipline**: `/clear` khi đổi task (miễn phí, tức thì); `/compact` chỉ khi cần giữ mạch 1 task dài. Tái dùng token/component. Giao search nặng cho subagent.
- **Git**: không commit/push/force khi Lead chưa yêu cầu.
