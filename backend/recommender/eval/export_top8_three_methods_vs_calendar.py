#!/usr/bin/env python3
"""Export top-8 ranked courses: primary backends + cosine vs UW calendar CSV (S1–S12, N1–N12).

STEM: include_other_depts=false (explore off). Non-STEM: include_other_depts=true (explore on).
Default min_similarity_cutoff=0.25 via weight_overrides.

Usage (from backend/):
  python recommender/eval/export_top8_three_methods_vs_calendar.py
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from recommender.main import get_recommendations  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parent

METHODS: Tuple[str, ...] = (
    "hybrid_ce_rrf_fused",
    "cross_encoder_rerank",
    "hybrid_bm25_dense",
    "cosine",
)

METHOD_SHORT: Dict[str, str] = {
    "hybrid_ce_rrf_fused": "fused",
    "cross_encoder_rerank": "ce_rerank",
    "hybrid_bm25_dense": "bm25_dense",
    "cosine": "cosine",
}

CASE_ORDER: Tuple[Tuple[str, str], ...] = (
    ("S1", "stem_s1_machine_learning"),
    ("S2", "stem_s2_heat_transfer_thermodynamics"),
    ("S3", "stem_s3_digital_logic_architecture"),
    ("S4", "stem_s4_materials_science"),
    ("S5", "stem_s5_fluid_mechanics_aerodynamics"),
    ("S6", "stem_s6_signals_systems"),
    ("S7", "stem_s7_neural_networks"),
    ("S8", "stem_s8_polymers_composites"),
    ("S9", "stem_s9_probability_statistics"),
    ("S10", "stem_s10_control_robotics"),
    ("S11", "stem_s11_circuits_embedded"),
    ("S12", "stem_s12_optimization_or"),
    ("N1", "breadth_n1_ethics_technology_society"),
    ("N2", "breadth_n2_professional_communication"),
    ("N3", "breadth_n3_psychology_decision_human_factors"),
    ("N4", "breadth_n4_economics_innovation"),
    ("N5", "breadth_n5_history_of_science"),
    ("N6", "breadth_n6_sustainability_policy_climate"),
    ("N7", "breadth_n7_law_ip_technology"),
    ("N8", "breadth_n8_leadership_teamwork_pm"),
    ("N9", "breadth_n9_urban_planning_community"),
    ("N10", "breadth_n10_philosophy_mind_logic"),
    ("N11", "breadth_n11_creative_writing"),
    ("N12", "breadth_n12_modern_film_studies"),
)


def _read_search_eval(path: Path) -> Dict[str, Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    out: Dict[str, Dict[str, Any]] = {}
    for c in data.get("cases", []):
        cid = c.get("id")
        if cid:
            out[str(cid)] = c
    return out


def _calendar_code(row: Dict[str, str]) -> Optional[str]:
    code = (row.get("course_code") or "").strip().upper().replace(" ", "")
    return code if code else None


def load_calendar_top(
    csv_path: Path,
    top_n: int,
) -> Dict[str, List[Tuple[str, str]]]:
    """query_id -> up to top_n (code, title) rows in rank order."""
    from collections import defaultdict

    bucket: Dict[str, List[Tuple[int, str, str]]] = defaultdict(list)
    if not csv_path.is_file():
        return {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            qid = (row.get("query_id") or "").strip()
            if not qid:
                continue
            if (row.get("error") or "").strip() == "no_results":
                continue
            code = _calendar_code(row)
            if not code:
                continue
            try:
                rnk = int(row.get("rank") or 0)
            except ValueError:
                rnk = 0
            title = (row.get("title") or "").strip()
            bucket[qid].append((rnk, code, title))
    out: Dict[str, List[Tuple[str, str]]] = {}
    for qid, rows in bucket.items():
        rows.sort(key=lambda x: x[0])
        slim = [(c, t) for _, c, t in rows[:top_n]]
        if slim:
            out[qid] = slim
    return out


def _method_rows_for_query(
    query: str,
    method: str,
    filters: Dict[str, Any],
    weight_overrides: Dict[str, Dict[str, float]],
    top_n: int,
) -> List[Dict[str, Any]]:
    with redirect_stdout(io.StringIO()):
        batch = get_recommendations(
            [query],
            data_file="course-api-new-data.json",
            method=method,
            filters=filters,
            weight_overrides=weight_overrides,
        )
    rows: List[Dict[str, Any]] = []
    if not batch or not batch[0]:
        return rows
    for item in batch[0]:
        if item.get("method") != method:
            continue
        rows.append(item)
        if len(rows) >= top_n:
            break
    return rows


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--search-eval",
        type=Path,
        default=EVAL_DIR / "search_evaluation_queries.json",
    )
    p.add_argument(
        "--calendar-csv",
        type=Path,
        default=EVAL_DIR / "uw_calendar_top10.csv",
    )
    p.add_argument("--top-n", type=int, default=8)
    p.add_argument(
        "--min-similarity-cutoff",
        type=float,
        default=0.25,
    )
    p.add_argument(
        "--output",
        type=Path,
        default=EVAL_DIR / "top8_three_methods_vs_uw_calendar.csv",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cases_by_id = _read_search_eval(args.search_eval)
    cal = load_calendar_top(args.calendar_csv, args.top_n)
    wo = {"ranking": {"min_similarity_cutoff": float(args.min_similarity_cutoff)}}

    fieldnames = [
        "query_prompt",
        "query_id",
        "segment",
        "explore_include_other_depts",
        "query_text",
        "rank",
    ]
    for m in METHODS:
        short = METHOD_SHORT[m]
        fieldnames.extend([f"{short}_course_code", f"{short}_title", f"{short}_score"])
    fieldnames.extend(["uw_calendar_course_code", "uw_calendar_title"])

    out_rows: List[Dict[str, Any]] = []

    for prompt, cid in CASE_ORDER:
        case = cases_by_id.get(cid)
        if not case:
            raise SystemExit(f"Missing case id {cid} in {args.search_eval}")

        seg = case.get("segment") or ""
        filters = deepcopy(case.get("filters") or {})
        if (seg or "").lower() in ("non_stem", "breadth"):
            filters["include_other_depts"] = True
            explore = True
        else:
            filters["include_other_depts"] = False
            explore = False

        query = str(case.get("query") or "")
        method_hits: Dict[str, List[Dict[str, Any]]] = {}
        for m in METHODS:
            method_hits[m] = _method_rows_for_query(query, m, filters, wo, args.top_n)

        cal_list = cal.get(cid, [])
        for rank_idx in range(args.top_n):
            r = rank_idx + 1
            row: Dict[str, Any] = {
                "query_prompt": prompt,
                "query_id": cid,
                "segment": seg,
                "explore_include_other_depts": explore,
                "query_text": query,
                "rank": r,
            }
            for m in METHODS:
                short = METHOD_SHORT[m]
                hit = method_hits[m][rank_idx] if rank_idx < len(method_hits[m]) else {}
                row[f"{short}_course_code"] = hit.get("course_code", "")
                row[f"{short}_title"] = hit.get("title", "")
                sc = hit.get("score")
                row[f"{short}_score"] = f"{float(sc):.6f}" if sc is not None and hit else ""

            if rank_idx < len(cal_list):
                row["uw_calendar_course_code"] = cal_list[rank_idx][0]
                row["uw_calendar_title"] = cal_list[rank_idx][1]
            else:
                row["uw_calendar_course_code"] = ""
                row["uw_calendar_title"] = ""

            out_rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)

    print(f"Wrote {args.output} ({len(out_rows)} rows)")


if __name__ == "__main__":
    main()
