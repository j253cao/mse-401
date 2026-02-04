"""
Parse course prerequisites from course-api-data.json and generate structured course dependencies.

Ported from Go: flow/importer/uw/parts/course/convert.go
Output matches Go's ConvertResult structure with separate courses[], prereqs[], antireqs[] lists.
"""

import json
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, Any, List, Tuple
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Load environment variables from project root .env file
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Regex patterns for course code parsing (ported from Go)
SUBJECT_REGEX = re.compile(r'\b[A-Z]{2,}\b')
NUMBER_REGEX = re.compile(r'\b[0-9]{3}[A-Z]*\b')
# Pattern to match complete course codes like CS115, MSE401, ECE240
COMPLETE_COURSE_CODE_REGEX = re.compile(r'\b([A-Z]{2,})([0-9]{3}[A-Z]*)\b')


# =============================================================================
# Data Structures (matching Go's struct.go)
# =============================================================================

@dataclass
class Course:
    """Course record with expanded prerequisite text."""
    code: str                          # e.g., "cs135" (lowercase)
    name: str                          # e.g., "Designing Functional Programs"
    description: Optional[str] = None  # Plain text description
    prereqs: Optional[str] = None      # Expanded prereq text
    coreqs: Optional[str] = None       # Expanded coreq text
    antireqs: Optional[str] = None     # Expanded antireq text


@dataclass
class Prereq:
    """Prerequisite/corequisite relationship record."""
    course_code: str   # The course that has this prereq
    prereq_code: str   # The prerequisite course code
    is_coreq: bool     # True if this is a corequisite


@dataclass
class Antireq:
    """Antirequisite relationship record."""
    course_code: str   # The course that has this antireq
    antireq_code: str  # The antirequisite course code


@dataclass
class ConvertResult:
    """Container for all converted course data (matches Go's convertResult)."""
    courses: List[Course] = field(default_factory=list)
    prereqs: List[Prereq] = field(default_factory=list)
    antireqs: List[Antireq] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "courses": [asdict(c) for c in self.courses],
            "prereqs": [asdict(p) for p in self.prereqs],
            "antireqs": [asdict(a) for a in self.antireqs],
        }


class CourseDependencyParser:
    """
    Parser for extracting structured prerequisite data from course HTML/text.
    
    Ported from Go: flow/importer/uw/parts/course/convert.go
    """
    
    def __init__(self):
        pass
    
    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract readable text from HTML prerequisite content."""
        if not html_content or html_content.strip() == '':
            return ""
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text and clean it up
            text = soup.get_text()
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            return text
        except Exception as e:
            print(f"Warning: Could not parse HTML: {e}")
            return html_content
    
    def _expand_course_codes(self, input_str: str) -> Tuple[str, List[str]]:
        """
        Expand course codes in a string.
        
        Takes a string containing course numbers not necessarily prefixed with a course subject
        and outputs a best attempt at a string where all such numbers are replaced with full 
        uppercase course codes. For example, "One of STAT 230/240/206" becomes 
        "One of STAT230/STAT240/STAT206".
        
        Also extracts complete course codes like "CS115", "MSE401", etc.
        
        Ported from Go's expandCourseCodes function.
        
        Returns:
            Tuple of (expanded_string, list_of_course_codes in lowercase)
        """
        if not input_str:
            return "", []
        
        # First, extract complete course codes (e.g., CS115, MSE401)
        codes = []
        for match in COMPLETE_COURSE_CODE_REGEX.finditer(input_str):
            subject = match.group(1)
            number = match.group(2)
            full_code = (subject + number).lower()
            if full_code not in codes:
                codes.append(full_code)
        
        # Also find separated subject and number matches for expansion
        subjects = [(m.start(), m.end()) for m in SUBJECT_REGEX.finditer(input_str)]
        numbers = [(m.start(), m.end()) for m in NUMBER_REGEX.finditer(input_str)]
        
        # Create sorted list of matches
        matches = []
        sidx, nidx = 0, 0
        slen, nlen = len(subjects), len(numbers)
        
        NUMBER_MATCH = 0
        SUBJECT_MATCH = 1
        
        while sidx < slen and nidx < nlen:
            # Add subjects that come before the next number
            while sidx < slen and subjects[sidx][1] < numbers[nidx][0]:
                matches.append({
                    'kind': SUBJECT_MATCH,
                    'start': subjects[sidx][0],
                    'end': subjects[sidx][1]
                })
                sidx += 1
            
            # Add numbers that come before the next subject
            while nidx < nlen and (sidx >= slen or numbers[nidx][1] < subjects[sidx][0]):
                matches.append({
                    'kind': NUMBER_MATCH,
                    'start': numbers[nidx][0],
                    'end': numbers[nidx][1]
                })
                nidx += 1
        
        # Process matches to build output (for separated format like "STAT 230")
        output_parts = []
        expanded_codes = []  # Codes from separated format expansion
        prev_kind = NUMBER_MATCH
        last_subjects = []
        last_end = 0
        
        for match in matches:
            if match['kind'] == SUBJECT_MATCH:
                if prev_kind == NUMBER_MATCH:
                    output_parts.append(input_str[last_end:match['start']])
                    last_subjects = []
                last_subjects.append(input_str[match['start']:match['end']])
            else:  # NUMBER_MATCH
                if prev_kind == NUMBER_MATCH:
                    output_parts.append(input_str[last_end:match['start']])
                last_end = match['end']
                
                number = input_str[match['start']:match['end']]
                for i, subject in enumerate(last_subjects):
                    output_parts.append(subject + number)
                    if i < len(last_subjects) - 1:
                        output_parts.append('/')
                    expanded_code = (subject + number).lower()
                    if expanded_code not in codes:
                        codes.append(expanded_code)
            
            prev_kind = match['kind']
        
        output_parts.append(input_str[last_end:])
        
        # Return expanded string and all extracted codes (both complete and separated formats)
        return ''.join(output_parts), codes

    # =========================================================================
    # Main Conversion Functions (matching Go's convert.go)
    # =========================================================================
    
    def convert_all(self, course_data: Dict[str, Any], 
                    departments: Optional[List[str]] = None) -> ConvertResult:
        """
        Convert all courses from API data to ConvertResult.
        
        Ported from Go's convertAll function.
        
        Args:
            course_data: Dictionary of course data from course-api-data.json
            departments: Optional list of department codes to filter (e.g., ['CS', 'MATH'])
                        If None, processes all courses.
        
        Returns:
            ConvertResult with populated courses, prereqs, and antireqs lists
        """
        result = ConvertResult()
        
        for course_code, course_info in course_data.items():
            # Filter by department if specified
            if departments:
                # Extract department from course code (e.g., "CS" from "CS135", "ACTSC" from "ACTSC231")
                dept = ''.join(c for c in course_code if c.isalpha())
                if dept not in departments:
                    continue
            
            self.convert_course(result, course_code, course_info)
        
        return result
    
    def convert_course(self, result: ConvertResult, course_code: str, 
                       course_info: Dict[str, Any]) -> None:
        """
        Convert a single course from API data and add to result.
        
        Ported from Go's convertCourse function.
        
        Args:
            result: ConvertResult to append to
            course_code: Course code (e.g., "CS135")
            course_info: Course info dict from course-api-data.json
        """
        api_data = course_info.get('api_data', {})
        
        # Create course code in lowercase (matching Go behavior)
        code = course_code.lower()
        
        # Create new course record
        new_course = Course(
            code=code,
            name=course_info.get('title', api_data.get('title', '')),
            description=api_data.get('description'),
        )
        
        # Process prerequisites (HTML field)
        prereqs_html = api_data.get('prerequisites')
        if prereqs_html:
            prereqs_text = self._extract_text_from_html(prereqs_html)
            if prereqs_text:
                prereq_expanded, prereq_codes = self._expand_course_codes(prereqs_text)
                new_course.prereqs = prereq_expanded if prereq_expanded else None
                
                # Create Prereq records for each extracted code
                for prereq_code in prereq_codes:
                    result.prereqs.append(Prereq(
                        course_code=code,
                        prereq_code=prereq_code,
                        is_coreq=False
                    ))
        
        # Process corequisites (HTML field)
        coreqs_html = api_data.get('corequisites')
        if coreqs_html:
            coreqs_text = self._extract_text_from_html(coreqs_html)
            if coreqs_text:
                coreq_expanded, coreq_codes = self._expand_course_codes(coreqs_text)
                new_course.coreqs = coreq_expanded if coreq_expanded else None
                
                # Create Prereq records with is_coreq=True (matching Go behavior)
                for coreq_code in coreq_codes:
                    result.prereqs.append(Prereq(
                        course_code=code,
                        prereq_code=coreq_code,
                        is_coreq=True
                    ))
        
        # Process antirequisites (HTML field)
        antireqs_html = api_data.get('antirequisites')
        if antireqs_html:
            antireqs_text = self._extract_text_from_html(antireqs_html)
            if antireqs_text:
                antireq_expanded, antireq_codes = self._expand_course_codes(antireqs_text)
                new_course.antireqs = antireq_expanded if antireq_expanded else None
                
                # Create Antireq records
                for antireq_code in antireq_codes:
                    result.antireqs.append(Antireq(
                        course_code=code,
                        antireq_code=antireq_code
                    ))
        
        result.courses.append(new_course)
    
def main():
    """
    Main function to parse course dependencies.
    
    Converts course-api-data.json to ConvertResult with separate courses[], prereqs[], antireqs[] lists.
    """
    # Paths
    project_root = PROJECT_ROOT
    course_data_path = os.path.join(project_root, 'data', 'courses', 'course-api-data.json')
    output_path = os.path.join(project_root, 'data', 'dependencies', 'course_expanded.json')
    
    # Load course data
    print(f"Loading course data from {course_data_path}...")
    with open(course_data_path, 'r', encoding='utf-8') as f:
        course_data = json.load(f)
    
    print(f"Loaded {len(course_data)} courses")
    
    # Initialize parser
    parser = CourseDependencyParser()
    
    # Engineering departments at University of Waterloo
    departments = [
        'BME',   # Biomedical Engineering
        'CHE',   # Chemical Engineering
        'CIVE',  # Civil Engineering
        'ECE',   # Electrical and Computer Engineering
        'ENVE',  # Environmental Engineering
        'GEOE',  # Geological Engineering
        'ME',    # Mechanical Engineering
        'MTE',   # Mechatronics Engineering
        'MSE',   # Management Science and Engineering
        'NE',    # Nanotechnology Engineering
        'SE',    # Software Engineering
        'SYDE',  # Systems Design Engineering
    ]
    
    # Convert all courses
    print(f"\nConverting courses...")
    if departments:
        print(f"Filtering by departments: {departments}")
    
    result = parser.convert_all(course_data, departments=departments)
    
    print(f"\nConversion complete:")
    print(f"  - Courses: {len(result.courses)}")
    print(f"  - Prerequisites: {len(result.prereqs)}")
    print(f"  - Antirequisites: {len(result.antireqs)}")
    
    # Save results as JSON
    print(f"\nSaving results to {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
    
    print(f"Done!")


if __name__ == "__main__":
    main()
