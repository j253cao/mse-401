#!/usr/bin/env python3
"""Benchmark dense + cross-encoder pairs for hybrid_ce_rrf_fused (quality + latency).

Phase 1 (default): baseline + 3 dense-only + 2 CE-only + auto mixed (best dense + best CE).
Phase 2 (--phase2): small grid if pilot beats baseline on NDCG@15 (queries) by >= --phase2-min-delta.

Usage (from backend/):
  python recommender/eval/model_sweep_benchmark.py
  python recommender/eval/model_sweep_benchmark.py --phase2
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from recommender.eval.compare_methods_dual_benchmark import (  # noqa: E402
    _load_calendar_lists,
    _load_course_snippets,
    run_calendar_track,
)
from recommender.eval.run_weight_sweep import (  # noqa: E402
    aggregate_metrics,
    evaluate_case,
    read_json,
)
from recommender.main import (  # noqa: E402
    get_recommendations,
    set_recommender_model_overrides,
)
from recommender.model_names import (  # noqa: E402
    DEFAULT_CROSS_ENCODER_MODEL,
    DEFAULT_DENSE_MODEL_NAME,
)

EVAL_DIR = Path(__file__).resolve().parent
TOP_K = 15
FIXED_WEIGHTS: Dict[str, Dict[str, float]] = {"ranking": {"min_similarity_cutoff": 0.25}}


def _graded_metrics(cases: List[Dict[str, Any]]) -> Dict[str, float]:
    rows = []
    for case in cases:
        with redirect_stdout(io.StringIO()):
            rows.append(
                evaluate_case(
                    case,
                    FIXED_WEIGHTS,
                    top_k=TOP_K,
                    method="hybrid_ce_rrf_fused",
                )
            )
    return aggregate_metrics(rows)


def _latency_profile(
    search_cases: List[Dict[str, Any]],
    warmup: int = 2,
) -> Dict[str, float]:
    times_ms: List[float] = []
    if not search_cases:
        return {"p50_ms": 0.0, "p95_ms": 0.0, "mean_ms": 0.0, "n": 0}
    q0 = str(search_cases[0].get("query") or "")
    flt = dict(search_cases[0].get("filters") or {})
    for _ in range(warmup):
        with redirect_stdout(io.StringIO()):
            get_recommendations(
                [q0],
                method="hybrid_ce_rrf_fused",
                filters=flt,
                weight_overrides=FIXED_WEIGHTS,
            )
    for case in search_cases:
        q = str(case.get("query") or "")
        flt = dict(case.get("filters") or {})
        t0 = time.perf_counter()
        with redirect_stdout(io.StringIO()):
            get_recommendations(
                [q],
                method="hybrid_ce_rrf_fused",
                filters=flt,
                weight_overrides=FIXED_WEIGHTS,
            )
        times_ms.append((time.perf_counter() - t0) * 1000.0)
    arr = np.asarray(times_ms, dtype=np.float64)
    return {
        "p50_ms": float(np.percentile(arr, 50)),
        "p95_ms": float(np.percentile(arr, 95)),
        "mean_ms": float(np.mean(arr)),
        "n": float(len(times_ms)),
    }


def _run_one_config(
    config_id: str,
    dense: str,
    ce: str,
    cases_queries: List[Dict[str, Any]],
    cases_402: List[Dict[str, Any]],
    search_cases: List[Dict[str, Any]],
    calendar_by_id: Dict[str, List[str]],
    catalog: Dict[str, Any],
) -> Dict[str, Any]:
    set_recommender_model_overrides(dense=dense, cross_encoder=ce)
    with redirect_stdout(io.StringIO()):
        get_recommendations(
            ["machine learning"],
            method="hybrid_ce_rrf_fused",
            weight_overrides=FIXED_WEIGHTS,
        )

    mq = _graded_metrics(cases_queries)
    m402 = _graded_metrics(cases_402)
    lat = _latency_profile(search_cases)

    cal = run_calendar_track(
        search_cases,
        calendar_by_id,
        catalog,
        ["hybrid_ce_rrf_fused"],
        TOP_K,
        FIXED_WEIGHTS,
        2.0,
        1.0,
        1.0,
        1e-6,
        1.5,
    )
    cp = cal["methods"]["hybrid_ce_rrf_fused"]

    return {
        "config_id": config_id,
        "dense_model": dense,
        "cross_encoder_model": ce,
        "queries_ndcg_at_k": mq["ndcg_at_k"],
        "queries_recall_at_k": mq["recall_at_k"],
        "queries_mrr": mq["mrr"],
        "test_plan_402_ndcg_at_k": m402["ndcg_at_k"],
        "test_plan_402_recall_at_k": m402["recall_at_k"],
        "test_plan_402_mrr": m402["mrr"],
        "calendar_win_rate": cp["win_rate"],
        "calendar_weighted_win_rate": cp["weighted_win_rate"],
        "calendar_non_stem_win_rate": cp["non_stem_win_rate"],
        "mean_jaccard_at_k": cp["mean_jaccard_at_k"],
        "mean_calendar_set_recall": cp["mean_calendar_set_recall"],
        "latency_p50_ms": lat["p50_ms"],
        "latency_p95_ms": lat["p95_ms"],
        "latency_mean_ms": lat["mean_ms"],
        "latency_n_queries": int(lat["n"]),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--output-dir",
        type=Path,
        default=EVAL_DIR / "reports_model_sweep",
    )
    p.add_argument("--phase2", action="store_true", help="Run expanded grid if pilot beats baseline")
    p.add_argument(
        "--phase2-min-delta",
        type=float,
        default=0.01,
        help="Min NDCG@15 improvement on queries.json to trigger phase2",
    )
    p.add_argument(
        "--phase2-max-p95-factor",
        type=float,
        default=2.0,
        help="Skip phase2 if p95 latency exceeds baseline * this factor",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    cases_queries = list(read_json(EVAL_DIR / "queries.json").get("cases", []))
    cases_402 = list(read_json(EVAL_DIR / "test_plan_402.json").get("cases", []))
    search_payload = read_json(EVAL_DIR / "search_evaluation_queries.json")
    search_cases = list(search_payload.get("cases", []))
    calendar_by_id = _load_calendar_lists(EVAL_DIR / "uw_calendar_top10.csv")
    catalog = _load_course_snippets(BACKEND_ROOT.parent / "data" / "courses" / "course-api-new-data.json")

    pilot: List[Tuple[str, str, str]] = [
        ("baseline", DEFAULT_DENSE_MODEL_NAME, DEFAULT_CROSS_ENCODER_MODEL),
        ("dense_mpnet", "all-mpnet-base-v2", DEFAULT_CROSS_ENCODER_MODEL),
        ("dense_bge_base", "BAAI/bge-base-en-v1.5", DEFAULT_CROSS_ENCODER_MODEL),
        ("dense_e5_base", "intfloat/e5-base-v2", DEFAULT_CROSS_ENCODER_MODEL),
        ("ce_ms_marco_l12", DEFAULT_DENSE_MODEL_NAME, "cross-encoder/ms-marco-MiniLM-L-12-v2"),
        ("ce_bge_reranker_base", DEFAULT_DENSE_MODEL_NAME, "BAAI/bge-reranker-base"),
    ]

    results: List[Dict[str, Any]] = []
    for cid, d, c in pilot:
        print(f"=== {cid} dense={d} ce={c} ===", flush=True)
        results.append(
            _run_one_config(
                cid, d, c,
                cases_queries, cases_402, search_cases,
                calendar_by_id, catalog,
            )
        )

    baseline_ndcg = results[0]["queries_ndcg_at_k"]
    baseline_p95 = results[0]["latency_p95_ms"]

    best_dense_swap = max(
        results[1:4],
        key=lambda r: r["queries_ndcg_at_k"],
    )
    best_ce_swap = max(
        results[4:6],
        key=lambda r: r["queries_ndcg_at_k"],
    )
    pilot_results = list(results)
    best_pilot_row = max(pilot_results, key=lambda r: r["queries_ndcg_at_k"])

    mixed_id = "mixed_best_dense_best_ce"
    print(f"=== {mixed_id} dense={best_dense_swap['dense_model']} ce={best_ce_swap['cross_encoder_model']} ===", flush=True)
    results.append(
        _run_one_config(
            mixed_id,
            best_dense_swap["dense_model"],
            best_ce_swap["cross_encoder_model"],
            cases_queries,
            cases_402,
            search_cases,
            calendar_by_id,
            catalog,
        )
    )

    phase2_ran = False
    if args.phase2 and best_pilot_row["queries_ndcg_at_k"] - baseline_ndcg >= args.phase2_min_delta:
        if best_pilot_row["latency_p95_ms"] <= baseline_p95 * args.phase2_max_p95_factor:
            phase2_ran = True
            extras: List[Tuple[str, str, str]] = [
                ("p2_mpnet_marco_l12", "all-mpnet-base-v2", "cross-encoder/ms-marco-MiniLM-L-12-v2"),
                ("p2_mpnet_bge_rerank", "all-mpnet-base-v2", "BAAI/bge-reranker-base"),
                ("p2_bge_marco_l12", "BAAI/bge-base-en-v1.5", "cross-encoder/ms-marco-MiniLM-L-12-v2"),
                ("p2_bge_bge_rerank", "BAAI/bge-base-en-v1.5", "BAAI/bge-reranker-base"),
            ]
            for cid, d, c in extras:
                print(f"=== phase2 {cid} ===", flush=True)
                results.append(
                    _run_one_config(
                        cid, d, c,
                        cases_queries, cases_402, search_cases,
                        calendar_by_id, catalog,
                    )
                )

    eligible = [
        r
        for r in results
        if r["latency_p95_ms"] <= baseline_p95 * args.phase2_max_p95_factor
    ]
    winner_pool = eligible if eligible else results
    winner = max(winner_pool, key=lambda r: r["queries_ndcg_at_k"])

    phase2_skip_reason: Optional[str] = None
    if args.phase2 and not phase2_ran:
        if best_pilot_row["queries_ndcg_at_k"] - baseline_ndcg < args.phase2_min_delta:
            phase2_skip_reason = "quality_delta_below_threshold"
        elif best_pilot_row["latency_p95_ms"] > baseline_p95 * args.phase2_max_p95_factor:
            phase2_skip_reason = "latency_p95_too_high_for_trigger_config"
        else:
            phase2_skip_reason = "unknown"

    summary = {
        "top_k_graded": TOP_K,
        "fixed_weights": FIXED_WEIGHTS,
        "baseline_queries_ndcg": baseline_ndcg,
        "baseline_latency_p95_ms": baseline_p95,
        "phase2_ran": phase2_ran,
        "phase2_skip_reason": phase2_skip_reason,
        "winner_balanced_config_id": winner["config_id"],
        "winner_balanced_dense": winner["dense_model"],
        "winner_balanced_cross_encoder": winner["cross_encoder_model"],
        "recommendation_notes": [],
        "results": results,
    }

    latency_ok = winner["latency_p95_ms"] <= baseline_p95 * args.phase2_max_p95_factor
    quality_ok = winner["queries_ndcg_at_k"] - baseline_ndcg >= args.phase2_min_delta
    if quality_ok and latency_ok:
        summary["recommendation_notes"].append(
            f"Candidate production pair: dense={winner['dense_model']} ce={winner['cross_encoder_model']} "
            f"(NDCG@15 {winner['queries_ndcg_at_k']:.4f} vs baseline {baseline_ndcg:.4f}; "
            f"p95 {winner['latency_p95_ms']:.1f}ms vs {baseline_p95:.1f}ms)."
        )
    else:
        summary["recommendation_notes"].append(
            "Keep defaults: best eligible config did not clear both quality-delta and latency guard vs baseline."
        )

    out_json = args.output_dir / "model_sweep_summary.json"
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        f.write("\n")

    csv_path = args.output_dir / "model_sweep_leaderboard.csv"
    keys = list(results[0].keys())
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        import csv
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(results)

    print("Wrote", csv_path)
    print("Wrote", out_json)

    set_recommender_model_overrides(dense=None, cross_encoder=None)


if __name__ == "__main__":
    main()
