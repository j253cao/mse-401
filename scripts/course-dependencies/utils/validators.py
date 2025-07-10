import re

def validate_course_code(code, departments=None, courses=None):
    """
    Validate a course code by checking if it exists in the courses set
    Returns True if valid, False otherwise
    """
    if not code:
        return False
    
    # If courses set is provided, check if the code exists in it
    if courses:
        return code in courses
    
    # Fallback to regex validation if no courses set provided
    if departments:
        dept_match = re.match(r'^([A-Z]+)\d+$', code)
        if dept_match:
            dept = dept_match.group(1)
            if dept in departments:
                return True
    return bool(re.match(r'^[A-Z]{2,6}\d{3,4}$', code)) 