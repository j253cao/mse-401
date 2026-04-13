FROM node:18-alpine AS build-frontend

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npx vite build

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

WORKDIR /app

# Install backend dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend source
COPY backend/ /app/backend/

# Copy only runtime data assets needed by the deployed API.
COPY data/courses/ /app/data/courses/
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
