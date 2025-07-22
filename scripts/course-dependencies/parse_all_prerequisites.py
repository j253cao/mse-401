#!/usr/bin/env python3
"""
Script to parse all prerequisites from course-api-data.json and create a comprehensive parsed_prerequisites.json file.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

def extract_course_info(html_content: str) -> List[Dict[str, str]]:
    """Extract course codes, titles, and credits from HTML content."""
    courses = []
    
    # Pattern to match course links with titles and credits
    pattern = r'<a[^>]*href="[^"]*courses/view[^"]*"[^>]*>([A-Z]{2,6}\d{3,4}[A-Z]?)</a>[^<]*<!--[^>]*-->[^<]*<!--[^>]*-->[^<]*([^<]+)<!--[^>]*-->[^<]*<span[^>]*>\(([^)]+)\)</span>'
    matches = re.findall(pattern, html_content)
    
    for match in matches:
        course_code, title, credits = match
        courses.append({
            "code": course_code.strip(),
            "title": title.strip(),
            "credits": credits.strip()
        })
    
    return courses

def extract_program_requirements(html_content: str) -> List[str]:
    """Extract program requirements from HTML content."""
    programs = []
    
    # Pattern to match program links
    pattern = r'<a[^>]*href="[^"]*programs/view[^"]*"[^>]*>([^<]+)</a>'
    matches = re.findall(pattern, html_content)
    
    for match in matches:
        program_name = match.strip()
        if program_name and program_name not in programs:
            programs.append(program_name)
    
    return programs

def extract_level_requirement(html_content: str) -> Optional[str]:
    """Extract level requirement from HTML content."""
    pattern = r'level\s+(\w+)'
    match = re.search(pattern, html_content)
    if match:
        return match.group(1)
    return None

def extract_grade_requirement(html_content: str) -> Optional[str]:
    """Extract grade requirement from HTML content."""
    pattern = r'Earned a minimum grade of\s+<span>(\d+%)</span>'
    match = re.search(pattern, html_content)
    if match:
        return match.group(1)
    return None

def parse_prerequisites_html(html_content: str) -> Dict[str, Any]:
    """Parse HTML content and extract prerequisite structure."""
    if not html_content or html_content.strip() == "":
        return {"type": "none", "rules": []}
    
    # Check for "Complete all of the following"
    if "Complete all of the following" in html_content:
        requirement_type = "all"
    elif "Complete 1 of the following" in html_content or "Complete one of the following" in html_content:
        requirement_type = "one_of"
    else:
        requirement_type = "one_of"
    
    rules = []
    
    # Extract course requirements
    courses = extract_course_info(html_content)
    if courses:
        course_rules = []
        for course in courses:
            course_rule = {
                "type": "course_requirement",
                "code": course["code"],
                "description": f"{course['code']} - {course['title']} ({course['credits']})"
            }
            
            # Check for grade requirement in the same section
            grade_req = extract_grade_requirement(html_content)
            if grade_req:
                course_rule["grade_requirement"] = grade_req
            
            course_rules.append(course_rule)
        
        if len(course_rules) > 1:
            rules.append({
                "type": "one_of",
                "rules": course_rules
            })
        else:
            rules.append({
                "type": "one_of",
                "rules": course_rules
            })
    
    # Extract program requirements
    programs = extract_program_requirements(html_content)
    if programs:
        program_rules = []
        for program in programs:
            program_rules.append({
                "type": "program_requirement",
                "description": program
            })
        
        rules.append({
            "type": "one_of",
            "rules": program_rules
        })
    
    # Extract level requirements
    level_req = extract_level_requirement(html_content)
    if level_req:
        rules.append({
            "type": "one_of",
            "rules": [{
                "type": "program_requirement",
                "description": level_req
            }]
        })
    
    # If no specific rules found, create a generic one
    if not rules:
        rules.append({
            "type": "one_of",
            "rules": [{
                "type": "other_requirement",
                "description": "Requirements specified in course description"
            }]
        })
    
    return {
        "type": requirement_type,
        "rules": rules
    }

def parse_corequisites_html(html_content: str) -> Optional[Dict[str, Any]]:
    """Parse corequisites HTML content."""
    if not html_content or html_content.strip() == "":
        return None
    
    courses = extract_course_info(html_content)
    if courses:
        course_rules = []
        for course in courses:
            course_rules.append({
                "type": "course_requirement",
                "code": course["code"],
                "description": f"{course['code']} - {course['title']} ({course['credits']})"
            })
        
        return {
            "type": "one_of",
            "rules": course_rules
        }
    
    return None

def parse_antirequisites_html(html_content: str) -> Optional[Dict[str, Any]]:
    """Parse antirequisites HTML content."""
    if not html_content or html_content.strip() == "":
        return None
    
    courses = extract_course_info(html_content)
    if courses:
        course_rules = []
        for course in courses:
            course_rules.append({
                "type": "course_requirement",
                "code": course["code"],
                "description": f"{course['code']} - {course['title']} ({course['credits']})"
            })
        
        return {
            "type": "all",
            "rules": course_rules
        }
    
    return None

def main():
    """Main function to parse all prerequisites from course-api-data.json."""
    print("🚀 Starting to parse all prerequisites from course-api-data.json...")
    
    # Load the course API data
    try:
        with open('course-api-data.json', 'r', encoding='utf-8') as f:
            course_data = json.load(f)
        print(f"📚 Loaded {len(course_data)} courses from course-api-data.json")
    except Exception as e:
        print(f"❌ Error loading course-api-data.json: {e}")
        return
    
    # Parse prerequisites for each course
    parsed_prerequisites = {}
    successful_parses = 0
    failed_parses = 0
    
    for course_code, course_info in course_data.items():
        try:
            print(f"📋 Processing {course_code}...")
            
            # Get the API data
            api_data = course_info.get('api_data', {})
            
            # Parse prerequisites
            prerequisites_html = api_data.get('prerequisites', '')
            parsed_prereq = parse_prerequisites_html(prerequisites_html)
            
            # Parse corequisites
            corequisites_html = api_data.get('corequisites', '')
            parsed_coreq = parse_corequisites_html(corequisites_html)
            
            # Parse antirequisites
            antirequisites_html = api_data.get('antirequisites', '')
            parsed_antireq = parse_antirequisites_html(antirequisites_html)
            
            # Create the complete course entry
            parsed_prerequisites[course_code] = {
                "courseCode": course_info.get('courseCode', course_code),
                "title": course_info.get('title', ''),
                "department": course_info.get('department', ''),
                "pid": course_info.get('pid', ''),
                "api_data": api_data,
                "parsed_prerequisites": {
                    "prerequisite": parsed_prereq if parsed_prereq.get("rules") else None,
                    "corequisite": parsed_coreq,
                    "antirequisite": parsed_antireq
                }
            }
            
            successful_parses += 1
            
        except Exception as e:
            print(f"❌ Error processing {course_code}: {e}")
            failed_parses += 1
    
    # Save the parsed prerequisites
    output_file = Path("../parsed_prerequisites.json")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(parsed_prerequisites, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved parsed prerequisites to {output_file}")
    except Exception as e:
        print(f"❌ Error saving parsed prerequisites: {e}")
        return
    
    # Print summary
    print(f"\n🎉 Parsing completed!")
    print(f"✅ Successful parses: {successful_parses}")
    print(f"❌ Failed parses: {failed_parses}")
    print(f"📊 Total courses processed: {len(parsed_prerequisites)}")
    print(f"📁 Output file: {output_file.absolute()}")

if __name__ == "__main__":
    main() 