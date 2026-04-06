"""Embedding generation utilities for course recommendations."""

from __future__ import annotations

from typing import List, Tuple

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD


def generate_tfidf_svd_embeddings(descriptions, max_features=5000, n_components=100, random_state=42):
    """Generate TF-IDF + SVD embeddings for course descriptions."""
    tfidf = TfidfVectorizer(max_features=max_features, stop_words="english")
    X_tfidf = tfidf.fit_transform(descriptions)
    svd = TruncatedSVD(n_components=n_components, random_state=random_state)
    embeddings = svd.fit_transform(X_tfidf)
    return tfidf, svd, embeddings


def format_dense_query_text(model_name: str, query: str) -> str:
    """Model-specific query wording for bi-encoder retrieval (e5 / bge-style)."""
    m = (model_name or "").lower()
    q = (query or "").strip()
    if "e5-base" in m or "e5-large" in m or "e5-small" in m or "/e5-" in m or "intfloat/e5" in m:
        return f"query: {q}"
    if "bge-base-en" in m or "bge-large-en" in m or "bge-small-en" in m:
        return f"Represent this sentence for searching relevant passages: {q}"
    return q


def format_dense_passage_text(model_name: str, text: str) -> str:
    m = (model_name or "").lower()
    t = (text or "").strip()
    if not t:
        return t
    if "e5-base" in m or "e5-large" in m or "e5-small" in m or "/e5-" in m or "intfloat/e5" in m:
        return f"passage: {t}"
    return t


def encode_dense_query_normalized(model_name: str, dense_model, query: str):
    """Encode one search query with L2 normalization (matches prior encode flags)."""
    wrapped = format_dense_query_text(model_name, query)
    q_emb = dense_model.encode(
        [wrapped],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return q_emb[0]


def build_multifield_course_texts(df: pd.DataFrame) -> List[str]:
    """Single string per course: code + title + description for dense embedding.

    Matches course search semantics (codes and titles become searchable in-vector).
    """
    texts: List[str] = []
    for _, row in df.iterrows():
        code = str(row.get("courseCode") or "").strip()
        title = str(row.get("title") or "").strip()
        desc = str(row.get("description") or "").strip()
        parts = [code, title]
        if desc:
            parts.append(desc)
        texts.append(". ".join(p for p in parts if p))
    return texts


def generate_dense_embeddings(
    texts: List[str],
    model_name: str = "all-MiniLM-L6-v2",
    batch_size: int = 64,
    show_progress_bar: bool = True,
) -> Tuple[object, np.ndarray]:
    """Encode texts with sentence-transformers. Returns (model, float32 array (n, dim))."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    formatted = [format_dense_passage_text(model_name, t) for t in texts]
    embeddings = model.encode(
        formatted,
        batch_size=batch_size,
        show_progress_bar=show_progress_bar,
        convert_to_numpy=True,
        normalize_embeddings=False,
    )
    return model, np.asarray(embeddings, dtype=np.float32)


def generate_bert_embeddings(descriptions, model_name="all-MiniLM-L6-v2"):
    """Generate BERT embeddings for course descriptions.
    Requires sentence-transformers: pip install sentence-transformers
    """
    return generate_dense_embeddings(
        list(descriptions),
        model_name=model_name,
        show_progress_bar=True,
    )
