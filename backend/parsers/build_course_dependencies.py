"""
Build course_dependencies.json from course_expanded.json.

Converts the expanded format (courses[], prereqs[], antireqs[]) to the 
structured format with prerequisites, corequisites, and antirequisites.
"""

import json
import os
import re
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict

# Load environment variables
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Regex patterns for parsing
LEVEL_PATTERN = re.compile(r'level\s+(\d+[A-Z])\s*(or\s+higher)?', re.IGNORECASE)
PROGRAM_ENROLLMENT_PATTERN = re.compile(r'enrolled\s+in\s+(?:H-|JH-)?([^,\.]+?)(?:,|\s+or\s+|\s*$)', re.IGNORECASE)
NOT_OPEN_PATTERN = re.compile(r'not\s+open\s+to\s+students\s+enrolled\s+in\s+([^,\.]+?)(?:,|\s+or\s+|\s*$)', re.IGNORECASE)
COURSE_CODE_PATTERN = re.compile(r'\b([A-Z]{2,})([0-9]{3}[A-Z]*)\b')
OR_GROUP_PATTERN = re.compile(r'complete\s+(?:at\s+least\s+)?(\d+)\s+of\s+the\s+following', re.IGNORECASE)
AND_GROUP_PATTERN = re.compile(r'complete\s+all\s+of\s+the\s+following', re.IGNORECASE)


class CourseDependencyBuilder:
    """Builder for converting expanded format to structured dependencies."""
    
    def __init__(self, expanded_data: Dict[str, Any]):
        """
        Initialize with expanded data.
        
        Args:
            expanded_data: Dictionary with 'courses', 'prereqs', 'antireqs' keys
        """
        self.courses = {c['code'].lower(): c for c in expanded_data.get('courses', [])}
        
        # Group prereqs by course_code (separating prereqs and coreqs)
        self.prereqs_by_course = defaultdict(list)
        self.coreqs_by_course = defaultdict(list)
        for prereq in expanded_data.get('prereqs', []):
            course_code = prereq['course_code'].lower()
            if prereq.get('is_coreq', False):
                self.coreqs_by_course[course_code].append(prereq)
            else:
                self.prereqs_by_course[course_code].append(prereq)
        
        # Group antireqs by course_code
        self.antireqs_by_course = defaultdict(list)
        for antireq in expanded_data.get('antireqs', []):
            course_code = antireq['course_code'].lower()
            self.antireqs_by_course[course_code].append(antireq)
    
    def parse_level_requirement(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parse level requirement from text.
        
        Returns:
            Dict with 'level' and 'comparison' keys, or None
        """
        match = LEVEL_PATTERN.search(text)
        if match:
            level = match.group(1).upper()
            is_at_least = bool(match.group(2))  # "or higher" indicates at_least
            return {
                "type": "level_requirement",
                "level": level,
                "comparison": "at_least" if is_at_least else "exact"
            }
        return None
    
    def parse_program_names(self, text: str) -> List[str]:
        """
        Parse program names from enrollment text.
        
        Returns:
            List of program names (cleaned)
        """
        programs = []
        matches = PROGRAM_ENROLLMENT_PATTERN.findall(text)
        for match in matches:
            program_text = match.strip()
            # Split by comma or "or" and clean each
            parts = re.split(r',|\s+or\s+', program_text)
            for part in parts:
                cleaned = part.strip().replace('H-', '').replace('JH-', '').strip()
                if cleaned and cleaned not in programs:
                    programs.append(cleaned)
        return programs
    
    def parse_program_restrictions(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse program restrictions from antireqs text.
        
        Returns:
            List of program restriction dictionaries
        """
        restrictions = []
        matches = NOT_OPEN_PATTERN.findall(text)
        for match in matches:
            program_text = match.strip()
            parts = re.split(r',|\s+or\s+', program_text)
            for part in parts:
                cleaned = part.strip().replace('H-', '').replace('JH-', '').strip()
                if cleaned:
                    restrictions.append({
                        "type": "program_restriction",
                        "program_name": cleaned,
                        "program_type": None,
                        "faculty": None,
                        "restriction_type": "not_open"
                    })
        return restrictions
    
    def _build_groups_from_courses(self, course_list: List[Dict], text: str, 
                                    code_key: str = 'prereq_code') -> List[Dict[str, Any]]:
        """
        Build course groups from a list of course relationships.
        
        Args:
            course_list: List of course relationship dicts
            text: Text to parse for OR/AND patterns
            code_key: Key to use for course code ('prereq_code' or 'antireq_code')
            
        Returns:
            List of course group dictionaries
        """
        groups = []
        
        if not course_list:
            return groups
        
        num_courses = len(course_list)
        
        # If only one course, always use flat structure
        if num_courses == 1:
            groups.append({
                "type": "course",
                "code": course_list[0][code_key].upper(),
                "name": None,
                "grade_requirement": None
            })
            return groups
        
        # For multiple courses, determine if they should be grouped
        # Check for OR patterns: "at least 1 of" or "1 of the following"
        or_match = OR_GROUP_PATTERN.search(text) if text else None
        and_match = AND_GROUP_PATTERN.search(text) if text else None
        at_least_one_pattern = re.compile(r'at\s+least\s+1\s+of\s+the\s+following', re.IGNORECASE)
        has_or_pattern = (at_least_one_pattern.search(text) if text else False) or \
                        (or_match and int(or_match.group(1)) == 1)
        
        # If we have OR pattern and multiple courses, create OR group
        if has_or_pattern and num_courses > 1:
            courses = [{
                "type": "course",
                "code": item[code_key].upper(),
                "name": None,
                "grade_requirement": None
            } for item in course_list]
            
            groups.append({
                "type": "prerequisite_group",
                "courses": courses,
                "operator": "OR"
            })
        else:
            # Default to individual courses (AND relationship)
            for item in course_list:
                groups.append({
                    "type": "course",
                    "code": item[code_key].upper(),
                    "name": None,
                    "grade_requirement": None
                })
        
        return groups
    
    def build_prerequisite_groups(self, course_code: str, prereqs_text: str) -> List[Dict[str, Any]]:
        """
        Build prerequisite groups from prerequisites.
        
        Args:
            course_code: Course code in lowercase
            prereqs_text: Prerequisite text
            
        Returns:
            List of prerequisite group dictionaries
        """
        course_prereqs = self.prereqs_by_course.get(course_code, [])
        return self._build_groups_from_courses(course_prereqs, prereqs_text, 'prereq_code')
    
    def build_corequisite_groups(self, course_code: str, coreqs_text: str) -> List[Dict[str, Any]]:
        """
        Build corequisite groups from corequisites.
        
        Args:
            course_code: Course code in lowercase
            coreqs_text: Corequisite text
            
        Returns:
            List of corequisite group dictionaries
        """
        course_coreqs = self.coreqs_by_course.get(course_code, [])
        return self._build_groups_from_courses(course_coreqs, coreqs_text, 'prereq_code')
    
    def build_antirequisite_groups(self, course_code: str, antireqs_text: str) -> List[Dict[str, Any]]:
        """
        Build antirequisite groups from antirequisites.
        
        Args:
            course_code: Course code in lowercase
            antireqs_text: Antirequisite text (not used for structure, but kept for consistency)
            
        Returns:
            List of antirequisite course dictionaries
        """
        course_antireqs = self.antireqs_by_course.get(course_code, [])
        
        # Antirequisites are typically individual courses (any one blocks enrollment)
        # So we list them individually without grouping
        groups = []
        for antireq in course_antireqs:
            groups.append({
                "type": "course",
                "code": antireq['antireq_code'].upper(),
                "name": None
            })
        
        return groups
    
    def build_program_requirements(self, prereqs_text: str) -> List[Dict[str, Any]]:
        """
        Build program requirements from prerequisite text.
        
        Args:
            prereqs_text: Prerequisite text
            
        Returns:
            List of program requirement dictionaries
        """
        requirements = []
        
        if not prereqs_text:
            return requirements
        
        # Parse level requirement
        level_req = self.parse_level_requirement(prereqs_text)
        
        # Parse program names
        program_names = self.parse_program_names(prereqs_text)
        
        # Combine level requirements with program names
        if program_names:
            for program_name in program_names:
                req = {
                    "type": "program_requirement",
                    "program_name": program_name,
                    "program_type": None,
                    "faculty": None,
                    "level_requirement": level_req.copy() if level_req else None
                }
                requirements.append(req)
        elif level_req:
            # Level requirement without specific program (use generic)
            req = {
                "type": "program_requirement",
                "program_name": None,
                "program_type": None,
                "faculty": None,
                "level_requirement": level_req
            }
            requirements.append(req)
        
        return requirements
    
    def build_course_dependencies(self, course_code: str) -> Dict[str, Any]:
        """
        Build dependency structure for a single course.
        
        Args:
            course_code: Course code in lowercase (e.g., 'mse401')
            
        Returns:
            Dictionary with prerequisites, corequisites, and antirequisites
        """
        course = self.courses.get(course_code)
        if not course:
            return {
                "prerequisites": {
                    "groups": [],
                    "program_requirements": [],
                    "root_operator": "AND"
                },
                "corequisites": {
                    "groups": [],
                    "root_operator": "AND"
                },
                "antirequisites": {
                    "courses": [],
                    "program_restrictions": []
                }
            }
        
        prereqs_text = course.get('prereqs', '') or ''
        coreqs_text = course.get('coreqs', '') or ''
        antireqs_text = course.get('antireqs', '') or ''
        
        # Build prerequisite groups
        prereq_groups = self.build_prerequisite_groups(course_code, prereqs_text)
        
        # Build corequisite groups
        coreq_groups = self.build_corequisite_groups(course_code, coreqs_text)
        
        # Build antirequisite courses
        antireq_courses = self.build_antirequisite_groups(course_code, antireqs_text)
        
        # Build program requirements (from prereqs text)
        program_requirements = self.build_program_requirements(prereqs_text)
        
        # Build program restrictions (from antireqs text)
        program_restrictions = self.parse_program_restrictions(antireqs_text)
        
        return {
            "prerequisites": {
                "groups": prereq_groups,
                "program_requirements": program_requirements,
                "root_operator": "AND"
            },
            "corequisites": {
                "groups": coreq_groups,
                "root_operator": "AND"
            },
            "antirequisites": {
                "courses": antireq_courses,
                "program_restrictions": program_restrictions
            }
        }
    
    def build_all_dependencies(self) -> Dict[str, Any]:
        """
        Build dependencies for all courses.
        
        Returns:
            Dictionary mapping course codes (uppercase) to dependency structures
        """
        result = {}
        
        for course_code in self.courses.keys():
            result[course_code.upper()] = self.build_course_dependencies(course_code)
        
        return result


def main():
    """Main function to build course_dependencies.json from course_expanded.json."""
    # Paths
    project_root = PROJECT_ROOT
    expanded_path = os.path.join(project_root, 'data', 'dependencies', 'course_expanded.json')
    output_path = os.path.join(project_root, 'data', 'dependencies', 'course_dependencies.json')
    
    # Load expanded data
    print(f"Loading course_expanded.json from {expanded_path}...")
    with open(expanded_path, 'r', encoding='utf-8') as f:
        expanded_data = json.load(f)
    
    courses_count = len(expanded_data.get('courses', []))
    prereqs_count = sum(1 for p in expanded_data.get('prereqs', []) if not p.get('is_coreq', False))
    coreqs_count = sum(1 for p in expanded_data.get('prereqs', []) if p.get('is_coreq', False))
    antireqs_count = len(expanded_data.get('antireqs', []))
    
    print(f"Loaded {courses_count} courses")
    print(f"  - Prerequisites: {prereqs_count}")
    print(f"  - Corequisites: {coreqs_count}")
    print(f"  - Antirequisites: {antireqs_count}")
    
    # Build dependencies
    print(f"\nBuilding course dependencies...")
    builder = CourseDependencyBuilder(expanded_data)
    dependencies = builder.build_all_dependencies()
    
    print(f"Built dependencies for {len(dependencies)} courses")
    
    # Count statistics
    total_prereq_groups = sum(len(dep['prerequisites'].get('groups', [])) for dep in dependencies.values())
    total_coreq_groups = sum(len(dep['corequisites'].get('groups', [])) for dep in dependencies.values())
    total_antireq_courses = sum(len(dep['antirequisites'].get('courses', [])) for dep in dependencies.values())
    total_program_reqs = sum(len(dep['prerequisites'].get('program_requirements', [])) for dep in dependencies.values())
    total_program_restrictions = sum(len(dep['antirequisites'].get('program_restrictions', [])) for dep in dependencies.values())
    
    # Count courses with each type
    courses_with_prereqs = sum(1 for dep in dependencies.values() if dep['prerequisites'].get('groups'))
    courses_with_coreqs = sum(1 for dep in dependencies.values() if dep['corequisites'].get('groups'))
    courses_with_antireqs = sum(1 for dep in dependencies.values() if dep['antirequisites'].get('courses'))
    courses_with_program_reqs = sum(1 for dep in dependencies.values() if dep['prerequisites'].get('program_requirements'))
    courses_with_restrictions = sum(1 for dep in dependencies.values() if dep['antirequisites'].get('program_restrictions'))
    
    print(f"\nStatistics:")
    print(f"  - Prerequisite groups: {total_prereq_groups}")
    print(f"  - Corequisite groups: {total_coreq_groups}")
    print(f"  - Antirequisite courses: {total_antireq_courses}")
    print(f"  - Program requirements: {total_program_reqs}")
    print(f"  - Program restrictions: {total_program_restrictions}")
    
    print(f"\nBreakdown:")
    print(f"  - Courses with prerequisites: {courses_with_prereqs}")
    print(f"  - Courses with corequisites: {courses_with_coreqs}")
    print(f"  - Courses with antirequisites: {courses_with_antireqs}")
    print(f"  - Courses with program requirements: {courses_with_program_reqs}")
    print(f"  - Courses with program restrictions: {courses_with_restrictions}")
    
    # Save results
    print(f"\nSaving results to {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(dependencies, f, indent=2, ensure_ascii=False)
    
    print("Done!")


if __name__ == "__main__":
    main()
