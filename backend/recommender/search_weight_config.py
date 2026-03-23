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
        "full_query_title_boost": 0.5,
        "phrase_title_boost": 0.35,
        "title_word_boost_per_overlap": 0.28,
        "title_word_boost_cap": 0.75,
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

