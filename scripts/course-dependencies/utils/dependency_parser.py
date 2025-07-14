import re
from .html_extractors import extract_rules_from_html, extract_simple_rules
from .validators import validate_course_code

def normalize_course_code(code):
    if code.startswith("MSCI"):
        return "MSE" + code[4:]
    return code

def parse_prerequisites(prerequisites_html, courses=None):
    if not prerequisites_html:
        return None
    prerequisites_html = re.sub(r'<!--.*?-->', '', prerequisites_html)
    print("DEBUG: Parsing prerequisites...")

    extracted_codes = set()
    # Pattern for "Complete all of the following"
    all_pattern = r'Complete\s+all\s+of\s+the\s+following'
    # Pattern for "Must have completed the following"
    must_all_pattern = r'Must have completed the following'
    # Pattern for "Enrolled in"
    enrolled_pattern = r'Enrolled in'

    # Check for "Complete all of the following"
    if re.search(all_pattern, prerequisites_html, re.IGNORECASE):
        print("DEBUG: Found 'Complete all of the following' pattern")
        all_match = re.search(r'<ul><li><span>Complete\s+all\s+of\s+the\s+following</span><ul>(.*?)</ul></li></ul>', prerequisites_html, re.DOTALL | re.IGNORECASE)
        if all_match:
            all_content = all_match.group(1)
            print(f"DEBUG: All content length: {len(all_content)}")
            all_items = []

            # First, find all nested "Complete 1 of the following" blocks
            complete_one_pattern = r'<span>Complete\s+1\s+of\s+the\s+following</span><ul>(.*?)</ul>'
            complete_one_matches = re.findall(complete_one_pattern, all_content, re.DOTALL)
            print(f"DEBUG: Found {len(complete_one_matches)} 'Complete 1 of the following' blocks")

            for i, one_content in enumerate(complete_one_matches):
                print(f"DEBUG: Processing complete_one block {i+1}")
                one_rules = extract_rules_from_html(one_content)
                print(f"DEBUG: Extracted {len(one_rules)} rules from complete_one block")
                for rule in one_rules:
                    if rule.get('code'):
                        print(f"DEBUG: Found course code: {rule['code']}")
                all_items.append({'type': 'one', 'rules': one_rules})

            # Remove the "Complete 1 of the following" blocks from content to avoid double-counting
            all_content_cleaned = re.sub(complete_one_pattern, '', all_content, flags=re.DOTALL)

            # Look for nested "Must have completed the following" blocks
            must_all_nested_pattern = r'Must have completed the following:.*?<ul[^>]*>(.*?)</ul>'
            must_all_nested_matches = re.findall(must_all_nested_pattern, all_content_cleaned, re.DOTALL | re.IGNORECASE)
            print(f"DEBUG: Found {len(must_all_nested_matches)} nested 'Must have completed the following' blocks")

            for i, must_all_content in enumerate(must_all_nested_matches):
                print(f"DEBUG: Processing nested must_all block {i+1}")
                must_all_rules = extract_rules_from_html(must_all_content)
                print(f"DEBUG: Extracted {len(must_all_rules)} rules from nested must_all block")
                for rule in must_all_rules:
                    if rule.get('code'):
                        print(f"DEBUG: Found course code: {rule['code']}")
                all_items.append({'type': 'all', 'rules': must_all_rules})

            # Remove the "Must have completed the following" blocks from content
            all_content_cleaned = re.sub(must_all_nested_pattern, '', all_content_cleaned, flags=re.DOTALL | re.IGNORECASE)

            # Look for nested "Enrolled in" blocks
            enrolled_nested_pattern = r'Enrolled in.*?<span>(.*?)</span>'
            enrolled_nested_matches = re.findall(enrolled_nested_pattern, all_content_cleaned, re.DOTALL | re.IGNORECASE)
            print(f"DEBUG: Found {len(enrolled_nested_matches)} nested 'Enrolled in' blocks")

            for i, enrolled_content in enumerate(enrolled_nested_matches):
                print(f"DEBUG: Processing nested enrolled block {i+1}")
                # Extract program names from anchor tags
                program_pattern = r'<a[^>]*>([^<]+)</a>'
                programs = re.findall(program_pattern, enrolled_content)
                print(f"DEBUG: Found programs: {programs}")
                if programs:
                    # Create individual program requirements
                    program_rules = []
                    for program in programs:
                        program_rules.append({
                            'type': 'program_requirement',
                            'description': f"Enrolled in: {program}"
                        })
                    # Wrap in a type "one" structure
                    all_items.append({
                        'type': 'one',
                        'rules': program_rules
                    })

            # Remove the "Enrolled in" blocks from content
            all_content_cleaned = re.sub(enrolled_nested_pattern, '', all_content_cleaned, flags=re.DOTALL | re.IGNORECASE)

            # Look for "Must have completed at least 1 of the following" pattern
            must_complete_match = re.search(r'Must have completed at least <span>1</span> of the following:(.*?)</div></div></li>', all_content_cleaned, re.DOTALL)
            if must_complete_match:
                print("DEBUG: Found 'Must have completed at least 1 of the following' pattern")
                must_complete_content = must_complete_match.group(1)
                must_complete_rules = extract_rules_from_html(must_complete_content)
                print(f"DEBUG: Extracted {len(must_complete_rules)} rules from must_complete block")
                for rule in must_complete_rules:
                    if rule.get('code'):
                        print(f"DEBUG: Found course code: {rule['code']}")
                all_items.append({'type': 'one', 'rules': must_complete_rules})

            # Look for any remaining "Must have completed the following:" patterns (individual course requirements)
            remaining_must_complete_pattern = r'Must have completed the following:\s*([A-Z]{2,6}\s*\d{3,4}[A-Z]?)'
            remaining_must_complete_matches = re.findall(remaining_must_complete_pattern, all_content_cleaned)
            print(f"DEBUG: Found {len(remaining_must_complete_matches)} remaining 'Must have completed the following' individual courses")
            for i, course_code in enumerate(remaining_must_complete_matches):
                clean_code = re.sub(r'\s+', '', course_code)
                norm_code = normalize_course_code(clean_code)
                print(f"DEBUG: Found individual course: {norm_code}")
                if norm_code not in extracted_codes:
                    all_items.append({
                        'type': 'course_requirement',
                        'code': norm_code,
                        'description': f"Must have completed: {clean_code}"
                    })
                    extracted_codes.add(norm_code)

            # Look for level requirements
            level_requirement_match = re.search(r'Students must be in level <span>(\d+[A-Z])</span> or higher', all_content_cleaned)
            if level_requirement_match:
                level = level_requirement_match.group(1)
                print(f"DEBUG: Found level requirement: {level}")
                all_items.append({'type': 'program_requirement', 'description': f"Students must be in level {level} or higher"})

            # Look for any remaining simple rules in the cleaned content
            # Collect all previously found codes from all nested structures
            # Apply similar logic for all other places where course codes are added to all_items or rules.
            # Also collect codes from any "Must have completed the following:" individual courses
            for item in all_items:
                if item.get('type') == 'course_requirement' and item.get('code'):
                    extracted_codes.add(normalize_course_code(item['code']))

            print(f"DEBUG: Found codes to exclude: {extracted_codes}")

            # Remove already found course codes from the content to prevent re-matching
            content_for_simple_rules = all_content_cleaned
            for code in extracted_codes:
                # Remove the course code from anchor tags (with spaces)
                content_for_simple_rules = re.sub(rf'<a[^>]*>{code}</a>', '', content_for_simple_rules)
                content_for_simple_rules = re.sub(rf'<a[^>]*>{code[:2]}\s+{code[2:]}</a>', '', content_for_simple_rules)
                # Remove the course code from span tags (with spaces)
                content_for_simple_rules = re.sub(rf'<span[^>]*>{code}</span>', '', content_for_simple_rules)
                content_for_simple_rules = re.sub(rf'<span[^>]*>{code[:2]}\s+{code[2:]}</span>', '', content_for_simple_rules)
                # Remove plain text course codes (with spaces)
                content_for_simple_rules = re.sub(rf'\b{code}\b', '', content_for_simple_rules)
                content_for_simple_rules = re.sub(rf'\b{code[:2]}\s+{code[2:]}\b', '', content_for_simple_rules)
                # Also remove any remaining instances in various HTML contexts
                content_for_simple_rules = re.sub(rf'<[^>]*>{code}[^<]*</[^>]*>', '', content_for_simple_rules)
                content_for_simple_rules = re.sub(rf'<[^>]*>{code[:2]}\s+{code[2:]}[^<]*</[^>]*>', '', content_for_simple_rules)
                # Remove any remaining HTML tags containing the course code
                content_for_simple_rules = re.sub(rf'<[^>]*>{code}[^<]*</[^>]*>', '', content_for_simple_rules, flags=re.DOTALL)
                content_for_simple_rules = re.sub(rf'<[^>]*>{code[:2]}\s+{code[2:]}[^<]*</[^>]*>', '', content_for_simple_rules, flags=re.DOTALL)

            print(f"DEBUG: Content length before simple rules: {len(content_for_simple_rules)}")
            print(f"DEBUG: Content preview before simple rules: {content_for_simple_rules[:500]}...")

            # Use the exclude_codes parameter in extract_simple_rules to prevent duplicates
            remaining_rules = extract_simple_rules(content_for_simple_rules, exclude_codes=extracted_codes)
            filtered_remaining_rules = []
            for rule in remaining_rules:
                if rule.get('code'):
                    rule['code'] = normalize_course_code(rule['code'])
                    if rule['code'] not in extracted_codes:
                        filtered_remaining_rules.append(rule)
                        extracted_codes.add(rule['code'])
            if filtered_remaining_rules:
                print(f"DEBUG: Found {len(filtered_remaining_rules)} remaining simple rules (excluding already found)")
                for rule in filtered_remaining_rules:
                    print(f"DEBUG: Found course code: {rule['code']}")
                all_items.append({'type': 'one', 'rules': filtered_remaining_rules})

            print(f"DEBUG: Total all_items: {len(all_items)}")
            return {'type': 'all', 'rules': all_items}

    # Check for "Must have completed the following" (type all) at the top level
    if re.search(must_all_pattern, prerequisites_html, re.IGNORECASE):
        print("DEBUG: Found top-level 'Must have completed the following' pattern")
        must_all_match = re.search(r'Must have completed the following:?\s*<ul>(.*?)</ul>', prerequisites_html, re.DOTALL | re.IGNORECASE)
        if must_all_match:
            must_all_content = must_all_match.group(1)
            must_all_rules = extract_rules_from_html(must_all_content)
            print(f"DEBUG: Extracted {len(must_all_rules)} rules from top-level must_all")
            for rule in must_all_rules:
                if rule.get('code'):
                    print(f"DEBUG: Found course code: {rule['code']}")
            return {'type': 'all', 'rules': must_all_rules}

    # Check for "Enrolled in" at the top level
    if re.search(enrolled_pattern, prerequisites_html, re.IGNORECASE):
        print("DEBUG: Found top-level 'Enrolled in' pattern")
        enrolled_match = re.search(r'Enrolled in.*?<span>(.*?)</span>', prerequisites_html, re.DOTALL | re.IGNORECASE)
        if enrolled_match:
            enrolled_content = enrolled_match.group(1)
            # Extract program names from anchor tags
            program_pattern = r'<a[^>]*>([^<]+)</a>'
            programs = re.findall(program_pattern, enrolled_content)
            print(f"DEBUG: Found programs: {programs}")
            if programs:
                # Create individual program requirements
                program_rules = []
                for program in programs:
                    program_rules.append({
                        'type': 'program_requirement',
                        'description': f"Enrolled in: {program}"
                    })
                # Return as a type "one" structure
                return {
                    'type': 'one',
                    'rules': program_rules
                }

    # Check for standalone "Complete 1 of the following" at the top level
    complete_one_standalone_pattern = r'<span>Complete\s+1\s+of\s+the\s+following</span><ul>(.*?)</ul>'
    complete_one_standalone_match = re.search(complete_one_standalone_pattern, prerequisites_html, re.DOTALL)
    if complete_one_standalone_match:
        print("DEBUG: Found standalone 'Complete 1 of the following' pattern")
        one_content = complete_one_standalone_match.group(1)
        one_rules = extract_rules_from_html(one_content)
        print(f"DEBUG: Extracted {len(one_rules)} rules from standalone complete_one")
        for rule in one_rules:
            if rule.get('code'):
                print(f"DEBUG: Found course code: {rule['code']}")
        return {'type': 'one', 'rules': one_rules}

    # Check for "Must have completed at least 1 of the following" at the top level
    must_complete_standalone_pattern = r'Must have completed at least <span>1</span> of the following:(.*?)</div></div></li>'
    must_complete_standalone_match = re.search(must_complete_standalone_pattern, prerequisites_html, re.DOTALL)
    if must_complete_standalone_match:
        print("DEBUG: Found standalone 'Must have completed at least 1 of the following' pattern")
        must_complete_content = must_complete_standalone_match.group(1)
        must_complete_rules = extract_rules_from_html(must_complete_content)
        print(f"DEBUG: Extracted {len(must_complete_rules)} rules from standalone must_complete")
        for rule in must_complete_rules:
            if rule.get('code'):
                print(f"DEBUG: Found course code: {rule['code']}")
        return {'type': 'one', 'rules': must_complete_rules}

    # Fallback to simple rules
    simple_rules = extract_simple_rules(prerequisites_html)
    if simple_rules:
        print(f"DEBUG: Found {len(simple_rules)} simple rules")
        for rule in simple_rules:
            if rule.get('code'):
                print(f"DEBUG: Found course code: {rule['code']}")
        return {'type': 'one', 'rules': simple_rules}

    print("DEBUG: No prerequisites found")
    return None

def parse_corequisites(html_content):
    if not html_content:
        return None

    all_course_codes = []

    # Pattern 1: Standard corequisite pattern
    coreq_pattern = r'Completed or concurrently enrolled in at least <span>1</span> of the following:(.*?)</div></div></li>'
    coreq_match = re.search(coreq_pattern, html_content, re.DOTALL)
    if coreq_match:
        coreq_content = coreq_match.group(1)
        coreq_rules = extract_rules_from_html(coreq_content, 'course_requirement')
        return {'type': 'one', 'rules': coreq_rules}

    # Pattern 2: Simple corequisite with anchor tags - with optional letter suffix
    simple_coreq_pattern = r'Corequisite:\s*<a[^>]*>([A-Z]{2,4}\d{3,4}[A-Z]?)</a>'
    simple_coreq_matches = re.findall(simple_coreq_pattern, html_content)
    all_course_codes.extend(simple_coreq_matches)

    # Pattern 3: Course codes in span tags - with optional letter suffix
    span_pattern = r'<span[^>]*>([A-Z]{2,6}\d{3,4}[A-Z]?)</span>'
    span_codes = re.findall(span_pattern, html_content)
    all_course_codes.extend(span_codes)

    # Pattern 4: Plain text course codes (fallback) - with optional letter suffix
    plain_pattern = r'\b([A-Z]{2,6}\d{3,4}[A-Z]?)\b'
    plain_codes = re.findall(plain_pattern, html_content)
    all_course_codes.extend(plain_codes)

    # Pattern 5: Course codes with spaces (e.g., "CS 135") - with optional letter suffix
    spaced_pattern = r'\b([A-Z]{2,6})\s+(\d{3,4}[A-Z]?)\b'
    spaced_matches = re.findall(spaced_pattern, html_content)
    for dept, num in spaced_matches:
        all_course_codes.append(f"{dept}{num}")

    # Remove duplicates
    unique_codes = list(set(all_course_codes))

    if unique_codes:
        return {'type': 'one', 'rules': [{'type': 'course_requirement', 'code': normalize_course_code(code)} for code in unique_codes]}

    return None

def parse_antirequisites(html_content, departments=None, courses=None):
    if not html_content:
        return None

    print("DEBUG: Parsing antirequisites...")
    print(f"DEBUG: HTML content length: {len(html_content)}")

    all_course_codes = []
    all_program_requirements = []

    # Pattern 1: "Not completed nor concurrently enrolled in:" (with HTML structure)
    antireq_pattern1 = r'Not completed nor concurrently enrolled in:(.*?)(?=</div></div></li>|$)'
    antireq_matches1 = re.findall(antireq_pattern1, html_content, re.DOTALL)
    print(f"DEBUG: Found {len(antireq_matches1)} antireq sections (pattern 1)")

    for i, antireq_content in enumerate(antireq_matches1):
        print(f"\nDEBUG: Processing antireq section {i+1} (pattern 1):")
        print(f"DEBUG: Content length: {len(antireq_content)}")
        print(f"DEBUG: Content preview: {antireq_content[:200]}...")

        # Extract course codes from this section
        # Pattern 1: Course codes in anchor tags (primary method) - with optional letter suffix
        anchor_pattern = r'<a[^>]*>([A-Z]{2,6}\d{3,4}[A-Z]?)</a>'
        course_codes = re.findall(anchor_pattern, antireq_content)
        print(f"DEBUG: Anchor pattern found: {course_codes}")
        all_course_codes.extend(course_codes)

        # Pattern 2: Course codes in span tags - with optional letter suffix
        span_pattern = r'<span[^>]*>([A-Z]{2,6}\d{3,4}[A-Z]?)</span>'
        course_codes = re.findall(span_pattern, antireq_content)
        print(f"DEBUG: Span pattern found: {course_codes}")
        all_course_codes.extend(course_codes)

        # Pattern 3: Plain text course codes (fallback) - with optional letter suffix
        plain_pattern = r'\b([A-Z]{2,6}\d{3,4}[A-Z]?)\b'
        course_codes = re.findall(plain_pattern, antireq_content)
        print(f"DEBUG: Plain pattern found: {course_codes}")
        all_course_codes.extend(course_codes)

        # Pattern 4: Course codes with spaces (e.g., "CS 135") - with optional letter suffix
        spaced_pattern = r'\b([A-Z]{2,6})\s+(\d{3,4}[A-Z]?)\b'
        spaced_matches = re.findall(spaced_pattern, antireq_content)
        spaced_codes = [f"{dept}{num}" for dept, num in spaced_matches]
        print(f"DEBUG: Spaced pattern found: {spaced_codes}")
        all_course_codes.extend(spaced_codes)

    # Pattern 2: "Not completed or concurrently enrolled in the following:" (plain text format)
    antireq_pattern2 = r'Not completed or concurrently enrolled in the following:(.*?)(?=</div>|$)'
    antireq_matches2 = re.findall(antireq_pattern2, html_content, re.DOTALL)
    print(f"DEBUG: Found {len(antireq_matches2)} antireq sections (pattern 2)")

    for i, antireq_content in enumerate(antireq_matches2):
        print(f"\nDEBUG: Processing antireq section {i+1} (pattern 2):")
        print(f"DEBUG: Content length: {len(antireq_content)}")
        print(f"DEBUG: Content preview: {antireq_content[:200]}...")

        # Extract course codes from plain text
        # Pattern 1: Plain text course codes - with optional letter suffix
        plain_pattern = r'\b([A-Z]{2,6}\d{3,4}[A-Z]?)\b'
        course_codes = re.findall(plain_pattern, antireq_content)
        print(f"DEBUG: Plain pattern found: {course_codes}")
        all_course_codes.extend(course_codes)

        # Pattern 2: Course codes with spaces (e.g., "CS 135") - with optional letter suffix
        spaced_pattern = r'\b([A-Z]{2,6})\s+(\d{3,4}[A-Z]?)\b'
        spaced_matches = re.findall(spaced_pattern, antireq_content)
        spaced_codes = [f"{dept}{num}" for dept, num in spaced_matches]
        print(f"DEBUG: Spaced pattern found: {spaced_codes}")
        all_course_codes.extend(spaced_codes)

    # Pattern 3: "Not open to students enrolled in:" (program requirements) - more flexible for nested structures
    antireq_pattern3 = r'Not open to students enrolled in:(.*?)(?=</div>|</li>|$)'
    antireq_matches3 = re.findall(antireq_pattern3, html_content, re.DOTALL)
    print(f"DEBUG: Found {len(antireq_matches3)} antireq sections (pattern 3 - programs)")
    print(f"DEBUG: Pattern 3 matches: {antireq_matches3}")

    for i, antireq_content in enumerate(antireq_matches3):
        print(f"\nDEBUG: Processing antireq section {i+1} (pattern 3 - programs):")
        print(f"DEBUG: Content length: {len(antireq_content)}")
        print(f"DEBUG: Content preview: {antireq_content[:200]}...")

        # Extract program names from anchor tags (same logic as prerequisites)
        program_pattern = r'<a[^>]*>([^<]+)</a>'
        programs = re.findall(program_pattern, antireq_content)
        print(f"DEBUG: Found programs: {programs}")
        if programs:
            # Create individual program requirements
            program_rules = []
            for program in programs:
                program_rules.append({
                    'type': 'program_requirement',
                    'description': f"Not open to students enrolled in: {program}"
                })
            # Add to all program requirements
            all_program_requirements.extend(program_rules)

    # Also search for any anchor tags that might be programs in the entire antireq content
    print(f"\nDEBUG: Searching entire antireq content for potential programs...")
    all_anchor_tags = re.findall(r'<a[^>]*>([^<]+)</a>', html_content)
    print(f"DEBUG: All anchor tags found in antireq content: {all_anchor_tags}")

    # Filter for potential programs (not course codes)
    potential_programs = []
    for tag in all_anchor_tags:
        # Skip if it looks like a course code
        if not re.match(r'^[A-Z]{2,6}\d{3,4}[A-Z]?$', tag):
            potential_programs.append(tag)

    print(f"DEBUG: Potential programs (non-course codes): {potential_programs}")

    # If we found potential programs but no "Not open to students enrolled in" pattern,
    # they might be in a different format
    if potential_programs and not all_program_requirements:
        print(f"DEBUG: Found potential programs but no explicit pattern match. Adding as program requirements.")
        for program in potential_programs:
            all_program_requirements.append({
                'type': 'program_requirement',
                'description': f"Not open to students enrolled in: {program}"
            })

    print(f"\nDEBUG: All found codes before deduplication: {all_course_codes}")
    print(f"DEBUG: All found program requirements: {len(all_program_requirements)}")

    # Remove duplicates and validate course codes
    unique_codes = list(set(all_course_codes))
    print(f"DEBUG: Unique codes: {unique_codes}")
    valid_codes = [code for code in unique_codes if validate_course_code(code, departments, courses)]
    print(f"DEBUG: Valid codes: {valid_codes}")

    # Combine course requirements and program requirements
    all_rules = []

    # Add course requirements
    if valid_codes:
        all_rules.extend([{'type': 'course_requirement', 'code': normalize_course_code(code)} for code in valid_codes])

    # Add program requirements
    if all_program_requirements:
        all_rules.extend(all_program_requirements)

    if all_rules:
        return {'type': 'all', 'rules': all_rules}

    return None

def format_course_requirements(course_response, departments=None, courses=None):
    return {
        'prerequisite': parse_prerequisites(course_response.get('prerequisites')),
        'corequisite': parse_corequisites(course_response.get('corequisites')),
        'antirequisite': parse_antirequisites(course_response.get('antirequisites'), departments, courses)
    } 


