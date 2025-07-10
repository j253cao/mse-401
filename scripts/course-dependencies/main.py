import json
import time
import os
from utils.data_loader import load_departments, load_courses, load_full_courses
from utils.dependency_parser import format_course_requirements
from utils.course_dependency_builder import get_course_data

def load_checkpoint():
    """Load progress from checkpoint file"""
    checkpoint_file = 'processing_checkpoint.json'
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
                print(f"Found checkpoint: {checkpoint['processed_count']} courses already processed")
                return checkpoint
        except Exception as e:
            print(f"Warning: Could not load checkpoint: {e}")
    return {'processed_count': 0, 'course_dependencies': {}}

def save_checkpoint(processed_count, course_dependencies):
    """Save progress to checkpoint file"""
    checkpoint_file = 'processing_checkpoint.json'
    checkpoint = {
        'processed_count': processed_count,
        'course_dependencies': course_dependencies
    }
    try:
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save checkpoint: {e}")

def main():
    # Load data
    departments = load_departments()
    course_codes_set = load_courses()
    full_courses = load_full_courses()
    
    if departments:
        print(f"DEBUG: Loaded {len(departments)} departments")
    else:
        print("DEBUG: No departments loaded, using regex validation")
    
    if course_codes_set:
        print(f"DEBUG: Loaded {len(course_codes_set)} course codes")
    else:
        print("DEBUG: No courses loaded, using regex validation")
    
    if not full_courses:
        print("ERROR: Could not load full course data. Exiting.")
        return
    
    print(f"DEBUG: Loaded {len(full_courses)} full course records")
    
    # Load checkpoint to resume from where we left off
    checkpoint = load_checkpoint()
    course_dependencies = checkpoint['course_dependencies']
    start_index = checkpoint['processed_count']
    
    total_courses = len(full_courses)
    
    print(f"Starting to process {total_courses} courses from index {start_index}...")
    print(f"Rate limiting: 1 request every 1.5 seconds")
    print("Completed courses:")
    
    for i, course in enumerate(full_courses[start_index:], start_index + 1):
        course_code = course.get('courseCode')
        pid = course.get('pid')
        
        if not course_code or not pid:
            print(f"WARNING: Skipping course {i}/{total_courses} - missing courseCode or pid")
            continue
        
        # Skip if already processed
        if course_code in course_dependencies:
            print(f"Skipping {course_code} ({i}/{total_courses}) - already processed")
            continue
        
        print(f"Processing {course_code} ({i}/{total_courses})...")
        
        try:
            # Fetch course data from API
            raw_data = get_course_data(pid)
            
            # Parse dependencies
            dependencies = format_course_requirements(raw_data, departments, course_codes_set)
            
            # Store results
            course_dependencies[course_code] = {
                'title': course.get('title', ''),
                'department': course.get('department', ''),
                'pid': pid,
                'dependencies': dependencies
            }
            
            # Log completed course
            print(f"✓ {course_code}")
            
            # Save checkpoint every 10 courses
            if i % 10 == 0:
                save_checkpoint(i, course_dependencies)
                print(f"Checkpoint saved at {i} courses")
            
            # Rate limiting: 1 request every 1.5 seconds
            time.sleep(1.5)
            
        except Exception as e:
            print(f"ERROR: Failed to process {course_code}: {str(e)}")
            # Store error information
            course_dependencies[course_code] = {
                'title': course.get('title', ''),
                'department': course.get('department', ''),
                'pid': pid,
                'error': str(e),
                'dependencies': None
            }
            
            # Save checkpoint on error
            save_checkpoint(i, course_dependencies)
            print(f"Checkpoint saved after error at {i} courses")
            
            # Continue with rate limiting even after error
            time.sleep(1.5)
    
    # Save final results to JSON file
    output_file = 'course-dependencies.json'
    with open(output_file, 'w') as f:
        json.dump(course_dependencies, f, indent=2)
    
    # Clean up checkpoint file after successful completion
    checkpoint_file = 'processing_checkpoint.json'
    if os.path.exists(checkpoint_file):
        os.remove(checkpoint_file)
        print("Checkpoint file cleaned up")
    
    print(f"\nCompleted! Processed {len(course_dependencies)} courses.")
    print(f"Results saved to {output_file}")
    
    # Print summary
    successful = sum(1 for data in course_dependencies.values() if data.get('dependencies') is not None)
    failed = len(course_dependencies) - successful
    print(f"Successful: {successful}, Failed: {failed}")

if __name__ == "__main__":
    main() 