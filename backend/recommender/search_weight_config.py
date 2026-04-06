"""Centralized search weight configuration.

This module is the single source of truth for production search/recommendation
weights used across:
- cosine ranking
- global weight computation
- option-completion boosts
- explore-high-value defaults
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional


DEFAULT_SEARCH_WEIGHTS: Dict[str, Dict[str, float]] = {
    "global_weight": {
        "gamma_prereq": 1.0,
        "gamma_depth": 0.3,
        "gamma_minor": 0.5,
    },
    "ranking": {
        "alpha": 0.4,
        "same_department_boost": 0.6,
        "min_similarity_cutoff": 0.25,
        "full_query_title_boost": 0.4,
        "phrase_title_boost": 0.3,
        "title_word_boost_per_overlap": 0.22,
        "title_word_boost_cap": 0.65,
    },
    "option_boost": {
        "tier1": 0.15,
        "tier2": 0.10,
        "tier3": 0.05,
    },
    "explore": {
        "depth_penalty": 0.15,
        "temperature": 0.5,
    },
    # Hybrid retrieval / cross-encoder reranking (used by recommend_* in separate modules).
    "hybrid": {
        "rrf_k": 60.0,
        "rrf_weight_lexical": 1.0,
        "rrf_weight_dense": 1.0,
        # Slightly deeper candidate pool so CE/graph shortlists see more recall.
        "retrieval_k": 270.0,
        "cross_encoder_pool": 128.0,
        "graph_rerank_pool": 105.0,
        # Fused CE reranker: weights on min-max-normalized CE, RRF, retrieval scores.
        "ce_fusion_w_ce": 0.55,
        "ce_fusion_w_rrf": 0.30,
        "ce_fusion_w_retrieval": 0.15,
    },
}


def default_search_weights() -> Dict[str, Dict[str, float]]:
    """Return a deep copy of baseline production weights."""
    return deepcopy(DEFAULT_SEARCH_WEIGHTS)


def merge_weight_overrides(
    overrides: Optional[Dict[str, Dict[str, Any]]],
) -> Dict[str, Dict[str, float]]:
    """Merge caller overrides into defaults and return resolved config.

    Unknown sections/keys are ignored to keep the interface forward-safe.
    """
    merged = default_search_weights()
    if not overrides:
        return merged

    for section, section_values in overrides.items():
        if section not in merged or not isinstance(section_values, dict):
            continue
        for key, value in section_values.items():
            if key not in merged[section]:
                continue
            try:
                merged[section][key] = float(value)
            except (TypeError, ValueError):
                continue
    return merged

