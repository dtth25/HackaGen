# Project Runbook

Project path:
D:/DTTH-Hackathon-2026-AI-Course-Generator

Backend:
cd src/backend
uv run uvicorn backend.main:app --app-dir .. --reload --host 127.0.0.1 --port 8000

Frontend:
cd src/frontend
npm run dev

Main priorities:
- Chroma stability
- Study Guide PDF quality
- Slides quality
- Mindmap
- Quiz
- Flashcards
- document_quality_report
- per-output readiness
- fallback generation
- clean frontend workspace
