---
name: study-pack-upgrade
description: Upgrade AI Course Generator into a Document-to-Study-Pack app with Chroma, Study Guide PDF, university-quality slides, mindmap, quiz, flashcards, quality gate, fallback handling, and clean frontend UI.
---

# Study Pack Upgrade Skill

Use this skill when working on my AI Course Generator / Document-to-Study-Pack project.

## Project goal

Upgrade this project from a simple PDF generator into a real Document-to-Study-Pack web app.

Core outputs:
1. Study Guide PDF
2. University-quality Slides
3. Mindmap
4. Quiz
5. Flashcards
6. High-yield Summary
7. Optional Audio Lecture / Podcast
8. Optional Video

## Tech stack

Frontend:
- Next.js / React

Backend:
- FastAPI / Python / uv

AI:
- Gemini API for generation and embeddings

Vector DB:
- Chroma is required for local/dev

## Important decision

Chroma is the main local/dev vector database.

Do not replace Chroma with FAISS as the main path.

FAISS may only be optional experimental fallback.

## Chroma requirements

Use:
- VECTOR_DB_PROVIDER=chroma
- CHROMA_PERSIST_DIR=./data/chroma
- CHROMA_COLLECTION_NAME=ai_course_chunks

Each chunk metadata should include:
- document_id
- user_id if auth exists
- chunk_id
- page
- source_file
- chunk_type
- quality_score
- use_for_generation

Retrieval must:
- filter by document_id
- exclude toc/noisy chunks
- prefer body, definition, example, code, formula, exercise, summary
- keep source_chunk_ids

## Quality rules

Never allow final user-facing output to contain:
- Contents
- dot leaders
- raw page numbers
- debug markers
- MA DINH DANH TRANG
- BAT DAU DU LIEU
- KET THUC DU LIEU
- NOI DUNG
- Y chinh
- Ghi nho y chinh
- raw JSON/debug logs

## Document quality behavior

Add or improve:
- document_quality_report
- chunk classification
- clean context filtering
- per-output readiness
- fallback generation

Readiness statuses:
- ready
- limited
- not_enough_context

Fallbacks:
- short_summary
- high_yield_notes
- document_outline
- key_terms
- shallow_mindmap
- short_video_script
- storyboard_only

Do not hallucinate when context is insufficient.

## Book upgrade

Study Guide PDF should feel like serious university courseware.

Must include:
- cover page
- how to use this guide
- prerequisites
- course roadmap
- chapters
- learning objectives
- intuition
- formal explanation
- examples
- non-examples
- common mistakes
- worked examples
- practice problems
- glossary
- final review plan
- source_chunk_ids

## Slides upgrade

Slides should feel like professional university lecture slides.

Must include:
- title slide
- learning objectives
- prerequisite reminder
- motivation
- concept slides
- diagram/visual explanation slides
- worked example slides
- common mistake slides
- quick check slides
- recap
- practice/problem set
- speaker notes
- source_chunk_ids

Do not copy MIT content or claim MIT.
Only match the quality standard: rigorous, structured, clear, academic, source-grounded.

## Frontend UI rules

Create a clean AI learning workspace.

Layout:
- Left panel: Sources/Documents
- Center panel: Learning Workspace
- Right panel: Study Pack Outputs

Visible UI:
- no emojis
- no unnecessary top clutter
- no raw chunks by default
- no debug logs by default
- clean dark theme
- dashboard loads metadata only
- lazy-load heavy components

Do not copy NotebookLM exactly.
Use only general workspace inspiration.

## Privacy/source grounding

Show concise trust messages:
- Tai lieu cua ban duoc giu rieng tu.
- Ban co the xoa tai lieu bat cu luc nao.
- Noi dung duoc tao dua tren nguon trong file cua ban.
- AI co the sai, hay kiem tra lai thong tin quan trong.

Every generated item should keep source_chunk_ids.

Frontend should show:
"Xem nguon duoc dung"
as a collapsible panel.

## Development rules

Before editing:
1. Inspect relevant files.
2. Explain the plan briefly.
3. Modify only necessary files.
4. Keep changes focused.
5. Do not rewrite the whole project unnecessarily.
6. Do not push or commit unless user asks.
7. Do not expose API keys.
8. Do not run destructive commands.

After editing:
1. Report changed files.
2. Report commands run.
3. Explain how to test.
4. List remaining risks.
