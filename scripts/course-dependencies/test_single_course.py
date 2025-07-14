import json
from utils.data_loader import load_departments, load_courses, load_full_courses
from utils.dependency_parser import format_course_requirements
from utils.course_dependency_builder import get_course_data

def test_single_course(course_code="ACTSC231"):
    """
    Test script to process a single course and display its dependencies
    """
    print(f"Testing course: {course_code}")
    print("=" * 50)
    
    # Load data
    print("Loading data...")
    departments = load_departments()
    course_codes_set = load_courses()
    full_courses = load_full_courses()
    
    if departments:
        print(f"✓ Loaded {len(departments)} departments")
    else:
        print("⚠ No departments loaded, using regex validation")
    
    if course_codes_set:
        print(f"✓ Loaded {len(course_codes_set)} course codes")
    else:
        print("⚠ No courses loaded, using regex validation")
    
    if not full_courses:
        print("❌ ERROR: Could not load full course data. Exiting.")
        return
    
    print(f"✓ Loaded {len(full_courses)} full course records")
    
    # Find the course
    target_course = None
    for course in full_courses:
        if course.get('courseCode') == course_code:
            target_course = course
            break
    
    if not target_course:
        print(f"❌ ERROR: Course {course_code} not found in course database")
        return
    
    print(f"✓ Found course: {course_code}")
    print(f"  Title: {target_course.get('title', 'N/A')}")
    print(f"  Department: {target_course.get('department', 'N/A')}")
    print(f"  PID: {target_course.get('pid', 'N/A')}")
    
    # Load course-api-data.json once
    from utils.data_loader import get_data_path
    with open(get_data_path('course-api-data.json'), 'r') as f:
        course_api_data = json.load(f)
    
    print("MSE436" in course_api_data.keys())

    # Fetch course data from API
    print(f"\nFetching course data from API...")
    try:
        raw_data = get_course_data(target_course['courseCode'], course_api_data)
        print("✓ Successfully fetched course data from API")
    except Exception as e:
        print(f"❌ ERROR: Failed to fetch course data: {str(e)}")
        return
    
    print(f"Raw data: {raw_data}")

    # Parse dependencies
    print(f"\nParsing dependencies...")
    dependencies = format_course_requirements(raw_data, departments, course_codes_set)
    
    # Display results
    print(f"\nDependencies for {course_code}:")
    print("=" * 50)
    
    for req_type, req_data in dependencies.items():
        if req_data:
            print(f"\n{req_type.upper()}:")
            print(json.dumps(req_data, indent=2))
        else:
            print(f"\n{req_type.upper()}: None")
    
    # Save to test file
    test_output = {
        'course_code': course_code,
        'course_info': {
            'title': target_course.get('title', ''),
            'department': target_course.get('department', ''),
            'pid': target_course.get('pid', '')
        },
        'dependencies': dependencies
    }
    
    with open('test_course_output.json', 'w') as f:
        json.dump(test_output, f, indent=2)
    
    print(f"\n✓ Test results saved to test_course_output.json")
    print("=" * 50)

if __name__ == "__main__":
    # You can change the course code here to test different courses
    test_single_course("MSE436")
    
    # Uncomment the line below to test a different course
    # test_single_course("CS135") 