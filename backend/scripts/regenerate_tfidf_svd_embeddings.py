#!/usr/bin/env python3
"""Rebuild TF-IDF + SVD pickles and course embedding matrix with the current scikit-learn.

This removes InconsistentVersionWarning when unpickling models trained on an older
sklearn and restores numeric parity for cosine search.

Usage (from repo root or backend/)::

    cd backend
    python scripts/regenerate_tfidf_svd_embeddings.py

Requires write access to data/embeddings/ under the project root.
"""

from __future__ import annotations

import os
import pickle
import sys
from pathlib import Path

import numpy as np

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from recommender.data_loader import load_course_data, save_embeddings  # noqa: E402
from recommender.embedding_generators import generate_tfidf_svd_embeddings  # noqa: E402


def is_regular_course(row) -> bool:
    title = row["title"].lower() if isinstance(row["title"], str) else ""
    code = row["courseCode"].lower() if isinstance(row["courseCode"], str) else ""
    description = row["description"].lower() if isinstance(row["description"], str) else ""
    return not (
        "seminar" in title
        or "seminar" in code
        or "work term" in title
        or "work term" in code
        or "coop" in title
        or "coop" in code
        or "co-op" in title
        or "co-op" in code
        or description.startswith("Work-term report")
        or description.startswith("General seminar")
        or "seminar" in description
        or "work term" in description
        or "coop" in description
        or "co-op" in description
    )


def main() -> None:
    data_json = PROJECT_ROOT / "data" / "courses" / "course-api-new-data.json"
    emb_dir = PROJECT_ROOT / "data" / "embeddings"
    emb_pkl = emb_dir / "course_embeddings.pkl"
    emb_npy = emb_dir / "course_embeddings.npy"
    tfidf_pkl = emb_dir / "tfidf_vectorizer.pkl"
    svd_pkl = emb_dir / "svd_model.pkl"

    print(f"Loading catalog: {data_json}")
    df = load_course_data(str(data_json))
    df = df[df.apply(is_regular_course, axis=1)].reset_index(drop=True)

    print(f"Rows: {len(df)} — fitting TF-IDF + SVD on descriptions")
    tfidf, svd, embeddings = generate_tfidf_svd_embeddings(df["description"])

    emb_dir.mkdir(parents=True, exist_ok=True)
    embeddings = np.asarray(embeddings, dtype=np.float32)
    save_embeddings(df, embeddings, str(emb_pkl), str(emb_npy))
    with tfidf_pkl.open("wb") as f:
        pickle.dump(tfidf, f)
    with svd_pkl.open("wb") as f:
        pickle.dump(svd, f)

    print(f"Wrote:\n  {tfidf_pkl}\n  {svd_pkl}\n  {emb_pkl}\n  {emb_npy}")
    print("Re-run dense embedding generation if you use precomputed dense_embeddings.npy (delete file to force regen).")


if __name__ == "__main__":
    main()
