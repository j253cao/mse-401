#!/usr/bin/env python3
"""
Test script for the recursive prerequisite parser.
This script demonstrates the recursive parsing functionality and tests it with sample HTML content.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.dependency_parser import parse_prerequisites_recursive
import json

def test_simple_prerequisites():
    """Test simple prerequisite patterns."""
    print("=== Testing Simple Prerequisites ===")
    
    # Test 1: Simple course requirement
    html1 = '<ul><li>Must have completed the following: <a href="#">CS 135</a></li></ul>'
    result1 = parse_prerequisites_recursive(html1)
    print(f"Test 1 Result: {json.dumps(result1, indent=2)}")
    
    # Test 2: Complete 1 of the following
    html2 = '''
    <ul><li><span>Complete 1 of the following</span><ul>
        <li><a href="#">CS 135</a> - Introduction to Computer Science</li>
        <li><a href="#">CS 145</a> - Design of Computing Systems</li>
    </ul></li></ul>
    '''
    result2 = parse_prerequisites_recursive(html2)
    print(f"Test 2 Result: {json.dumps(result2, indent=2)}")

def test_nested_prerequisites():
    """Test nested prerequisite patterns."""
    print("\n=== Testing Nested Prerequisites ===")
    
    # Test 3: Complete all of the following with nested Complete 1 of the following
    html3 = '''
    <ul><li><span>Complete all of the following</span><ul>
        <li><span>Complete 1 of the following</span><ul>
            <li><a href="#">MATH 135</a> - Algebra</li>
            <li><a href="#">MATH 145</a> - Calculus</li>
        </ul></li>
        <li><span>Complete 1 of the following</span><ul>
            <li><a href="#">CS 135</a> - Introduction to Computer Science</li>
            <li><a href="#">CS 145</a> - Design of Computing Systems</li>
        </ul></li>
        <li>Must have completed the following: <a href="#">ENGL 109</a></li>
    </ul></li></ul>
    '''
    result3 = parse_prerequisites_recursive(html3)
    print(f"Test 3 Result: {json.dumps(result3, indent=2)}")

def test_complex_nested_prerequisites():
    """Test complex nested prerequisite patterns."""
    print("\n=== Testing Complex Nested Prerequisites ===")
    
    # Test 4: Complex nested structure with multiple levels
    html4 = '''
    <ul><li><span>Complete all of the following</span><ul>
        <li><span>Complete 1 of the following</span><ul>
            <li><a href="#">MATH 135</a> - Algebra</li>
            <li><a href="#">MATH 145</a> - Calculus</li>
        </ul></li>
        <li>Must have completed the following: <ul>
            <li><a href="#">CS 135</a> - Introduction to Computer Science</li>
            <li><a href="#">CS 136</a> - Elementary Algorithm Design</li>
        </ul></li>
        <li>Enrolled in: <span><a href="#">Computer Science</a></span></li>
        <li>Students must be in level <span>2A</span> or higher</li>
    </ul></li></ul>
    '''
    result4 = parse_prerequisites_recursive(html4)
    print(f"Test 4 Result: {json.dumps(result4, indent=2)}")

def test_program_requirements():
    """Test program requirement patterns."""
    print("\n=== Testing Program Requirements ===")
            
    # Test 5: Enrolled in program requirement
    html5 = '''
    <ul><li>Enrolled in: <span><a href="#">Computer Science</a> or <a href="#">Software Engineering</a></span></li></ul>
    '''
    result5 = parse_prerequisites_recursive(html5)
    print(f"Test 5 Result: {json.dumps(result5, indent=2)}")

def test_must_complete_at_least():
    """Test 'Must have completed at least X of the following' pattern."""
    print("\n=== Testing 'Must have completed at least X of the following' ===")
    
    # Test 6: Must have completed at least 1 of the following
    html6 = '''
    <ul><li>Must have completed at least <span>1</span> of the following:
        <ul><li><a href="#">CS 135</a> - Introduction to Computer Science</li>
            <li><a href="#">CS 145</a> - Design of Computing Systems</li></ul>
    </div></div></li></ul>
    '''
    result6 = parse_prerequisites_recursive(html6)
    print(f"Test 6 Result: {json.dumps(result6, indent=2)}")

def test_real_world_example():
    """Test with a more realistic example."""
    print("\n=== Testing Real World Example ===")
    
    # Test 7: Realistic course prerequisite structure
    html7 = '''
    <ul><li><span>Complete all of the following</span><ul>
        <li><span>Complete 1 of the following</span><ul>
            <li><a href="#">MATH 135</a> - Algebra for Honours Mathematics</li>
            <li><a href="#">MATH 145</a> - Calculus 1 for Honours Mathematics</li>
        </ul></li>
        <li><span>Complete 1 of the following</span><ul>
            <li><a href="#">CS 135</a> - Designing Functional Programs</li>
            <li><a href="#">CS 145</a> - Designing Functional Programs (Advanced Level)</li>
        </ul></li>
        <li>Must have completed the following: <ul>
            <li><a href="#">CS 136</a> - Elementary Algorithm Design and Data Abstraction</li>
        </ul></li>
        <li>Enrolled in: <span><a href="#">Computer Science</a></span></li>
        <li>Students must be in level <span>2A</span> or higher</li>
    </ul></li></ul>
    '''
    result7 = parse_prerequisites_recursive(html7)
    print(f"Test 7 Result: {json.dumps(result7, indent=2)}")

def test_user_provided_case():
    """Test the specific HTML structure provided by the user."""
    print("=== Testing User Provided Complex Case ===")
    
    html = '''<li><span>Complete all of the following</span><ul><div><span></span><li><span>Complete 1 of the following</span><ul><li data-test="ruleView-A.1"><div data-test="ruleView-A.1-result">Must have completed the following: <div><ul style="margin-top: 5px; margin-bottom: 5px;"><li><span><a href="#/courses/view/660d9e053123427965b7e67f">CS136L</a> - Tools and Techniques for Software Development <span style="margin-left: 5px;">(0.25)</span></span></li><li><span><a href="#/courses/view/65b2689c7786302cf67fd926">CS146</a> - Elementary Algorithm Design and Data Abstraction (Advanced Level) <span style="margin-left: 5px;">(0.50)</span></span></li></ul></div></div></li><li data-test="ruleView-A.1.1"><div data-test="ruleView-A.1.1-result">Earned a minimum grade of <span>60%</span> in each of the following: <div><ul style="margin-top: 5px; margin-bottom: 5px;"><li><span><a href="#/courses/view/65b267bd23cba719b1479aa2">CS138</a> - Introduction to Data Abstraction and Implementation <span style="margin-left: 5px;">(0.50)</span></span></li></ul></div></div></li><div><span></span><li><span>Complete all of the following</span><ul><li data-test="ruleView-A.2.1"><div data-test="ruleView-A.2.1-result">Must have completed the following: <div><ul style="margin-top: 5px; margin-bottom: 5px;"><li><span><a href="#/courses/view/660d9e053123427965b7e67f">CS136L</a> - Tools and Techniques for Software Development <span style="margin-left: 5px;">(0.25)</span></span></li></ul></div></div></li><li data-test="ruleView-A.2.2"><div data-test="ruleView-A.2.2-result">Earned a minimum grade of <span>60%</span> in each of the following: <div><ul style="margin-top: 5px; margin-bottom: 5px;"><li><span><a href="#/courses/view/67b75730db899d90f349f8b3">CS136</a> - Elementary Algorithm Design and Data Abstraction <span style="margin-left: 5px;">(0.50)</span></span></li></ul></div></div></li></ul></li></div></ul></li></div><li data-test="ruleView-A"><div data-test="ruleView-A-result"><div>Enrolled in an Honours Mathematics program</div></div></li></ul></li>'''
    
    print("Input HTML length:", len(html))
    print("Input HTML preview:", html[:200] + "..." if len(html) > 200 else html)
    
    result = parse_prerequisites_recursive(html)
    print(f"User Case Result: {json.dumps(result, indent=2)}")
    
    # Also test with the original parse_prerequisites function for comparison
    from utils.dependency_parser import parse_prerequisites
    original_result = parse_prerequisites(html)
    print(f"Original Parser Result: {json.dumps(original_result, indent=2)}")

def test_mse436_complex_case():
    """Test the specific MSE436 complex HTML structure provided by the user."""
    print("\n=== Testing MSE436 Complex Case ===")
    
    html = '''<div><div><div><ul><li><span>Complete <!-- -->all<!-- --> of the following</span><ul><div><span></span><li><span>Complete <!-- -->1<!-- --> of the following</span><ul><li data-test="ruleView-A.1"><div data-test="ruleView-A.1-result">Must have completed the following: <div><ul style="margin-top:5px;margin-bottom:5px"><li><span><a href="#/courses/view/6737ccf56bf59e7b202141a8" target="_blank">MSE332</a> <!-- -->-<!-- --> <!-- -->Deterministic Optimization Models and Methods<!-- --> <span style="margin-left:5px">(0.50)</span></span></li></ul></div></div></li><li data-test="ruleView-A.2"><div data-test="ruleView-A.2-result"><div>Must have completed the following: MSCI332</div></div></li></ul></li></div><div><span></span><li><span>Complete <!-- -->1<!-- --> of the following</span><ul><li data-test="ruleView-B.1"><div data-test="ruleView-B.1-result">Must have completed at least <span>1</span> of the following: <div><ul style="margin-top:5px;margin-bottom:5px"><li><span><a href="#/courses/view/6627d1d87be622222eefb8ba" target="_blank">CS348</a> <!-- -->-<!-- --> <!-- -->Introduction to Database Management<!-- --> <span style="margin-left:5px">(0.50)</span></span></li><li><span><a href="#/courses/view/65ce3baa3c5b4479fa1d75fb" target="_blank">MSE245</a> <!-- -->-<!-- --> <!-- -->Databases and Software Design<!-- --> <span style="margin-left:5px">(0.50)</span></span></li></ul></div></div></li><li data-test="ruleView-B.2"><div data-test="ruleView-B.2-result"><div>Must have completed the following: MSCI245</div></div></li></ul></li></div><div><span></span><li><span>Complete <!-- -->1<!-- --> of the following</span><ul><li data-test="ruleView-C.1"><div data-test="ruleView-C.1-result">Must have completed at least <span>1</span> of the following: <div><ul style="margin-top:5px;margin-bottom:5px"><li><span><a href="#/courses/view/6626b654b4dce0ae892ac57c" target="_blank">CS247</a> <!-- -->-<!-- --> <!-- -->Software Engineering Principles<!-- --> <span style="margin-left:5px">(0.50)</span></span></li><li><span><a href="#/courses/view/65ce491af34cd459067a222f" target="_blank">MSE342</a> <!-- -->-<!-- --> <!-- -->Principles of Software Engineering<!-- --> <span style="margin-left:5px">(0.50)</span></span></li><li><span><a href="#/courses/view/6626bae2a1b5e832cb99953e" target="_blank">SYDE322</a> <!-- -->-<!-- --> <!-- -->Software Design<!-- --> <span style="margin-left:5px">(0.50)</span></span></li></ul></div></div></li><li data-test="ruleView-C.2"><div data-test="ruleView-C.2-result"><div>Must have completed the following: MSCI342</div></div></li></ul></li></div><div><span></span><li><span>Complete <!-- -->1<!-- --> of the following</span><ul><li data-test="ruleView-D.1"><div data-test="ruleView-D.1-result">Must have completed at least <span>1</span> of the following: <div><ul style="margin-top:5px;margin-bottom:5px"><li><span><a href="#/courses/view/6627bf7c466ac1c9e1cb4ce5" target="_blank">CS449</a> <!-- -->-<!-- --> <!-- -->Human-Computer Interaction<!-- --> <span style="margin-left:5px">(0.50)</span></span></li><li><span><a href="#/courses/view/65e0c0447a54051a2380d63c" target="_blank">MSE343</a> <!-- -->-<!-- --> <!-- -->Human-Computer Interaction<!-- --> <span style="margin-left:5px">(0.50)</span></span></li><li><span><a href="#/courses/view/65ce6ec67a5405025a805889" target="_blank">SYDE548</a> <!-- -->-<!-- --> <!-- -->User Centred Design Methods<!-- --> <span style="margin-left:5px">(0.50)</span></span></li></ul></div></div></li><li data-test="ruleView-D.2"><div data-test="ruleView-D.2-result"><div>Must have completed at least 1 of the following: MSCI343, SYDE348</div></div></li></ul></li></div></ul></li></ul></div></div></div>'''
    
    print("Input HTML length:", len(html))
    print("Input HTML preview:", html[:200] + "..." if len(html) > 200 else html)
    
    result = parse_prerequisites_recursive(html)
    print(f"MSE436 Complex Case Result: {json.dumps(result, indent=2)}")
    
    # Also test with the original parse_prerequisites function for comparison
    from utils.dependency_parser import parse_prerequisites
    original_result = parse_prerequisites(html)
    print(f"Original Parser Result: {json.dumps(original_result, indent=2)}")

def test_recursion_depth_limit():
    """Test the recursion depth limit functionality."""
    print("\n=== Testing Recursion Depth Limit ===")
    
    # Create a deeply nested structure that would exceed the default max_depth of 5
    html_deep = '''
    <ul><li><span>Complete all of the following</span><ul>
        <li><span>Complete 1 of the following</span><ul>
            <li><span>Complete all of the following</span><ul>
                <li><span>Complete 1 of the following</span><ul>
                    <li><span>Complete all of the following</span><ul>
                        <li><span>Complete 1 of the following</span><ul>
                            <li><span>Complete all of the following</span><ul>
                                <li><span>Complete 1 of the following</span><ul>
                                    <li><a href="#">CS 999</a> - Deeply Nested Course</li>
                                </ul></li>
                            </ul></li>
                        </ul></li>
                    </ul></li>
                </ul></li>
            </ul></li>
        </ul></li>
    </ul></li></ul>
    '''
    
    print("Testing with default max_depth=5:")
    result_default = parse_prerequisites_recursive(html_deep)
    print(f"Result with default depth limit: {json.dumps(result_default, indent=2)}")
    
    print("\nTesting with max_depth=3:")
    result_limited = parse_prerequisites_recursive(html_deep, max_depth=3)
    print(f"Result with depth limit 3: {json.dumps(result_limited, indent=2)}")
    
    print("\nTesting with max_depth=10:")
    result_extended = parse_prerequisites_recursive(html_deep, max_depth=10)
    print(f"Result with depth limit 10: {json.dumps(result_extended, indent=2)}")

def main():
    """Run all tests."""
    print("Testing Recursive Prerequisite Parser")
    print("=" * 50)
    
    # Test the user-provided case first
    test_user_provided_case()
    
    # Test the MSE436 complex case
    test_mse436_complex_case()
    
    # Test recursion depth limit
    test_recursion_depth_limit()
    
    print("\n" + "=" * 50)
    print("Testing other cases...")
    
    test_simple_prerequisites()
    test_nested_prerequisites()
    test_complex_nested_prerequisites()
    test_program_requirements()
    test_must_complete_at_least()
    test_real_world_example()
    
    print("\n" + "=" * 50)
    print("All tests completed!")

if __name__ == "__main__":
    main() 