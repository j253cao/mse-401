"""Shared utilities for BM25 + dense hybrid retrieval, RRF, and ranking fusion."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd

from rank_bm25 import BM25Okapi

from .recommenders import (
    _apply_course_filters,
    _get_course_dept,
    _subject_prefixes_for_same_dept_search_boost,
)
from .search_weight_config import DEFAULT_SEARCH_WEIGHTS

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> List[str]:
    """Lowercase alphanumeric tokens for BM25."""
    if not isinstance(text, str) or not text.strip():
        return []
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def load_prereq_snippet_map(deps_path: str) -> Dict[str, str]:
    """Build a short lexical string of prerequisite course codes per course (for BM25)."""
    try:
        with open(deps_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}

    out: Dict[str, str] = {}

    def collect_codes(obj, acc: Set[str]) -> None:
        if isinstance(obj, str):
            acc.add(obj.strip().upper().replace(" ", ""))
        elif isinstance(obj, dict):
            if obj.get("type") == "course" and obj.get("code"):
                acc.add(str(obj["code"]).strip().upper().replace(" ", ""))
            for v in obj.values():
                collect_codes(v, acc)
        elif isinstance(obj, list):
            for item in obj:
                collect_codes(item, acc)

    for raw_code, entry in data.items():
        if not raw_code:
            continue
        code = str(raw_code).strip().upper().replace(" ", "")
        acc: Set[str] = set()
        prereqs = entry.get("prerequisites", entry) if isinstance(entry, dict) else entry
        if isinstance(prereqs, dict):
            for g in prereqs.get("groups", []) or []:
                collect_codes(g, acc)
        elif isinstance(prereqs, list):
            collect_codes(prereqs, acc)
        acc.discard(code)
        if acc:
            out[code] = " ".join(sorted(acc))

    return out


def build_tokenized_corpus(df: pd.DataFrame, prereq_snippets: Optional[Dict[str, str]] = None) -> List[List[str]]:
    """One token list per row: code, subject, title, description, optional prereq codes."""
    prereq_snippets = prereq_snippets or {}
    corpus: List[List[str]] = []
    for _, row in df.iterrows():
        code = str(row.get("courseCode") or "").strip().upper().replace(" ", "")
        subj = str(row.get("subjectCode") or "").strip().upper()
        title = str(row.get("title") or "")
        desc = str(row.get("description") or "")
        pre_txt = prereq_snippets.get(code, "")
        blob = " ".join(
            [
                code,
                subj,
                " ".join(tokenize(code)),
                title,
                desc,
                pre_txt,
            ]
        )
        corpus.append(tokenize(blob))
    return corpus


def bm25_rank_scores(bm25: BM25Okapi, query_tokens: List[str]) -> np.ndarray:
    """BM25 relevance score per document (same length as corpus)."""
    n_docs = len(getattr(bm25, "doc_len", []))
    if not query_tokens or n_docs == 0:
        return np.zeros(n_docs, dtype=np.float64)
    return np.asarray(bm25.get_scores(query_tokens), dtype=np.float64)


def ranks_from_scores(scores: np.ndarray, higher_is_better: bool = True) -> np.ndarray:
    """For each index, 0-based rank position (0 = best)."""
    n = len(scores)
    if n == 0:
        return np.array([], dtype=np.int32)
    order = np.argsort(-scores) if higher_is_better else np.argsort(scores)
    ranks = np.empty(n, dtype=np.int32)
    ranks[order] = np.arange(n, dtype=np.int32)
    return ranks


def rrf_scores_from_ranks(
    rank_arrays: Sequence[np.ndarray],
    k: float = 60.0,
    weights: Optional[Sequence[float]] = None,
) -> np.ndarray:
    """Standard RRF: sum_w w / (k + rank + 1) per document index."""
    if not rank_arrays:
        raise ValueError("rank_arrays must be non-empty")
    n = len(rank_arrays[0])
    if weights is None:
        weights = [1.0] * len(rank_arrays)
    if len(weights) != len(rank_arrays):
        raise ValueError("weights length must match rank_arrays")
    out = np.zeros(n, dtype=np.float64)
    kk = float(k)
    for w, ranks in zip(weights, rank_arrays):
        if len(ranks) != n:
            raise ValueError("all rank arrays must have same length")
        ww = float(w)
        out += ww / (kk + ranks.astype(np.float64) + 1.0)
    return out


def eligible_indices(filters_applied: Set[str], df: pd.DataFrame) -> np.ndarray:
    """Row indices in df allowed by filters (or all rows if no filter set)."""
    if not filters_applied:
        return np.arange(len(df), dtype=np.int32)
    mask = df["courseCode"].isin(filters_applied)
    return np.where(mask.to_numpy())[0].astype(np.int32)


def apply_global_dept_option_multipliers(
    candidate_idxs: np.ndarray,
    df: pd.DataFrame,
    base_scores: np.ndarray,
    filters: Optional[Dict[str, Any]],
    ranking_weights: Optional[Dict[str, float]],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Same multiplicative fusion as recommend_cosine/dense stage 2 (global_weight, dept, option)."""
    rw = ranking_weights or {}
    default = DEFAULT_SEARCH_WEIGHTS["ranking"]
    alpha = float(rw.get("alpha", default["alpha"]))
    same_department_boost = float(rw.get("same_department_boost", default["same_department_boost"]))

    m = len(candidate_idxs)
    if m == 0:
        return (
            np.array([], dtype=np.int64),
            np.array([], dtype=np.float64),
            np.array([], dtype=np.float64),
            np.array([], dtype=np.float64),
            np.array([], dtype=np.float64),
        )

    if "global_weight" in df.columns:
        global_w = df["global_weight"].to_numpy(dtype=float)
        global_mult = 1.0 + alpha * global_w[candidate_idxs]
    else:
        global_mult = np.ones(m, dtype=np.float64)

    weighted = base_scores.astype(np.float64) * global_mult

    user_dept = (filters or {}).get("user_department")
    subject_prefixes = _subject_prefixes_for_same_dept_search_boost(str(user_dept) if user_dept else "")
    if subject_prefixes:
        codes_cd = df["courseCode"].iloc[candidate_idxs]
        same_dept = np.array(
            [_get_course_dept(str(c)) in subject_prefixes for c in codes_cd],
            dtype=np.float64,
        )
        dept_mult = 1.0 + same_department_boost * same_dept
    else:
        dept_mult = np.ones(m, dtype=np.float64)

    weighted = weighted * dept_mult

    option_boost_map = (filters or {}).get("option_boost_multipliers") or {}
    if option_boost_map:

        def norm_c(c: Any) -> str:
            return (str(c) or "").strip().upper().replace(" ", "")

        codes_ob = df["courseCode"].iloc[candidate_idxs]
        option_mult = np.array([option_boost_map.get(norm_c(c), 1.0) for c in codes_ob], dtype=np.float64)
    else:
        option_mult = np.ones(m, dtype=np.float64)

    weighted = weighted * option_mult
    return weighted, global_mult, dept_mult, option_mult


def hybrid_retrieval_candidates(
    query: str,
    q_dense: np.ndarray,
    dense_emb_norm: np.ndarray,
    bm25: BM25Okapi,
    df: pd.DataFrame,
    filters: Optional[Dict[str, Any]],
    hybrid_weights: Dict[str, float],
    *,
    min_similarity_dense: float,
    retrieval_similarity: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Returns:
        candidate_idxs: row indices after RRF + dense cutoff, sorted by RRF desc (best first)
        rrf_raw: full-length RRF score per row (zeros for ineligible)
        dense_semantic: dense cosine similarity per row (same as dot with normalized emb)
    """
    n = len(df)
    filters_applied = _apply_course_filters(filters, df)
    elig = eligible_indices(filters_applied, df)

    dense_semantic = np.dot(dense_emb_norm, q_dense.astype(np.float64))
    dense_semantic = np.nan_to_num(dense_semantic, nan=0.0, posinf=0.0, neginf=0.0)

    q_tokens = tokenize(query)
    bm25_s = bm25_rank_scores(bm25, q_tokens)

    rank_lex = ranks_from_scores(bm25_s, higher_is_better=True)
    rank_den = ranks_from_scores(dense_semantic, higher_is_better=True)

    rrf_k = float(hybrid_weights.get("rrf_k", 60.0))
    w_lex = float(hybrid_weights.get("rrf_weight_lexical", 1.0))
    w_den = float(hybrid_weights.get("rrf_weight_dense", 1.0))
    rrf_full = rrf_scores_from_ranks([rank_lex, rank_den], k=rrf_k, weights=[w_lex, w_den])

    # Eligible only
    mask = np.zeros(n, dtype=bool)
    mask[elig] = True
    rrf_masked = np.where(mask, rrf_full, -1.0)

    # Min-similarity gate: use dense+title if provided (matches recommend_dense), else raw dense.
    gate = (
        np.asarray(retrieval_similarity, dtype=np.float64)
        if retrieval_similarity is not None
        else dense_semantic
    )
    gate = np.nan_to_num(gate, nan=0.0, posinf=0.0, neginf=0.0)
    rrf_masked = np.where(gate >= float(min_similarity_dense), rrf_masked, -1.0)

    retrieval_k = int(hybrid_weights.get("retrieval_k", 250))
    candidate_pool = np.where(rrf_masked >= 0)[0]
    if len(candidate_pool) == 0:
        return np.array([], dtype=np.int64), rrf_full, dense_semantic

    pool_rrf = rrf_masked[candidate_pool]
    top_within = min(len(candidate_pool), max(retrieval_k, 1))
    if top_within < len(candidate_pool):
        pick = np.argpartition(-pool_rrf, top_within)[:top_within]
        candidate_idxs = candidate_pool[pick]
        order = np.argsort(-rrf_masked[candidate_idxs])
        candidate_idxs = candidate_idxs[order]
    else:
        candidate_idxs = candidate_pool[np.argsort(-pool_rrf)]

    return candidate_idxs.astype(np.int64), rrf_full, dense_semantic


def build_bm25_index(df: pd.DataFrame, prereq_snippets: Optional[Dict[str, str]] = None) -> BM25Okapi:
    corpus = build_tokenized_corpus(df, prereq_snippets)
    return BM25Okapi(corpus)
