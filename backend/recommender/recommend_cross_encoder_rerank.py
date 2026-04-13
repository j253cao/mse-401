"""Two-stage retrieval: BM25+dense RRF, then cross-encoder rerank on a shortlist."""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from rank_bm25 import BM25Okapi

from .embedding_generators import build_multifield_course_texts
from .hybrid_retrieval_common import (
    hybrid_retrieval_candidates,
    predict_cross_encoder_scores,
    prepare_hybrid_query,
)
from .recommenders import MIN_SIMILARITY_CUTOFF
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
    dense_model_name: Optional[str] = None,
) -> pd.DataFrame:
    """RRF retrieval then MS-MARCO-style cross-encoder scores (no graph multipliers)."""
    ranking_weights = ranking_weights or {}
    hw = dict(DEFAULT_SEARCH_WEIGHTS.get("hybrid", {}))
    if hybrid_weights:
        hw.update(hybrid_weights)

    min_similarity = float(
        ranking_weights.get("min_similarity_cutoff", MIN_SIMILARITY_CUTOFF)
    )

    q_norm, dense_semantic, retrieval_sim = prepare_hybrid_query(
        query,
        dense_model,
        dense_emb_norm,
        df,
        ranking_weights,
        dense_model_name=dense_model_name,
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
        dense_semantic=dense_semantic,
    )

    if len(candidate_idxs) == 0:
        return pd.DataFrame(columns=["courseCode", "title", "description"])

    pool_n = int(hw.get("cross_encoder_pool", 120))
    pool_n = max(pool_n, top_k)
    shortlist = candidate_idxs[: min(len(candidate_idxs), pool_n)]

    if multifield_texts is None:
        multifield_texts = build_multifield_course_texts(df)

    ce_scores = predict_cross_encoder_scores(
        cross_encoder,
        query,
        multifield_texts,
        shortlist,
        batch_size=int(hw.get("cross_encoder_batch_size", 8)),
    )

    order = np.argsort(-ce_scores)
    shortlist = shortlist[order]
    ce_scores = ce_scores[order]

    k_final = min(top_k, len(shortlist))
    idxs = shortlist[:k_final]
    ce_top = ce_scores[:k_final]

    result = df.iloc[idxs][["courseCode", "title", "description"]].copy()
    result["similarity_raw"] = retrieval_sim[idxs].astype(np.float32)
    result["similarity"] = ce_top
    result["similarity"] = np.nan_to_num(result["similarity"], nan=0.0, posinf=0.0, neginf=0.0)
    result["score_semantic"] = dense_semantic[idxs].astype(np.float32)
    result["score_cross_encoder"] = ce_top.astype(np.float32)
    result["score_title_boost"] = np.zeros(len(idxs), dtype=np.float32)
    result["score_global_mult"] = np.ones(len(idxs), dtype=np.float32)
    result["score_dept_mult"] = np.ones(len(idxs), dtype=np.float32)
    result["score_option_mult"] = np.ones(len(idxs), dtype=np.float32)

    result = result[result["similarity_raw"] >= min_similarity]
    print(f"[recommend_cross_encoder_rerank] returned {len(result)} rows")
    return result
