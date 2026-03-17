"""
Fetch course data from Waterloo OpenData API and save to course-api-new-data.json

Usage:
    python backend/scripts/parsers/fetch_course_data.py
"""

import json
import os
import requests
import time
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables from project root .env file
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# API Configuration
API_BASE_URL = "https://openapi.data.uwaterloo.ca/v3"
API_KEY = os.getenv("WATERLOO_API_KEY")
# Term code for Winter 2026
TERM_CODE = "1261"
TERM_NAME = "Winter 2026"
OUTPUT_FILE = os.path.join(PROJECT_ROOT, 'data', 'courses', 'course-api-new-data.json')

if not API_KEY:
    raise ValueError(
        "WATERLOO_API_KEY environment variable is not set. "
        "Please add it to your .env file. See .env.example for format."
    )


def make_api_request(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict]:
    """
    Make a request to the Waterloo OpenData API.

    Args:
        endpoint: API endpoint (e.g., '/courses' or '/subjects')
        params: Optional query parameters

    Returns:
        JSON response as dictionary, or None if request failed
    """
    url = f"{API_BASE_URL}{endpoint}"
    headers = {
        'X-API-KEY': API_KEY,
        'Accept': 'application/json'
    }

    try:
        print(f"Fetching: {url}")
        response = requests.get(url, headers=headers, params=params, timeout=30)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            print(f"Rate limited. Waiting 60 seconds...")
            time.sleep(60)
            return make_api_request(endpoint, params)
        else:
            print(f"Error {response.status_code}: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None


def get_all_subjects() -> List[Dict[str, Any]]:
    """Fetch all subject codes from the API."""
    print("Fetching all subjects...")
    data = make_api_request('/subjects')

    if data and isinstance(data, list):
        print(f"Found {len(data)} subjects")
        return data
    elif data and isinstance(data, dict) and 'data' in data:
        print(f"Found {len(data['data'])} subjects")
        return data['data']
    else:
        print("No subjects found or unexpected response format")
        return []


def get_courses_for_subject(subject_code: str) -> List[Dict[str, Any]]:
    """Fetch all courses for a given subject code."""
    endpoint = f'/subjects/{subject_code}/courses'
    data = make_api_request(endpoint)

    if data and isinstance(data, list):
        return data
    elif data and isinstance(data, dict) and 'data' in data:
        return data['data']
    else:
        return []


def get_terms() -> List[Dict[str, Any]]:
    """Fetch available terms from the API."""
    print("Fetching available terms...")
    data = make_api_request('/terms')

    if data and isinstance(data, list):
        return data
    elif data and isinstance(data, dict) and 'data' in data:
        return data['data']
    else:
        # Fallback: return current term (1255 = Spring 2025)
        return [{"termCode": "1255", "termName": "Spring 2025"}]


def get_all_courses() -> Optional[List[Dict[str, Any]]]:
    """Try to fetch all courses directly if endpoint exists."""
    print("Attempting to fetch all courses directly...")
    data = make_api_request('/courses')

    if data and isinstance(data, list):
        print(f"Found {len(data)} courses")
        return data
    elif data and isinstance(data, dict) and 'data' in data:
        print(f"Found {len(data['data'])} courses")
        return data['data']
    else:
        print("Direct /courses endpoint not available or returned unexpected format")
        return None


def get_courses_by_term(term_code: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch courses for a specific term.
    If term_code is None, tries to get current/latest term.
    """
    if term_code:
        endpoint = f'/terms/{term_code}/courses'
    else:
        # Try to get current term courses
        endpoint = '/courses'  # May need term parameter

    data = make_api_request(endpoint)

    if data and isinstance(data, list):
        return data
    elif data and isinstance(data, dict) and 'data' in data:
        return data['data']
    else:
        return []


def format_course_key(course: Dict[str, Any]) -> str:
    """
    Generate a course key from course data.
    Format: SUBJECTCODE + CATALOGNUMBER (e.g., "ACC610")
    """
    subject_code = course.get('subjectCode', '')
    catalog_number = course.get('catalogNumber', '')

    if subject_code and catalog_number:
        return f"{subject_code}{catalog_number}"
    else:
        # Fallback: try other fields
        course_id = course.get('courseId', '')
        return course_id if course_id else f"UNKNOWN_{hash(str(course))}"


def get_courses_for_term(term_code: str) -> List[Dict[str, Any]]:
    """Fetch all courses for a specific term."""
    endpoint = f'/Courses/{term_code}'
    data = make_api_request(endpoint)

    if data and isinstance(data, list):
        return data
    elif data and isinstance(data, dict) and 'data' in data:
        return data['data']
    else:
        return []


def fetch_all_courses() -> Dict[str, Dict[str, Any]]:
    """
    Fetch all courses for Winter 2026 (term 1261).

    Returns:
        Dictionary mapping course codes to course data
    """
    all_courses = {}

    print(f"Fetching courses for {TERM_NAME} (term {TERM_CODE})...")
    courses = get_courses_for_term(TERM_CODE)

    if not courses:
        print(f"ERROR: No courses found for term {TERM_CODE}")
        return {}

    print(f"Found {len(courses)} courses for term {TERM_CODE}")

    for course in courses:
        course_key = format_course_key(course)
        all_courses[course_key] = course

    return all_courses


def main():
    """Main function to fetch and save course data."""
    print("=" * 60)
    print("Waterloo OpenData API Course Fetcher")
    print("=" * 60)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Term: {TERM_NAME} ({TERM_CODE})")
    print(f"Output file: {OUTPUT_FILE}")
    print()

    # Fetch all courses
    courses = fetch_all_courses()

    if not courses:
        print("ERROR: No courses fetched. Exiting.")
        return

    print(f"\nSuccessfully fetched {len(courses)} courses")

    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    # Save to JSON file
    print(f"Saving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(courses, f, indent=2, ensure_ascii=False)

    print(f"✓ Successfully saved {len(courses)} courses to {OUTPUT_FILE}")

    # Print sample course
    if courses:
        sample_key = list(courses.keys())[0]
        print(f"\nSample course ({sample_key}):")
        print(json.dumps(courses[sample_key], indent=2)[:500] + "...")


if __name__ == "__main__":
    main()

