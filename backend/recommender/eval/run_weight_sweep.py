#!/usr/bin/env python3
"""Offline sweep runner for search-weight tuning.

Usage examples:
  python recommender/eval/run_weight_sweep.py
  python recommender/eval/run_weight_sweep.py --candidates recommender/eval/candidates.json
  python recommender/eval/run_weight_sweep.py --method hybrid_bm25_dense
  python recommender/eval/run_weight_sweep.py --compare-methods --num-random 0
  python recommender/eval/run_weight_sweep.py --eval-set recommender/eval/test_plan_402.json --compare-methods --num-random 0
  python recommender/eval/run_weight_sweep.py --method hybrid_bm25_dense --append-method-candidates --num-random 12
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from recommender.main import get_recommendations  # noqa: E402
from recommender.eval.eval_filter_validation import validate_eval_cases_filter_policy  # noqa: E402
from recommender.search_weight_config import default_search_weights  # noqa: E402

# All backends accepted by get_recommendations(..., method=...) (keep in sync with scripts/run_search_evaluation_queries.py).
EVAL_BACKEND_METHODS: Tuple[str, ...] = (
    "cosine",
    "dense",
    "hybrid_bm25_dense",
    "cross_encoder_rerank",
    "hybrid_ce_rrf_fused",
    "hybrid_rerank_graph",
    "faiss",
    "mmr",
    "graph",
    "fuzzy_multi",
    "keyword_overlap",
)

# Primary methods for graded score tuning / regression (subset of EVAL_BACKEND_METHODS).
PRIMARY_GRADED_METHODS: Tuple[str, ...] = (
    "cosine",
    "dense",
    "hybrid_bm25_dense",
    "cross_encoder_rerank",
    "hybrid_ce_rrf_fused",
    "hybrid_rerank_graph",
)


def normalize_code(code: str) -> str:
    return (code or "").strip().upper().replace(" ", "")


def deep_merge(base: Dict[str, Dict[str, float]], delta: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    out = deepcopy(base)
    for section, values in (delta or {}).items():
        if section not in out or not isinstance(values, dict):
            continue
        for key, value in values.items():
            # Allow adding keys that exist in the current production default template
            # (forward-compatible sweeps for new hybrid knobs).
            template = default_search_weights().get(section) or {}
            if key not in out[section] and key not in template:
                continue
            out[section][key] = float(value)
    return out


def make_candidate_id(weights: Dict[str, Dict[str, float]]) -> str:
    ranking = weights["ranking"]
    global_weight = weights["global_weight"]
    base = (
        f"a{ranking['alpha']:.2f}_dept{ranking['same_department_boost']:.2f}"
        f"_g{global_weight['gamma_prereq']:.2f}-{global_weight['gamma_depth']:.2f}-{global_weight['gamma_minor']:.2f}"
    )
    hyb = weights.get("hybrid") or {}
    hyb_default = default_search_weights()["hybrid"]
    hy_parts: List[str] = []
    for key in sorted(hyb.keys()):
        if key not in hyb_default:
            continue
        if abs(float(hyb[key]) - float(hyb_default[key])) > 1e-9:
            hy_parts.append(f"{key[:4]}{float(hyb[key]):g}".replace(".", "p"))
    if hy_parts:
        base = base + "_H" + "-".join(hy_parts[:8])
    return base


def _ranking_grid() -> Dict[str, List[float]]:
    return {
        "min_similarity_cutoff": [0.15, 0.2, 0.25, 0.3, 0.35],
        "full_query_title_boost": [0.2, 0.35, 0.5, 0.65, 0.8],
        "phrase_title_boost": [0.15, 0.25, 0.35, 0.45, 0.55],
        "title_word_boost_per_overlap": [0.12, 0.2, 0.28, 0.36, 0.44],
        "title_word_boost_cap": [0.45, 0.6, 0.75, 0.9],
        "alpha": [0.1, 0.2, 0.3, 0.4, 0.5],
        "same_department_boost": [0.0, 0.2, 0.4, 0.6],
    }


def _global_grid() -> Dict[str, List[float]]:
    return {
        "gamma_prereq": [0.6, 0.8, 1.0, 1.2, 1.4],
        "gamma_depth": [0.0, 0.15, 0.3, 0.45, 0.6],
        "gamma_minor": [0.2, 0.35, 0.5, 0.65, 0.8],
    }


def _option_triplets() -> List[Tuple[float, float, float]]:
    return [
        (0.10, 0.07, 0.03),
        (0.12, 0.08, 0.04),
        (0.15, 0.10, 0.05),  # baseline
        (0.18, 0.12, 0.06),
        (0.22, 0.15, 0.08),
    ]


def _hybrid_grid() -> Dict[str, List[float]]:
    return {
        "rrf_k": [40.0, 50.0, 60.0, 70.0, 80.0],
        "rrf_weight_lexical": [0.75, 0.9, 1.0, 1.1, 1.25],
        "rrf_weight_dense": [0.75, 0.9, 1.0, 1.1, 1.25],
        "retrieval_k": [180.0, 220.0, 250.0, 280.0, 300.0, 320.0],
        "cross_encoder_pool": [80.0, 100.0, 120.0, 140.0, 150.0],
        "graph_rerank_pool": [70.0, 85.0, 100.0, 110.0, 120.0],
        "ce_fusion_w_ce": [0.45, 0.55, 0.65],
        "ce_fusion_w_rrf": [0.22, 0.30, 0.38],
        "ce_fusion_w_retrieval": [0.10, 0.15, 0.22],
    }


def method_conditional_candidate_overrides(method: str) -> List[Dict[str, Dict[str, float]]]:
    """Extra sweep candidates tailored to a retrieval backend family (use with --append-method-candidates)."""
    m = (method or "").strip()
    if m in ("cosine", "dense"):
        return [
            {"ranking": {"min_similarity_cutoff": 0.20, "full_query_title_boost": 0.65}},
            {"ranking": {"phrase_title_boost": 0.45, "title_word_boost_per_overlap": 0.36}},
            {"ranking": {"alpha": 0.30, "same_department_boost": 0.40}},
            {"global_weight": {"gamma_prereq": 0.9, "gamma_depth": 0.25, "gamma_minor": 0.45}},
        ]
    if m == "hybrid_bm25_dense":
        return [
            {"hybrid": {"retrieval_k": 300.0, "rrf_weight_lexical": 1.15, "rrf_weight_dense": 0.90}},
            {"hybrid": {"rrf_k": 50.0, "retrieval_k": 280.0}},
            {"hybrid": {"rrf_k": 55.0, "rrf_weight_lexical": 1.10, "rrf_weight_dense": 0.95}},
            {"ranking": {"min_similarity_cutoff": 0.22}},
        ]
    if m in ("cross_encoder_rerank", "hybrid_ce_rrf_fused"):
        return [
            {"hybrid": {"cross_encoder_pool": 140.0, "retrieval_k": 300.0}},
            {"hybrid": {"cross_encoder_pool": 150.0, "rrf_weight_lexical": 1.10}},
            {"hybrid": {"rrf_k": 50.0, "cross_encoder_pool": 130.0}},
            {
                "hybrid": {
                    "ce_fusion_w_ce": 0.50,
                    "ce_fusion_w_rrf": 0.35,
                    "ce_fusion_w_retrieval": 0.15,
                }
            },
        ]
    if m == "hybrid_rerank_graph":
        return [
            {"hybrid": {"graph_rerank_pool": 120.0, "cross_encoder_pool": 130.0}},
            {"hybrid": {"graph_rerank_pool": 110.0, "retrieval_k": 290.0}},
            {"ranking": {"alpha": 0.35, "same_department_boost": 0.50}},
        ]
    return []


def local_search_jitter(
    base_overrides: List[Dict[str, Dict[str, float]]],
    seed: int,
    replicas: int = 8,
) -> List[Dict[str, Dict[str, float]]]:
    """Small random perturbations around hybrid knobs for local refinement."""
    rng = random.Random(seed)
    hy_keys = (
        "rrf_k",
        "rrf_weight_lexical",
        "rrf_weight_dense",
        "retrieval_k",
        "cross_encoder_pool",
        "graph_rerank_pool",
    )
    out: List[Dict[str, Dict[str, float]]] = []
    for tpl in base_overrides:
        if "hybrid" not in tpl:
            continue
        for _ in range(replicas):
            hybrid = dict(tpl["hybrid"])
            # jitter 1–2 keys
            for _j in range(rng.randint(1, 2)):
                k = rng.choice(hy_keys)
                if k not in hybrid:
                    continue
                delta = rng.choice([-5.0, -2.0, 2.0, 5.0, 8.0])
                hybrid[k] = max(10.0, float(hybrid[k]) + delta)
            out.append({"hybrid": hybrid})
    return out


def _dedupe_overrides(
    overrides: List[Dict[str, Dict[str, float]]],
) -> List[Dict[str, Dict[str, float]]]:
    seen = set()
    output = []
    for override in overrides:
        key = json.dumps(override, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        output.append(override)
    return output


def _sample_random_overrides(num_random: int, seed: int) -> List[Dict[str, Dict[str, float]]]:
    rng = random.Random(seed)
    ranking_grid = _ranking_grid()
    global_grid = _global_grid()
    hybrid_grid = _hybrid_grid()
    option_sets = _option_triplets()
    out: List[Dict[str, Dict[str, float]]] = []

    for _ in range(max(0, num_random)):
        tier1, tier2, tier3 = rng.choice(option_sets)
        cand: Dict[str, Dict[str, float]] = {
            "ranking": {k: rng.choice(v) for k, v in ranking_grid.items()},
            "global_weight": {k: rng.choice(v) for k, v in global_grid.items()},
            "option_boost": {
                "tier1": tier1,
                "tier2": tier2,
                "tier3": tier3,
            },
        }
        if rng.random() < 0.45:
            cand["hybrid"] = {k: rng.choice(v) for k, v in hybrid_grid.items()}
        out.append(cand)
    return out


def default_candidate_overrides(seed: int = 42, num_random: int = 48) -> List[Dict[str, Dict[str, float]]]:
    """Deterministic + random sweep that covers all ranking/global/personal weights."""
    baseline = default_search_weights()
    ranking_base = baseline["ranking"]
    global_base = baseline["global_weight"]
    option_base = baseline["option_boost"]
    hybrid_base = baseline["hybrid"]

    candidates: List[Dict[str, Dict[str, float]]] = [{}]

    # One-at-a-time deterministic sweeps for every ranking/global knob.
    for key, values in _ranking_grid().items():
        for value in values:
            if abs(value - ranking_base[key]) < 1e-12:
                continue
            candidates.append({"ranking": {key: value}})

    for key, values in _global_grid().items():
        for value in values:
            if abs(value - global_base[key]) < 1e-12:
                continue
            candidates.append({"global_weight": {key: value}})

    for tier1, tier2, tier3 in _option_triplets():
        if (
            abs(tier1 - option_base["tier1"]) < 1e-12
            and abs(tier2 - option_base["tier2"]) < 1e-12
            and abs(tier3 - option_base["tier3"]) < 1e-12
        ):
            continue
        candidates.append(
            {
                "option_boost": {
                    "tier1": tier1,
                    "tier2": tier2,
                    "tier3": tier3,
                }
            }
        )

    for key, values in _hybrid_grid().items():
        for value in values:
            if abs(value - hybrid_base[key]) < 1e-12:
                continue
            candidates.append({"hybrid": {key: value}})

    # Coupled interaction candidates and random mixes.
    candidates.extend(
        [
            {"ranking": {"alpha": 0.2, "same_department_boost": 0.2}},
            {"ranking": {"alpha": 0.4, "same_department_boost": 0.6}},
            {"ranking": {"full_query_title_boost": 0.65, "phrase_title_boost": 0.45}},
            {"ranking": {"title_word_boost_per_overlap": 0.36, "title_word_boost_cap": 0.9}},
            {"global_weight": {"gamma_prereq": 1.2, "gamma_depth": 0.15, "gamma_minor": 0.65}},
            {"global_weight": {"gamma_prereq": 0.8, "gamma_depth": 0.45, "gamma_minor": 0.35}},
            {"hybrid": {"rrf_weight_lexical": 1.15, "rrf_weight_dense": 0.9}},
            {"hybrid": {"retrieval_k": 300.0, "cross_encoder_pool": 140.0}},
            {"hybrid": {"rrf_k": 50.0, "graph_rerank_pool": 110.0}},
        ]
    )
    candidates.extend(_sample_random_overrides(num_random=num_random, seed=seed))
    return _dedupe_overrides(candidates)


def dcg_at_k(grades: Iterable[float], k: int) -> float:
    score = 0.0
    for i, grade in enumerate(list(grades)[:k]):
        score += (2.0 ** grade - 1.0) / math.log2(i + 2.0)
    return score


def ndcg_at_k(ranked_codes: List[str], relevance: Dict[str, float], k: int) -> float:
    ranked_grades = [float(relevance.get(normalize_code(c), 0.0)) for c in ranked_codes]
    dcg = dcg_at_k(ranked_grades, k)
    ideal = sorted((float(v) for v in relevance.values()), reverse=True)
    idcg = dcg_at_k(ideal, k)
    if idcg <= 0.0:
        return 0.0
    return dcg / idcg


def recall_at_k(ranked_codes: List[str], relevance: Dict[str, float], k: int) -> float:
    positives = {normalize_code(c) for c, rel in relevance.items() if float(rel) > 0.0}
    if not positives:
        return 0.0
    retrieved = {normalize_code(c) for c in ranked_codes[:k]}
    return len(positives & retrieved) / float(len(positives))


def mrr(ranked_codes: List[str], relevance: Dict[str, float]) -> float:
    positives = {normalize_code(c) for c, rel in relevance.items() if float(rel) > 0.0}
    for i, code in enumerate(ranked_codes, start=1):
        if normalize_code(code) in positives:
            return 1.0 / float(i)
    return 0.0


def evaluate_case(
    case: Dict[str, Any],
    weight_overrides: Dict[str, Dict[str, float]],
    top_k: int,
    method: str = "cosine",
) -> Dict[str, Any]:
    query = case["query"]
    filters = case.get("filters", {})
    graded_relevance = {normalize_code(k): float(v) for k, v in case.get("graded_relevance", {}).items()}

    results = get_recommendations(
        [query],
        data_file="course-api-new-data.json",
        method=method,
        filters=filters,
        weight_overrides=weight_overrides,
    )
    ranked = [normalize_code(item["course_code"]) for item in results[0] if item.get("method") == method]

    return {
        "id": case.get("id"),
        "segment": case.get("segment", "unknown"),
        "ndcg_at_k": ndcg_at_k(ranked, graded_relevance, top_k),
        "recall_at_k": recall_at_k(ranked, graded_relevance, top_k),
        "mrr": mrr(ranked, graded_relevance),
        "result_count": len(ranked),
    }


def aggregate_metrics(per_case: List[Dict[str, Any]]) -> Dict[str, float]:
    if not per_case:
        return {"ndcg_at_k": 0.0, "recall_at_k": 0.0, "mrr": 0.0}
    n = float(len(per_case))
    return {
        "ndcg_at_k": sum(x["ndcg_at_k"] for x in per_case) / n,
        "recall_at_k": sum(x["recall_at_k"] for x in per_case) / n,
        "mrr": sum(x["mrr"] for x in per_case) / n,
    }


def segment_metrics(per_case: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for row in per_case:
        buckets.setdefault(row["segment"], []).append(row)
    return {segment: aggregate_metrics(rows) for segment, rows in buckets.items()}


def run_sweep(
    cases: List[Dict[str, Any]],
    top_k: int,
    candidate_overrides: List[Dict[str, Dict[str, float]]],
    method: str = "cosine",
) -> List[Dict[str, Any]]:
    baseline = default_search_weights()
    outputs: List[Dict[str, Any]] = []
    for idx, override in enumerate(candidate_overrides):
        merged = deep_merge(baseline, override)
        candidate_name = f"candidate_{idx:02d}_{make_candidate_id(merged)}"
        per_case = [evaluate_case(case, merged, top_k=top_k, method=method) for case in cases]
        macro = aggregate_metrics(per_case)
        outputs.append(
            {
                "candidate": candidate_name,
                "override": override,
                "resolved_weights": merged,
                "method": method,
                "metrics": macro,
                "segment_metrics": segment_metrics(per_case),
                "per_case": per_case,
            }
        )
    outputs.sort(key=lambda row: row["metrics"]["ndcg_at_k"], reverse=True)
    return outputs


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["candidate", "ndcg_at_k", "recall_at_k", "mrr"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "candidate": row["candidate"],
                    "ndcg_at_k": f"{row['metrics']['ndcg_at_k']:.6f}",
                    "recall_at_k": f"{row['metrics']['recall_at_k']:.6f}",
                    "mrr": f"{row['metrics']['mrr']:.6f}",
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run offline search-weight sweeps.")
    parser.add_argument(
        "--eval-set",
        type=Path,
        default=Path(__file__).resolve().parent / "queries.json",
        help="Path to evaluation set JSON.",
    )
    parser.add_argument(
        "--candidates",
        type=Path,
        default=None,
        help="Optional path to candidate overrides JSON (list of override objects).",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=15,
        help="Cutoff used for NDCG/Recall.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for candidate generation.",
    )
    parser.add_argument(
        "--num-random",
        type=int,
        default=48,
        help="How many random full-combination candidates to include (when --candidates is not provided).",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path(__file__).resolve().parent / "weight_sweep_results.json",
        help="Output JSON file path.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path(__file__).resolve().parent / "weight_sweep_leaderboard.csv",
        help="Output CSV leaderboard path.",
    )
    parser.add_argument(
        "--method",
        type=str,
        default="cosine",
        choices=list(EVAL_BACKEND_METHODS),
        help="Retrieval backend to evaluate (default: cosine).",
    )
    parser.add_argument(
        "--compare-methods",
        action="store_true",
        help=(
            "Print NDCG/Recall/MRR for every backend in EVAL_BACKEND_METHODS with baseline weights only "
            "(use e.g. --num-random 0)."
        ),
    )
    parser.add_argument(
        "--skip-filter-validation",
        action="store_true",
        help="Skip breadth/non-STEM include_other_depts policy checks on the eval set.",
    )
    parser.add_argument(
        "--append-method-candidates",
        action="store_true",
        help="Append method-family override pack for the selected --method (see method_conditional_candidate_overrides).",
    )
    parser.add_argument(
        "--local-search-replicas",
        type=int,
        default=0,
        help="Add N jitters around a few hybrid-only candidates (0 disables).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    random.seed(args.seed)

    eval_payload = read_json(args.eval_set)
    cases = list(eval_payload.get("cases", []))
    if not cases:
        raise ValueError("Evaluation set has no cases.")

    if not args.skip_filter_validation:
        policy_errors = validate_eval_cases_filter_policy(cases)
        if policy_errors:
            raise ValueError(
                "Eval set failed filter policy validation:\n"
                + "\n".join(policy_errors[:25])
                + (f"\n... and {len(policy_errors) - 25} more" if len(policy_errors) > 25 else "")
            )

    if args.candidates:
        candidate_overrides = read_json(args.candidates)
        if not isinstance(candidate_overrides, list):
            raise ValueError("Candidates file must be a JSON list of override objects.")
    else:
        candidate_overrides = default_candidate_overrides(seed=args.seed, num_random=args.num_random)

    if args.append_method_candidates:
        candidate_overrides = _dedupe_overrides(
            candidate_overrides + method_conditional_candidate_overrides(args.method)
        )
    if args.local_search_replicas > 0:
        hybrid_pick = [c for c in candidate_overrides if c.get("hybrid")][:6]
        candidate_overrides = _dedupe_overrides(
            candidate_overrides
            + local_search_jitter(
                hybrid_pick,
                seed=args.seed + 777,
                replicas=args.local_search_replicas,
            )
        )

    results = run_sweep(
        cases,
        top_k=args.top_k,
        candidate_overrides=candidate_overrides,
        method=args.method,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)

    with args.output_json.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "top_k": args.top_k,
                "eval_set": str(args.eval_set),
                "candidates_evaluated": len(candidate_overrides),
                "method": args.method,
                "results": results,
            },
            handle,
            indent=2,
        )
    write_csv(args.output_csv, results)

    best = results[0]
    print("Top candidate:", best["candidate"])
    print(
        "Metrics:",
        f"NDCG@{args.top_k}={best['metrics']['ndcg_at_k']:.4f}",
        f"Recall@{args.top_k}={best['metrics']['recall_at_k']:.4f}",
        f"MRR={best['metrics']['mrr']:.4f}",
    )
    print("Wrote:", args.output_json)
    print("Wrote:", args.output_csv)
    print("Candidates evaluated:", len(candidate_overrides))
    print("Top 5 candidates:")
    for row in results[:5]:
        print(
            f"  {row['candidate']}: "
            f"NDCG@{args.top_k}={row['metrics']['ndcg_at_k']:.4f}, "
            f"Recall@{args.top_k}={row['metrics']['recall_at_k']:.4f}, "
            f"MRR={row['metrics']['mrr']:.4f}"
        )

    if args.compare_methods:
        print("Method comparison (baseline weights, top candidate each):")
        for m in EVAL_BACKEND_METHODS:
            baseline_rows = run_sweep(cases, args.top_k, [{}], method=m)
            row0 = baseline_rows[0]
            print(
                f"  {m}: "
                f"NDCG@{args.top_k}={row0['metrics']['ndcg_at_k']:.4f}, "
                f"Recall@{args.top_k}={row0['metrics']['recall_at_k']:.4f}, "
                f"MRR={row0['metrics']['mrr']:.4f}"
            )


if __name__ == "__main__":
    main()

