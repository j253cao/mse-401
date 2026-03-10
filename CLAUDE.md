# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**UW Guide** — a full-stack course recommendation and degree-planning web app for University of Waterloo engineering students. Core features: text-based course search, resume/transcript upload for personalized recommendations, and high-value course discovery for first-year students.

## Commands

### Frontend (React + TypeScript + Vite)

```bash
cd frontend
npm install          # Install dependencies
npm run dev          # Dev server at http://localhost:5173
npm run build        # tsc -b && vite build
npm run lint         # ESLint
```

### Backend (Python + FastAPI)

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000  # API at http://localhost:8000
```

### Data

```bash
python scripts/extract_program_core_courses.py  # Regenerate program_core_courses.json
```

Environment: copy `.env.example` → `.env` and fill in `GEMINI_API_KEY`, `WATERLOO_API_KEY`.

## Architecture

### Stack

- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Radix UI, React Router v6
- **Backend:** FastAPI, Pydantic v2, Uvicorn
- **ML:** TF-IDF + SVD + BERT (sentence-transformers `all-MiniLM-L6-v2`), FAISS, scikit-learn
- **Parsing:** pdfplumber, pypdf, Gemini API (LLM for resume/transcript analysis)
- **Storage:** JSON files (no database); browser localStorage for user profile

### Directory Structure

```
mse-401/
├── backend/
│   ├── api/main.py              # All FastAPI endpoints
│   ├── parsers/                 # resume_parser.py, transcript_parser.py, resume_llm_client.py
│   └── recommender/             # main.py (orchestration), embedding_generators.py,
│                                #   recommenders.py, data_loader.py, weights.py
├── frontend/src/
│   ├── App.tsx                  # Router + nav
│   ├── RecommendationPage.tsx   # Main recommendations UI
│   ├── services/api.ts          # All API calls (single source of truth)
│   ├── types/api.ts             # Shared TypeScript interfaces
│   ├── constants/               # engineeringPrograms.ts, filterDepartments.ts
│   ├── hooks/                   # useStoredProfile (localStorage persistence)
│   └── data/                    # program_core_courses.json
└── data/
    ├── courses/                 # course-api-new-data.json (primary catalog)
    ├── embeddings/              # Pre-computed .npy/.pkl embedding files
    ├── dependencies/            # course_dependencies_llm.json (prereq graph)
    └── programs/                # degree_requirements/, all_programs.json
```

### Key Data Flows

**Text search:** `api.ts` → `POST /recommend` → `recommender/main.py:get_recommendations()` → loads cached embeddings → cosine similarity → enriched with prereqs + contributing programs.

**Resume upload:** `POST /resume-recommend` → `ResumeParser` extracts text → Gemini LLM → builds query → same recommendation pipeline.

**Transcript upload:** `POST /transcript-parse` → `parse_transcript_bytes()` → returns completed courses per term → populates `completedCourses` in frontend state.

**Cold start (1A/1B):** `GET /explore-high-value` → popular 100-level courses biased by program.

### State Management (Frontend)

- `RecommendationsContext` (React Context) holds program, incoming level, completed courses, term summaries, student profile, and recommended courses.
- Profile persisted to localStorage under key `uw-guide-profile` via `useStoredProfile` hook.

### Backend Caching

`recommender/main.py` uses a module-level `_cached` dict to avoid reloading embeddings and course data on every request. Pre-computed embeddings live in `data/embeddings/`.

### API Endpoints

| Endpoint                      | Purpose                            |
| ----------------------------- | ---------------------------------- |
| `POST /recommend`             | Text query → ranked courses        |
| `POST /resume-recommend`      | Resume PDF → recommendations       |
| `POST /transcript-parse`      | UW transcript PDF → course history |
| `GET /explore-high-value`     | High-value courses for cold start  |
| `GET /courses/search`         | Autocomplete course search         |
| `GET /courses/{code}/similar` | Similar courses by description     |
| `GET /options-and-minors`     | Available options/minors list      |

## Workflow Orchestration

### 1. Plan Mode Default

- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately - don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy to keep main context window clean

- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop

- After ANY correction from the user: update 'tasks/lessons.md' with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done

- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)

- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes - don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing

- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests -> then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management

1. **Plan First**: Write plan to 'tasks/todo.md' with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review to 'tasks/todo.md'
6. **Capture Lessons**: Update 'tasks/lessons.md' after corrections

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.
- **Verify Before Done:** Never mark a task complete without proving it works.
