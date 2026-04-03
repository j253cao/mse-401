#!/usr/bin/env python3
"""
Run queries from tasks/search-evaluation-queries.txt against each recommender method.

Uses get_recommendations(..., method=...) from the backend (same as the API pipeline,
but the live /recommend endpoint only accepts cosine/dense; this script exercises all
implemented methods: cosine, dense, faiss, mmr, graph, fuzzy_multi, keyword_overlap).

Requires optional packages for full coverage: faiss-cpu (faiss), networkx (graph).

Usage (from repo root):
  python scripts/run_search_evaluation_queries.py
  python scripts/run_search_evaluation_queries.py --methods cosine,dense,keyword_overlap --top-k 10
  python scripts/run_search_evaluation_queries.py --output eval_results.csv --include-other-depts
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

# Repo layout: scripts/ -> project root -> backend/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from recommender.main import get_recommendations  # noqa: E402

# Keep in sync with backend/api/main.py ENGINEERING_DEPARTMENTS
ENGINEERING_DEPARTMENTS = (
    "AE",
    "BME",
    "CHE",
    "CIVE",
    "ECE",
    "ENVE",
    "GENE",
    "GEOE",
    "ME",
    "MTE",
    "MSE",
    "NE",
    "SE",
    "SYDE",
)

KNOWN_METHODS = (
    "cosine",
    "dense",
    "faiss",
    "mmr",
    "graph",
    "fuzzy_multi",
    "keyword_overlap",
)

# Lines like: S1   machine learning
QUERY_LINE_RE = re.compile(r"^([SN]\d+)\s+(.+?)\s*$")


def load_queries(queries_path: Path) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    text = queries_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        raw = line.strip()
        if not raw:
            continue
        m = QUERY_LINE_RE.match(raw)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def parse_methods_arg(s: str) -> List[str]:
    methods = [x.strip().lower() for x in s.split(",") if x.strip()]
    bad = [m for m in methods if m not in KNOWN_METHODS]
    if bad:
        raise SystemExit(
            f"Unknown method(s): {bad}. Choose from: {', '.join(KNOWN_METHODS)}"
        )
    return methods


def build_filters(include_other_depts: bool) -> dict:
    return {
        "include_undergrad": True,
        "include_grad": True,
        "department": list(ENGINEERING_DEPARTMENTS),
        "include_other_depts": include_other_depts,
        "completed_courses": [],
        "ignore_dependencies": True,
    }


def run_rows(
    queries: Iterable[Tuple[str, str]],
    methods: List[str],
    filters: dict,
    data_file: str,
    top_k: int,
) -> List[dict]:
    rows: List[dict] = []
    for qid, qtext in queries:
        for method in methods:
            try:
                batch = get_recommendations(
                    [qtext],
                    data_file=data_file,
                    method=method,
                    filters=filters,
                )
            except Exception as exc:  # noqa: BLE001
                rows.append(
                    {
                        "query_id": qid,
                        "query_text": qtext,
                        "method": method,
                        "rank": "",
                        "course_code": "",
                        "title": "",
                        "score": "",
                        "error": str(exc),
                    }
                )
                continue
            if not batch or not batch[0]:
                rows.append(
                    {
                        "query_id": qid,
                        "query_text": qtext,
                        "method": method,
                        "rank": "",
                        "course_code": "",
                        "title": "",
                        "score": "",
                        "error": "no_results",
                    }
                )
                continue
            for item in batch[0]:
                if item.get("method") != method:
                    continue
                rank = int(item.get("rank", 0))
                if rank > top_k:
                    break
                rows.append(
                    {
                        "query_id": qid,
                        "query_text": qtext,
                        "method": method,
                        "rank": rank,
                        "course_code": item.get("course_code", ""),
                        "title": item.get("title", ""),
                        "score": item.get("score", ""),
                        "error": "",
                    }
                )
    return rows


def write_csv(path: Path, rows: List[dict]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run search-evaluation queries across recommender methods."
    )
    parser.add_argument(
        "--queries-file",
        type=Path,
        default=PROJECT_ROOT / "tasks" / "search-evaluation-queries.txt",
        help="Path to search-evaluation-queries.txt",
    )
    parser.add_argument(
        "--methods",
        type=str,
        default=",".join(KNOWN_METHODS),
        help=f"Comma-separated methods (default: all). Options: {', '.join(KNOWN_METHODS)}",
    )
    parser.add_argument("--top-k", type=int, default=5, help="Max rank to record per query/method")
    parser.add_argument(
        "--data-file",
        default="course-api-new-data.json",
        help="Catalog JSON under data/courses/",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write CSV here (default: print table to stdout)",
    )
    parser.add_argument(
        "--include-other-depts",
        action="store_true",
        help="Include non-engineering departments (mirrors API include_other_depts)",
    )
    args = parser.parse_args()

    queries_path: Path = args.queries_file
    if not queries_path.is_file():
        raise SystemExit(f"Queries file not found: {queries_path}")

    queries = load_queries(queries_path)
    if not queries:
        raise SystemExit(f"No S*/N* query lines parsed from {queries_path}")

    methods = parse_methods_arg(args.methods)
    filters = build_filters(include_other_depts=args.include_other_depts)
    rows = run_rows(queries, methods, filters, args.data_file, args.top_k)

    if args.output:
        write_csv(args.output, rows)
        print(f"Wrote {len(rows)} row(s) to {args.output}", file=sys.stderr)
    else:
        w = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys()) if rows else [])
        if rows:
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
