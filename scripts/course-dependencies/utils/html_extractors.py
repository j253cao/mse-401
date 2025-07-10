import re

def extract_rules_from_html(html_section, rule_type='course_requirement'):
    rules = []
    print(f"DEBUG: extract_rules_from_html called with rule_type: {rule_type}")
    print(f"DEBUG: HTML section length: {len(html_section)}")
    html_section = re.sub(r'<!--.*?-->', '', html_section)
    print(f"DEBUG: HTML section after comment removal: {html_section[:200]}...")
    
    # Pattern 1: Detailed course pattern with title and credits (more flexible)
    course_pattern = r'<a\s+href="[^"]*"[^>]*>([A-Z]{2,6}\d{3,4})</a>.*?<span[^>]*>\(([^)]+)\)</span>'
    course_matches = re.findall(course_pattern, html_section)
    print(f"DEBUG: Detailed pattern found {len(course_matches)} matches: {course_matches}")
    for code, credits in course_matches:
        # Extract title from between the link and credits
        title_pattern = rf'<a[^>]*>{code}</a>(.*?)<span[^>]*>\({credits}\)</span>'
        title_match = re.search(title_pattern, html_section)
        title = title_match.group(1).strip() if title_match else code
        
        # Clean up title (remove extra dashes, etc.)
        title = re.sub(r'^[-\s]+', '', title)  # Remove leading dashes/spaces
        title = re.sub(r'[-\s]+$', '', title)  # Remove trailing dashes/spaces
        
        rule_info = {
            'type': rule_type,
            'code': code.strip(),
            'description': f"{code} - {title} ({credits.strip()})"
        }
        grade_match = re.search(r'Earned a minimum grade of\s+<span>(\d+%)</span>', html_section)
        if grade_match:
            rule_info['grade_requirement'] = grade_match.group(1)
        rules.append(rule_info)
        print(f"DEBUG: Added detailed rule: {rule_info}")
    
    # Pattern 2: Simple course links (fallback)
    simple_course_links = re.findall(r'<a\s+href="[^"]*"[^>]*>([A-Z]{2,6}\d{3,4})</a>', html_section)
    print(f"DEBUG: Simple pattern found {len(simple_course_links)} matches: {simple_course_links}")
    for code in simple_course_links:
        if not any(r.get('code') == code for r in rules):
            rule_info = {
                'type': rule_type,
                'code': code.strip(),
                'description': code.strip()
            }
            rules.append(rule_info)
            print(f"DEBUG: Added simple rule: {rule_info}")
    
    # Pattern 3: Requirements (non-course)
    requirement_pattern = r'<div[^>]*>([^<]+)</div>'
    requirement_matches = re.findall(requirement_pattern, html_section)
    print(f"DEBUG: Requirement pattern found {len(requirement_matches)} matches: {requirement_matches}")
    for req in requirement_matches:
        req = req.strip()
        if req and not any(r.get('code') and r['code'] in req for r in rules):
            if 'Students must be in level' in req or 'Corequisite' in req:
                rule_info = {
                    'type': 'program_requirement',
                    'description': req
                }
                rules.append(rule_info)
                print(f"DEBUG: Added requirement rule: {rule_info}")
    
    print(f"DEBUG: Total rules extracted: {len(rules)}")
    return rules

def extract_simple_rules(html):
    course_codes = re.findall(r'\b([A-Z]{2,6}\d{3,4})\b', html)
    print(f"DEBUG: extract_simple_rules found {len(course_codes)} codes: {course_codes}")
    return [{'type': 'course_requirement', 'code': code} for code in course_codes] 