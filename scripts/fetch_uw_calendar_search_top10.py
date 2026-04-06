#!/usr/bin/env python3
"""
Fetch top-N course search results via the Kuali catalog API used by the UW
undergrad Academic Calendar SPA.

API (example):
  https://uwaterloocm.kuali.co/api/v1/catalog/search/67e557ed6ed2fe2bd3a38956
    ?q=modern%20film&limit=8&skip=0&itemTypes=courses

When the API returns fewer rows than requested in one call, we paginate with
skip= until we reach ``--limit`` or the result set is exhausted.

itemTypes=courses matches the calendar UI course-only search; without it the API
returns mixed hits (often programs first).

Returns JSON: list of course objects with fields such as code, title, pid,
description, type.

Human-facing catalog links use the same pid as the in-browser hash route, e.g.
  https://uwaterloo.ca/academic-calendar/undergraduate-studies/catalog#/courses/{pid}

No Playwright or browser required (stdlib only).

Risks: Kuali may change API shape or catalog id; adjust --catalog-id or parsing if needed.

Usage (from repo root):
  python scripts/fetch_uw_calendar_search_top10.py
  python scripts/fetch_uw_calendar_search_top10.py --eval-json backend/recommender/eval/search_evaluation_queries.json
  python scripts/fetch_uw_calendar_search_top10.py --only breadth_n12_modern_film_studies --output-csv out.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import quote, urlencode

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EVAL_JSON = (
    PROJECT_ROOT / "backend" / "recommender" / "eval" / "search_evaluation_queries.json"
)

DEFAULT_API_SEARCH_BASE = "https://uwaterloocm.kuali.co/api/v1/catalog/search"
DEFAULT_CATALOG_ID = "67e557ed6ed2fe2bd3a38956"
CATALOG_BASE = "https://uwaterloo.ca/academic-calendar/undergraduate-studies/catalog"


def build_api_url(
    api_search_base: str,
    catalog_id: str,
    query: str,
    *,
    limit: int,
    skip: int,
    item_types: str,
) -> str:
    base = api_search_base.rstrip("/")
    params: Dict[str, str] = {
        "q": query,
        "limit": str(limit),
        "skip": str(skip),
    }
    if item_types:
        params["itemTypes"] = item_types
    return f"{base}/{catalog_id}?{urlencode(params)}"


def build_course_href(pid: str, query: str, limit: int, skip: int) -> str:
    """Mirror SPA-style deep link (pid + search context)."""
    q = quote(query, safe="")
    tail = f"?q={q}&limit={limit}&skip={skip}&bc=true&bcItemType=courses"
    return f"{CATALOG_BASE}#/courses/{pid}{tail}"


def _fetch_one_page(
    api_search_base: str,
    catalog_id: str,
    query: str,
    *,
    page_limit: int,
    skip: int,
    timeout_s: float,
    item_types: str,
) -> List[Dict[str, Any]]:
    """Return raw course-shaped dicts from one API page (type=courses only)."""
    url = build_api_url(
        api_search_base,
        catalog_id,
        query,
        limit=page_limit,
        skip=skip,
        item_types=item_types,
    )
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "uw-guide-calendar-eval/1.0 (course search eval)",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON list from API, got {type(data).__name__}")

    page: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("type") or "courses").lower()
        if item_type != "courses":
            continue

        code = str(item.get("code") or "").strip()
        if not code:
            sub = item.get("subjectCode")
            if isinstance(sub, dict):
                name = str(sub.get("name") or "").strip()
                num = str(item.get("number") or "").strip()
                if name and num:
                    code = f"{name}{num}"

        title = str(item.get("title") or "").strip()
        pid = str(item.get("pid") or "").strip()
        page.append({"course_code": code, "title": title, "pid": pid})
        if len(page) >= page_limit:
            break
    return page


def fetch_search_results(
    api_search_base: str,
    catalog_id: str,
    query: str,
    *,
    limit: int,
    skip: int,
    timeout_s: float,
    item_types: str,
    page_chunk: int = 8,
) -> List[Dict[str, str]]:
    """Fetch up to ``limit`` course rows, paginating if the API returns short pages."""
    if limit <= 0:
        return []
    out_rows: List[Dict[str, str]] = []
    cursor = int(skip)
    target = int(limit)

    while len(out_rows) < target:
        need = target - len(out_rows)
        req_limit = min(max(page_chunk, 1), need)
        page = _fetch_one_page(
            api_search_base,
            catalog_id,
            query,
            page_limit=req_limit,
            skip=cursor,
            timeout_s=timeout_s,
            item_types=item_types,
        )
        if not page:
            break
        for raw in page:
            if len(out_rows) >= target:
                break
            pid = str(raw.get("pid") or "").strip()
            code = str(raw.get("course_code") or "").strip()
            title = str(raw.get("title") or "").strip()
            href = build_course_href(pid, query, target, 0) if pid else ""
            out_rows.append(
                {
                    "rank": str(len(out_rows) + 1),
                    "course_code": code,
                    "title": title,
                    "href": href,
                }
            )
        cursor += len(page)
        if len(page) < req_limit:
            break
    return out_rows


def load_cases(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data.get("cases") or []
    if not cases:
        raise ValueError(f"No cases in {path}")
    return cases


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="UW undergrad catalog course search via Kuali API (top N per eval query)."
    )
    p.add_argument(
        "--eval-json",
        type=Path,
        default=DEFAULT_EVAL_JSON,
        help="Eval JSON with cases[].id and cases[].query",
    )
    p.add_argument(
        "--only",
        type=str,
        default="",
        help="Comma-separated case ids to run (default: all)",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=8,
        help="Max course results per query (total across paginated API calls; default 8).",
    )
    p.add_argument(
        "--page-chunk",
        type=int,
        default=8,
        help="Per-request API limit= (default 8).",
    )
    p.add_argument("--skip", type=int, default=0, help="API skip= offset")
    p.add_argument("--delay-ms", type=int, default=400, help="Pause between API calls")
    p.add_argument(
        "--catalog-id",
        type=str,
        default=DEFAULT_CATALOG_ID,
        help="Kuali catalog id segment in the search URL path",
    )
    p.add_argument(
        "--api-search-base",
        type=str,
        default=DEFAULT_API_SEARCH_BASE,
        help="Base URL without trailing catalog id (e.g. .../api/v1/catalog/search)",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="HTTP timeout in seconds per request",
    )
    p.add_argument(
        "--item-types",
        type=str,
        default="courses",
        help="Kuali itemTypes query param (default: courses). Empty string to omit.",
    )
    p.add_argument(
        "--output-csv",
        type=Path,
        default=PROJECT_ROOT / "backend" / "recommender" / "eval" / "uw_calendar_top10.csv",
    )
    p.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Optional path to write JSON array of rows",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cases = load_cases(args.eval_json)
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    if only:
        cases = [c for c in cases if c.get("id") in only]
        if not cases:
            raise SystemExit(f"No cases matched --only {args.only!r}")

    fetched_at = datetime.now(timezone.utc).isoformat()
    rows: List[Dict[str, str]] = []

    for case in cases:
        qid = str(case.get("id", ""))
        qtext = str(case.get("query", "")).strip()
        segment = str(case.get("segment", ""))
        if not qtext:
            continue
        try:
            results = fetch_search_results(
                args.api_search_base,
                args.catalog_id,
                qtext,
                limit=args.limit,
                skip=args.skip,
                timeout_s=args.timeout,
                item_types=(args.item_types or "").strip(),
                page_chunk=args.page_chunk,
            )
        except urllib.error.HTTPError as exc:
            rows.append(
                {
                    "query_id": qid,
                    "segment": segment,
                    "query": qtext,
                    "rank": "",
                    "course_code": "",
                    "title": "",
                    "href": "",
                    "fetched_at": fetched_at,
                    "error": f"HTTP {exc.code}: {exc.reason}",
                }
            )
        except Exception as exc:  # noqa: BLE001
            rows.append(
                {
                    "query_id": qid,
                    "segment": segment,
                    "query": qtext,
                    "rank": "",
                    "course_code": "",
                    "title": "",
                    "href": "",
                    "fetched_at": fetched_at,
                    "error": str(exc),
                }
            )
        else:
            if not results:
                rows.append(
                    {
                        "query_id": qid,
                        "segment": segment,
                        "query": qtext,
                        "rank": "",
                        "course_code": "",
                        "title": "",
                        "href": "",
                        "fetched_at": fetched_at,
                        "error": "no_results",
                    }
                )
            for r in results:
                rows.append(
                    {
                        "query_id": qid,
                        "segment": segment,
                        "query": qtext,
                        "rank": r["rank"],
                        "course_code": r["course_code"],
                        "title": r["title"],
                        "href": r["href"],
                        "fetched_at": fetched_at,
                        "error": "",
                    }
                )
        time.sleep(max(0, args.delay_ms) / 1000.0)

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "query_id",
        "segment",
        "query",
        "rank",
        "course_code",
        "title",
        "href",
        "fetched_at",
        "error",
    ]
    with args.output_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} row(s) to {args.output_csv}", file=sys.stderr)

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(f"Wrote JSON to {args.output_json}", file=sys.stderr)


if __name__ == "__main__":
    main()
