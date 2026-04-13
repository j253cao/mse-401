"""Runtime dense + cross-encoder model selection (defaults, env, benchmark overrides)."""

from __future__ import annotations

import os
import re
from typing import Optional

# Public defaults (also used when no override / env)
DEFAULT_DENSE_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_RUNTIME_DENSE: Optional[str] = None
_RUNTIME_CROSS_ENCODER: Optional[str] = None


def get_effective_dense_model_name() -> str:
    return (
        _RUNTIME_DENSE
        or os.environ.get("RECOMMENDER_DENSE_MODEL", "").strip()
        or DEFAULT_DENSE_MODEL_NAME
    )


def get_effective_cross_encoder_model_name() -> str:
    return (
        _RUNTIME_CROSS_ENCODER
        or os.environ.get("RECOMMENDER_CROSS_ENCODER_MODEL", "").strip()
        or DEFAULT_CROSS_ENCODER_MODEL
    )


def get_effective_model_cache_dir() -> Optional[str]:
    return (
        os.environ.get("HF_HOME", "").strip()
        or os.environ.get("SENTENCE_TRANSFORMERS_HOME", "").strip()
        or None
    )


def set_runtime_model_overrides(
    dense: Optional[str] = None,
    cross_encoder: Optional[str] = None,
) -> None:
    """Set in-process overrides (None = clear override for that slot, fall back to env/default)."""
    global _RUNTIME_DENSE, _RUNTIME_CROSS_ENCODER
    _RUNTIME_DENSE = dense.strip() if dense else None
    _RUNTIME_CROSS_ENCODER = cross_encoder.strip() if cross_encoder else None


def clear_runtime_model_overrides() -> None:
    global _RUNTIME_DENSE, _RUNTIME_CROSS_ENCODER
    _RUNTIME_DENSE = None
    _RUNTIME_CROSS_ENCODER = None


def dense_embedding_file_slug(model_name: str) -> str:
    """Filesystem-safe stem for per-model dense embedding files."""
    s = model_name.strip().replace("/", "_").replace("\\", "_")
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", s)
    return s[:180] if len(s) > 180 else s
