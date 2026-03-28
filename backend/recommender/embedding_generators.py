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
    embeddings = model.encode(
        texts,
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
