import json
import os

def get_data_path(filename):
    """Get the path to a data file in the data directory"""
    # Get the current script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up to the project root (utils -> course-dependencies -> scripts -> root)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    # Construct path to data directory
    data_dir = os.path.join(project_root, 'data')
    return os.path.join(data_dir, filename)

def load_departments(path=None):
    if path is None:
        path = get_data_path("departments.json")
    try:
        with open(path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Warning: {path} not found. Course validation will use regex fallback.")
        return None

def load_courses(path=None):
    if path is None:
        path = get_data_path("courses.json")
    try:
        with open(path, 'r') as file:
            courses_data = json.load(file)
            # Extract just the course codes into a set for efficient lookup
            course_codes = {course.get('courseCode', '') for course in courses_data if course.get('courseCode')}
            return course_codes
    except FileNotFoundError:
        print(f"Warning: {path} not found.")
        return None

def load_full_courses(path=None):
    """Load full course data including PIDs for API calls"""
    if path is None:
        path = get_data_path("courses.json")
    try:
        with open(path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Warning: {path} not found.")
        return None 