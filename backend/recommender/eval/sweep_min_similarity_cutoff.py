#!/usr/bin/env python3
"""Sweep ranking.min_similarity_cutoff across graded eval sets and calendar tracks.

Graded tracks:
  - queries.json / test_plan_402.json (full case filters, incl. major/term where present)

Calendar tracks ( uw_calendar_top10.csv , IDs from search_evaluation_queries.json ):
  - profiled: original filters ( user_department , incoming_level , etc.)
  - neutral: no major/term — drops user_department , incoming_level , completed_courses ;
    keeps department list + include_other_depts so STEM vs breadth coverage stays aligned
    with the query set (closer to public calendar search).

Usage (from backend/):
  python recommender/eval/sweep_min_similarity_cutoff.py
  python recommender/eval/sweep_min_similarity_cutoff.py --methods cosine,hybrid_ce_rrf_fused
  python recommender/eval/sweep_min_similarity_cutoff.py --skip-calendar  # graded only
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from recommender.eval.compare_methods_dual_benchmark import (  # noqa: E402
    _load_calendar_lists,
    _load_course_snippets,
    run_calendar_track,
)
from recommender.eval.run_weight_sweep import (  # noqa: E402
    PRIMARY_GRADED_METHODS,
    aggregate_metrics,
    evaluate_case,
    read_json,
)
from recommender.recommenders import _ENG_DEPTS  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parent
DEFAULT_CATALOG = BACKEND_ROOT.parent / "data" / "courses" / "course-api-new-data.json"

# Wide sweep around production default 0.25 (permissive → strict). Override with --cutoffs.
DEFAULT_CUTOFFS: Tuple[float, ...] = (
    0.12,
    0.15,
    0.18,
    0.20,
    0.22,
    0.25,
    0.28,
    0.30,
    0.33,
    0.35,
    0.40,
)


def _neutral_filters_for_case(case: Dict[str, Any]) -> Dict[str, Any]:
    f = case.get("filters") or {}
    dept = f.get("department")
    if not dept:
        dept = sorted(_ENG_DEPTS)
    return {
        "include_undergrad": True,
        "include_grad": True,
        "department": list(dept),
        "include_other_depts": bool(f.get("include_other_depts", False)),
        "ignore_dependencies": True,
        "completed_courses": [],
    }


def build_calendar_neutral_cases(search_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{**c, "filters": _neutral_filters_for_case(c)} for c in search_cases]


def write_calendar_neutral_json(
    source_path: Path,
    dest_path: Path,
) -> None:
    raw = read_json(source_path)
    cases = list(raw.get("cases", []))
    neutral_cases = build_calendar_neutral_cases(cases)
    out = {
        "version": raw.get("version", 1),
        "description": (
            "Neutral calendar-style filters derived from search_evaluation_queries.json: "
            "no user_department, incoming_level, or completed_courses; prereqs ignored. "
            "Same query IDs and department breadth as each row."
        ),
        "default_top_k": raw.get("default_top_k", 10),
        "source_file": str(source_path.name),
        "cases": neutral_cases,
    }
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with dest_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
        f.write("\n")


def run_graded_track(
    cases: List[Dict[str, Any]],
    methods: Sequence[str],
    top_k: int,
    cutoff: float,
) -> Dict[str, Dict[str, float]]:
    wo: Dict[str, Dict[str, float]] = {"ranking": {"min_similarity_cutoff": float(cutoff)}}
    out: Dict[str, Dict[str, float]] = {}
    for method in methods:
        rows: List[Dict[str, Any]] = []
        for case in cases:
            with redirect_stdout(io.StringIO()):
                rows.append(evaluate_case(case, wo, top_k=top_k, method=method))
        out[method] = aggregate_metrics(rows)
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--cutoffs",
        type=str,
        default=",".join(str(x) for x in DEFAULT_CUTOFFS),
        help="Comma-separated min_similarity_cutoff values",
    )
    p.add_argument(
        "--methods",
        type=str,
        default=",".join(PRIMARY_GRADED_METHODS),
        help="Comma-separated methods (default: PRIMARY_GRADED_METHODS)",
    )
    p.add_argument("--top-k", type=int, default=15)
    p.add_argument(
        "--queries-json",
        type=Path,
        default=EVAL_DIR / "queries.json",
    )
    p.add_argument(
        "--plan402-json",
        type=Path,
        default=EVAL_DIR / "test_plan_402.json",
    )
    p.add_argument(
        "--search-eval-json",
        type=Path,
        default=EVAL_DIR / "search_evaluation_queries.json",
    )
    p.add_argument(
        "--neutral-json-out",
        type=Path,
        default=EVAL_DIR / "search_evaluation_queries_calendar_neutral.json",
        help="Calendar-neutral eval cases (no major/term); rewritten each run unless skipped",
    )
    p.add_argument(
        "--skip-neutral-json",
        action="store_true",
        help="Do not rewrite search_evaluation_queries_calendar_neutral.json",
    )
    p.add_argument(
        "--calendar-csv",
        type=Path,
        default=EVAL_DIR / "uw_calendar_top10.csv",
    )
    p.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    p.add_argument(
        "--output-dir",
        type=Path,
        default=EVAL_DIR / "reports_min_similarity_sweep",
    )
    p.add_argument(
        "--skip-graded",
        action="store_true",
    )
    p.add_argument(
        "--skip-calendar",
        action="store_true",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cutoffs = [float(x.strip()) for x in args.cutoffs.split(",") if x.strip()]
    methods = [m.strip() for m in args.methods.split(",") if m.strip()]
    if not args.skip_neutral_json:
        write_calendar_neutral_json(args.search_eval_json, args.neutral_json_out)
        print("Wrote", args.neutral_json_out, flush=True)

    rows_out: List[Dict[str, Any]] = []

    queries_cases: List[Dict[str, Any]] = []
    plan_cases: List[Dict[str, Any]] = []
    if not args.skip_graded:
        queries_cases = list(read_json(args.queries_json).get("cases", []))
        plan_cases = list(read_json(args.plan402_json).get("cases", []))

    search_payload = read_json(args.search_eval_json)
    search_cases_profiled = list(search_payload.get("cases", []))
    search_cases_neutral = build_calendar_neutral_cases(search_cases_profiled)

    catalog = _load_course_snippets(args.catalog)
    calendar_by_id = _load_calendar_lists(args.calendar_csv)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    for ci, cutoff in enumerate(cutoffs):
        wo = {"ranking": {"min_similarity_cutoff": float(cutoff)}}
        print(f"[{ci + 1}/{len(cutoffs)}] min_similarity_cutoff={cutoff}", flush=True)

        if not args.skip_graded:
            for name, cases in (
                ("queries.json", queries_cases),
                ("test_plan_402.json", plan_cases),
            ):
                metrics_by_m = run_graded_track(cases, methods, args.top_k, cutoff)
                for m in methods:
                    met = metrics_by_m[m]
                    rows_out.append(
                        {
                            "track": "graded",
                            "eval_set": name,
                            "calendar_mode": "",
                            "min_similarity_cutoff": cutoff,
                            "method": m,
                            "ndcg_at_k": met["ndcg_at_k"],
                            "recall_at_k": met["recall_at_k"],
                            "mrr": met["mrr"],
                            "calendar_win_rate": "",
                            "mean_jaccard_at_k": "",
                            "non_stem_win_rate": "",
                        }
                    )

        if not args.skip_calendar:
            for cal_label, scases in (
                ("profiled", search_cases_profiled),
                ("neutral_no_major_term", search_cases_neutral),
            ):
                cal_block = run_calendar_track(
                    scases,
                    calendar_by_id,
                    catalog,
                    list(methods),
                    args.top_k,
                    wo,
                    2.0,
                    1.0,
                    1.0,
                    1e-6,
                    1.5,
                )
                for m in methods:
                    payload = cal_block["methods"][m]
                    rows_out.append(
                        {
                            "track": "calendar",
                            "eval_set": str(args.search_eval_json.name),
                            "calendar_mode": cal_label,
                            "min_similarity_cutoff": cutoff,
                            "method": m,
                            "ndcg_at_k": "",
                            "recall_at_k": "",
                            "mrr": "",
                            "calendar_win_rate": payload["win_rate"],
                            "mean_jaccard_at_k": payload["mean_jaccard_at_k"],
                            "non_stem_win_rate": payload["non_stem_win_rate"],
                        }
                    )

    summary_path = args.output_dir / "min_similarity_sweep_summary.json"
    csv_path = args.output_dir / "min_similarity_sweep.csv"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "top_k": args.top_k,
                "cutoffs": cutoffs,
                "methods": methods,
                "queries_json": str(args.queries_json),
                "test_plan_402_json": str(args.plan402_json),
                "search_eval_json": str(args.search_eval_json),
                "calendar_csv": str(args.calendar_csv),
                "calendar_modes": ["profiled", "neutral_no_major_term"],
                "neutral_filters_note": (
                    "neutral_no_major_term omits user_department, incoming_level, "
                    "completed_courses; ignore_dependencies true"
                ),
                "rows": rows_out,
            },
            f,
            indent=2,
        )
        f.write("\n")

    fieldnames = [
        "track",
        "eval_set",
        "calendar_mode",
        "min_similarity_cutoff",
        "method",
        "ndcg_at_k",
        "recall_at_k",
        "mrr",
        "calendar_win_rate",
        "mean_jaccard_at_k",
        "non_stem_win_rate",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows_out:
            w.writerow({k: r.get(k, "") for k in fieldnames})

    print("Wrote", summary_path)
    print("Wrote", csv_path)


if __name__ == "__main__":
    main()
