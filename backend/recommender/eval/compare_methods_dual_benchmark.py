#!/usr/bin/env python3
"""Run dual-benchmark comparison: graded internal eval + calendar baseline.

See DUAL_BENCHMARK.md for metric definitions.

Usage (from backend/):
  python recommender/eval/compare_methods_dual_benchmark.py \\
    --output-dir recommender/eval/reports

  python recommender/eval/compare_methods_dual_benchmark.py --top-k 10 --methods cosine,dense
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import defaultdict
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from recommender.main import get_recommendations  # noqa: E402
from recommender.eval.run_weight_sweep import (  # noqa: E402
    EVAL_BACKEND_METHODS,
    aggregate_metrics,
    evaluate_case,
    normalize_code,
    segment_metrics,
)

DEFAULT_METHODS = (
    "cosine",
    "dense",
    "hybrid_bm25_dense",
    "cross_encoder_rerank",
    "hybrid_ce_rrf_fused",
    "hybrid_rerank_graph",
)

_STOP = frozenset(
    "a an and are as at be been being by for from has have had in is it its of on or "
    "that the these they this those to was were will with would could should may might "
    "must can do does did into through during before after the".split()
)

_TOKEN_RE = re.compile(r"[A-Za-z]{2,}\d{0,3}[A-Za-z]?|\w+", re.UNICODE)
_CODE_FROM_TITLE_RE = re.compile(r"^([A-Z]{2,}\d{3,}[A-Z]?|[A-Z]{2,}\d{2,}[A-Z])")


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _tokenize(text: str) -> Set[str]:
    if not text:
        return set()
    return {t.lower() for t in _TOKEN_RE.findall(text) if len(t) > 1 and t.lower() not in _STOP}


def _load_course_snippets(catalog_path: Path) -> Dict[str, Tuple[str, str]]:
    """Map normalized course code -> (title, description)."""
    raw = _load_json(catalog_path)
    out: Dict[str, Tuple[str, str]] = {}
    for code, info in (raw or {}).items():
        c = normalize_code(str(code))
        title = (info or {}).get("title") or ""
        desc = (info or {}).get("description") or ""
        out[c] = (str(title), str(desc))
    return out


def _parse_calendar_row_code(row: Dict[str, str]) -> Optional[str]:
    code = (row.get("course_code") or "").strip().upper().replace(" ", "")
    if code:
        return normalize_code(code)
    title = row.get("title") or ""
    m = _CODE_FROM_TITLE_RE.match(title.strip())
    if m:
        return normalize_code(m.group(1))
    return None


def _load_calendar_lists(csv_path: Path) -> Dict[str, List[str]]:
    """query_id -> ordered list of normalized course codes (top-N as in file)."""
    by_id: Dict[str, List[str]] = defaultdict(list)
    if not csv_path.is_file():
        return {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            qid = (row.get("query_id") or "").strip()
            if not qid:
                continue
            err = (row.get("error") or "").strip()
            if err == "no_results":
                continue
            code = _parse_calendar_row_code(row)
            if code:
                by_id[qid].append(code)
    return dict(by_id)


def _overlap_metrics(
    method_ranked: List[str],
    calendar_ranked: List[str],
    k: int,
) -> Tuple[int, float]:
    m_set = set(method_ranked[:k])
    c_set = set(calendar_ranked[:k])
    overlap = m_set & c_set
    n_ov = len(overlap)
    if not overlap:
        return n_ov, 0.0
    rsum = 0.0
    for code in overlap:
        try:
            idx = method_ranked[:k].index(code) + 1
            rsum += 1.0 / float(idx)
        except ValueError:
            continue
    return n_ov, rsum / float(len(overlap))


def _sets_topk(a: List[str], b: List[str], k: int) -> Tuple[Set[str], Set[str]]:
    return set(a[:k]), set(b[:k])


def _jaccard_at_k(method_ranked: List[str], calendar_ranked: List[str], k: int) -> float:
    m_set, c_set = _sets_topk(method_ranked, calendar_ranked, k)
    union = m_set | c_set
    if not union:
        return 0.0
    return len(m_set & c_set) / float(len(union))


def _mror_intersection(ranked: List[str], intersection: Set[str], k: int) -> float:
    """Mean reciprocal rank in `ranked[:k]` over codes in intersection (0 if empty)."""
    if not intersection:
        return 0.0
    top = ranked[:k]
    s = 0.0
    n = 0
    for code in intersection:
        try:
            idx = top.index(code) + 1
            s += 1.0 / float(idx)
            n += 1
        except ValueError:
            continue
    return s / float(n) if n else 0.0


def _calendar_coverage_scores(
    method_ranked: List[str], calendar_ranked: List[str], k: int
) -> Tuple[float, float, int]:
    """Returns (calendar_set_recall, method_set_recall, overlap_count).

    *calendar_set_recall* = fraction of distinct calendar top-k codes that appear in method top-k.
    *method_set_recall* = fraction of distinct method top-k codes that also appear in calendar top-k.

    These treat the calendar as a **weak, unfiltered keyword bag** (not ground truth)—useful
    when major/term do not match the calendar UI.
    """
    m_set, c_set = _sets_topk(method_ranked, calendar_ranked, k)
    inter = m_set & c_set
    n = len(inter)
    cal_rec = n / float(len(c_set)) if c_set else 0.0
    met_rec = n / float(len(m_set)) if m_set else 0.0
    return cal_rec, met_rec, n


def _lexical_avg_for_ranked(
    ranked: List[str],
    catalog: Dict[str, Tuple[str, str]],
    query_tokens: Set[str],
    k: int,
) -> float:
    if not query_tokens:
        return 0.0
    scores = []
    for code in ranked[:k]:
        tit, desc = catalog.get(code, ("", ""))
        blob = f"{tit} {desc}"
        ct = _tokenize(blob)
        if not ct:
            scores.append(0.0)
            continue
        scores.append(len(query_tokens & ct) / float(math.sqrt(len(query_tokens)) + 1e-9))
    return sum(scores) / float(len(scores)) if scores else 0.0


def _composite(
    overlap_n: int,
    mror: float,
    lex: float,
    w_ov: float,
    w_mror: float,
    w_lex: float,
) -> float:
    return w_ov * float(overlap_n) + w_mror * mror + w_lex * lex


def _graded_cases(cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for c in cases:
        gr = c.get("graded_relevance") or {}
        if any(float(v) > 0 for v in gr.values()):
            out.append(c)
    return out


def _nonstem_case(case: Dict[str, Any]) -> bool:
    seg = (case.get("segment") or "").lower()
    return seg in ("non_stem", "breadth", "test_plan_402_nonstem")


def run_internal_track(
    cases: List[Dict[str, Any]],
    methods: List[str],
    top_k: int,
    weight_overrides: Optional[Dict[str, Dict[str, float]]],
) -> Dict[str, Any]:
    graded = _graded_cases(cases)
    by_method: Dict[str, Any] = {}
    wo: Dict[str, Dict[str, float]] = weight_overrides or {}
    for method in methods:
        rows = []
        with redirect_stdout(StringIO()):
            for case in graded:
                rows.append(evaluate_case(case, wo, top_k=top_k, method=method))
        nonstem_rows = [r for r, c in zip(rows, graded) if _nonstem_case(c)]
        by_method[method] = {
            "cases_evaluated": len(graded),
            "macro": aggregate_metrics(rows),
            "segment_metrics": segment_metrics(rows),
            "non_stem_labeled_macro": aggregate_metrics(nonstem_rows) if nonstem_rows else None,
            "per_case": rows,
        }
    return {"graded_case_count": len(graded), "methods": by_method}


def run_calendar_track(
    search_cases: List[Dict[str, Any]],
    calendar_by_id: Dict[str, List[str]],
    catalog: Dict[str, Tuple[str, str]],
    methods: List[str],
    top_k: int,
    weight_overrides: Optional[Dict[str, Dict[str, float]]],
    w_ov: float,
    w_mror: float,
    w_lex: float,
    eps: float,
    non_stem_query_weight: float,
) -> Dict[str, Any]:
    wo: Dict[str, Dict[str, float]] = weight_overrides or {}
    by_method: Dict[str, Any] = {}

    for method in methods:
        per_query: List[Dict[str, Any]] = []
        wins = weighted_wins = 0.0
        total = weighted_total = 0.0
        ns_wins = ns_weighted_wins = 0.0
        ns_total = ns_weighted_total = 0.0
        sum_jacc = sum_cal_rec = 0.0
        ns_sum_jacc = ns_sum_cal_rec = 0.0
        ns_count_metrics = 0

        for case in search_cases:
            qid = case.get("id")
            if not qid:
                continue
            if qid not in calendar_by_id:
                continue
            cal_ranked = calendar_by_id[qid]
            if not cal_ranked:
                continue
            query = case["query"]
            filters = case.get("filters") or {}
            q_tokens = _tokenize(query)

            with redirect_stdout(StringIO()):
                batch = get_recommendations(
                    [query],
                    data_file="course-api-new-data.json",
                    method=method,
                    filters=filters,
                    weight_overrides=wo,
                )
            ranked: List[str] = []
            if batch and batch[0]:
                ranked = [
                    normalize_code(item["course_code"])
                    for item in batch[0]
                    if item.get("method") == method
                ]

            m_ov, _legacy_m_mror = _overlap_metrics(ranked, cal_ranked, top_k)
            m_set, c_set = _sets_topk(ranked, cal_ranked, top_k)
            inter_set = m_set & c_set
            jacc = _jaccard_at_k(ranked, cal_ranked, top_k)
            m_mror_sym = _mror_intersection(ranked, inter_set, top_k)
            c_mror_sym = _mror_intersection(cal_ranked, inter_set, top_k)
            cal_rec, met_rec, n_inter = _calendar_coverage_scores(
                ranked, cal_ranked, top_k
            )

            m_lex = _lexical_avg_for_ranked(ranked, catalog, q_tokens, top_k)
            c_lex = _lexical_avg_for_ranked(cal_ranked, catalog, q_tokens, top_k)

            # Symmetric head-to-head: same Jaccard for both sides; MROR compares
            # ranking of the *shared* codes (fair vs calendar-self overlap inflation).
            m_comp = w_ov * jacc + w_mror * m_mror_sym + w_lex * m_lex
            c_comp = w_ov * jacc + w_mror * c_mror_sym + w_lex * c_lex
            
            sum_jacc += jacc
            sum_cal_rec += cal_rec
            outcome = "win" if m_comp > c_comp + eps else ("loss" if m_comp + eps < c_comp else "tie")

            seg = (case.get("segment") or "").lower()
            is_ns = seg == "non_stem"
            mult = non_stem_query_weight if is_ns else 1.0

            per_query.append(
                {
                    "query_id": qid,
                    "segment": case.get("segment"),
                    "query": query,
                    "outcome": outcome,
                    "method_composite": m_comp,
                    "calendar_composite": c_comp,
                    "jaccard_at_k": jacc,
                    "overlap_at_k": m_ov,
                    "overlap_distinct_count": n_inter,
                    "calendar_set_recall": cal_rec,
                    "method_set_recall_vs_calendar": met_rec,
                    "method_mror_symmetric": m_mror_sym,
                    "calendar_mror_symmetric": c_mror_sym,
                    "method_lex_avg": m_lex,
                    "calendar_lex_avg": c_lex,
                    "method_top_k": ranked[:top_k],
                    "calendar_top_k": cal_ranked[:top_k],
                }
            )

            total += 1.0
            weighted_total += mult
            if outcome == "win":
                wins += 1.0
                weighted_wins += mult
            if is_ns:
                ns_total += 1.0
                ns_weighted_total += mult
                ns_sum_jacc += jacc
                ns_sum_cal_rec += cal_rec
                ns_count_metrics += 1
                if outcome == "win":
                    ns_wins += 1.0
                    ns_weighted_wins += mult

        by_method[method] = {
            "queries_compared": int(total),
            "win_rate": wins / total if total else 0.0,
            "weighted_win_rate": weighted_wins / weighted_total if weighted_total else 0.0,
            "non_stem_queries": int(ns_total),
            "non_stem_win_rate": ns_wins / ns_total if ns_total else 0.0,
            "non_stem_weighted_win_rate": ns_weighted_wins / ns_weighted_total if ns_weighted_total else 0.0,
            "mean_jaccard_at_k": sum_jacc / total if total else 0.0,
            "mean_calendar_set_recall": sum_cal_rec / total if total else 0.0,
            "non_stem_mean_jaccard_at_k": ns_sum_jacc / ns_count_metrics if ns_count_metrics else 0.0,
            "non_stem_mean_calendar_set_recall": ns_sum_cal_rec / ns_count_metrics
            if ns_count_metrics
            else 0.0,
            "per_query": per_query,
        }

    return {"methods": by_method}


def _calendar_gates(
    calendar_block: Dict[str, Any],
    thr_ns: float,
    thr_overall: float,
) -> Dict[str, Any]:
    flags: Dict[str, Any] = {}
    for method, payload in calendar_block["methods"].items():
        o = payload["win_rate"]
        ns = payload["non_stem_win_rate"]
        flags[method] = {
            "pass_overall_calendar": o >= thr_overall,
            "pass_non_stem_calendar": ns >= thr_ns,
            "win_rate": o,
            "non_stem_win_rate": ns,
        }
    return flags


def _internal_gates(
    internal: Dict[str, Any],
    baseline: str,
    tolerance: float,
) -> Dict[str, Any]:
    methods_payload = internal["methods"]
    if baseline not in methods_payload:
        return {
            m: {
                "pass_internal": True,
                "skipped": True,
                "reason": "baseline_not_in_methods",
            }
            for m in methods_payload
        }
    base_macro = methods_payload[baseline]["macro"]
    base_ns = methods_payload[baseline]["non_stem_labeled_macro"] or {}
    base_ns_ndcg = float(base_ns.get("ndcg_at_k") or 0.0)
    flags: Dict[str, Any] = {}
    for m, payload in methods_payload.items():
        macro = payload["macro"]
        ns = payload["non_stem_labeled_macro"] or {}
        ns_ndcg = float(ns.get("ndcg_at_k") or 0.0)
        if m == baseline:
            flags[m] = {
                "pass_internal": True,
                "is_baseline": True,
                "pass_ndcg": True,
                "pass_mrr": True,
                "pass_non_stem_ndcg": True,
            }
            continue
        pass_ndcg = macro["ndcg_at_k"] >= base_macro["ndcg_at_k"] - tolerance
        pass_mrr = macro["mrr"] >= base_macro["mrr"] - tolerance
        pass_ns = ns_ndcg >= base_ns_ndcg - tolerance
        flags[m] = {
            "pass_internal": pass_ndcg and pass_mrr and pass_ns,
            "pass_ndcg_vs_baseline": pass_ndcg,
            "pass_mrr_vs_baseline": pass_mrr,
            "pass_non_stem_ndcg_vs_baseline": pass_ns,
            "is_baseline": False,
        }
    return flags


def _pick_winner(
    methods: List[str],
    internal: Optional[Dict[str, Any]],
    internal_gates: Dict[str, Any],
    calendar_gates: Dict[str, Any],
    calendar_block: Optional[Dict[str, Any]],
    skip_internal: bool,
    skip_calendar: bool,
) -> Optional[str]:
    candidates: List[Tuple[float, str]] = []
    for method in methods:
        ig = internal_gates.get(method, {})
        cg = calendar_gates.get(method, {})
        ig_ok = skip_internal or bool(ig.get("pass_internal"))
        cg_ok = skip_calendar or (
            bool(cg.get("pass_overall_calendar")) and bool(cg.get("pass_non_stem_calendar"))
        )
        if not (ig_ok and cg_ok):
            continue
        if internal is not None and method in internal["methods"]:
            score = internal["methods"][method]["macro"]["ndcg_at_k"]
        elif calendar_block is not None and method in calendar_block["methods"]:
            score = calendar_block["methods"][method]["non_stem_weighted_win_rate"]
        else:
            score = 0.0
        candidates.append((score, method))
    if not candidates:
        for method in methods:
            if internal is not None and method in internal["methods"]:
                candidates.append((internal["methods"][method]["macro"]["ndcg_at_k"], method))
            elif calendar_block is not None and method in calendar_block["methods"]:
                candidates.append(
                    (calendar_block["methods"][method]["non_stem_weighted_win_rate"], method)
                )
    candidates.sort(key=lambda x: (-x[0], x[1]))
    return candidates[0][1] if candidates else None


def _csv_serialize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in row.items():
        if isinstance(v, (list, dict)):
            out[k] = json.dumps(v, ensure_ascii=False)
        else:
            out[k] = v
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Dual-benchmark method comparison.")
    parser.add_argument(
        "--eval-set",
        type=Path,
        default=Path(__file__).resolve().parent / "queries.json",
        help="Labeled eval set (Track A).",
    )
    parser.add_argument(
        "--search-eval-set",
        type=Path,
        default=Path(__file__).resolve().parent / "search_evaluation_queries.json",
        help="24-query cases with filters (Track B); IDs must match calendar CSV.",
    )
    parser.add_argument(
        "--calendar-csv",
        type=Path,
        default=Path(__file__).resolve().parent / "uw_calendar_top10.csv",
        help="Academic calendar top-10 export.",
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=BACKEND_ROOT.parent / "data" / "courses" / "course-api-new-data.json",
    )
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument(
        "--methods",
        type=str,
        default=",".join(DEFAULT_METHODS),
        help="Comma-separated method names (ignored if --all-eval-methods).",
    )
    parser.add_argument(
        "--all-eval-methods",
        action="store_true",
        help=f"Run every backend in run_weight_sweep.EVAL_BACKEND_METHODS ({len(EVAL_BACKEND_METHODS)} methods).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "reports",
    )
    parser.add_argument("--w-overlap", type=float, default=2.0)
    parser.add_argument("--w-mror", type=float, default=1.0)
    parser.add_argument("--w-lex", type=float, default=1.0)
    parser.add_argument("--composite-epsilon", type=float, default=1e-6)
    parser.add_argument(
        "--non-stem-query-weight",
        type=float,
        default=1.5,
        help="Weight on wins for segment=non_stem in weighted_win_rate.",
    )
    parser.add_argument("--threshold-non-stem-win-rate", type=float, default=0.55)
    parser.add_argument("--threshold-overall-win-rate", type=float, default=0.50)
    parser.add_argument(
        "--weights-json",
        type=Path,
        default=None,
        help="Optional resolved weights JSON (single object) for sweeps.",
    )
    parser.add_argument(
        "--internal-baseline",
        type=str,
        default="cosine",
        help="Baseline method for Track A no-regression gate (must appear in --methods unless gate skipped).",
    )
    parser.add_argument(
        "--internal-tolerance",
        type=float,
        default=0.0,
        help="Allowed drop vs internal baseline on NDCG/MRR/non-STEM NDCG.",
    )
    parser.add_argument(
        "--skip-internal",
        action="store_true",
        help="Skip graded eval (Track A); internal gates reported as skipped.",
    )
    parser.add_argument(
        "--skip-calendar",
        action="store_true",
        help="Skip calendar comparison (Track B); calendar gates reported as skipped.",
    )
    args = parser.parse_args()

    if args.all_eval_methods:
        methods = list(EVAL_BACKEND_METHODS)
    else:
        methods = [m.strip() for m in args.methods.split(",") if m.strip()]

    weight_overrides: Optional[Dict[str, Dict[str, float]]] = None
    if args.weights_json and args.weights_json.is_file():
        weight_overrides = _load_json(args.weights_json)
        if not isinstance(weight_overrides, dict):
            raise SystemExit("--weights-json must be a JSON object of sections")

    catalog = _load_course_snippets(args.catalog)

    internal: Optional[Dict[str, Any]] = None
    if not args.skip_internal:
        eval_payload = _load_json(args.eval_set)
        cases = list(eval_payload.get("cases", []))
        internal = run_internal_track(cases, methods, args.top_k, weight_overrides)

    calendar_block: Optional[Dict[str, Any]] = None
    if not args.skip_calendar:
        search_payload = _load_json(args.search_eval_set)
        search_cases = list(search_payload.get("cases", []))
        calendar_by_id = _load_calendar_lists(args.calendar_csv)
        calendar_block = run_calendar_track(
            search_cases,
            calendar_by_id,
            catalog,
            methods,
            args.top_k,
            weight_overrides,
            args.w_overlap,
            args.w_mror,
            args.w_lex,
            args.composite_epsilon,
            args.non_stem_query_weight,
        )

    if internal is not None:
        internal_gates = _internal_gates(
            internal, args.internal_baseline, args.internal_tolerance
        )
    else:
        internal_gates = {
            m: {"pass_internal": True, "skipped_track_a": True} for m in methods
        }

    if calendar_block is not None:
        calendar_gates = _calendar_gates(
            calendar_block, args.threshold_non_stem_win_rate, args.threshold_overall_win_rate
        )
    else:
        calendar_gates = {
            m: {
                "pass_overall_calendar": True,
                "pass_non_stem_calendar": True,
                "skipped_track_b": True,
                "win_rate": None,
                "non_stem_win_rate": None,
            }
            for m in methods
        }

    winner = _pick_winner(
        methods,
        internal,
        internal_gates,
        calendar_gates,
        calendar_block,
        args.skip_internal,
        args.skip_calendar,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary: Dict[str, Any] = {
        "top_k": args.top_k,
        "methods": methods,
        "calendar_scoring": {
            "mode": "symmetric_jaccard_mror_lex",
            "diagnostics": [
                "jaccard_at_k",
                "calendar_set_recall",
                "method_set_recall_vs_calendar",
            ],
            "weak_baseline_note": "Calendar export ignores per-user major/term; use Track A for quality and these metrics for overlap diagnostics.",
        },
        "tracks": {"skip_internal": args.skip_internal, "skip_calendar": args.skip_calendar},
        "weights": {
            "w_overlap": args.w_overlap,
            "w_mror": args.w_mror,
            "w_lex": args.w_lex,
            "composite_epsilon": args.composite_epsilon,
            "non_stem_query_weight": args.non_stem_query_weight,
        },
        "gates": {
            "internal_baseline": args.internal_baseline,
            "internal_tolerance": args.internal_tolerance,
            "threshold_non_stem_win_rate": args.threshold_non_stem_win_rate,
            "threshold_overall_win_rate": args.threshold_overall_win_rate,
            "per_method": {
                m: {"internal": internal_gates.get(m), "calendar": calendar_gates.get(m)}
                for m in methods
            },
        },
        "recommended_winner": winner,
    }
    if internal is not None:
        summary["internal_track"] = {
            "eval_set": str(args.eval_set),
            "graded_case_count": internal["graded_case_count"],
            "per_method_macro": {m: internal["methods"][m]["macro"] for m in methods},
            "per_method_non_stem_labeled": {
                m: internal["methods"][m]["non_stem_labeled_macro"] for m in methods
            },
            "per_method_segments": {m: internal["methods"][m]["segment_metrics"] for m in methods},
        }
    else:
        summary["internal_track"] = {"skipped": True}

    if calendar_block is not None:
        summary["calendar_track"] = {
            "search_eval_set": str(args.search_eval_set),
            "calendar_csv": str(args.calendar_csv),
            "per_method": {
                m: {
                    k: v
                    for k, v in calendar_block["methods"][m].items()
                    if k != "per_query"
                }
                for m in methods
            },
            "non_stem_losses_by_method": {
                m: [
                    {
                        "query_id": r["query_id"],
                        "query": r["query"],
                        "outcome": r["outcome"],
                        "method_composite": r["method_composite"],
                        "calendar_composite": r["calendar_composite"],
                    }
                    for r in calendar_block["methods"][m]["per_query"]
                    if (r.get("segment") == "non_stem" and r.get("outcome") == "loss")
                ]
                for m in methods
            },
        }
    else:
        summary["calendar_track"] = {"skipped": True}

    summary_path = args.output_dir / "dual_benchmark_summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Leaderboard CSV: one row per method
    lb_path = args.output_dir / "dual_benchmark_leaderboard.csv"
    with lb_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "method",
                "internal_ndcg",
                "internal_recall",
                "internal_mrr",
                "internal_nonstem_ndcg",
                "pass_gate_internal",
                "calendar_win_rate",
                "calendar_weighted_win_rate",
                "calendar_non_stem_win_rate",
                "mean_jaccard_at_k",
                "mean_calendar_set_recall",
                "non_stem_mean_jaccard",
                "non_stem_mean_calendar_set_recall",
                "pass_gate_overall_calendar",
                "pass_gate_non_stem_calendar",
            ]
        )
        for m in methods:
            if internal is not None:
                macro = internal["methods"][m]["macro"]
                ns = internal["methods"][m]["non_stem_labeled_macro"] or {}
                i_ndcg = f"{macro['ndcg_at_k']:.6f}"
                i_rec = f"{macro['recall_at_k']:.6f}"
                i_mrr = f"{macro['mrr']:.6f}"
                i_ns = f"{(ns.get('ndcg_at_k') or 0):.6f}"
            else:
                i_ndcg = i_rec = i_mrr = i_ns = ""
            ig = internal_gates[m].get("pass_internal", True)
            if calendar_block is not None:
                cal = calendar_block["methods"][m]
                c_wr = f"{cal['win_rate']:.6f}"
                c_wwr = f"{cal['weighted_win_rate']:.6f}"
                c_nsw = f"{cal['non_stem_win_rate']:.6f}"
                mj = f"{cal['mean_jaccard_at_k']:.6f}"
                mcr = f"{cal['mean_calendar_set_recall']:.6f}"
                nsj = f"{cal['non_stem_mean_jaccard_at_k']:.6f}"
                nscr = f"{cal['non_stem_mean_calendar_set_recall']:.6f}"
            else:
                c_wr = c_wwr = c_nsw = mj = mcr = nsj = nscr = ""
            cg = calendar_gates[m]
            w.writerow(
                [
                    m,
                    i_ndcg,
                    i_rec,
                    i_mrr,
                    i_ns,
                    ig,
                    c_wr,
                    c_wwr,
                    c_nsw,
                    mj,
                    mcr,
                    nsj,
                    nscr,
                    cg.get("pass_overall_calendar", True),
                    cg.get("pass_non_stem_calendar", True),
                ]
            )

    # Per-query calendar detail (long CSV)
    detail_path = args.output_dir / "dual_benchmark_calendar_per_query.csv"
    if calendar_block is not None:
        fieldname_set: Set[str] = {"method"}
        for m in methods:
            for row in calendar_block["methods"][m]["per_query"]:
                flat = _csv_serialize_row(dict(row))
                flat["method"] = m
                fieldname_set.update(flat.keys())
        preferred = [
            "method",
            "query_id",
            "segment",
            "query",
            "outcome",
            "method_composite",
            "calendar_composite",
            "jaccard_at_k",
            "overlap_at_k",
            "overlap_distinct_count",
            "calendar_set_recall",
            "method_set_recall_vs_calendar",
            "method_mror_symmetric",
            "calendar_mror_symmetric",
            "method_lex_avg",
            "calendar_lex_avg",
            "method_top_k",
            "calendar_top_k",
        ]
        fieldnames = [c for c in preferred if c in fieldname_set] + sorted(
            fieldname_set.difference(preferred)
        )
        with detail_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for m in methods:
                for row in calendar_block["methods"][m]["per_query"]:
                    flat = _csv_serialize_row(dict(row))
                    flat["method"] = m
                    writer.writerow({k: flat.get(k, "") for k in fieldnames})
    else:
        detail_path.write_text(
            "skipped_track_b\n",
            encoding="utf-8",
        )

    # Labeled-eval per-case diagnostics
    internal_detail_path = args.output_dir / "dual_benchmark_internal_per_case.csv"
    if internal is not None:
        with internal_detail_path.open("w", encoding="utf-8", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(
                ["method", "case_id", "segment", "ndcg_at_k", "recall_at_k", "mrr", "result_count"]
            )
            for m in methods:
                for row in internal["methods"][m]["per_case"]:
                    wr.writerow(
                        [
                            m,
                            row.get("id"),
                            row.get("segment"),
                            f"{row['ndcg_at_k']:.6f}",
                            f"{row['recall_at_k']:.6f}",
                            f"{row['mrr']:.6f}",
                            row.get("result_count"),
                        ]
                    )
    else:
        internal_detail_path.write_text("skipped_track_a\n", encoding="utf-8")

    print("Dual-benchmark run complete.")
    print("Summary:", summary_path)
    print("Leaderboard:", lb_path)
    print("Calendar per-query:", detail_path)
    print("Internal per-case:", internal_detail_path)
    print("Recommended winner:", winner)


if __name__ == "__main__":
    main()
