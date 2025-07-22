from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from vectorizer.main import get_recommendations, get_abs_path
from vectorizer.data_loader import load_course_data
import random
import time
import os
import tempfile
import sys
import json
from enum import Enum
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../src')))
from resume_parser import ResumeParser

app = FastAPI()

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
    filters: Optional[Dict[str, Any]] = None  # Flexible filters dictionary

@app.post("/recommend")
def recommend(request: QueryRequest):
    t0 = time.time()
    print(f"[endpoint] Request received: {request.queries}")
    print(f"[endpoint] Filters: {request.filters}")
    
    t1 = time.time()
    # Pass filters to get_recommendations
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
        
        # Pass filters to get_recommendations
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
    data_json = get_abs_path('data', 'waterloo-open-api-data.json')
    df = load_course_data(data_json)
    row = df.sample(1).iloc[0]
    return {
        "course_code": row["courseCode"],
        "title": row["title"],
        "description": row["description"]
    } 