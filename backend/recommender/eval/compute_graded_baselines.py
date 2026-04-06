#!/usr/bin/env python3
"""Compute and save macro + segment metrics per method for graded eval sets.

Writes [backend/recommender/eval/graded_method_baselines.json](graded_method_baselines.json).

Usage (from backend/):
  python recommender/eval/compute_graded_baselines.py --top-k 15
"""

from __future__ import annotations

import argparse
import json
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from recommender.eval.eval_filter_validation import validate_eval_cases_filter_policy  # noqa: E402
from recommender.eval.run_weight_sweep import (  # noqa: E402
    PRIMARY_GRADED_METHODS,
    aggregate_metrics,
    evaluate_case,
    segment_metrics,
)
def _graded_cases(cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for c in cases:
        gr = c.get("graded_relevance") or {}
        if any(float(v) > 0 for v in gr.values()):
            out.append(c)
    return out


def run_for_set(path: Path, top_k: int, methods: tuple) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    cases = list(payload.get("cases", []))
    graded = _graded_cases(cases)
    errs = validate_eval_cases_filter_policy(cases)
    if errs:
        raise ValueError("Filter policy:\n" + "\n".join(errs[:25]))

    per_method: Dict[str, Any] = {}
    for method in methods:
        rows = []
        with redirect_stdout(StringIO()):
            for case in graded:
                rows.append(evaluate_case(case, {}, top_k=top_k, method=method))
        per_method[method] = {
            "graded_case_count": len(graded),
            "macro": aggregate_metrics(rows),
            "segment_metrics": segment_metrics(rows),
        }
    return {
        "eval_set": str(path),
        "top_k": top_k,
        "weights_note": "Baseline weights only: weight_overrides={}.",
        "methods": per_method,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=15)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "graded_method_baselines.json",
    )
    args = parser.parse_args()

    eval_dir = Path(__file__).resolve().parent
    sets = [
        eval_dir / "queries.json",
        eval_dir / "test_plan_402.json",
    ]
    report = {
        "top_k": args.top_k,
        "methods_evaluated": list(PRIMARY_GRADED_METHODS),
        "datasets": [run_for_set(p, args.top_k, PRIMARY_GRADED_METHODS) for p in sets],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
