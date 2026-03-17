"""
Parse course prerequisites from course-api-new-data.json and generate structured course dependencies.

Ported from Go: flow/importer/uw/parts/course/convert.go
Output matches Go's ConvertResult structure with separate courses[], prereqs[], antireqs[] lists.

Supports two data formats:
1. Old format: Nested structure with api_data containing separate HTML fields for prerequisites, corequisites, antirequisites
2. New format: Flat structure with combined plain text requirementsDescription field
"""

import json
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, Any, List, Tuple
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Load environment variables from project root .env file
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
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

    Supports two data formats:
    1. Old format: Nested structure with api_data containing separate HTML fields
    2. New format: Flat structure with combined plain text requirementsDescription field
    """

    def __init__(self):
        pass

    def _parse_course_requirements(self, requirements: Optional[str]) -> Tuple[str, str, str]:
        """
        Parse course requirements description to separate prereqs, coreqs, antireqs.

        Ported from Go: parseCourseRequirements function in convert.go

        Args:
            requirements: Combined requirements string like "Prereq: CS115. Antireq: CS135"

        Returns:
            Tuple of (prereqs, coreqs, antireqs) strings
        """
        if not requirements or requirements.strip() == '':
            return "", "", ""

        prereqs = ""
        coreqs = ""
        antireqs = ""
        reqs = requirements

        # Find all occurrences of ":" to find where to split the string
        # For each colon, find start index immediately preceding word to determine
        # type such as prereq, coreq, antireq. There are some special cases where
        # multiple show up, such as "prereq/coreq:" where we default to prereq
        start_indices = []
        end_indices = []

        for i, c in enumerate(reqs):
            if c == ':':
                cur_idx = i - 1
                preceding_word = ""

                # Walk backwards to find the preceding word
                while cur_idx >= 0 and reqs[cur_idx] != ' ':
                    preceding_word = reqs[cur_idx] + preceding_word
                    cur_idx -= 1

                # Adjust cur_idx to point to start of word (after the space)
                if cur_idx < 0:
                    cur_idx = 0
                else:
                    cur_idx += 1  # Move past the space to the start of the word

                preceding_word_lower = preceding_word.lower()
                if ('prereq' in preceding_word_lower or
                    'coreq' in preceding_word_lower or
                    'antireq' in preceding_word_lower):
                    start_indices.append(cur_idx)
                    end_indices.append(i)

        # Parse out required substrings without the prefix and trim whitespace
        for i in range(len(start_indices)):
            if i == len(start_indices) - 1:
                next_start_idx = len(reqs)
            else:
                next_start_idx = start_indices[i + 1]

            req_type_string = reqs[start_indices[i]:end_indices[i] + 1].lower()
            req_string = reqs[end_indices[i] + 1:next_start_idx].strip()

            # Remove trailing periods or semicolons
            req_string = req_string.rstrip('.;')

            if 'prereq' in req_type_string:
                prereqs = req_string
            elif 'coreq' in req_type_string:
                coreqs = req_string
            else:  # antireq
                antireqs = req_string

        return prereqs, coreqs, antireqs

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

    def convert_all(self, course_data: Dict[str, Any],
                    departments: Optional[List[str]] = None) -> ConvertResult:
        result = ConvertResult()

        for course_code, course_info in course_data.items():
            if departments:
                dept = ''.join(c for c in course_code if c.isalpha())
                if dept not in departments:
                    continue

            self.convert_course(result, course_code, course_info)

        return result

    def _detect_data_format(self, course_info: Dict[str, Any]) -> str:
        if 'api_data' in course_info:
            return 'old'
        elif 'requirementsDescription' in course_info or 'subjectCode' in course_info:
            return 'new'
        return 'old'

    def convert_course(self, result: ConvertResult, course_code: str,
                       course_info: Dict[str, Any]) -> None:
        code = course_code.lower()
        data_format = self._detect_data_format(course_info)

        if data_format == 'new':
            self._convert_course_new_format(result, code, course_info)
        else:
            self._convert_course_old_format(result, code, course_info)

    def _convert_course_new_format(self, result: ConvertResult, code: str,
                                    course_info: Dict[str, Any]) -> None:
        new_course = Course(
            code=code,
            name=course_info.get('title', ''),
            description=course_info.get('description'),
        )

        requirements_desc = course_info.get('requirementsDescription', '')
        prereqs_text, coreqs_text, antireqs_text = self._parse_course_requirements(requirements_desc)

        if prereqs_text:
            prereq_expanded, prereq_codes = self._expand_course_codes(prereqs_text)
            new_course.prereqs = prereq_expanded if prereq_expanded else None

            for prereq_code in prereq_codes:
                result.prereqs.append(Prereq(
                    course_code=code,
                    prereq_code=prereq_code,
                    is_coreq=False
                ))

        if coreqs_text:
            coreq_expanded, coreq_codes = self._expand_course_codes(coreqs_text)
            new_course.coreqs = coreq_expanded if coreq_expanded else None

            for coreq_code in coreq_codes:
                result.prereqs.append(Prereq(
                    course_code=code,
                    prereq_code=coreq_code,
                    is_coreq=True
                ))

        if antireqs_text:
            antireq_expanded, antireq_codes = self._expand_course_codes(antireqs_text)
            new_course.antireqs = antireq_expanded if antireq_expanded else None

            for antireq_code in antireq_codes:
                result.antireqs.append(Antireq(
                    course_code=code,
                    antireq_code=antireq_code
                ))

        result.courses.append(new_course)

    def _convert_course_old_format(self, result: ConvertResult, code: str,
                                    course_info: Dict[str, Any]) -> None:
        api_data = course_info.get('api_data', {})

        new_course = Course(
            code=code,
            name=course_info.get('title', api_data.get('title', '')),
            description=api_data.get('description'),
        )

        prereqs_html = api_data.get('prerequisites')
        if prereqs_html:
            prereqs_text = self._extract_text_from_html(prereqs_html)
            if prereqs_text:
                prereq_expanded, prereq_codes = self._expand_course_codes(prereqs_text)
                new_course.prereqs = prereq_expanded if prereq_expanded else None

                for prereq_code in prereq_codes:
                    result.prereqs.append(Prereq(
                        course_code=code,
                        prereq_code=prereq_code,
                        is_coreq=False
                    ))

        coreqs_html = api_data.get('corequisites')
        if coreqs_html:
            coreqs_text = self._extract_text_from_html(coreqs_html)
            if coreqs_text:
                coreq_expanded, coreq_codes = self._expand_course_codes(coreqs_text)
                new_course.coreqs = coreq_expanded if coreq_expanded else None

                for coreq_code in coreq_codes:
                    result.prereqs.append(Prereq(
                        course_code=code,
                        prereq_code=coreq_code,
                        is_coreq=True
                    ))

        antireqs_html = api_data.get('antirequisites')
        if antireqs_html:
            antireqs_text = self._extract_text_from_html(antireqs_html)
            if antireqs_text:
                antireq_expanded, antireq_codes = self._expand_course_codes(antireqs_text)
                new_course.antireqs = antireq_expanded if antireq_expanded else None

                for antireq_code in antireq_codes:
                    result.antireqs.append(Antireq(
                        course_code=code,
                        antireq_code=antireq_code
                    ))

        result.courses.append(new_course)


def main():
    """
    Main function to parse course dependencies.

    Converts course API data to ConvertResult with separate courses[], prereqs[], antireqs[] lists.

    Supports both old format (course-api-data.json) and new format (course-api-new-data.json).
    """
    import argparse

    arg_parser = argparse.ArgumentParser(description='Parse course dependencies from API data.')
    arg_parser.add_argument(
        '--input', '-i',
        choices=['old', 'new'],
        default='new',
        help='Input data format: "old" for course-api-data.json, "new" for course-api-new-data.json (default: new)'
    )
    arg_parser.add_argument(
        '--all-departments', '-a',
        action='store_true',
        help='Process all departments instead of just engineering departments'
    )
    args = arg_parser.parse_args()

    project_root = PROJECT_ROOT

    if args.input == 'new':
        course_data_path = os.path.join(project_root, 'data', 'courses', 'course-api-new-data.json')
    else:
        course_data_path = os.path.join(project_root, 'data', 'courses', 'course-api-data.json')

    output_path = os.path.join(project_root, 'data', 'dependencies', 'course_expanded.json')

    print(f"Loading course data from {course_data_path}...")
    with open(course_data_path, 'r', encoding='utf-8') as f:
        course_data = json.load(f)

    print(f"Loaded {len(course_data)} courses")

    parser = CourseDependencyParser()

    departments = None
    if not args.all_departments:
        departments = [
            'AE', 'BME', 'CHE', 'CIVE', 'ECE', 'ENVE', 'GENE', 'GEOE',
            'ME', 'MTE', 'MSE', 'NE', 'SE', 'SYDE',
        ]

    print(f"\nConverting courses...")
    if departments:
        print(f"Filtering by departments: {departments}")
    else:
        print("Processing all departments")

    result = parser.convert_all(course_data, departments=departments)

    coreq_count = sum(1 for p in result.prereqs if p.is_coreq)
    prereq_count = len(result.prereqs) - coreq_count

    print(f"\nConversion complete:")
    print(f"  - Courses: {len(result.courses)}")
    print(f"  - Prerequisites: {prereq_count}")
    print(f"  - Corequisites: {coreq_count}")
    print(f"  - Antirequisites: {len(result.antireqs)}")

    print(f"\nSaving results to {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)

    print("Done!")


if __name__ == "__main__":
    main()

