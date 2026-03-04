"""
FastAPI Backend for Course Recommendations

Run with:
    cd backend
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum
import json
import time
import os
import tempfile
import sys
from dotenv import load_dotenv

# Add backend to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables from project root .env file
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# 14 UW Engineering departments (matches course_dependency_parser)
ENGINEERING_DEPARTMENTS = (
    "AE", "BME", "CHE", "CIVE", "ECE", "ENVE", "GENE", "GEOE",
    "ME", "MTE", "MSE", "NE", "SE", "SYDE",
)

from recommender.main import get_recommendations, get_high_value_courses, get_abs_path
from recommender.data_loader import load_course_data
from recommender.weights import load_course_to_programs
from parsers.resume_parser import ResumeParser

# Cached course-to-programs lookup for enriching responses
_course_to_programs_cache = None


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
    code = (course.get('course_code') or '').strip().upper().replace(' ', '')
    lookup = _get_course_to_programs()
    programs = lookup.get(code, [])
    return {**course, 'contributing_programs': programs}
from parsers.transcript_parser import parse_transcript_bytes, term_id_to_name, get_all_courses

app = FastAPI(
    title="UW Course Recommendation API",
    description="API for course recommendations based on text queries, resumes, and transcripts",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CourseLevel(str, Enum):
    UNDERGRAD = "undergrad"
    GRAD = "grad"


class QueryRequest(BaseModel):
    queries: List[str]
    filters: Optional[Dict[str, Any]] = None


@app.get("/")
def root():
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


@app.post("/recommend")
def recommend(request: QueryRequest):
    """
    Get course recommendations based on text queries.
    
    Args:
        request: QueryRequest with queries and optional filters
        
    Returns:
        Dictionary with recommendation results for each query
    """
    t0 = time.time()
    print(f"[endpoint] Request received: {request.queries}")
    print(f"[endpoint] Filters: {request.filters}")

    # Default to engineering departments only when no department filter provided
    filters = dict(request.filters) if request.filters else {}
    if not filters.get("department"):
        filters["department"] = list(ENGINEERING_DEPARTMENTS)
    
    t1 = time.time()
    results = get_recommendations(
        request.queries,
        data_file='course-api-new-data.json',
        method='cosine',
        filters=filters
    )
    t2 = time.time()
    print(f"[endpoint] Recommendation call: {t2-t1:.4f}s")
    
    # Formatting
    formatted = {}
    for q, q_results in zip(request.queries, results):
        cosine_results = [r for r in q_results if r["method"] == "cosine"]
        formatted[q] = [
            _enrich_course_with_programs({
                "rank": r["rank"],
                "course_code": r["course_code"],
                "title": r["title"],
                "description": r["description"],
                "score": r["score"]
            })
            for r in cosine_results
        ]
    
    t3 = time.time()
    print(f"[endpoint] Formatting: {t3-t2:.4f}s")
    print(f"[endpoint] Total endpoint time: {t3-t0:.4f}s")
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
    t0 = time.time()
    
    # Save uploaded PDF to a temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name
    
    try:
        parser = ResumeParser()
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
        if not res_filters.get("department"):
            res_filters["department"] = list(ENGINEERING_DEPARTMENTS)
        
        recommendations = get_recommendations(
            [query],
            data_file='course-api-new-data.json',
            method='cosine',
            filters=res_filters
        )
        
        formatted = [
            _enrich_course_with_programs({
                "rank": r["rank"],
                "course_code": r["course_code"],
                "title": r["title"],
                "description": r["description"],
                "score": r["score"]
            })
            for r in recommendations[0] if r["method"] == "cosine"
        ]
        
        t1 = time.time()
        print(f"[resume-recommend] Total endpoint time: {t1-t0:.4f}s")
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


@app.get("/random-course")
def random_course():
    """Get a random course from the database."""
    data_json = get_abs_path('data', 'courses', 'course-api-new-data.json')
    df = load_course_data(data_json)
    row = df.sample(1).iloc[0]
    return _enrich_course_with_programs({
        "course_code": row["courseCode"],
        "title": row["title"],
        "description": row["description"]
    })


@app.post("/transcript-parse")
def transcript_parse(file: UploadFile = File(...)):
    """
    Parse an uploaded transcript PDF and return course history.
    
    Args:
        file: Uploaded transcript PDF file
        
    Returns:
        Dictionary with courses, latest_term, program, student_number, term_summaries
    """
    t0 = time.time()
    
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
        
        t1 = time.time()
        print(f"[transcript-parse] Total endpoint time: {t1-t0:.4f}s")
        
        return {
            "courses": all_courses,
            "latest_term": latest_term,
            "program": result.program_name,
            "student_number": result.student_number,
            "term_summaries": term_summaries
        }
        
    except Exception as e:
        print(f"[transcript-parse] Error: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

