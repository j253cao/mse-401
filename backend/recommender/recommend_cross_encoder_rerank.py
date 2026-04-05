"""Two-stage retrieval: BM25+dense RRF, then cross-encoder rerank on a shortlist."""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from rank_bm25 import BM25Okapi

from .embedding_generators import build_multifield_course_texts
from .hybrid_retrieval_common import hybrid_retrieval_candidates
from .recommenders import MIN_SIMILARITY_CUTOFF, dense_semantic_plus_title_boost
from .search_weight_config import DEFAULT_SEARCH_WEIGHTS


def recommend_cross_encoder_rerank(
    query: str,
    dense_model,
    dense_emb_norm: np.ndarray,
    bm25: BM25Okapi,
    cross_encoder,
    df: pd.DataFrame,
    *,
    multifield_texts: Optional[list] = None,
    filters: Optional[Dict[str, Any]] = None,
    top_k: int = 30,
    ranking_weights: Optional[Dict[str, float]] = None,
    hybrid_weights: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """RRF retrieval then MS-MARCO-style cross-encoder scores (no graph multipliers)."""
    ranking_weights = ranking_weights or {}
    hw = dict(DEFAULT_SEARCH_WEIGHTS.get("hybrid", {}))
    if hybrid_weights:
        hw.update(hybrid_weights)

    min_similarity = float(
        ranking_weights.get("min_similarity_cutoff", MIN_SIMILARITY_CUTOFF)
    )

    q_emb = dense_model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    q_norm = np.asarray(q_emb[0], dtype=np.float32)

    dense_semantic_gate = np.dot(dense_emb_norm, q_norm.astype(np.float64))
    dense_semantic_gate = np.nan_to_num(dense_semantic_gate, nan=0.0, posinf=0.0, neginf=0.0)
    retrieval_sim = dense_semantic_plus_title_boost(
        query, df, dense_semantic_gate, ranking_weights=ranking_weights
    )

    candidate_idxs, _rrf_full, dense_semantic = hybrid_retrieval_candidates(
        query,
        q_norm,
        dense_emb_norm,
        bm25,
        df,
        filters,
        hw,
        min_similarity_dense=min_similarity,
        retrieval_similarity=retrieval_sim,
    )

    if len(candidate_idxs) == 0:
        return pd.DataFrame(columns=["courseCode", "title", "description"])

    pool_n = int(hw.get("cross_encoder_pool", 120))
    pool_n = max(pool_n, top_k)
    shortlist = candidate_idxs[: min(len(candidate_idxs), pool_n)]

    if multifield_texts is None:
        multifield_texts = build_multifield_course_texts(df)

    pairs = [[query, multifield_texts[i]] for i in shortlist]
    ce_scores = cross_encoder.predict(pairs, show_progress_bar=False, batch_size=16)
    ce_scores = np.asarray(ce_scores, dtype=np.float64)

    order = np.argsort(-ce_scores)
    shortlist = shortlist[order]
    ce_scores = ce_scores[order]

    k_final = min(top_k, len(shortlist))
    idxs = shortlist[:k_final]
    ce_top = ce_scores[:k_final]

    result = df.iloc[idxs][["courseCode", "title", "description"]].copy()
    result["similarity_raw"] = retrieval_sim[idxs].astype(np.float64)
    result["similarity"] = ce_top
    result["similarity"] = np.nan_to_num(result["similarity"], nan=0.0, posinf=0.0, neginf=0.0)
    result["score_semantic"] = dense_semantic[idxs].astype(np.float64)
    result["score_cross_encoder"] = ce_top.astype(np.float64)
    result["score_title_boost"] = np.zeros(len(idxs), dtype=np.float64)
    result["score_global_mult"] = np.ones(len(idxs), dtype=np.float64)
    result["score_dept_mult"] = np.ones(len(idxs), dtype=np.float64)
    result["score_option_mult"] = np.ones(len(idxs), dtype=np.float64)

    result = result[result["similarity_raw"] >= min_similarity]
    print(f"[recommend_cross_encoder_rerank] returned {len(result)} rows")
    return result
