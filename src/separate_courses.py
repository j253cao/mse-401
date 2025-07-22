import json
from pathlib import Path
import ijson  # For streaming large JSON files

def load_json_file(file_path: str) -> list:
    """Load and return JSON file content, handling different structures."""
    try:
        courses = []
        with open(file_path, 'rb') as f:
            # Use ijson to stream the file
            parser = ijson.parse(f)
            current_course = {}
            
            for prefix, event, value in parser:
                # Handle both array and object structures
                if prefix.endswith('.courseCode'):
                    if current_course:
                        courses.append(current_course)
                    current_course = {'courseCode': value}
                elif prefix.endswith('.description'):
                    current_course['description'] = value
                elif prefix.endswith('.name'):
                    current_course['name'] = value
                elif prefix.endswith('.prerequisites'):
                    current_course['prerequisites'] = value
                elif prefix.endswith('.antirequisites'):
                    current_course['antirequisites'] = value
                elif prefix.endswith('.corequisites'):
                    current_course['corequisites'] = value
                elif prefix.endswith('.terms'):
                    current_course['terms'] = value
                elif prefix.endswith('.notes'):
                    current_course['notes'] = value
            
            if current_course:
                courses.append(current_course)
                
        print(f"Loaded {len(courses)} courses from {file_path}")
        return courses
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return []

def save_json_file(data: dict, file_path: str):
    """Save data to JSON file."""
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Successfully saved: {file_path}")
    except Exception as e:
        print(f"Error saving {file_path}: {e}")

def main():
    # Get the project root directory
    root_dir = Path(__file__).parent.parent
    
    # Load both course files
    print("Loading undergraduate courses...")
    undergrad_data = load_json_file(root_dir / "data/course-api-data.json")
    print("\nLoading graduate courses...")
    waterloo_data = load_json_file(root_dir / "data/waterloo-open-api-data.json")
    
    if not undergrad_data and not waterloo_data:
        print("Failed to load any course data")
        return
    
    # Extract undergrad course codes
    undergrad_courses = {}
    for course in undergrad_data:
        if 'courseCode' in course:
            undergrad_courses[course['courseCode']] = course
    
    # Extract grad courses (courses in waterloo data but not in undergrad)
    grad_courses = {}
    for course in waterloo_data:
        if 'courseCode' in course and course['courseCode'] not in undergrad_courses:
            # Check if it's likely a graduate course (usually 600+ level)
            course_number = ''.join(filter(str.isdigit, course['courseCode']))
            if course_number and int(course_number) >= 600:
                grad_courses[course['courseCode']] = course
    
    # Save to separate files
    save_json_file(undergrad_courses, root_dir / "data/undergrad-courses.json")
    save_json_file(grad_courses, root_dir / "data/grad-courses.json")
    
    # Print summary
    print(f"\nSummary:")
    print(f"Undergraduate courses: {len(undergrad_courses)}")
    print(f"Graduate courses: {len(grad_courses)}")
    
    # Print some example courses from each
    print("\nExample undergraduate courses:")
    for code in sorted(list(undergrad_courses.keys()))[:5]:
        course = undergrad_courses[code]
        print(f"- {code}: {course.get('name', 'No name available')}")
    
    print("\nExample graduate courses:")
    for code in sorted(list(grad_courses.keys()))[:5]:
        course = grad_courses[code]
        print(f"- {code}: {course.get('name', 'No name available')}")

if __name__ == "__main__":
    main() 