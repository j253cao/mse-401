"""Validate eval JSON cases follow segment-level filter policies."""

from __future__ import annotations

from typing import Any, Dict, List

# Segments where catalog search should include non-engineering departments.
SEGMENTS_REQUIRE_INCLUDE_OTHER_DEPTS = frozenset(
    {"breadth", "non_stem", "test_plan_402_nonstem"}
)


def validate_eval_cases_filter_policy(cases: List[Dict[str, Any]]) -> List[str]:
    """Return human-readable error strings; empty list means all cases pass."""
    errors: List[str] = []
    for case in cases:
        cid = case.get("id", "?")
        segment = case.get("segment") or ""
        filters = case.get("filters") or {}
        if segment in SEGMENTS_REQUIRE_INCLUDE_OTHER_DEPTS:
            if not filters.get("include_other_depts"):
                errors.append(
                    f"{cid}: segment '{segment}' must set filters.include_other_depts=true"
                )
    return errors
