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
import random
import time
import os
import tempfile
import sys

# Add backend to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from recommender.main import get_recommendations, get_abs_path
from recommender.data_loader import load_course_data
from parsers.resume_parser import ResumeParser
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
    
    t1 = time.time()
    results = get_recommendations(
        request.queries,
        data_file='waterloo-open-api-data.json',
        method='cosine',
        filters=request.filters
    )
    t2 = time.time()
    print(f"[endpoint] Recommendation call: {t2-t1:.4f}s")
    
    # Formatting
    formatted = {}
    for q, q_results in zip(request.queries, results):
        cosine_results = [r for r in q_results if r["method"] == "cosine"]
        formatted[q] = [
            {
                "rank": r["rank"],
                "course_code": r["course_code"],
                "title": r["title"],
                "description": r["description"],
                "score": r["score"]
            }
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
        
        recommendations = get_recommendations(
            [query],
            data_file='waterloo-open-api-data.json',
            method='cosine',
            filters=filters
        )
        
        formatted = [
            {
                "rank": r["rank"],
                "course_code": r["course_code"],
                "title": r["title"],
                "description": r["description"],
                "score": r["score"]
            }
            for r in recommendations[0] if r["method"] == "cosine"
        ]
        
        t1 = time.time()
        print(f"[resume-recommend] Total endpoint time: {t1-t0:.4f}s")
        return formatted
    finally:
        os.remove(tmp_path)


@app.get("/random-course")
def random_course():
    """Get a random course from the database."""
    data_json = get_abs_path('data', 'courses', 'waterloo-open-api-data.json')
    df = load_course_data(data_json)
    row = df.sample(1).iloc[0]
    return {
        "course_code": row["courseCode"],
        "title": row["title"],
        "description": row["description"]
    }


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

