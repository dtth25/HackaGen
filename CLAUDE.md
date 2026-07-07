# AI Course Generator — Project Instructions

> These instructions apply to the whole repository. See also `AGENTS.md` (agent
> roles/workflow) and `ROOT_CONTEXT.md` (pipeline detail). These docs should now
> describe the same current Chroma/auth Study Pack architecture.

## Project identity

AI Course Generator / Document-to-Study-Pack web app. Users upload a document
and get a connected study pack back — not a single PDF export.

## Core product outputs

1. Study Guide PDF / Book
2. Mindmap
3. Quiz
4. Flashcards
5. High-yield summary
6. Slide
7. Vid

Book, Slide, Quiz, and Vid are the four direct generation endpoints. Mindmap,
Flashcards, and Summary are course-scoped Study Pack components, not standalone
chat/custom-prompt surfaces.

## Tech stack

- **Frontend:** Next.js / React
- **Backend:** FastAPI / Python, dependencies managed with `uv`
- **Vector DB:** Chroma is required for local/dev
- **LLM & embeddings:** Gemini, unless configured otherwise

## Non-negotiable product rules

1. This is not a PDF generator — treat the Study Pack as one connected product.
2. Everything must come from a clean structured source pipeline:
   clean chunks -> teaching notes/book plan -> Study Guide/Book + mindmap + quiz + flashcards + summary + slide/video.
3. Never show raw RAG/debug/noisy text in final user-facing content.
4. Reject or clean: `Contents`, dot leaders, raw page numbers, debug markers,
   `MÃ ĐỊNH DANH TRANG`, `BẮT ĐẦU DỮ LIỆU`, `KẾT THÚC DỮ LIỆU`,
   `NỘI DUNG:`, `Ý chính`, `Ghi nhớ ý chính`.
5. Every generated major item must keep `source_chunk_ids` in metadata.
6. If context is insufficient, fall back to a limited/high-yield version or warn the user.
7. Never hallucinate when source context is insufficient.
8. Auth and ownership are part of the product: protected upload/generation/output/delete APIs require an active user, regular users only access their own documents, and admin routes are reserved for support/management.
9. The UI must communicate:
   - Your documents are private.
   - You can delete a document anytime.
   - Sources are grounded in your file.
   - AI may be wrong — verify important information.
10. Don't make privacy claims the code doesn't back up. If a delete control is shown, delete must actually work.
11. Target hardware is an 8GB RAM Windows laptop — keep the frontend lightweight.

## Development rules

- Inspect relevant files before editing.
- Keep changes focused; don't rewrite the whole repo.
- Don't modify files outside this repository.
- Don't push or commit unless explicitly asked.
- Don't expose API keys or modify real `.env` secrets.
- Don't run destructive commands.
- Report changed files, commands run, test results, and remaining risks after each task.
