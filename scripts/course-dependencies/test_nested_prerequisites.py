#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.dependency_parser import parse_prerequisites

# Test HTML with nested structure: "Complete all of the following" containing "Complete 1 of the following"
test_html = '''
<ul><li><span>Complete all of the following</span><ul>
    <li><span>Complete 1 of the following</span><ul>
        <li><a href="/courses/CS135">CS 135</a></li>
        <li><a href="/courses/CS145">CS 145</a></li>
    </ul></li>
    <li><span>Complete 1 of the following</span><ul>
        <li><a href="/courses/MATH135">MATH 135</a></li>
        <li><a href="/courses/MATH145">MATH 145</a></li>
    </ul></li>
    <li><a href="/courses/CS240">CS 240</a></li>
</ul></li></ul>
'''

print("Testing nested prerequisite parsing...")
print("=" * 50)
print("Input HTML:")
print(test_html)
print("=" * 50)

result = parse_prerequisites(test_html)

print("=" * 50)
print("Parsed result:")
import json
print(json.dumps(result, indent=2))
print("=" * 50)

# Verify the structure
if result and result.get('type') == 'all':
    rules = result.get('rules', [])
    print(f"Found {len(rules)} items in 'all' block")
    
    for i, rule in enumerate(rules):
        print(f"Item {i+1}: type = {rule.get('type')}")
        if rule.get('type') == 'one':
            one_rules = rule.get('rules', [])
            print(f"  Contains {len(one_rules)} 'one' rules")
            for j, one_rule in enumerate(one_rules):
                if one_rule.get('code'):
                    print(f"    Rule {j+1}: {one_rule['code']}")
        elif rule.get('type') == 'course_requirement':
            print(f"  Course: {rule.get('code')}")
else:
    print("Failed to parse as 'all' structure") 