# Project Memory — AI Course Generator

Stable, long-term facts to carry into future sessions. Not a changelog — see git log for history.

## Architecture facts

- Auth tokens live only in browser `localStorage` (JWT via `src/lib/auth.ts`), never in a cookie.
  Any Next.js **Server Component** that calls an authenticated backend endpoint server-side will
  always get 401 and silently fall back to empty data. Data fetching for authenticated pages must
  happen in a **Client Component** (`"use client"`, fetch in `useEffect`). Fixed instances:
  `mindmap/[id]/page.tsx`, `course/[id]/page.tsx` (via `StudyPackDashboardClient`).
- When restructuring a component to fetch its own data client-side, all hooks (`useState`/`useEffect`/
  `useMemo`) must be declared before any conditional early `return` (loading/error/not-found states) —
  violating this causes a silent Rules-of-Hooks mismatch that only surfaces as a client crash on
  navigation, not at build time.
- `src/backend/main.py` and `src/backend/services/resource_gen.py` each import `get_course_path`
  independently into their own module namespace. Monkeypatching it on one module in a test does
  **not** affect the other — must patch both (`main.get_course_path` and
  `backend.services.resource_gen.get_course_path`) or generator-level file I/O silently uses real
  production paths instead of the test's tmp_path.
- New parameters added to generator methods in `resource_gen.py` are easy to silently drop: a
  parameter can be accepted by a method signature but never actually placed into the
  `chain.invoke(...)` payload dict (this happened with the old `learning_mode` field in 3 of 6
  generators). When adding a new cross-cutting parameter, grep every `.invoke(`/`.format(` call site
  (including retry branches) to confirm it's actually threaded through.
- `core/db.py` (SQLite) has no migration system — new columns are added via
  `ALTER TABLE ... ADD COLUMN` wrapped in try/except `sqlite3.OperationalError` inside `init_db()`.
- Gemini free-tier quota in this dev environment is very limited (~20 requests/day) and is
  frequently exhausted mid-session, causing generation calls to fall back to deterministic/extractive
  paths. Tests and manual verification should not depend on live LLM output — assert on
  fallback-safe, structural properties instead (schema shape, grounding, directive text presence).
- Vector DB adapter classes don't auto-delegate to their wrapped store. `rag.vectorstore` is a
  `ChromaCourseVectorStore` (course-scoped adapter in `vector_db/chroma_store.py`), not the raw
  `ChromaVectorStore` — it must explicitly redefine/delegate any method callers expect (e.g.
  `get_document_chunks`), otherwise calls silently 500 with "object has no attribute ...". This bit
  the "Xem nguồn" grounding endpoint for a long time before being caught by live browser testing
  (code review alone had missed it — always exercise a real document end-to-end, not just read code).
- Any new "list all X" endpoint must filter by the requesting user's ownership (or require
  admin/demo) from the start — `GET /api/courses/all` shipped with no auth at all and leaked every
  user's documents to any visitor via the SSR-rendered `/course` page. Same fix pattern as the
  Server Component auth issue above: ownership filtering belongs in the backend query, and the page
  that lists it must fetch client-side (`CourseListClient` now fetches in `useEffect`, not via a
  server-side prop).
- The embedding cache in `services/cache.py` (`get_embedding`/`set_embedding`) is keyed by content
  hash, not document_id, and is only read/written by the unused FAISS path — Chroma stores its own
  embeddings directly and already gets fully purged by `remove_course`. No document-specific cache
  cleanup is needed there.
- Frontend proxy routes under `app/api/backend/**/route.ts` hand-map request bodies field-by-field
  before forwarding to the backend — adding a new field to a feature's request schema (e.g.
  `video_mode`, `chapter_id`, `force` for video generation) does nothing until the matching proxy
  route is updated too, since unmapped fields are silently dropped. Same class of bug as the
  learning_mode note above, but at the Next.js proxy layer instead of the generator layer.
- In `StudyPackDashboardClient.tsx`'s tab-based lazy-load effects (slides/video/etc.), do not put the
  loading boolean in the effect's own dependency array while the effect body calls
  `setLoading(true)` — that re-triggers the effect, whose cleanup cancels the fetch it just started,
  so the tab hangs forever on "Đang nạp...". Use a `useRef` in-flight guard instead of a state flag
  for effect dependencies.

## Product/feature state (as of this session)

- Mindmap, Quiz, Flashcards, and the Learning Profile (User Mode) system are implemented and tested.
- Flashcards previously had no dedicated generator (only derived from quiz Q&A or dead book-lesson
  fields) — `generate_flashcards_v2` in `resource_gen.py` is the real generator now.
- `source_chunk_ids` must be present on every generated item (quiz questions, flashcards, book
  chapters, etc.) per product grounding requirements — never strip it from public payloads.
- Learning Profile: 7 role modes (student/teacher/self_learner/exam_prep/enterprise_trainer/
  researcher/developer), stored per-user, injected into every generator via a shared
  `build_profile_directives()` → `{profile_directives}` prompt placeholder. Changing mode never
  deletes previously generated outputs.
- Privacy & Trust Layer implemented: exact required trust messages shown on upload page and course
  dashboard, delete cascade covers file/chunks/vector DB/outputs, "Xem nguồn" shows filename+page+
  clean excerpt with raw chunk ids hidden unless admin+developer mode, document listing/delete is
  ownership-scoped.
- Video generation has 4 real modes (`sixty_second`/`three_minute`/`ten_minute`/`playlist_by_chapter`)
  each with fixed duration/scene-count/teaching-flow enforced server-side via `VIDEO_MODE_CONFIG` in
  `resource_gen.py` — not just accepted-and-ignored. Large/broad documents (≥15 retrieved docs) get a
  playlist recommendation instead of one compressed video, unless a `chapter_id`/`topic_id` narrows
  scope or the caller passes `force: true`. Playlist mode returns a plan (`status: "planned"`) without
  rendering any MP4s; each video renders on demand via `POST /api/course/{id}/vid/render`. The video
  quality gate rejects/scores down scenes missing `source_chunk_ids`, with repeated identical
  voiceover, or with screen_text lines over 15 words.

## Dev environment

- Local dev servers are launched via `.claude/launch.json` configs "backend" (`uv run uvicorn` from
  `src/`) and "frontend" (`npm run dev` from `src/frontend/`), used with the Preview tools.
- Frontend is Next.js 16.2.9 with breaking API changes vs. training data — see
  `src/frontend/AGENTS.md` before assuming standard Next.js behavior.
