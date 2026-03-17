## Backend scripts (non-runtime)

This folder contains **non-runtime** utilities used to generate/update data files
or scrape upstream sources. These scripts are **not imported by the FastAPI app**
and are excluded from the deployed Docker image via `.dockerignore`.

### Local development setup

The runtime `requirements.txt` only includes packages needed by the API server.
If you need to run scripts in this folder, install their extra dependencies manually:

```bash
# Scraper (calendar_catalog_scraper.py)
pip install playwright beautifulsoup4 ollama
playwright install chromium

# Course data fetcher (fetch_course_data.py)
pip install requests

# LLM prerequisite parsers (batch_llm_parser.py, llm_prereq_parser.py)
pip install google-generativeai   # already in requirements.txt

# Local LLM parser (batch_local_llm_parser.py)
pip install ollama
```

### Recent changes that affect local dev

- **`sentence-transformers` removed from `requirements.txt`** — PyTorch and the
  BERT model were only used by recommendation methods (`recommend_bert`,
  `recommend_hybrid_ensemble`) that no active API endpoint calls. They were removed
  to fit the 512 MB RAM limit on Koyeb. If you need them locally for experiments,
  install manually: `pip install sentence-transformers`.

- **`.env` moved to `backend/.env`** — the API loads env vars from `backend/.env`
  first, then falls back to the project-root `.env`. Place your `GEMINI_API_KEY`
  (and any other secrets) in `backend/.env`.

- **Non-runtime scripts relocated here** — files previously in `backend/parsers/`
  and `backend/scrapers/` that aren't imported by the API were moved into
  `backend/scripts/parsers/` and `backend/scripts/scrapers/`.

### Guidelines

- The deployed backend only relies on `backend/api/`, `backend/recommender/`,
  and the runtime parsers in `backend/parsers/`.
- If you add new scripts, put them here (or a subfolder) so they don't accidentally
  become runtime dependencies.
