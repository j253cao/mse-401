#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.dependency_parser import parse_prerequisites

# Test HTML with complex nested structure including plain-text requirements
test_html = '''
<ul><li><span>Complete all of the following</span><ul>
    <li><span>Complete 1 of the following</span><ul>
        <li>Must have completed the following: MSCI332</li>
    </ul></li>
    <li><span>Complete 1 of the following</span><ul>
        <li><a href="/courses/CS348">CS 348</a></li>
        <li><a href="/courses/MSE245">MSE 245</a></li>
    </ul></li>
    <li><span>Complete 1 of the following</span><ul>
        <li><a href="/courses/CS247">CS 247</a></li>
        <li><a href="/courses/MSE342">MSE 342</a></li>
        <li><a href="/courses/SYDE322">SYDE 322</a></li>
    </ul></li>
    <li><span>Complete 1 of the following</span><ul>
        <li><a href="/courses/CS449">CS 449</a></li>
        <li><a href="/courses/MSE343">MSE 343</a></li>
        <li><a href="/courses/SYDE548">SYDE 548</a></li>
    </ul></li>
    <li><span>Complete 1 of the following</span><ul>
        <li>Must have completed the following: MSCI245</li>
    </ul></li>
    <li><span>Complete 1 of the following</span><ul>
        <li>Must have completed the following: MSCI342</li>
    </ul></li>
    <li><span>Complete 1 of the following</span><ul>
        <li>Must have completed at least 1 of the following:<ul>
            <li><a href="/courses/MSE343">MSE 343</a></li>
            <li><a href="/courses/SYDE348">SYDE 348</a></li>
        </ul></li>
    </ul></li>
</ul></li></ul>
'''

print("Testing complex nested prerequisite parsing...")
print("=" * 60)
print("Input HTML:")
print(test_html)
print("=" * 60)

result = parse_prerequisites(test_html)

print("=" * 60)
print("Parsed result:")
import json
print(json.dumps(result, indent=2))
print("=" * 60)

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
                if one_rule.get('type') == 'course_requirement':
                    print(f"    Rule {j+1}: {one_rule['code']}")
                elif one_rule.get('type') == 'one':
                    nested_rules = one_rule.get('rules', [])
                    print(f"    Rule {j+1}: nested 'one' with {len(nested_rules)} rules")
                    for k, nested_rule in enumerate(nested_rules):
                        if nested_rule.get('code'):
                            print(f"      Nested rule {k+1}: {nested_rule['code']}")
        elif rule.get('type') == 'course_requirement':
            print(f"  Course: {rule.get('code')}")
else:
    print("Failed to parse as 'all' structure") 