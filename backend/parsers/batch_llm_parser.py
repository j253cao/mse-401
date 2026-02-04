"""
Batch LLM parser for course prerequisites with checkpointing.

Processes all courses from course-api-new-data.json using LLM-based parsing
with rate limiting, checkpointing, and error recovery.

Supports multiple API keys for higher throughput via key rotation.

Usage:
    python batch_llm_parser.py [--test] [--batch-size N] [--departments DEPT1,DEPT2]
    
Examples:
    # Test with 3 batches
    python batch_llm_parser.py --test
    
    # Process all courses
    python batch_llm_parser.py
    
    # Process specific departments
    python batch_llm_parser.py --departments MSE,ECE,SYDE
    
    # Custom batch size
    python batch_llm_parser.py --batch-size 15

API Keys:
    Set one of the following in your .env file:
    
    # Single key
    GEMINI_API_KEY=your_key_here
    
    # Multiple keys (comma-separated) for higher throughput
    GEMINI_API_KEYS=key1,key2,key3,key4
    
    With 4 keys, you get 4x the rate limit (60 RPM instead of 15 RPM).
"""

import json
import os
import sys
import asyncio
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dotenv import load_dotenv

# Ensure output is flushed immediately
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

# Load environment variables
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / '.env')

from llm_prereq_parser import LLMPrereqParser


# Priority departments for processing (processed first)
PRIORITY_DEPARTMENTS = ['MSE', 'ECE', 'SYDE', 'BME', 'ME', 'MTE', 'SE', 'NE', 'CHE', 'CIVE', 'ENVE', 'GEOE']


def get_department_from_code(code: str) -> str:
    """Extract department from course code."""
    for i, char in enumerate(code):
        if char.isdigit():
            return code[:i]
    return code


def get_course_priority(course_tuple: Tuple[str, str]) -> Tuple[int, str]:
    """Get priority level for sorting courses."""
    code = course_tuple[0]
    dept = get_department_from_code(code)
    try:
        priority = PRIORITY_DEPARTMENTS.index(dept)
        return (priority, dept)
    except ValueError:
        return (len(PRIORITY_DEPARTMENTS), dept)


class RateLimitedParser:
    """Rate-limited wrapper around LLMPrereqParser with retry logic and key rotation."""
    
    def __init__(self, requests_per_minute: int = 30, batch_size: int = 12, api_keys: Optional[List[str]] = None):
        self.parser = LLMPrereqParser(api_keys=api_keys)
        self.num_keys = len(self.parser.api_keys)
        
        # Adjust rate limit based on number of keys
        self.requests_per_minute = requests_per_minute * self.num_keys
        self.min_interval = 60.0 / self.requests_per_minute
        self.last_request_time = 0
        self.batch_size = batch_size
        self.max_retries = 3 * self.num_keys  # More retries with more keys
        self.base_retry_delay = 5  # seconds (shorter with key rotation)
        
        print(f"Rate limit: {self.requests_per_minute} RPM (with {self.num_keys} key(s))")
    
    async def parse_batch_async(self, courses_batch: List[Tuple[str, str]]) -> Optional[Dict[str, Any]]:
        """Parse a batch with rate limiting, retry logic, and key rotation."""
        
        for retry in range(self.max_retries):
            # Rate limiting
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.min_interval:
                wait_time = self.min_interval - time_since_last
                print(f"  Rate limiting: waiting {wait_time:.2f}s...")
                await asyncio.sleep(wait_time)
            
            self.last_request_time = time.time()
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            try:
                result = await loop.run_in_executor(None, self.parser.parse_batch, courses_batch)
                if result is not None:
                    return result
                # If result is None but no exception, it might be a quota issue handled internally
                # The parser rotates keys internally, so we can retry quickly
                if self.num_keys > 1:
                    await asyncio.sleep(self.base_retry_delay)
                    continue
            except Exception as e:
                error_str = str(e)
                if '429' in error_str or 'quota' in error_str.lower():
                    if self.num_keys > 1:
                        # With multiple keys, retry quickly after rotation
                        retry_delay = self.base_retry_delay
                    else:
                        # With single key, use exponential backoff
                        retry_delay = self.base_retry_delay * (2 ** retry)
                    print(f"  ⚠️  Quota exceeded. Retry {retry + 1}/{self.max_retries} in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                else:
                    raise
        
        print(f"  ✗ Max retries exceeded")
        return None


class BatchCourseProcessor:
    """
    Batch processor for course prerequisites with checkpointing.
    
    Processes courses in batches, saves progress, and can resume from failures.
    """
    
    def __init__(self, 
                 api_data_path: Path,
                 output_dir: Path,
                 batch_size: int = 12,
                 departments: Optional[List[str]] = None,
                 api_keys: Optional[List[str]] = None):
        """
        Initialize the processor.
        
        Args:
            api_data_path: Path to course-api-new-data.json
            output_dir: Directory for output files
            batch_size: Number of courses per batch
            departments: Optional list of departments to filter
            api_keys: Optional list of Gemini API keys for rotation
        """
        self.api_data_path = api_data_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.checkpoint_file = output_dir / 'llm_checkpoint.json'
        self.output_file = output_dir / 'course_dependencies_llm.json'
        self.error_log_file = output_dir / 'llm_error_log.json'
        
        self.parser = RateLimitedParser(requests_per_minute=15, batch_size=batch_size, api_keys=api_keys)
        self.departments = departments
        
        # Load checkpoint and results
        self.checkpoint = self._load_checkpoint()
        self.results = self._load_results()
        
        self.error_log = {
            'last_error_timestamp': None,
            'last_error_batch': None,
            'error_type': None,
            'error_details': None,
            'failed_courses': [],
            'checkpoint_state': self.checkpoint
        }
    
    def _load_checkpoint(self) -> Dict[str, Any]:
        """Load or initialize checkpoint."""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        return {
            'last_processed_index': 0,
            'successful': 0,
            'failed': 0,
            'total_courses': 0
        }
    
    def _load_results(self) -> Dict[str, Any]:
        """Load or initialize results."""
        if self.output_file.exists():
            with open(self.output_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_checkpoint(self):
        """Save current checkpoint."""
        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.checkpoint, f, indent=2)
    
    def _save_results(self):
        """Save results to file."""
        with open(self.output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
    
    def _log_error(self, batch_num: int, error_type: str, error_details: str, affected_courses: List[str]):
        """Log error to file."""
        self.error_log = {
            'last_error_timestamp': datetime.now().isoformat(),
            'last_error_batch': batch_num,
            'error_type': error_type,
            'error_details': str(error_details),
            'failed_courses': affected_courses,
            'checkpoint_state': self.checkpoint
        }
        
        with open(self.error_log_file, 'w') as f:
            json.dump(self.error_log, f, indent=2)
        
        print(f"\n=== Error Details ===")
        print(f"Error Type: {error_type}")
        print(f"Error Details: {error_details}")
        print(f"Failed Courses: {affected_courses}")
    
    def _get_courses_with_requirements(self) -> List[Tuple[str, str]]:
        """Load and filter courses with requirements."""
        with open(self.api_data_path, 'r') as f:
            api_data = json.load(f)
        
        courses = []
        for course_code, course_data in api_data.items():
            req = course_data.get('requirementsDescription', '')
            if req:
                # Filter by department if specified
                if self.departments:
                    dept = get_department_from_code(course_code)
                    if dept not in self.departments:
                        continue
                courses.append((course_code, req))
        
        # Sort by priority
        courses.sort(key=get_course_priority)
        return courses
    
    async def process_courses(self, test_mode: bool = False, test_batches: int = 3):
        """
        Process all courses with checkpointing.
        
        Args:
            test_mode: If True, only process a few batches for testing
            test_batches: Number of batches to process in test mode
        """
        print(f"Loading courses from {self.api_data_path}...")
        courses = self._get_courses_with_requirements()
        
        if not courses:
            print("No courses found with requirements")
            return
        
        print(f"Found {len(courses)} courses with requirements")
        
        if self.departments:
            print(f"Filtering by departments: {self.departments}")
        
        # Update checkpoint
        if self.checkpoint['total_courses'] == 0:
            self.checkpoint['total_courses'] = len(courses)
            self._save_checkpoint()
        
        # In test mode, limit courses
        if test_mode:
            max_courses = test_batches * self.parser.batch_size
            courses = courses[:max_courses]
            self.checkpoint['total_courses'] = len(courses)
            self.checkpoint['last_processed_index'] = 0
            self.checkpoint['successful'] = 0
            self.checkpoint['failed'] = 0
            self._save_checkpoint()
            print(f"\n=== TEST MODE: Processing {len(courses)} courses ({test_batches} batches) ===")
        
        print(f"\n=== Processing Status ===")
        print(f"Total courses: {self.checkpoint['total_courses']}")
        print(f"Starting from index: {self.checkpoint['last_processed_index']}")
        print(f"Previously successful: {self.checkpoint['successful']}")
        print(f"Previously failed: {self.checkpoint['failed']}")
        
        # Get remaining courses
        remaining = courses[self.checkpoint['last_processed_index']:]
        
        # Split into batches
        batches = [
            remaining[i:i + self.parser.batch_size]
            for i in range(0, len(remaining), self.parser.batch_size)
        ]
        
        print(f"\nProcessing {len(batches)} batches...")
        
        for batch_num, batch in enumerate(batches, 1):
            current_batch_num = batch_num + (self.checkpoint['last_processed_index'] // self.parser.batch_size)
            
            print(f"\n--- Batch {current_batch_num} ---")
            print(f"Courses: {[code for code, _ in batch]}")
            
            try:
                # Process batch
                result = await self.parser.parse_batch_async(batch)
                
                if result is None:
                    self._log_error(
                        current_batch_num,
                        "LLM_NO_RESPONSE",
                        "No response from LLM",
                        [code for code, _ in batch]
                    )
                    print("\n⚠️  Critical error - stopping")
                    return
                
                # Update results
                missing_courses = []
                for code, _ in batch:
                    if code in result:
                        self.results[code] = result[code]
                        self.checkpoint['successful'] += 1
                        print(f"  ✓ {code}")
                    else:
                        missing_courses.append(code)
                        self.checkpoint['failed'] += 1
                        print(f"  ✗ {code} (missing from response)")
                
                # Check for majority missing
                if len(missing_courses) > len(batch) / 2:
                    self._log_error(
                        current_batch_num,
                        "BATCH_MAJORITY_MISSING",
                        f"More than 50% missing ({len(missing_courses)}/{len(batch)})",
                        missing_courses
                    )
                    print("\n⚠️  Critical error - stopping")
                    return
                
            except Exception as e:
                self._log_error(
                    current_batch_num,
                    "UNEXPECTED_ERROR",
                    str(e),
                    [code for code, _ in batch]
                )
                print(f"\n⚠️  Unexpected error: {e}")
                return
            
            # Save progress
            self.checkpoint['last_processed_index'] += len(batch)
            self._save_checkpoint()
            self._save_results()
            
            # Print progress
            progress = (self.checkpoint['last_processed_index'] / self.checkpoint['total_courses']) * 100
            print(f"\nProgress: {progress:.1f}% ({self.checkpoint['last_processed_index']}/{self.checkpoint['total_courses']})")
        
        print(f"\n=== Processing Complete ===")
        print(f"Total processed: {self.checkpoint['total_courses']}")
        print(f"Successful: {self.checkpoint['successful']}")
        print(f"Failed: {self.checkpoint['failed']}")
        print(f"Results saved to: {self.output_file}")
    
    def reset_checkpoint(self):
        """Reset checkpoint to start fresh."""
        self.checkpoint = {
            'last_processed_index': 0,
            'successful': 0,
            'failed': 0,
            'total_courses': 0
        }
        self._save_checkpoint()
        self.results = {}
        self._save_results()
        print("Checkpoint reset")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Batch LLM parser for course prerequisites')
    parser.add_argument('--test', action='store_true', help='Run in test mode (3 batches)')
    parser.add_argument('--batch-size', type=int, default=12, help='Batch size (default: 12)')
    parser.add_argument('--departments', type=str, help='Comma-separated list of departments to process')
    parser.add_argument('--reset', action='store_true', help='Reset checkpoint and start fresh')
    parser.add_argument('--input', type=str, default='new', choices=['old', 'new'],
                        help='Input data format (default: new)')
    args = parser.parse_args()
    
    # Paths
    if args.input == 'new':
        api_data_path = PROJECT_ROOT / 'data' / 'courses' / 'course-api-new-data.json'
    else:
        api_data_path = PROJECT_ROOT / 'data' / 'courses' / 'course-api-data.json'
    
    output_dir = PROJECT_ROOT / 'data' / 'dependencies'
    
    # Parse departments
    departments = None
    if args.departments:
        departments = [d.strip().upper() for d in args.departments.split(',')]
    
    print(f"API data: {api_data_path}")
    print(f"Output dir: {output_dir}")
    
    # Create processor
    processor = BatchCourseProcessor(
        api_data_path=api_data_path,
        output_dir=output_dir,
        batch_size=args.batch_size,
        departments=departments
    )
    
    if args.reset:
        processor.reset_checkpoint()
    
    await processor.process_courses(test_mode=args.test)


if __name__ == "__main__":
    asyncio.run(main())
