FROM node:18-alpine AS build-frontend

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npx vite build

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/app/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence_transformers \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

WORKDIR /app

# Install backend dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir \
      --index-url https://download.pytorch.org/whl/cpu \
      --extra-index-url https://pypi.org/simple \
      -r /app/backend/requirements.txt && \
    python -c "from pathlib import Path; import shutil, site; \
[shutil.rmtree(path, ignore_errors=True) \
 for root in (Path(p) for p in site.getsitepackages()) if root.exists() \
 for pattern in ('**/__pycache__', '**/tests', '**/test') \
 for path in root.glob(pattern) if path.is_dir()]"

# Copy backend source
COPY backend/ /app/backend/

# Bake the default dense and cross-encoder models into the image to avoid
# cold-start downloads on first request.
RUN python -c "from pathlib import Path; [Path(p).mkdir(parents=True, exist_ok=True) for p in ('$HF_HOME', '$SENTENCE_TRANSFORMERS_HOME')]" && \
    PYTHONPATH=/app/backend python -c "from recommender.main import _get_cross_encoder, _get_dense_sentence_model; _get_dense_sentence_model(); _get_cross_encoder()"

# Copy only runtime data assets needed by the deployed API.
COPY data/courses/course-api-new-data.json /app/data/courses/course-api-new-data.json
COPY data/courses/undergrad-courses.json /app/data/courses/undergrad-courses.json
COPY data/courses/grad-courses.json /app/data/courses/grad-courses.json
COPY data/programs/ /app/data/programs/
COPY data/degree_requirements/program_core_courses.json /app/data/degree_requirements/program_core_courses.json
COPY data/dependencies/course_dependencies_llm.json /app/data/dependencies/course_dependencies_llm.json
COPY data/embeddings/course_embeddings.pkl /app/data/embeddings/course_embeddings.pkl
COPY data/embeddings/course_embeddings.npy /app/data/embeddings/course_embeddings.npy
COPY data/embeddings/dense_embeddings.npy /app/data/embeddings/dense_embeddings.npy
COPY data/embeddings/dense_model_name.txt /app/data/embeddings/dense_model_name.txt
COPY data/embeddings/svd_model.pkl /app/data/embeddings/svd_model.pkl
COPY data/embeddings/tfidf_vectorizer.pkl /app/data/embeddings/tfidf_vectorizer.pkl

# Copy frontend build output
COPY --from=build-frontend /build/dist /app/frontend-dist/

WORKDIR /app/backend
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--limit-concurrency", "15", "--timeout-keep-alive", "30"]
