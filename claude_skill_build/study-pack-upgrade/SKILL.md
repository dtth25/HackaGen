---
name: study-pack-upgrade
description: Upgrade AI Course Generator into a Document-to-Study-Pack app with Chroma, university-quality study guide, slides, mindmap, quiz, flashcards, quality gate, fallback handling, and clean frontend UI.
---

# Study Pack Upgrade

Use this skill when working on the AI Course Generator / Document-to-Study-Pack project.

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
- Next.js
- React

Backend:
- FastAPI
- Python
- uv

AI:
- Gemini API for generation and embeddings

Vector database:
- Chroma is required for local/dev.

## Chroma decision

Chroma is the main local/dev vector database.

Do not replace Chroma with FAISS as the main path.

Required env variables:
- VECTOR_DB_PROVIDER=chroma
- CHROMA_PERSIST_DIR=./data/chroma
- CHROMA_COLLECTION_NAME=ai_course_chunks

Every stored chunk should include metadata:
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
- exclude chunk_type=toc
- exclude chunk_type=noisy
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
- raw JSON
- raw debug logs

Every generated item should keep source_chunk_ids:
- Study Guide lesson
- Slide
- Mindmap node
- Quiz question
- Flashcard
- Summary section
- Audio segment
- Video scene

## Document quality behavior

Add or improve:
- document_quality_report
- chunk classification
- context cleaning
- retrieval quality report
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

## Book quality standard

The Study Guide PDF should feel like serious university courseware.

It should include:
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

## Slide quality standard

Slides should feel like professional university lecture slides.

They should include:
- title slide
- learning objectives
- prerequisite reminder
- motivation
- concept slides
- diagram or visual explanation slides
- worked example slides
- common mistake slides
- quick check slides
- recap
- practice problem set
- speaker notes
- source_chunk_ids

Do not copy MIT content or claim MIT.
Only match the quality standard: rigorous, structured, clear, academic, source-grounded, visually clean.

## Frontend UI direction

Create a clean AI learning workspace.

General layout:
- Left panel: Sources / Documents
- Center panel: Learning Workspace
- Right panel: Study Pack Outputs

Visible UI rules:
- no emojis
- no unnecessary top clutter
- no raw chunks by default
- no debug logs by default
- clean dark theme if current design supports it
- dashboard loads metadata only
- lazy-load heavy components
- do not render all outputs at once
- do not store huge raw JSON in React state

Do not copy NotebookLM exactly.
Use only the general workspace idea.

## Privacy and source grounding

Show concise trust messages:
- Tai lieu cua ban duoc giu rieng tu.
- Ban co the xoa tai lieu bat cu luc nao.
- Noi dung duoc tao dua tren nguon trong file cua ban.
- AI co the sai, hay kiem tra lai thong tin quan trong.

Every generated item should keep source_chunk_ids.

Frontend should show:
Xem nguon duoc dung

as a collapsible panel.

Show clean excerpts, not raw debug chunks.

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
