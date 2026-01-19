"""
Transcript Parser Test Suite

A simple testing framework for the UW transcript parser.
Tests utility functions, parsing logic, and real PDF transcripts.

Usage:
    python test.py              # Run all tests
    python test.py --verbose    # Run with detailed output
"""

import sys
import os
from pathlib import Path
from typing import Callable, List, Tuple, Any, Optional
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from main import (
    parse_transcript,
    parse_transcript_pdf,
    term_season_year_to_id,
    term_id_to_name,
    TranscriptSummary,
    TermSummary,
    TranscriptParseError,
)


# =============================================================================
# Simple Test Framework
# =============================================================================

@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    passed: bool
    message: str = ""
    error: Optional[Exception] = None


class TestRunner:
    """Simple test runner that collects and runs tests."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[TestResult] = []
    
    def run_test(self, name: str, test_fn: Callable[[], None]) -> TestResult:
        """Run a single test and capture the result."""
        try:
            test_fn()
            result = TestResult(name=name, passed=True, message="OK")
        except AssertionError as e:
            result = TestResult(name=name, passed=False, message=str(e), error=e)
        except Exception as e:
            result = TestResult(name=name, passed=False, message=f"Error: {e}", error=e)
        
        self.results.append(result)
        
        # Print result
        status = "✓" if result.passed else "✗"
        print(f"  {status} {name}")
        if not result.passed and self.verbose:
            print(f"      {result.message}")
        
        return result
    
    def summary(self) -> Tuple[int, int]:
        """Print summary and return (passed, total) counts."""
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        
        print(f"\n{'='*60}")
        print(f"Results: {passed}/{total} tests passed")
        
        if passed < total:
            print("\nFailed tests:")
            for r in self.results:
                if not r.passed:
                    print(f"  - {r.name}: {r.message}")
        
        return passed, total


def assert_equal(actual: Any, expected: Any, msg: str = ""):
    """Assert two values are equal."""
    if actual != expected:
        raise AssertionError(f"{msg}\nExpected: {expected}\nActual: {actual}")


def assert_true(condition: bool, msg: str = ""):
    """Assert condition is true."""
    if not condition:
        raise AssertionError(msg or "Condition was False")


def assert_in(item: Any, container: Any, msg: str = ""):
    """Assert item is in container."""
    if item not in container:
        raise AssertionError(msg or f"{item} not found in {container}")


def assert_raises(exception_type: type, fn: Callable, msg: str = ""):
    """Assert that calling fn raises the expected exception."""
    try:
        fn()
        raise AssertionError(msg or f"Expected {exception_type.__name__} but no exception was raised")
    except exception_type:
        pass  # Expected


# =============================================================================
# Unit Tests - Utility Functions
# =============================================================================

def test_term_season_year_to_id_fall():
    """Test Fall term conversion."""
    assert_equal(term_season_year_to_id("Fall", "2018"), 1189)
    assert_equal(term_season_year_to_id("Fall", "2023"), 1239)
    assert_equal(term_season_year_to_id("Fall", "2020"), 1209)


def test_term_season_year_to_id_winter():
    """Test Winter term conversion."""
    assert_equal(term_season_year_to_id("Winter", "2019"), 1191)
    assert_equal(term_season_year_to_id("Winter", "2024"), 1241)


def test_term_season_year_to_id_spring():
    """Test Spring term conversion."""
    assert_equal(term_season_year_to_id("Spring", "2019"), 1195)
    assert_equal(term_season_year_to_id("Spring", "2023"), 1235)


def test_term_season_year_to_id_invalid_season():
    """Test invalid season raises error."""
    assert_raises(
        TranscriptParseError,
        lambda: term_season_year_to_id("Summer", "2019"),
        "Should raise error for invalid season"
    )


def test_term_season_year_to_id_invalid_year():
    """Test invalid year raises error."""
    assert_raises(
        TranscriptParseError,
        lambda: term_season_year_to_id("Fall", "abc"),
        "Should raise error for invalid year"
    )


def test_term_id_to_name():
    """Test term ID to name conversion."""
    assert_equal(term_id_to_name(1189), "Fall 2018")
    assert_equal(term_id_to_name(1191), "Winter 2019")
    assert_equal(term_id_to_name(1195), "Spring 2019")
    assert_equal(term_id_to_name(1239), "Fall 2023")


def test_term_id_roundtrip():
    """Test that converting to ID and back gives original values."""
    test_cases = [
        ("Fall", "2018"),
        ("Winter", "2020"),
        ("Spring", "2022"),
        ("Fall", "2025"),
    ]
    for season, year in test_cases:
        term_id = term_season_year_to_id(season, year)
        name = term_id_to_name(term_id)
        assert_equal(name, f"{season} {year}", f"Roundtrip failed for {season} {year}")


# =============================================================================
# Integration Tests - PDF Parsing
# =============================================================================

TEST_DATA_DIR = Path(__file__).parent / "test_data"


def get_test_pdfs() -> List[Path]:
    """Get all PDF files in the test_data directory."""
    if not TEST_DATA_DIR.exists():
        return []
    return list(TEST_DATA_DIR.glob("*.pdf"))


def test_pdf_parsing_returns_valid_structure():
    """Test that parsing PDFs returns valid TranscriptSummary structure."""
    pdfs = get_test_pdfs()
    if not pdfs:
        raise AssertionError("No test PDFs found in test_data directory")
    
    for pdf_path in pdfs:
        result = parse_transcript_pdf(str(pdf_path))
        
        # Check basic structure
        assert_true(isinstance(result, TranscriptSummary), 
                   f"{pdf_path.name}: Result should be TranscriptSummary")
        assert_true(isinstance(result.student_number, int),
                   f"{pdf_path.name}: Student number should be int")
        assert_true(isinstance(result.program_name, str),
                   f"{pdf_path.name}: Program name should be string")
        assert_true(len(result.program_name) > 0,
                   f"{pdf_path.name}: Program name should not be empty")
        assert_true(isinstance(result.term_summaries, list),
                   f"{pdf_path.name}: Term summaries should be list")


def test_pdf_has_valid_student_number():
    """Test that parsed student numbers are valid (8 digits)."""
    pdfs = get_test_pdfs()
    if not pdfs:
        raise AssertionError("No test PDFs found")
    
    for pdf_path in pdfs:
        result = parse_transcript_pdf(str(pdf_path))
        
        # UW student numbers are 8 digits
        assert_true(10000000 <= result.student_number <= 99999999,
                   f"{pdf_path.name}: Student number {result.student_number} should be 8 digits")


def test_pdf_has_term_summaries():
    """Test that parsed transcripts have at least one term."""
    pdfs = get_test_pdfs()
    if not pdfs:
        raise AssertionError("No test PDFs found")
    
    for pdf_path in pdfs:
        result = parse_transcript_pdf(str(pdf_path))
        
        assert_true(len(result.term_summaries) > 0,
                   f"{pdf_path.name}: Should have at least one term")


def test_pdf_term_summaries_valid():
    """Test that term summaries have valid structure."""
    pdfs = get_test_pdfs()
    if not pdfs:
        raise AssertionError("No test PDFs found")
    
    for pdf_path in pdfs:
        result = parse_transcript_pdf(str(pdf_path))
        
        for term in result.term_summaries:
            # Check term_id is valid (reasonable range)
            assert_true(1000 <= term.term_id <= 2000,
                       f"{pdf_path.name}: Term ID {term.term_id} out of range")
            
            # Check level format (1A, 2B, etc.)
            assert_true(len(term.level) >= 2,
                       f"{pdf_path.name}: Level '{term.level}' too short")
            
            # Check courses are lowercase
            for course in term.courses:
                assert_equal(course, course.lower(),
                           f"{pdf_path.name}: Course '{course}' should be lowercase")


def test_pdf_courses_format():
    """Test that course codes follow expected format."""
    pdfs = get_test_pdfs()
    if not pdfs:
        raise AssertionError("No test PDFs found")
    
    import re
    course_pattern = re.compile(r'^[a-z]{2,6}\d{1,3}[a-z]?$')
    
    for pdf_path in pdfs:
        result = parse_transcript_pdf(str(pdf_path))
        
        for term in result.term_summaries:
            for course in term.courses:
                assert_true(course_pattern.match(course),
                           f"{pdf_path.name}: Course '{course}' doesn't match expected format")


# =============================================================================
# Detailed PDF Report (for manual verification)
# =============================================================================

def print_pdf_report(verbose: bool = True):
    """Print detailed report of all parsed PDFs for manual verification."""
    pdfs = get_test_pdfs()
    
    if not pdfs:
        print("\nNo test PDFs found in test_data directory")
        return
    
    print(f"\n{'='*60}")
    print("PDF PARSING REPORT")
    print(f"{'='*60}")
    
    for pdf_path in pdfs:
        print(f"\n📄 {pdf_path.name}")
        print("-" * 40)
        
        try:
            result = parse_transcript_pdf(str(pdf_path))
            
            print(f"  Student Number: {result.student_number}")
            print(f"  Program: {result.program_name}")
            print(f"  Terms: {len(result.term_summaries)}")
            
            if verbose:
                total_courses = 0
                print(f"\n  Course History:")
                for term in result.term_summaries:
                    term_name = term_id_to_name(term.term_id)
                    course_count = len(term.courses)
                    total_courses += course_count
                    
                    print(f"    {term_name} (Level {term.level}): {course_count} courses")
                    if term.courses:
                        # Show courses in rows of 6
                        for i in range(0, len(term.courses), 6):
                            chunk = term.courses[i:i+6]
                            print(f"      {', '.join(chunk)}")
                
                print(f"\n  Total Courses: {total_courses}")
            
        except Exception as e:
            print(f"  ❌ Error parsing: {e}")


# =============================================================================
# Main Test Runner
# =============================================================================

def run_all_tests(verbose: bool = False):
    """Run all tests and return exit code."""
    runner = TestRunner(verbose=verbose)
    
    # Unit tests
    print("\n📋 Unit Tests - Utility Functions")
    print("-" * 40)
    runner.run_test("term_season_year_to_id (Fall)", test_term_season_year_to_id_fall)
    runner.run_test("term_season_year_to_id (Winter)", test_term_season_year_to_id_winter)
    runner.run_test("term_season_year_to_id (Spring)", test_term_season_year_to_id_spring)
    runner.run_test("term_season_year_to_id (invalid season)", test_term_season_year_to_id_invalid_season)
    runner.run_test("term_season_year_to_id (invalid year)", test_term_season_year_to_id_invalid_year)
    runner.run_test("term_id_to_name", test_term_id_to_name)
    runner.run_test("term_id roundtrip", test_term_id_roundtrip)
    
    # Integration tests (PDF parsing)
    print("\n📋 Integration Tests - PDF Parsing")
    print("-" * 40)
    
    if get_test_pdfs():
        runner.run_test("PDF returns valid structure", test_pdf_parsing_returns_valid_structure)
        runner.run_test("PDF has valid student number", test_pdf_has_valid_student_number)
        runner.run_test("PDF has term summaries", test_pdf_has_term_summaries)
        runner.run_test("PDF term summaries valid", test_pdf_term_summaries_valid)
        runner.run_test("PDF courses format", test_pdf_courses_format)
    else:
        print("  ⚠ No test PDFs found - skipping integration tests")
        print(f"    Place PDF files in: {TEST_DATA_DIR}")
    
    # Summary
    passed, total = runner.summary()
    
    # Print detailed report if verbose
    if verbose:
        print_pdf_report(verbose=True)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    exit_code = run_all_tests(verbose=verbose)
    sys.exit(exit_code)

