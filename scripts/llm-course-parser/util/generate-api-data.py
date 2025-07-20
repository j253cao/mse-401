API_URL = "https://openapi.data.uwaterloo.ca/v3/Courses/1255"

import requests

# Remove unused initial request
# response = requests.get(API_URL)

import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
api_key = os.getenv('waterloo-open-api-key')

# Set up headers with API key
headers = {
    'x-api-key': api_key
}
import time

# Dictionary to store API responses
course_api_data = {}

def save_api_data(data):
    """Save the API data to a JSON file"""
    output_path = data_dir / 'waterloo-open-api-data.json'
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Saved API data to {output_path}")

# Load courses from data folder
# Load courses from data/courses.json
script_dir = Path(__file__).resolve().parent
# data_dir is now absolute, relative to script location
data_dir = script_dir.parent.parent.parent / 'data'
courses_path = data_dir / 'courses.json'
with open(courses_path) as f:
    courses = json.load(f)

course_api_data = {}

# Query the API URL and print the response
response = requests.get(API_URL, headers=headers)
print(f"Processing {API_URL}: {response.status_code}")
if response.ok:
    data = response.json()
    print(json.dumps(data, indent=2))
    # Build dict with course code as key and API data as value
    course_dict = {}
    for course in data:
        code = f"{course.get('associatedAcademicOrgCode','')}{course.get('catalogNumber','')}"
        course_dict[code] = course
    # Save to JSON file
    output_path = script_dir.parent.parent.parent / 'data' / 'waterloo-open-api-data.json'
    with open(output_path, 'w') as f:
        json.dump(course_dict, f, indent=2)
    print(f"Saved API data to {output_path}")
else:
    print(f"Failed to fetch data: {response.status_code}")