#!/usr/bin/env python3
"""Export per-query diagnostics for graded eval cases (missed positives, first-hit rank).

Usage (from backend/):
  python recommender/eval/export_eval_diagnostics.py \\
    --eval-set recommender/eval/queries.json \\
    --method cross_encoder_rerank \\
    --output recommender/eval/reports/diag_cross_encoder.json
"""

from __future__ import annotations

import argparse
import json
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Set

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from recommender.eval.eval_filter_validation import validate_eval_cases_filter_policy  # noqa: E402
from recommender.eval.run_weight_sweep import (  # noqa: E402
    EVAL_BACKEND_METHODS,
    evaluate_case,
    normalize_code,
)
from recommender.main import get_recommendations  # noqa: E402


def _positives(graded: Dict[str, Any]) -> Set[str]:
    return {
        normalize_code(k)
        for k, v in (graded or {}).items()
        if float(v) > 0.0
    }


def _first_hit_rank(ranked: List[str], positives: Set[str]) -> int:
    for i, c in enumerate(ranked, start=1):
        if normalize_code(c) in positives:
            return i
    return 0


def _missed(ranked: List[str], positives: Set[str], k: int) -> List[str]:
    got = {normalize_code(c) for c in ranked[:k]}
    return sorted(positives - got)


def main() -> None:
    parser = argparse.ArgumentParser(description="Graded eval diagnostics export.")
    parser.add_argument(
        "--eval-set",
        type=Path,
        default=Path(__file__).resolve().parent / "queries.json",
    )
    parser.add_argument("--method", type=str, required=True, choices=list(EVAL_BACKEND_METHODS))
    parser.add_argument("--top-k", type=int, default=15)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--skip-filter-validation",
        action="store_true",
    )
    args = parser.parse_args()

    with args.eval_set.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    cases = list(payload.get("cases", []))
    if not cases:
        raise SystemExit("No cases in eval set")

    if not args.skip_filter_validation:
        errs = validate_eval_cases_filter_policy(cases)
        if errs:
            raise SystemExit("Filter policy errors:\n" + "\n".join(errs[:20]))

    rows = []
    for case in cases:
        gr = case.get("graded_relevance") or {}
        positives = _positives(gr)
        if not positives:
            continue
        query = case["query"]
        filters = case.get("filters") or {}
        cid = case.get("id")
        segment = case.get("segment")

        base_metrics = evaluate_case(case, {}, top_k=args.top_k, method=args.method)

        with redirect_stdout(StringIO()):
            batch = get_recommendations(
                [query],
                data_file="course-api-new-data.json",
                method=args.method,
                filters=filters,
                weight_overrides={},
            )
        ranked = [
            normalize_code(item["course_code"])
            for item in (batch[0] if batch else [])
            if item.get("method") == args.method
        ]
        fh = _first_hit_rank(ranked, positives)
        missed = _missed(ranked, positives, args.top_k)
        rows.append(
            {
                "id": cid,
                "segment": segment,
                "query": query,
                "ndcg_at_k": base_metrics["ndcg_at_k"],
                "recall_at_k": base_metrics["recall_at_k"],
                "mrr": base_metrics["mrr"],
                "first_hit_rank": fh,
                "num_positives": len(positives),
                "missed_positives_top_k": missed,
                "top_k_codes": ranked[: args.top_k],
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "eval_set": str(args.eval_set),
        "method": args.method,
        "top_k": args.top_k,
        "cases": rows,
    }
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {len(rows)} labeled cases to {args.output}")


if __name__ == "__main__":
    main()
