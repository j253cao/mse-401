import re

def extract_rules_from_html(html_section, rule_type='course_requirement'):
    rules = []
    print(f"DEBUG: extract_rules_from_html called with rule_type: {rule_type}")
    print(f"DEBUG: HTML section length: {len(html_section)}")
    html_section = re.sub(r'<!--.*?-->', '', html_section)
    print(f"DEBUG: HTML section after comment removal: {html_section[:200]}...")
    
    # Pattern 1: Detailed course pattern with title and credits (more flexible) - with optional letter suffix
    course_pattern = r'<a\s+href="[^"]*"[^>]*>([A-Z]{2,6}\s*\d{3,4}[A-Z]?)</a>.*?<span[^>]*>\(([^)]+)\)</span>'
    course_matches = re.findall(course_pattern, html_section)
    print(f"DEBUG: Detailed pattern found {len(course_matches)} matches: {course_matches}")
    for code, credits in course_matches:
        # Clean up course code (remove spaces)
        clean_code = re.sub(r'\s+', '', code)
        
        # Extract title from between the link and credits
        title_pattern = rf'<a[^>]*>{re.escape(code)}</a>(.*?)<span[^>]*>\({re.escape(credits)}\)</span>'
        title_match = re.search(title_pattern, html_section)
        title = title_match.group(1).strip() if title_match else clean_code
        
        # Clean up title (remove extra dashes, etc.)
        title = re.sub(r'^[-\s]+', '', title)  # Remove leading dashes/spaces
        title = re.sub(r'[-\s]+$', '', title)  # Remove trailing dashes/spaces
        
        rule_info = {
            'type': rule_type,
            'code': clean_code,
            'description': f"{clean_code} - {title} ({credits.strip()})"
        }
        grade_match = re.search(r'Earned a minimum grade of\s+<span>(\d+%)</span>', html_section)
        if grade_match:
            rule_info['grade_requirement'] = grade_match.group(1)
        rules.append(rule_info)
        print(f"DEBUG: Added detailed rule: {rule_info}")
    
    # Pattern 2: Simple course links (fallback) - with optional letter suffix
    simple_course_links = re.findall(r'<a\s+href="[^"]*"[^>]*>([A-Z]{2,6}\s*\d{3,4}[A-Z]?)</a>', html_section)
    print(f"DEBUG: Simple pattern found {len(simple_course_links)} matches: {simple_course_links}")
    for code in simple_course_links:
        # Clean up course code (remove spaces)
        clean_code = re.sub(r'\s+', '', code)
        if not any(r.get('code') == clean_code for r in rules):
            rule_info = {
                'type': rule_type,
                'code': clean_code,
                'description': clean_code
            }
            rules.append(rule_info)
            print(f"DEBUG: Added simple rule: {rule_info}")
    
    # Pattern 3: Course codes in span tags - with optional letter suffix
    span_pattern = r'<span[^>]*>([A-Z]{2,6}\s*\d{3,4}[A-Z]?)</span>'
    span_codes = re.findall(span_pattern, html_section)
    print(f"DEBUG: Span pattern found {len(span_codes)} matches: {span_codes}")
    for code in span_codes:
        # Clean up course code (remove spaces)
        clean_code = re.sub(r'\s+', '', code)
        if not any(r.get('code') == clean_code for r in rules):
            rule_info = {
                'type': rule_type,
                'code': clean_code,
                'description': clean_code
            }
            rules.append(rule_info)
            print(f"DEBUG: Added span rule: {rule_info}")
    
    # Pattern 4: Plain text course codes (fallback) - with optional letter suffix
    plain_pattern = r'\b([A-Z]{2,6}\s*\d{3,4}[A-Z]?)\b'
    plain_codes = re.findall(plain_pattern, html_section)
    print(f"DEBUG: Plain pattern found {len(plain_codes)} matches: {plain_codes}")
    for code in plain_codes:
        # Clean up course code (remove spaces)
        clean_code = re.sub(r'\s+', '', code)
        if not any(r.get('code') == clean_code for r in rules):
            rule_info = {
                'type': rule_type,
                'code': clean_code,
                'description': clean_code
            }
            rules.append(rule_info)
            print(f"DEBUG: Added plain rule: {rule_info}")
    
    # Pattern 5: Requirements (non-course)
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

def extract_simple_rules(html, exclude_codes=None):
    # Updated to handle course codes with spaces and optional letter suffixes
    # Pattern 1: Course codes without spaces - with optional letter suffix
    course_codes = re.findall(r'\b([A-Z]{2,6}\d{3,4}[A-Z]?)\b', html)
    
    # Pattern 2: Course codes with spaces (e.g., "CS 135") - with optional letter suffix
    spaced_pattern = r'\b([A-Z]{2,6})\s+(\d{3,4}[A-Z]?)\b'
    spaced_matches = re.findall(spaced_pattern, html)
    for dept, num in spaced_matches:
        course_codes.append(f"{dept}{num}")
    
    # Pattern 3: Course codes in HTML tags (anchor, span, etc.) - with optional letter suffix
    html_pattern = r'<[^>]*>([A-Z]{2,6}\s*\d{3,4}[A-Z]?)</[^>]*>'
    html_matches = re.findall(html_pattern, html)
    for code in html_matches:
        # Clean up course code (remove spaces)
        clean_code = re.sub(r'\s+', '', code)
        course_codes.append(clean_code)
    
    # Deduplicate course codes while preserving order
    seen = set()
    unique_codes = []
    for code in course_codes:
        if code not in seen:
            unique_codes.append(code)
            seen.add(code)
    
    # Exclude codes if provided
    if exclude_codes is not None:
        filtered_codes = [code for code in unique_codes if code not in exclude_codes]
        print(f"DEBUG: extract_simple_rules excluded codes: {[code for code in unique_codes if code in exclude_codes]}")
    else:
        filtered_codes = unique_codes
    
    print(f"DEBUG: extract_simple_rules found {len(filtered_codes)} unique codes (after exclusion): {filtered_codes}")
    return [{'type': 'course_requirement', 'code': code} for code in filtered_codes] 