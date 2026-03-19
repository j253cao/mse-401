"""
FastAPI Backend for Course Recommendations

Run with:
    cd backend
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
"""

from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum
import json
import logging
import re
import time
import os
import tempfile
from dotenv import load_dotenv

# Load environment variables from backend/.env (preferred for deployment)
# Fallback to project root .env for compatibility.
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_ROOT, '..'))
load_dotenv(os.path.join(BACKEND_ROOT, '.env'))
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# 14 UW Engineering departments (matches course_dependency_parser)
ENGINEERING_DEPARTMENTS = (
    "AE", "BME", "CHE", "CIVE", "ECE", "ENVE", "GENE", "GEOE",
    "ME", "MTE", "MSE", "NE", "SE", "SYDE",
)

from recommender.main import get_recommendations, get_high_value_courses, get_similar_courses, get_abs_path, get_filtered_courses
from recommender.data_loader import load_course_data
from recommender.weights import load_course_to_programs, compute_options_progress, get_option_boost_multipliers

# Cached course-to-programs lookup for enriching responses
_course_to_programs_cache = None


def _normalize_course_code(code: str) -> str:
    """Normalize to uppercase/no-spaces and map legacy MSCI -> MSE."""
    result = (code or "").strip().upper().replace(" ", "")
    if result.startswith("MSCI"):
        result = "MSE" + result[4:]
    return result


def _get_course_to_programs():
    global _course_to_programs_cache
    if _course_to_programs_cache is None:
        options_path = get_abs_path('data', 'programs', 'all_options.json')
        programs_path = get_abs_path('data', 'programs', 'all_programs.json')
        _course_to_programs_cache = load_course_to_programs([
            (options_path, 'option'),
            (programs_path, 'minor'),
        ])
    return _course_to_programs_cache


def _enrich_course_with_programs(course: dict) -> dict:
    """Add contributing_programs to a course dict keyed by course_code."""
    code = _normalize_course_code(course.get('course_code') or '')
    lookup = _get_course_to_programs()
    programs = lookup.get(code, [])
    return {**course, 'contributing_programs': programs}


def _enrich_results_with_deps(results: List[Dict[str, Any]], deps_lookup: Dict) -> List[Dict[str, Any]]:
    """Enrich a list of course result dicts with prereqs, coreqs, antireqs, and contributing programs."""
    enriched = []
    for r in results:
        dep_info = deps_lookup.get(_normalize_course_code(str(r["course_code"])), {})
        base_course = {
            "rank": r["rank"],
            "course_code": r["course_code"],
            "title": r["title"],
            "description": r["description"],
            "score": r["score"],
            "prereqs": dep_info.get("prereqs"),
            "coreqs": dep_info.get("coreqs"),
            "antireqs": dep_info.get("antireqs"),
        }
        enriched.append(_enrich_course_with_programs(base_course))
    return enriched


from parsers.transcript_parser import parse_transcript_bytes, term_id_to_name, get_all_courses


_COURSE_DEPENDENCIES_CACHE: Optional[Dict[str, Dict[str, Optional[str]]]] = None


def _flatten_groups(groups: list) -> str:
    """Flatten prerequisite/corequisite groups into a readable string."""
    parts: List[str] = []
    for group in groups:
        g_type = group.get("type", "")
        if g_type == "prerequisite_group":
            codes = [c.get("code", "") if isinstance(c, dict) else str(c) for c in group.get("courses", []) if (c.get("code") if isinstance(c, dict) else c)]
            op = group.get("operator", "OR")
            joiner = " or " if op == "OR" else " and "
            if codes:
                parts.append(joiner.join(codes))
        elif g_type == "course":
            code = group.get("code", "")
            if code:
                parts.append(code)
    return "; ".join(parts)


def _flatten_program_requirements(reqs: list) -> str:
    """Flatten program_requirements into a readable string."""
    parts: List[str] = []
    for req in reqs:
        fragments: List[str] = []
        level_req = req.get("level_requirement")
        if level_req:
            level = level_req.get("level", "")
            comparison = level_req.get("comparison", "at_least")
            if comparison == "exactly":
                fragments.append(f"Level exactly {level}")
            else:
                fragments.append(f"Level at least {level}")
        prog = req.get("program_name")
        if prog:
            fragments.append(f"{prog} students")
        faculty = req.get("faculty")
        if faculty and not prog:
            fragments.append(f"{faculty} students")
        if fragments:
            parts.append(", ".join(fragments))
    return "; ".join(parts)


def _flatten_antireq_courses(courses: list) -> str:
    """Flatten antirequisite course entries (objects or plain strings)."""
    codes: List[str] = []
    for entry in courses:
        if isinstance(entry, dict):
            code = entry.get("code", "")
        else:
            code = str(entry)
        if code:
            codes.append(code)
    return ", ".join(codes)


def _flatten_program_restrictions(restrictions: list) -> str:
    """Flatten program_restrictions into a readable string."""
    names = [r.get("program_name", "") for r in restrictions if isinstance(r, dict) and r.get("program_name")]
    if not names:
        return ""
    return "Not open to " + ", ".join(names) + " students"


def load_course_dependencies() -> Dict[str, Dict[str, Optional[str]]]:
    """
    Load structured course dependency data from course_dependencies_llm.json
    and flatten it into human-readable prereqs/coreqs/antireqs strings.
    """
    global _COURSE_DEPENDENCIES_CACHE
    if _COURSE_DEPENDENCIES_CACHE is not None:
        return _COURSE_DEPENDENCIES_CACHE

    deps_path = get_abs_path("data", "dependencies", "course_dependencies_llm.json")
    if not os.path.exists(deps_path):
        _COURSE_DEPENDENCIES_CACHE = {}
        return _COURSE_DEPENDENCIES_CACHE

    with open(deps_path, "r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)

    cache: Dict[str, Dict[str, Optional[str]]] = {}
    for code, info in data.items():
        # Prerequisites
        prereq_section = info.get("prerequisites", {})
        if isinstance(prereq_section, list):
            prereq_section = {}
        prereq_parts: List[str] = []
        groups_text = _flatten_groups(prereq_section.get("groups", []))
        if groups_text:
            prereq_parts.append(groups_text)
        prog_text = _flatten_program_requirements(prereq_section.get("program_requirements", []))
        if prog_text:
            prereq_parts.append(prog_text)
        prereqs = "; ".join(prereq_parts) or None

        # Corequisites
        coreq_section = info.get("corequisites", {})
        if isinstance(coreq_section, list):
            coreq_section = {}
        coreqs_text = _flatten_groups(coreq_section.get("groups", []))
        coreqs = coreqs_text or None

        # Antirequisites
        antireq_section = info.get("antirequisites", {})
        if isinstance(antireq_section, list):
            antireq_section = {}
        antireq_parts: List[str] = []
        courses_text = _flatten_antireq_courses(antireq_section.get("courses", []))
        if courses_text:
            antireq_parts.append(courses_text)
        restrict_text = _flatten_program_restrictions(antireq_section.get("program_restrictions", []))
        if restrict_text:
            antireq_parts.append(restrict_text)
        antireqs = "; ".join(antireq_parts) or None

        cache[_normalize_course_code(code)] = {
            "prereqs": prereqs,
            "coreqs": coreqs,
            "antireqs": antireqs,
        }

    _COURSE_DEPENDENCIES_CACHE = cache
    return _COURSE_DEPENDENCIES_CACHE


_THREE_PLUS_DIGITS_PATTERN = re.compile(r"\d{3,}")


def _is_course_code_query(query: str) -> bool:
    """True if query looks like a course code (e.g. MSE446, MSE 446, CS 135)."""
    if not query or not query.strip():
        return False
    normalized = _normalize_course_code(query)
    # Must have letters + 3+ digits
    return bool(re.match(r"^[A-Z]{2,}[0-9]{3}[A-Z]*$", normalized))


def _has_three_plus_consecutive_digits(query: str) -> bool:
    """True if query contains 3 or more consecutive digits."""
    return bool(_THREE_PLUS_DIGITS_PATTERN.search(query or ""))


_COURSE_DATA_LOOKUP_CACHE: Optional[Dict[str, Dict[str, Any]]] = None


def _load_course_data_for_lookup() -> Dict[str, Dict[str, Any]]:
    """Load course JSON for lookup. Keys are canonical codes (e.g. MSE446).
    Result is cached in-process so disk is only read once per server lifetime.
    """
    global _COURSE_DATA_LOOKUP_CACHE
    if _COURSE_DATA_LOOKUP_CACHE is not None:
        return _COURSE_DATA_LOOKUP_CACHE
    data_json = get_abs_path("data", "courses", "course-api-new-data.json")
    with open(data_json, "r", encoding="utf-8") as f:
        _COURSE_DATA_LOOKUP_CACHE = json.load(f)
    return _COURSE_DATA_LOOKUP_CACHE


def _lookup_courses_by_code(
    normalized_query: str,
    filters: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Exact course code lookup. Returns courses matching the normalized code.
    Applies department filter from filters.
    """
    data = _load_course_data_for_lookup()
    include_other = filters.get("include_other_depts", False)
    departments = filters.get("department") or list(ENGINEERING_DEPARTMENTS)
    if isinstance(departments, str):
        dept_set = {departments.upper()}
    elif isinstance(departments, (list, tuple)):
        dept_set = set(d.upper() for d in departments)
    else:
        dept_set = set(ENGINEERING_DEPARTMENTS)

    def _dept_ok(subject: str) -> bool:
        if not dept_set:
            return True
        if subject in dept_set:
            return True
        # include_other: allow non-engineering departments
        if include_other and subject not in ENGINEERING_DEPARTMENTS:
            return True
        return False

    results = []
    # Direct key lookup (keys are canonical: MSE446, etc.)
    if normalized_query in data:
        info = data[normalized_query]
        subject = (info.get("subjectCode") or "").upper()
        if _dept_ok(subject):
            results.append({
                "course_code": normalized_query,
                "title": info.get("title", ""),
                "description": info.get("description", ""),
            })
    # Also scan for canonical_code match (in case keys differ)
    if not results:
        for key, info in data.items():
            subject = (info.get("subjectCode") or "").upper()
            catalog = info.get("catalogNumber") or ""
            canonical = f"{subject}{catalog}" if catalog else key
            if canonical.upper() == normalized_query:
                if _dept_ok(subject):
                    results.append({
                        "course_code": canonical,
                        "title": info.get("title", ""),
                        "description": info.get("description", ""),
                    })
                break
    return results


def _lookup_courses_by_number_sequence(
    query: str,
    filters: Dict[str, Any],
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Find courses whose catalog number contains 3+ consecutive digits from the query.
    Digits are matched against catalogNumber only (not the full course code string),
    so "446" matches ECE446 but not a hypothetical subject whose letters include that
    substring. Results are sorted by catalog number for a stable, predictable order.
    """
    data = _load_course_data_for_lookup()
    include_other = filters.get("include_other_depts", False)
    departments = filters.get("department") or list(ENGINEERING_DEPARTMENTS)
    if isinstance(departments, str):
        dept_set = {departments.upper()}
    elif isinstance(departments, (list, tuple)):
        dept_set = set(d.upper() for d in departments)
    else:
        dept_set = set(ENGINEERING_DEPARTMENTS)

    def _dept_ok(subject: str) -> bool:
        if not dept_set:
            return True
        if subject in dept_set:
            return True
        if include_other and subject not in ENGINEERING_DEPARTMENTS:
            return True
        return False

    digit_matches = _THREE_PLUS_DIGITS_PATTERN.findall(query)
    if not digit_matches:
        return []

    # Use longest match (e.g. "1234" over "123")
    search_digits = max(digit_matches, key=len)

    results = []
    seen = set()
    for key, info in data.items():
        subject = (info.get("subjectCode") or "").upper()
        catalog = info.get("catalogNumber") or ""
        canonical = f"{subject}{catalog}" if catalog else key
        if canonical in seen:
            continue
        # Fix 5: match digits against catalog number only, not the full course code
        if search_digits not in catalog:
            continue
        if not _dept_ok(subject):
            continue
        seen.add(canonical)
        results.append({
            "course_code": canonical,
            "title": info.get("title", ""),
            "description": info.get("description", ""),
            "_catalog": catalog,  # temporary sort key
        })

    # Fix 6: sort by catalog number for a stable, meaningful order
    results.sort(key=lambda r: r["_catalog"])
    for r in results:
        r.pop("_catalog")

    return results[:limit]


def _course_lookup_results_to_recommend_format(
    lookup_results: List[Dict[str, Any]],
    deps_lookup: Dict[str, Dict[str, Optional[str]]],
) -> List[Dict[str, Any]]:
    """Convert lookup results to the same format as get_recommendations output."""
    enriched = []
    for rank, r in enumerate(lookup_results, 1):
        code = str(r.get("course_code", "")).upper()
        dep_info = deps_lookup.get(code, {})
        base_course = {
            "rank": rank,
            "course_code": r.get("course_code", ""),
            "title": r.get("title", ""),
            "description": r.get("description", ""),
            "score": 1.0,
            "prereqs": dep_info.get("prereqs"),
            "coreqs": dep_info.get("coreqs"),
            "antireqs": dep_info.get("antireqs"),
        }
        enriched.append(_enrich_course_with_programs(base_course))
    return enriched


app = FastAPI(
    title="UW Course Recommendation API",
    description="API for course recommendations based on text queries, resumes, and transcripts",
    version="1.0.0"
)

def _env_csv(name: str) -> List[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return []
    return [v.strip() for v in raw.split(",") if v.strip()]


# Security defaults:
# - Explicit CORS origins (no "*" + credentials)
# - Trusted hosts (set ALLOWED_HOSTS in production)
environment = (os.getenv("ENVIRONMENT") or os.getenv("ENV") or "development").strip().lower()
allowed_hosts = _env_csv("ALLOWED_HOSTS") or (["*"] if environment != "production" else [])
if allowed_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

allowed_origins = _env_csv("ALLOWED_ORIGINS") or (["http://localhost:5173"] if environment != "production" else [])
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("api")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = (time.time() - start) * 1000
    logger.info(
        "%s %s %s %.0fms",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )
    return response


class CourseLevel(str, Enum):
    UNDERGRAD = "undergrad"
    GRAD = "grad"


class QueryRequest(BaseModel):
    queries: List[str]
    filters: Optional[Dict[str, Any]] = None


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "message": "UW Course Recommendation API"}


@app.get("/options-and-minors")
def options_and_minors():
    """
    Return lists of option and minor names for filter UI.
    Loads from all_options.json and all_programs.json.
    """
    options_path = get_abs_path('data', 'programs', 'all_options.json')
    programs_path = get_abs_path('data', 'programs', 'all_programs.json')
    options = []
    minors = []
    if os.path.exists(options_path):
        with open(options_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
        options = [{"name": item.get("option_name", "")} for item in items if item.get("option_name")]
    if os.path.exists(programs_path):
        with open(programs_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
        minors = [{"name": item.get("program_name", "")} for item in items if item.get("program_name")]
    return {"options": options, "minors": minors}


class OptionsProgressRequest(BaseModel):
    completed_courses: List[str]


_OPTIONS_DATA_CACHE: Optional[List[Dict[str, Any]]] = None


def _load_options_data() -> List[Dict[str, Any]]:
    global _OPTIONS_DATA_CACHE
    if _OPTIONS_DATA_CACHE is None:
        options_path = get_abs_path('data', 'programs', 'all_options.json')
        with open(options_path, 'r', encoding='utf-8') as f:
            _OPTIONS_DATA_CACHE = json.load(f)
    return _OPTIONS_DATA_CACHE


@app.post("/options-progress")
def options_progress(request: OptionsProgressRequest):
    """
    Compute option completion progress for a set of completed courses.

    Returns a list of OptionProgress objects sorted by completion_ratio descending.
    """
    options_data = _load_options_data()
    return compute_options_progress(request.completed_courses, options_data)


@app.post("/recommend")
def recommend(request: QueryRequest):
    """
    Get course recommendations based on text queries.
    
    If a query looks like a course code (e.g. MSE446) or contains 3+ consecutive
    digits, returns matching courses directly. Otherwise uses semantic search.
    
    Args:
        request: QueryRequest with queries and optional filters
        
    Returns:
        Dictionary with recommendation results for each query
    """
    filters = dict(request.filters) if request.filters else {}
    include_other = filters.pop("include_other_depts", False)
    if not filters.get("department"):
        filters["department"] = list(ENGINEERING_DEPARTMENTS)
    if include_other:
        filters["include_other_depts"] = True

    # Option-completion boost: tiered by option + list progress (for ranking)
    options_data = _load_options_data()
    completed = filters.get("completed_courses") or []
    filters["option_boost_multipliers"] = get_option_boost_multipliers(options_data, completed)

    deps_lookup = load_course_dependencies()
    formatted: Dict[str, Any] = {}

    # Queries that used course lookup (skip semantic search)
    queries_for_semantic = []
    query_to_lookup_results: Dict[str, List[Dict[str, Any]]] = {}

    for q in request.queries:
        # Empty query with filters: use filter-only path
        if not (q or "").strip():
            formatted[q] = _enrich_results_with_deps(
                get_filtered_courses(filters=filters), deps_lookup
            )
            continue

        # Fix 3: normalize once and use consistently across all lookup paths
        q_clean = _normalize_course_code(q)
        lookup_results = []
        attempted_code_lookup = False

        # Priority 1: Exact course code match
        if _is_course_code_query(q_clean):
            attempted_code_lookup = True
            lookup_results = _lookup_courses_by_code(q_clean, filters)

        # Fix 4: only try digit search when the query was NOT a course-code pattern.
        # If it looked like a code (e.g. MSE446) but returned nothing (dept mismatch),
        # fall through to semantic rather than returning unrelated courses like ECE446.
        # Fix 3: pass q_clean so digit detection and lookup see the same normalised string.
        if not lookup_results and not attempted_code_lookup and _has_three_plus_consecutive_digits(q_clean):
            lookup_results = _lookup_courses_by_number_sequence(q_clean, filters)

        if lookup_results:
            query_to_lookup_results[q] = lookup_results
        else:
            queries_for_semantic.append(q)

    # Process course lookup results
    for q, lookup_results in query_to_lookup_results.items():
        formatted[q] = _course_lookup_results_to_recommend_format(
            lookup_results, deps_lookup
        )

    # Semantic search for remaining queries
    if queries_for_semantic:
        results = get_recommendations(
            queries_for_semantic,
            data_file="course-api-new-data.json",
            method="cosine",
            filters=filters,
        )

        for q, q_results in zip(queries_for_semantic, results):
            cosine_results = [r for r in q_results if r["method"] == "cosine"]
            formatted[q] = _enrich_results_with_deps(cosine_results, deps_lookup)

    return {"results": formatted}


@app.post("/resume-recommend")
def resume_recommend(
    file: UploadFile = File(...),
    filters: Optional[Dict[str, Any]] = None
):
    """
    Get course recommendations based on an uploaded resume PDF.
    
    Args:
        file: Uploaded resume PDF file
        filters: Optional filters to apply
        
    Returns:
        List of recommended courses based on resume analysis
    """
    # Feature-flag: allow deploying without GEMINI_API_KEY.
    if not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(status_code=503, detail="Resume recommendations are disabled (GEMINI_API_KEY not set).")
    
    # Save uploaded PDF to a temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name
    
    try:
        # Avoid writing parsed resumes by default on ephemeral disks.
        from parsers.resume_parser import ResumeParser
        parser = ResumeParser(output_file=None)
        parsed_resume = parser.parse(tmp_path)
        if not parsed_resume:
            return {"error": "Failed to parse resume."}
        
        # Extract subfields, preferred_domains, and suggested_directions
        subfields = parsed_resume.get('core_interests', {}).get('subfields', [])
        learning_patterns = parsed_resume.get('learning_patterns', {})
        preferred_domains = learning_patterns.get('preferred_domains', [])
        suggested_directions = list(map(lambda x: x.get('field'), parsed_resume.get('suggested_directions', [])))
        
        # Build a search query string
        query_parts = subfields + preferred_domains + suggested_directions
        query = ' '.join(query_parts)

        # Default to engineering departments only when no department filter provided
        res_filters = dict(filters) if filters else {}
        include_other = res_filters.pop("include_other_depts", False)
        if not res_filters.get("department"):
            res_filters["department"] = list(ENGINEERING_DEPARTMENTS)
        if include_other:
            res_filters["include_other_depts"] = True
        
        deps_lookup = load_course_dependencies()

        recommendations = get_recommendations(
            [query],
            data_file='course-api-new-data.json',
            method='cosine',
            filters=res_filters
        )
        
        formatted = []
        for r in recommendations[0]:
            if r["method"] != "cosine":
                continue
            dep_info = deps_lookup.get(str(r["course_code"]).upper(), {})
            base_course = {
                "rank": r["rank"],
                "course_code": r["course_code"],
                "title": r["title"],
                "description": r["description"],
                "score": r["score"],
                "prereqs": dep_info.get("prereqs"),
                "coreqs": dep_info.get("coreqs"),
                "antireqs": dep_info.get("antireqs"),
            }
            formatted.append(_enrich_course_with_programs(base_course))
        
        return formatted
    finally:
        os.remove(tmp_path)


@app.get("/courses/search")
def courses_search(q: str = "", limit: int = 20):
    """
    Search courses by code or title prefix.
    Returns { code, title }[] for use in course picker autocomplete.
    Restricted to engineering departments only.
    Uses subjectCode for department check (keys may be ENGDEAN* for ENVE, etc.).
    Returns canonical code (subjectCode + catalogNumber) to match undergrad/grad lists.
    """
    if not q or len(q.strip()) < 2:
        return []
    query = q.strip().upper()
    data_json = get_abs_path('data', 'courses', 'course-api-new-data.json')
    with open(data_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    results = []
    seen = set()
    for key, info in data.items():
        if len(results) >= limit:
            break
        # Use subjectCode for department (keys like ENGDEAN583 have subjectCode ENVE)
        subject = (info.get('subjectCode') or '').upper()
        catalog = info.get('catalogNumber') or ''
        if subject not in ENGINEERING_DEPARTMENTS:
            continue
        # Canonical code matches undergrad/grad lists (e.g. ENVE223)
        canonical_code = f"{subject}{catalog}" if catalog else key
        if canonical_code in seen:
            continue
        title = info.get('title', '')
        code_upper = canonical_code.upper()
        title_upper = title.upper()
        if query in code_upper or query in title_upper or query in key.upper():
            seen.add(canonical_code)
            results.append({"code": canonical_code, "title": title})
    return results[:limit]


@app.get("/explore-high-value")
def explore_high_value(
    level: Optional[str] = None,
    limit: int = 12,
    program: Optional[str] = None,
    depth_penalty: float = 0.15,
    temperature: float = 0.5,
):
    """
    Get high-value courses (common prereqs, many options/minors).
    No search query needed—solves cold start for first-year students.
    When level is 1A or 1B, restricts to 100-level courses only.
    Program bias: when level is 1A/1B, boosts courses in that program's core.
    Temperature: higher = more variety in results (0 = deterministic).
    """
    raw = get_high_value_courses(
        level=level,
        limit=limit,
        program=program,
        depth_penalty=depth_penalty,
        temperature=temperature,
    )
    return {
        "courses": [_enrich_course_with_programs(c) for c in raw],
    }


@app.get("/courses/{course_code}/similar")
def similar_courses(course_code: str, limit: int = 6):
    """Return courses most similar to the given course based on description embeddings."""
    similar = get_similar_courses(course_code, data_file='course-api-new-data.json', top_k=limit)
    deps_lookup = load_course_dependencies()
    enriched = []
    for item in similar:
        code = str(item['course_code']).upper()
        dep_info = deps_lookup.get(code, {})
        base_course = {
            "course_code": item['course_code'],
            "title": item['title'],
            "description": item['description'],
            "score": item['score'],
            "prereqs": dep_info.get("prereqs"),
            "coreqs": dep_info.get("coreqs"),
            "antireqs": dep_info.get("antireqs"),
        }
        enriched.append(_enrich_course_with_programs(base_course))
    return enriched


@app.get("/random-course")
def random_course():
    """Get a random course from the database."""
    data_json = get_abs_path('data', 'courses', 'course-api-new-data.json')
    df = load_course_data(data_json)
    row = df.sample(1).iloc[0]
    deps_lookup = load_course_dependencies()
    code = str(row["courseCode"])
    dep_info = deps_lookup.get(code.upper(), {})
    base_course = {
        "course_code": code,
        "title": row["title"],
        "description": row["description"],
        "prereqs": dep_info.get("prereqs"),
        "coreqs": dep_info.get("coreqs"),
        "antireqs": dep_info.get("antireqs"),
    }
    return _enrich_course_with_programs(base_course)


@app.post("/transcript-parse")
def transcript_parse(file: UploadFile = File(...)):
    """
    Parse an uploaded transcript PDF and return course history.
    
    Args:
        file: Uploaded transcript PDF file
        
    Returns:
        Dictionary with courses, latest_term, program, student_number, term_summaries
    """
    try:
        pdf_bytes = file.file.read()
        result = parse_transcript_bytes(pdf_bytes)
        all_courses = get_all_courses(result)
        
        latest_term = None
        if result.term_summaries:
            last = result.term_summaries[-1]
            latest_term = {
                "term_id": last.term_id,
                "term_name": term_id_to_name(last.term_id),
                "level": last.level,
                "courses": last.courses
            }
        
        term_summaries = [
            {
                "term_id": term.term_id,
                "term_name": term_id_to_name(term.term_id),
                "level": term.level,
                "courses": term.courses
            }
            for term in result.term_summaries
        ]
        
        return {
            "courses": all_courses,
            "latest_term": latest_term,
            "program": result.program_name,
            "student_number": result.student_number,
            "term_summaries": term_summaries
        }
        
    except Exception as e:
        logger.error("transcript-parse error: %s", e)
        return {"error": str(e)}


FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend-dist"

if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)