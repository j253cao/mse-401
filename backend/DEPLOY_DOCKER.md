## Backend Docker deployment

This repository deploys the backend as a separate container.

### Build image (from repo root)

```bash
docker build -t uw-guide-backend:latest -f backend/Dockerfile .
```

### Run locally

```bash
docker run --rm -p 8000:8000 ^
  -e ENVIRONMENT=development ^
  -e ALLOWED_ORIGINS=http://localhost:5173 ^
  uw-guide-backend:latest
```

### Required runtime files

The container bundles the runtime `data/` directory. The backend expects at least:

- `data/courses/course-api-new-data.json`
- `data/courses/undergrad-courses.json`
- `data/courses/grad-courses.json`
- `data/dependencies/course_dependencies_llm.json`
- `data/programs/all_programs.json`
- `data/programs/all_options.json`
- `data/degree_requirements/program_core_courses.json`
- `data/embeddings/*` (precomputed)

### Env vars

- `ALLOWED_ORIGINS`: comma-separated list of allowed origins for CORS (no `*`).
- `ALLOWED_HOSTS`: comma-separated list of allowed Host headers (set in production).
- `GEMINI_API_KEY`: optional; if unset, `/resume-recommend` returns 503.

