#!/usr/bin/env python3
"""
Script to split the large course-api-data.json file into 10 smaller files.
"""

import json
import os
from pathlib import Path

def split_course_data():
    """Split course-api-data.json into 10 smaller files."""
    print("🚀 Starting to split course-api-data.json...")
    
    # Create output directory
    output_dir = Path("split_course_data")
    output_dir.mkdir(exist_ok=True)
    print(f"📁 Created output directory: {output_dir}")
    
    # Load the large JSON file
    try:
        with open('course-api-data.json', 'r', encoding='utf-8') as f:
            course_data = json.load(f)
        print(f"📚 Loaded {len(course_data)} courses from course-api-data.json")
    except Exception as e:
        print(f"❌ Error loading course-api-data.json: {e}")
        return
    
    # Convert to list of (course_code, course_data) tuples
    course_items = list(course_data.items())
    total_courses = len(course_items)
    courses_per_file = total_courses // 10
    remainder = total_courses % 10
    
    print(f"📊 Splitting {total_courses} courses into 10 files")
    print(f"📋 Courses per file: {courses_per_file} (with {remainder} extra courses distributed)")
    
    # Split into 10 files
    start_index = 0
    for i in range(10):
        # Calculate how many courses for this file
        if i < remainder:
            file_size = courses_per_file + 1
        else:
            file_size = courses_per_file
        
        end_index = start_index + file_size
        
        # Extract courses for this file
        file_courses = dict(course_items[start_index:end_index])
        
        # Create filename
        filename = f"course_data_part_{i+1:02d}.json"
        filepath = output_dir / filename
        
        # Save to file
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(file_courses, f, indent=2, ensure_ascii=False)
            print(f"💾 Saved {len(file_courses)} courses to {filename}")
        except Exception as e:
            print(f"❌ Error saving {filename}: {e}")
        
        start_index = end_index
    
    print(f"\n🎉 Successfully split course data into 10 files!")
    print(f"📁 Output directory: {output_dir.absolute()}")
    
    # Create a summary file
    summary = {
        "total_courses": total_courses,
        "files_created": 10,
        "courses_per_file": courses_per_file,
        "extra_courses": remainder,
        "file_list": [f"course_data_part_{i+1:02d}.json" for i in range(10)]
    }
    
    summary_file = output_dir / "split_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"📝 Created summary file: {summary_file}")

if __name__ == "__main__":
    split_course_data() 