"""
Batch LLM parser for course prerequisites using Claude Haiku 3.

Processes courses from course-api-new-data.json with rate limiting, checkpointing, and error recovery.

CODE FLOW EXPLANATION:
=====================

1. INITIALIZATION (main() function)
   - Parse command-line arguments (test mode, batch size, departments, etc.)
   - Load course data from course-api-new-data.json
   - Create BatchCourseProcessor instance

2. BATCH PROCESSING (BatchCourseProcessor.process_courses())
   - Load courses with requirements from JSON file
   - Filter by departments if specified
   - Sort courses by priority (engineering departments first)
   - Split remaining courses into batches (default: 12 courses per batch)
   - For each batch:
     a. Call RateLimitedParser.parse_batch_async()
     b. Rate limiting ensures we don't exceed API limits
     c. Claude API processes the batch
     d. Parse and validate JSON response
     e. Save results to checkpoint and output files
     f. Continue to next batch

3. RATE LIMITING (RateLimitedParser)
   - Enforces Claude Haiku 3 Free Tier limits:
     * 5 requests/min (regular API)
     * 5 batch requests/min (batch API)
     * 25,000 input tokens/min
     * 5,000 output tokens/min (BOTTLENECK)
   - Calculates minimum interval between batches (30 seconds)
   - Waits if needed before making next request
   - Handles rate limit errors with exponential backoff retry

4. API CALL (ClaudePrereqParser._process_single_batch())
   - Formats course batch as JSON input
   - Sends to Claude API with system prompt (parsing instructions)
   - Receives structured JSON response
   - Cleans response (removes markdown code blocks if present)
   - Validates JSON structure and ensures all courses are present

5. CHECKPOINTING
   - Saves progress after each successful batch
   - Tracks: last_processed_index, successful count, failed count
   - Allows resuming from last checkpoint if script is interrupted
   - Results saved incrementally to course_dependencies_llm.json

6. ERROR HANDLING
   - Rate limit errors: Retry with exponential backoff
   - JSON parsing errors: Reduce batch size and retry
   - Missing courses: Log error and continue
   - Critical errors: Stop processing and save error log

Usage:
    python batch_llm_parser.py [--test] [--batch-size N] [--departments DEPT1,DEPT2]

Examples:
    # Test with 3 batches
    python batch_llm_parser.py --test

    # Process all courses
    python batch_llm_parser.py

    # Process specific departments
    python batch_llm_parser.py --departments MSE,ECE,SYDE

    # Process engineering departments only
    python batch_llm_parser.py --engineering

API Key:
    Set ANTHROPIC_API_KEY in your .env file.
    Get your key from: https://console.anthropic.com/

Rate Limits (Claude Haiku 3 Free Tier):
    - 5 requests/min
    - 5 batch requests/min
    - 25,000 input tokens/min
    - 5,000 output tokens/min (bottleneck - limits to ~2 batches/min)
"""

import json
import os
import sys
import asyncio
import time
import argparse
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dotenv import load_dotenv
from concurrent.futures import TimeoutError as FutureTimeoutError

try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

# Ensure output is flushed immediately
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

# Load environment variables
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / '.env')

# Debug output path for raw LLM responses
RAW_RESPONSE_DEBUG_PATH = PROJECT_ROOT / 'data' / 'dependencies' / 'llm_raw_response_debug.json'

# System context for the LLM - defines the parsing rules and output format
PREREQ_PARSER_CONTEXT = """# Course Prerequisites Parser - System Context

You are a specialized parser that converts university course prerequisite strings into structured JSON data. Your job is to analyze prerequisite text and output a specific JSON structure that captures all the requirements, logical relationships, and constraints.

## Input Format
You will receive a JSON object containing multiple course prerequisite information in the following format:
{
  "courses": [
    {
      "code": "CS146",
      "requirements": "Prerequisite text here"
    }
  ]
}

Each course's prerequisite string may include:
- Course codes (e.g., "CS 146", "MATH 135", "STAT 230")
- Grade requirements (e.g., "minimum grade of 60%", "grade of 65% or higher")
- Logical operators (e.g., "and", "or", "one of", "two of", "/")
- Program restrictions (e.g., "Honours Mathematics students only", "Not open to Software Engineering students")
- Academic level requirements (e.g., "Level at least 2A", "3B or higher")
- Faculty specifications (e.g., "Engineering", "Mathematics")

## Output Structure
You must output a JSON object with course codes as keys and their parsed prerequisites as values:

{
  "CS146": {
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
}

### Course Object Structure
{
  "type": "course",
  "code": "CS146",
  "name": null,
  "grade_requirement": {
    "type": "grade_requirement",
    "value": 60,
    "operator": "minimum",
    "unit": "%"
  }
}

### Prerequisite Group Structure
{
  "type": "prerequisite_group",
  "courses": [],
  "operator": "AND" | "OR",
  "quantity": 1
}

### Program Requirement Structure
{
  "type": "program_requirement",
  "program_name": "Mathematics",
  "program_type": "honours" | "regular" | null,
  "faculty": "Engineering" | null,
  "level_requirement": {
    "type": "level_requirement",
    "level": "2A",
    "comparison": "at_least" | "exactly"
  }
}

### Program Restriction Structure
{
  "type": "program_restriction",
  "program_name": "Software Engineering",
  "program_type": null,
  "faculty": null,
  "restriction_type": "not_open"
}

## Parsing Rules

### 1. Logical Operators
- "and", "&", ";" → AND operator
- "or", "|", "/" → OR operator
- "one of", "any of" → OR operator with quantity: 1
- "two of", "any two of" → OR operator with quantity: 2
- Parentheses indicate grouping

### 2. Course Codes
- Normalize course codes: "CS 146" → "CS146", "MATH 135" → "MATH135"
- Remove spaces between subject and number

### 3. Grade Requirements
- "minimum grade of X%" → operator: "minimum", value: X
- "grade of X% or higher" → operator: ">=", value: X
- "at least X%" → operator: ">=", value: X

### 4. Level Requirements
- "Level at least 2A" → level: "2A", comparison: "at_least"
- "2A or higher" → level: "2A", comparison: "at_least"

### 5. Section Identification
- **Prereq/Prerequisite**: Parse into prerequisites.groups
- **Coreq/Corequisite**: Parse into corequisites.groups
- **Antireq/Antirequisite**: Parse into antirequisites.courses

## Important Notes
- Always normalize course codes (remove spaces): "CS 146" → "CS146"
- Default root_operator is "AND"
- If no grade requirement, set grade_requirement to null
- Empty arrays for missing sections
- Parse ALL sections (prereq, coreq, antireq) from the requirements string

## Output Format
- Return valid JSON as a single line with NO whitespace, newlines, or indentation (minified/compact format)
- Do not wrap in markdown code blocks"""


def _save_raw_response_debug(raw_response: str, courses_batch: List[Tuple[str, str]]) -> None:
    """Save raw LLM response to JSON file for debugging before any parsing."""
    RAW_RESPONSE_DEBUG_PATH.parent.mkdir(parents=True, exist_ok=True)
    debug_data = {
        'timestamp': datetime.now().isoformat(),
        'batch_codes': [code for code, _ in courses_batch],
        'raw_response': raw_response if raw_response else '(empty)',
    }
    with open(RAW_RESPONSE_DEBUG_PATH, 'w') as f:
        json.dump(debug_data, f, indent=2)


class ClaudePrereqParser:
    """LLM-based prerequisite parser using Claude Haiku 3."""

    def __init__(self, model_name: str = 'claude-haiku-4-5-20251001', api_key: Optional[str] = None):
        if not HAS_ANTHROPIC:
            raise ImportError("Anthropic package not installed. Run: pip install anthropic")

        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("No Anthropic API key found. Set ANTHROPIC_API_KEY in .env file")

        self.client = Anthropic(api_key=self.api_key)
        self.model_name = model_name
        self.api_keys = [self.api_key]

        print(f"Claude initialized with model: {model_name}")

        self.min_batch_size = 1
        self.reduction_factor = 2

    def _clean_json_response(self, response: str) -> Optional[str]:
        if not response:
            return None

        cleaned = response.strip()

        json_pattern = r'```json\s*(.*?)\s*```'
        matches = re.findall(json_pattern, cleaned, re.DOTALL)
        if matches:
            for match in matches:
                try:
                    json.loads(match.strip())
                    return match.strip()
                except json.JSONDecodeError:
                    continue

        code_pattern = r'```\s*(.*?)\s*```'
        matches = re.findall(code_pattern, cleaned, re.DOTALL)
        if matches:
            for match in matches:
                try:
                    json.loads(match.strip())
                    return match.strip()
                except json.JSONDecodeError:
                    continue

        try:
            json.loads(cleaned)
            return cleaned
        except json.JSONDecodeError:
            pass

        return None

    def _process_single_batch(self, courses_batch: List[Tuple[str, str]]) -> Tuple[bool, str]:
        try:
            batch_input = {
                "courses": [
                    {"code": code, "requirements": requirements}
                    for code, requirements in courses_batch
                ]
            }

            prompt = json.dumps(batch_input, indent=2)

            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=8192,
                system=PREREQ_PARSER_CONTEXT,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )

            raw_response = (
                response.content[0].text
                if response.content and len(response.content) > 0
                else ""
            )

            _save_raw_response_debug(raw_response, courses_batch)

            response_text = self._clean_json_response(raw_response)

            if not response_text:
                return False, "Failed to extract valid JSON from response"

            try:
                parsed = json.loads(response_text)

                if not isinstance(parsed, dict):
                    return False, "Invalid JSON structure - expected object"

                expected_codes = {code for code, _ in courses_batch}
                for code in expected_codes:
                    if code not in parsed:
                        return False, f"Missing results for {code}"

                return True, response_text

            except json.JSONDecodeError as e:
                return False, f"Invalid JSON: {str(e)}"

        except Exception as e:
            error_str = str(e)
            if '429' in error_str or 'rate' in error_str.lower():
                return False, f"RATE_LIMITED: {error_str}"
            elif 'credit' in error_str.lower() or 'billing' in error_str.lower() or 'balance' in error_str.lower():
                return False, f"BILLING_ERROR: {error_str}"
            return False, error_str

    def parse_batch(self, courses_batch: List[Tuple[str, str]]) -> Optional[Dict[str, Any]]:
        current_batch_size = len(courses_batch)

        while current_batch_size >= self.min_batch_size:
            print(f"  Attempting batch size: {current_batch_size}")

            if current_batch_size == len(courses_batch):
                success, result = self._process_single_batch(courses_batch)
                if success:
                    return json.loads(result)
            else:
                sub_batches = [
                    courses_batch[i:i + current_batch_size]
                    for i in range(0, len(courses_batch), current_batch_size)
                ]

                all_results = {}
                all_successful = True

                for sub_batch in sub_batches:
                    success, result = self._process_single_batch(sub_batch)
                    if not success:
                        all_successful = False
                        print(f"    Sub-batch failed: {result}")
                        break

                    try:
                        all_results.update(json.loads(result))
                    except json.JSONDecodeError:
                        all_successful = False
                        break

                if all_successful:
                    return all_results

            current_batch_size = current_batch_size // self.reduction_factor
            if current_batch_size >= self.min_batch_size:
                print(f"  Reducing batch size to: {current_batch_size}")

        print("  Failed even with minimum batch size")
        return None


PRIORITY_DEPARTMENTS = ['MSE', 'ECE', 'SYDE', 'BME', 'ME', 'MTE', 'SE', 'NE', 'CHE', 'CIVE', 'ENVE', 'GEOE']

ENGINEERING_DEPARTMENTS = [
    'AE', 'BME', 'CHE', 'CIVE', 'ECE', 'ENVE', 'GENE', 'GEOE',
    'ME', 'MTE', 'MSE', 'NE', 'SE', 'SYDE',
]


def get_department_from_code(code: str) -> str:
    for i, char in enumerate(code):
        if char.isdigit():
            return code[:i]
    return code


def get_course_priority(course_tuple: Tuple[str, str]) -> Tuple[int, str]:
    code = course_tuple[0]
    dept = get_department_from_code(code)
    try:
        priority = PRIORITY_DEPARTMENTS.index(dept)
        return (priority, dept)
    except ValueError:
        return (len(PRIORITY_DEPARTMENTS), dept)


class RateLimitedParser:
    def __init__(self, batch_size: int = 12):
        self.parser = ClaudePrereqParser()
        self.num_keys = 1

        self.max_requests_per_minute = 5
        self.max_batch_requests_per_minute = 5
        self.max_input_tokens_per_minute = 25000
        self.max_output_tokens_per_minute = 5000

        self.estimated_input_tokens_per_batch = 2846
        self.estimated_output_tokens_per_batch = 2000

        self.effective_batches_per_minute = min(
            self.max_batch_requests_per_minute,
            self.max_output_tokens_per_minute // self.estimated_output_tokens_per_batch
        )

        self.requests_per_minute = self.effective_batches_per_minute
        self.min_interval = 60.0 / self.requests_per_minute
        self.last_request_time = 0
        self.batch_size = batch_size
        self.max_retries = 3
        self.base_retry_delay = 5

        print(f"Claude Haiku 3 Rate Limits:")
        print(f"  - Requests/min: {self.max_requests_per_minute}")
        print(f"  - Batch requests/min: {self.max_batch_requests_per_minute}")
        print(f"  - Input tokens/min: {self.max_input_tokens_per_minute:,}")
        print(f"  - Output tokens/min: {self.max_output_tokens_per_minute:,} (BOTTLENECK)")
        print(f"  - Effective rate: {self.requests_per_minute} batches/min ({self.min_interval:.1f}s between batches)")

    async def parse_batch_async(self, courses_batch: List[Tuple[str, str]]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        last_error_type = None

        for retry in range(self.max_retries):
            current_time = time.time()
            if self.last_request_time > 0:
                time_since_last = current_time - self.last_request_time
                if time_since_last < self.min_interval:
                    wait_time = self.min_interval - time_since_last
                    print(f"  Rate limiting: waiting {wait_time:.2f}s...")
                    await asyncio.sleep(wait_time)

            loop = asyncio.get_event_loop()
            try:
                result = await loop.run_in_executor(None, self.parser.parse_batch, courses_batch)

                if result is not None:
                    self.last_request_time = time.time()
                    return result, None

                await asyncio.sleep(self.base_retry_delay)
                continue

            except Exception as e:
                error_str = str(e)

                if '429' in error_str or 'rate' in error_str.lower() or 'quota' in error_str.lower():
                    is_daily_quota = 'daily' in error_str.lower() or 'per day' in error_str.lower()

                    if is_daily_quota:
                        print(f"  ⚠️  Daily quota exceeded. This resets at midnight UTC.")
                        return None, "DAILY_QUOTA"

                    last_error_type = "RATE_LIMIT"
                    retry_delay = self.base_retry_delay * (2 ** retry)
                    print(f"  ⚠️  Rate limit exceeded (429). Retry {retry + 1}/{self.max_retries} in {retry_delay}s...")
                    print(f"  ⚠️  Note: These are PER MINUTE limits - if all retries fail, wait 1-2 min and resume")
                    print(f"  ⚠️  Error details: {error_str[:200]}")
                    await asyncio.sleep(retry_delay)
                elif 'credit' in error_str.lower() or 'billing' in error_str.lower() or 'balance' in error_str.lower():
                    print(f"  ⚠️  Billing/Credit error detected. Please add credits to your Anthropic account.")
                    print(f"  ⚠️  Visit: https://console.anthropic.com/settings/billing")
                    return None, "BILLING_ERROR"
                else:
                    raise

        print(f"  ✗ Max retries exceeded (likely rate limit)")
        print(f"  💡 Rate limits are PER MINUTE - wait 1-2 minutes and resume")
        return None, last_error_type


class BatchCourseProcessor:
    def __init__(self,
                 api_data_path: Path,
                 output_dir: Path,
                 batch_size: int = 12,
                 departments: Optional[List[str]] = None):
        self.api_data_path = api_data_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.checkpoint_file = output_dir / 'llm_checkpoint.json'
        self.output_file = output_dir / 'course_dependencies_llm.json'
        self.error_log_file = output_dir / 'llm_error_log.json'

        self.parser = RateLimitedParser(batch_size=batch_size)
        self.departments = departments

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
        if self.output_file.exists():
            with open(self.output_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_checkpoint(self):
        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.checkpoint, f, indent=2)

    def _save_results(self):
        with open(self.output_file, 'w') as f:
            json.dump(self.results, f, indent=2)

    def _log_error(self, batch_num: int, error_type: str, error_details: str, affected_courses: List[str]):
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

    def _print_courses_summary(self):
        if self.results:
            print(f"\n=== Courses Successfully Parsed ({len(self.results)} total) ===")
            for code in sorted(self.results.keys()):
                print(f"  {code}")
        else:
            print(f"\n=== No courses parsed yet ===")

    def _get_courses_with_requirements(self) -> List[Tuple[str, str]]:
        with open(self.api_data_path, 'r') as f:
            api_data = json.load(f)

        courses = []
        for course_code, course_data in api_data.items():
            req = course_data.get('requirementsDescription', '')
            if req:
                if self.departments:
                    dept = get_department_from_code(course_code)
                    if dept not in self.departments:
                        continue
                courses.append((course_code, req))

        courses.sort(key=get_course_priority)
        return courses

    async def process_courses(self, test_mode: bool = False, test_batches: int = 3):
        print(f"Loading courses from {self.api_data_path}...")
        courses = self._get_courses_with_requirements()

        if not courses:
            print("No courses found with requirements")
            return

        print(f"Found {len(courses)} courses with requirements")

        if self.departments:
            print(f"Filtering by departments: {self.departments}")

        if self.checkpoint['total_courses'] == 0:
            self.checkpoint['total_courses'] = len(courses)
            self._save_checkpoint()

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

        remaining = courses[self.checkpoint['last_processed_index']:]

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
                result, error_type = await self.parser.parse_batch_async(batch)

                if result is None:
                    if error_type == "RATE_LIMIT":
                        error_msg = "Rate limit exceeded (429). These are PER MINUTE limits - wait 1-2 minutes and resume."
                        print("\n⚠️  Rate limit exceeded - stopping gracefully")
                        print("💡 These are PER MINUTE limits (not daily)")
                        print("💡 Wait 1-2 minutes, then run the script again to resume")
                    elif error_type == "DAILY_QUOTA":
                        error_msg = "Daily quota exceeded. This resets at midnight UTC."
                        print("\n⚠️  Daily quota exceeded - stopping")
                        print("💡 This resets at midnight UTC - resume tomorrow")
                    elif error_type == "BILLING_ERROR":
                        error_msg = "Insufficient credits/billing issue. Please add credits to your Anthropic account."
                        print("\n⚠️  Billing/Credit Error - stopping")
                        print("💡 Your Anthropic account needs credits to use the API")
                        print("💡 Visit: https://console.anthropic.com/settings/billing")
                        print("💡 After adding credits, run the script again to resume")
                    else:
                        error_msg = "No response from LLM after retries"
                        print("\n⚠️  Critical error - stopping")

                    self._log_error(
                        current_batch_num,
                        error_type or "LLM_NO_RESPONSE",
                        error_msg,
                        [code for code, _ in batch]
                    )

                    self._save_checkpoint()
                    self._save_results()

                    print(f"💡 Progress saved: {self.checkpoint['successful']} courses processed")
                    print(f"💡 Next run will resume from batch {current_batch_num}")
                    self._print_courses_summary()
                    return

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

                if len(missing_courses) > len(batch) / 2:
                    self._log_error(
                        current_batch_num,
                        "BATCH_MAJORITY_MISSING",
                        f"More than 50% missing ({len(missing_courses)}/{len(batch)})",
                        missing_courses
                    )
                    print("\n⚠️  Critical error - stopping")
                    self._print_courses_summary()
                    return

            except Exception as e:
                self._log_error(
                    current_batch_num,
                    "UNEXPECTED_ERROR",
                    str(e),
                    [code for code, _ in batch]
                )
                print(f"\n⚠️  Unexpected error: {e}")
                self._print_courses_summary()
                return

            self.checkpoint['last_processed_index'] += len(batch)
            self._save_checkpoint()
            self._save_results()

            progress = (self.checkpoint['last_processed_index'] / self.checkpoint['total_courses']) * 100
            print(f"\nProgress: {progress:.1f}% ({self.checkpoint['last_processed_index']}/{self.checkpoint['total_courses']})")

        print(f"\n=== Processing Complete ===")
        print(f"Total processed: {self.checkpoint['total_courses']}")
        print(f"Successful: {self.checkpoint['successful']}")
        print(f"Failed: {self.checkpoint['failed']}")
        print(f"Results saved to: {self.output_file}")

        self._print_courses_summary()

    def reset_checkpoint(self):
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
    parser = argparse.ArgumentParser(description='Batch LLM parser for course prerequisites using Claude')
    parser.add_argument('--test', action='store_true', help='Run in test mode (3 batches)')
    parser.add_argument('--batch-size', type=int, default=12, help='Batch size (default: 12)')
    parser.add_argument('--departments', type=str, help='Comma-separated list of departments to process')
    parser.add_argument('--engineering', action='store_true',
                        help='Process only engineering departments (default: all departments)')
    parser.add_argument('--reset', action='store_true', help='Reset checkpoint and start fresh')
    parser.add_argument('--input', type=str, default='new', choices=['old', 'new'],
                        help='Input data format (default: new)')
    args = parser.parse_args()

    if args.input == 'new':
        api_data_path = PROJECT_ROOT / 'data' / 'courses' / 'course-api-new-data.json'
    else:
        api_data_path = PROJECT_ROOT / 'data' / 'courses' / 'course-api-data.json'

    output_dir = PROJECT_ROOT / 'data' / 'dependencies'

    departments = None
    if args.engineering:
        departments = ENGINEERING_DEPARTMENTS
        print(f"Filtering to engineering departments: {departments}")
    elif args.departments:
        departments = [d.strip().upper() for d in args.departments.split(',')]

    print(f"API data: {api_data_path}")
    print(f"Output dir: {output_dir}")

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

