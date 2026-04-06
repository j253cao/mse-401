"""Hybrid BM25 + dense bi-encoder retrieval fused with reciprocal rank fusion (RRF)."""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from rank_bm25 import BM25Okapi

from .hybrid_retrieval_common import (
    apply_global_dept_option_multipliers,
    hybrid_retrieval_candidates,
)
from .recommenders import MIN_SIMILARITY_CUTOFF, dense_semantic_plus_title_boost
from .search_weight_config import DEFAULT_SEARCH_WEIGHTS


def recommend_hybrid_bm25_dense(
    query: str,
    dense_model,
    dense_emb_norm: np.ndarray,
    bm25: BM25Okapi,
    df: pd.DataFrame,
    filters: Optional[Dict[str, Any]] = None,
    top_k: int = 30,
    ranking_weights: Optional[Dict[str, float]] = None,
    hybrid_weights: Optional[Dict[str, float]] = None,
    dense_model_name: Optional[str] = None,
) -> pd.DataFrame:
    """Retrieve with BM25+dense RRF, then apply global/dept/option multipliers (like cosine/dense)."""
    ranking_weights = ranking_weights or {}
    hw = dict(DEFAULT_SEARCH_WEIGHTS.get("hybrid", {}))
    if hybrid_weights:
        hw.update(hybrid_weights)

    default_ranking = DEFAULT_SEARCH_WEIGHTS["ranking"]
    min_similarity = float(
        ranking_weights.get("min_similarity_cutoff", MIN_SIMILARITY_CUTOFF)
    )

    from .embedding_generators import encode_dense_query_normalized
    from .model_names import get_effective_dense_model_name

    dname = dense_model_name or get_effective_dense_model_name()
    q_norm = np.asarray(
        encode_dense_query_normalized(dname, dense_model, query),
        dtype=np.float32,
    )

    dense_semantic_gate = np.dot(dense_emb_norm, q_norm.astype(np.float64))
    dense_semantic_gate = np.nan_to_num(dense_semantic_gate, nan=0.0, posinf=0.0, neginf=0.0)
    retrieval_sim = dense_semantic_plus_title_boost(
        query, df, dense_semantic_gate, ranking_weights=ranking_weights
    )

    candidate_idxs, rrf_full, dense_semantic = hybrid_retrieval_candidates(
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

    base = rrf_full[candidate_idxs].astype(np.float64)
    weighted, g_mult, d_mult, o_mult = apply_global_dept_option_multipliers(
        candidate_idxs,
        df,
        base,
        filters,
        ranking_weights,
    )

    order = np.argsort(-weighted)
    candidate_idxs = candidate_idxs[order]
    base = base[order]
    weighted = weighted[order]
    g_mult = g_mult[order]
    d_mult = d_mult[order]
    o_mult = o_mult[order]

    idxs = candidate_idxs[:top_k]
    final_scores = weighted[:top_k]
    g_k = g_mult[:top_k]
    d_k = d_mult[:top_k]
    o_k = o_mult[:top_k]
    base_k = base[:top_k]

    result = df.iloc[idxs][["courseCode", "title", "description"]].copy()
    result["similarity_raw"] = retrieval_sim[idxs].astype(np.float64)
    result["similarity"] = final_scores
    result["similarity"] = np.nan_to_num(result["similarity"], nan=0.0, posinf=0.0, neginf=0.0)
    result["score_semantic"] = dense_semantic[idxs].astype(np.float64)
    result["score_rrf"] = base_k.astype(np.float64)
    result["score_title_boost"] = np.zeros(len(idxs), dtype=np.float64)
    result["score_global_mult"] = g_k.astype(np.float64)
    result["score_dept_mult"] = d_k.astype(np.float64)
    result["score_option_mult"] = o_k.astype(np.float64)

    result = result[result["similarity_raw"] >= min_similarity]
    print(f"[recommend_hybrid_bm25_dense] returned {len(result)} rows")
    return result
