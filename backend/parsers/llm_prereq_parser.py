"""
LLM-based prerequisite parser using Google Gemini or Groq.

Parses course prerequisite strings into structured JSON with proper AND/OR groupings.
Handles complex patterns like "(A or B) and (C or D)" that are difficult to parse with regex.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

# Optional imports - will be loaded based on provider
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

# Load environment variables from project root .env file
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / '.env')

# Debug output path for raw LLM responses
RAW_RESPONSE_DEBUG_PATH = PROJECT_ROOT / 'data' / 'dependencies' / 'llm_raw_response_debug.json'


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


# System context for the LLM - defines the parsing rules and output format
PREREQ_PARSER_CONTEXT = """
# Course Prerequisites Parser - System Context

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

## Example Input
{
  "courses": [
    {
      "code": "CS371",
      "requirements": "Prereq: One of CS 116, CS 136, CS 138, CS 146; One of (CS 114 with a minimum grade of 60%), CS 115, 135, 145; MATH 235 or MATH 245; MATH 237 or MATH 247"
    }
  ]
}

## Example Output
{
  "CS371": {
    "prerequisites": {
      "groups": [
        {
          "type": "prerequisite_group",
          "courses": [
            {"type": "course", "code": "CS116", "name": null, "grade_requirement": null},
            {"type": "course", "code": "CS136", "name": null, "grade_requirement": null},
            {"type": "course", "code": "CS138", "name": null, "grade_requirement": null},
            {"type": "course", "code": "CS146", "name": null, "grade_requirement": null}
          ],
          "operator": "OR",
          "quantity": 1
        },
        {
          "type": "prerequisite_group",
          "courses": [
            {"type": "course", "code": "CS114", "name": null, "grade_requirement": {"type": "grade_requirement", "value": 60, "operator": "minimum", "unit": "%"}},
            {"type": "course", "code": "CS115", "name": null, "grade_requirement": null},
            {"type": "course", "code": "CS135", "name": null, "grade_requirement": null},
            {"type": "course", "code": "CS145", "name": null, "grade_requirement": null}
          ],
          "operator": "OR",
          "quantity": 1
        },
        {
          "type": "prerequisite_group",
          "courses": [
            {"type": "course", "code": "MATH235", "name": null, "grade_requirement": null},
            {"type": "course", "code": "MATH245", "name": null, "grade_requirement": null}
          ],
          "operator": "OR"
        },
        {
          "type": "prerequisite_group",
          "courses": [
            {"type": "course", "code": "MATH237", "name": null, "grade_requirement": null},
            {"type": "course", "code": "MATH247", "name": null, "grade_requirement": null}
          ],
          "operator": "OR"
        }
      ],
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

## Important Notes
- Always normalize course codes (remove spaces): "CS 146" → "CS146"
- Default root_operator is "AND"
- If no grade requirement, set grade_requirement to null
- Empty arrays for missing sections
- Parse ALL sections (prereq, coreq, antireq) from the requirements string

## Output Format
- Return valid JSON as a single line with NO whitespace, newlines, or indentation (minified/compact format)
- Do not wrap in markdown code blocks
"""


class LLMPrereqParser:
    """
    LLM-based prerequisite parser using Google Gemini.
    
    Processes courses in batches with rate limiting and automatic retry.
    Supports multiple API keys for higher throughput.
    """
    
    def __init__(self, model_name: str = 'gemini-2.0-flash', api_keys: Optional[List[str]] = None):
        """
        Initialize the LLM parser.
        
        Args:
            model_name: Gemini model to use (default: gemini-2.0-flash)
            api_keys: Optional list of API keys for rotation. If None, uses GEMINI_API_KEY env var.
                      Can also set GEMINI_API_KEYS env var with comma-separated keys.
        """
        # Load API keys
        if api_keys:
            self.api_keys = api_keys
        else:
            # Try GEMINI_API_KEYS first (comma-separated), then fall back to GEMINI_API_KEY
            keys_str = os.getenv('GEMINI_API_KEYS', '')
            if keys_str:
                self.api_keys = [k.strip() for k in keys_str.split(',') if k.strip()]
            else:
                single_key = os.getenv('GEMINI_API_KEY')
                if single_key:
                    self.api_keys = [single_key]
                else:
                    raise ValueError("No API keys found. Set GEMINI_API_KEY or GEMINI_API_KEYS in .env file")
        
        print(f"Loaded {len(self.api_keys)} API key(s)")
        
        self.model_name = model_name
        self.current_key_index = 0
        
        # Initialize with first key
        self._configure_model(self.api_keys[0])
        
        # Batch processing settings
        self.min_batch_size = 1
        self.reduction_factor = 2
        
        # API timeout settings (in seconds)
        self.api_timeout = 120  # 2 minutes timeout for API calls
    
    def _configure_model(self, api_key: str):
        """Configure the model with the given API key."""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            self.model_name,
            system_instruction=PREREQ_PARSER_CONTEXT
        )
    
    def _rotate_key(self):
        """Rotate to the next API key."""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self._configure_model(self.api_keys[self.current_key_index])
        print(f"    Rotated to API key {self.current_key_index + 1}/{len(self.api_keys)}")
    
    def _clean_json_response(self, response: str) -> Optional[str]:
        """
        Clean markdown code blocks from LLM response.
        
        Args:
            response: Raw LLM response text
            
        Returns:
            Cleaned JSON string or None if invalid
        """
        import re
        
        if not response:
            return None
        
        cleaned = response.strip()
        
        # Try to extract JSON from ```json blocks
        json_pattern = r'```json\s*(.*?)\s*```'
        matches = re.findall(json_pattern, cleaned, re.DOTALL)
        if matches:
            for match in matches:
                try:
                    json.loads(match.strip())
                    return match.strip()
                except json.JSONDecodeError:
                    continue
        
        # Try generic code blocks
        code_pattern = r'```\s*(.*?)\s*```'
        matches = re.findall(code_pattern, cleaned, re.DOTALL)
        if matches:
            for match in matches:
                try:
                    json.loads(match.strip())
                    return match.strip()
                except json.JSONDecodeError:
                    continue
        
        # Try parsing as-is
        try:
            json.loads(cleaned)
            return cleaned
        except json.JSONDecodeError:
            pass
        
        return None
    
    def _process_single_batch(self, courses_batch: List[Tuple[str, str]]) -> Tuple[bool, str]:
        """
        Process a single batch of courses.
        
        Args:
            courses_batch: List of (course_code, requirements_description) tuples
            
        Returns:
            Tuple of (success, result_or_error)
        """
        try:
            batch_input = {
                "courses": [
                    {"code": code, "requirements": requirements}
                    for code, requirements in courses_batch
                ]
            }
            
            prompt = json.dumps(batch_input, indent=2)
            
            generation_config = {
                "temperature": 0.1,
                "max_output_tokens": 8192
            }
            
            # Wrap API call with timeout to prevent infinite hangs
            def _make_api_call():
                return self.model.generate_content(prompt, generation_config=generation_config)
            
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_make_api_call)
                    response = future.result(timeout=self.api_timeout)
            except FutureTimeoutError:
                return False, f"API call timed out after {self.api_timeout} seconds"
            except Exception as e:
                # Re-raise to be caught by outer exception handler
                raise
            
            raw_response = response.text if response and response.text else ""

            # Save raw response for debugging (before any parsing)
            _save_raw_response_debug(raw_response, courses_batch)

            # Clean and validate response
            response_text = self._clean_json_response(raw_response)
            
            if not response_text:
                return False, "Failed to extract valid JSON from response"
            
            # Validate JSON structure
            try:
                parsed = json.loads(response_text)
                
                if not isinstance(parsed, dict):
                    return False, "Invalid JSON structure - expected object"
                
                # Check all expected courses are present
                expected_codes = {code for code, _ in courses_batch}
                for code in expected_codes:
                    if code not in parsed:
                        return False, f"Missing results for {code}"
                
                return True, response_text
                
            except json.JSONDecodeError as e:
                return False, f"Invalid JSON: {str(e)}"
        
        except Exception as e:
            error_str = str(e)
            error_type = type(e).__name__
            
            # Check for quota exceeded error - Gemini API can raise various exceptions
            # Check status code if available
            status_code = None
            if hasattr(e, 'status_code'):
                status_code = e.status_code
            elif hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                status_code = e.response.status_code
            
            # Check for rate limit/quota errors
            is_rate_limit = (
                status_code == 429 or
                '429' in error_str or
                'quota' in error_str.lower() or
                'rate limit' in error_str.lower() or
                'rate_limit_exceeded' in error_str.lower() or
                'RESOURCE_EXHAUSTED' in error_str
            )
            
            if is_rate_limit:
                # Check if it's a daily quota vs per-minute rate limit
                is_daily = 'daily' in error_str.lower() or 'per day' in error_str.lower()
                error_detail = f"{error_type}: {error_str}"
                
                if len(self.api_keys) > 1:
                    print(f"    ⚠️  API Quota/Rate limit exceeded on key {self.current_key_index + 1}.")
                    if is_daily:
                        print(f"    ⚠️  Daily quota exceeded - rotating to next key...")
                    else:
                        print(f"    ⚠️  Rate limit exceeded - rotating to next key...")
                    print(f"    ⚠️  Error: {error_detail[:200]}")
                    self._rotate_key()
                    return False, f"API_QUOTA_EXCEEDED_ROTATING: {error_detail}"
                else:
                    if is_daily:
                        print(f"    ⚠️  Daily quota exceeded. This resets at midnight UTC/PST.")
                    else:
                        print(f"    ⚠️  Rate limit/quota exceeded. Please check your Gemini API plan.")
                    print(f"    ⚠️  Error: {error_detail[:200]}")
                    print(f"    See: https://ai.google.dev/gemini-api/docs/rate-limits")
                    return False, f"API_QUOTA_EXCEEDED: {error_detail}"
            
            return False, f"{error_type}: {error_str}"
    
    def parse_batch(self, courses_batch: List[Tuple[str, str]]) -> Optional[Dict[str, Any]]:
        """
        Parse a batch of courses with automatic retry and batch size reduction.
        
        Args:
            courses_batch: List of (course_code, requirements_description) tuples
            
        Returns:
            Dictionary of parsed prerequisites or None if failed
        """
        current_batch_size = len(courses_batch)
        last_error = None
        
        while current_batch_size >= self.min_batch_size:
            print(f"  Attempting batch size: {current_batch_size}")
            
            if current_batch_size == len(courses_batch):
                # Try processing entire batch
                success, result = self._process_single_batch(courses_batch)
                if success:
                    return json.loads(result)
                last_error = result
                
                # If it's a quota/rate limit error, don't keep reducing batch size
                # Reducing won't help - the issue is with the API, not the batch size
                if result and ('API_QUOTA_EXCEEDED' in result or 'quota' in result.lower() or '429' in result):
                    print(f"  ⚠️  Quota/rate limit error detected. Stopping batch size reduction.")
                    print(f"  ⚠️  Error: {result[:200]}")
                    return None
            else:
                # Process smaller sub-batches
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
                        last_error = result
                        print(f"    Sub-batch failed: {result[:200]}")
                        
                        # If it's a quota/rate limit error, stop trying smaller batches
                        if result and ('API_QUOTA_EXCEEDED' in result or 'quota' in result.lower() or '429' in result):
                            print(f"  ⚠️  Quota/rate limit error detected. Stopping batch size reduction.")
                            return None
                        break
                    
                    try:
                        all_results.update(json.loads(result))
                    except json.JSONDecodeError:
                        all_successful = False
                        last_error = f"JSON decode error: {result[:100]}"
                        break
                
                if all_successful:
                    return all_results
            
            # Reduce batch size and retry (only if not a quota error)
            current_batch_size = current_batch_size // self.reduction_factor
            if current_batch_size >= self.min_batch_size:
                print(f"  Reducing batch size to: {current_batch_size}")
        
        print(f"  Failed even with minimum batch size")
        if last_error:
            print(f"  Last error: {last_error[:200]}")
        return None
    
    def parse_single(self, course_code: str, requirements: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single course's requirements.
        
        Args:
            course_code: Course code (e.g., "CS371")
            requirements: Requirements description string
            
        Returns:
            Parsed prerequisites dictionary or None if failed
        """
        result = self.parse_batch([(course_code, requirements)])
        if result and course_code in result:
            return result[course_code]
        return None


class GroqPrereqParser:
    """
    LLM-based prerequisite parser using Groq.
    
    Groq offers much higher free tier limits (~14,400 requests/day).
    Uses Llama 3 models which are very capable for structured output.
    """
    
    def __init__(self, model_name: str = 'llama-3.3-70b-versatile', api_key: Optional[str] = None):
        """
        Initialize the Groq parser.
        
        Args:
            model_name: Groq model to use (default: llama-3.3-70b-versatile)
            api_key: Optional API key. If None, uses GROQ_API_KEY env var.
        """
        if not HAS_GROQ:
            raise ImportError("Groq package not installed. Run: pip install groq")
        
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        if not self.api_key:
            raise ValueError("No Groq API key found. Set GROQ_API_KEY in .env file")
        
        self.client = Groq(api_key=self.api_key)
        self.model_name = model_name
        self.api_keys = [self.api_key]  # For compatibility with batch processor
        
        print(f"Groq initialized with model: {model_name}")
        
        # Batch processing settings
        self.min_batch_size = 1
        self.reduction_factor = 2
    
    def _clean_json_response(self, response: str) -> Optional[str]:
        """Clean markdown code blocks from LLM response."""
        import re
        
        if not response:
            return None
        
        cleaned = response.strip()
        
        # Try to extract JSON from ```json blocks
        json_pattern = r'```json\s*(.*?)\s*```'
        matches = re.findall(json_pattern, cleaned, re.DOTALL)
        if matches:
            for match in matches:
                try:
                    json.loads(match.strip())
                    return match.strip()
                except json.JSONDecodeError:
                    continue
        
        # Try generic code blocks
        code_pattern = r'```\s*(.*?)\s*```'
        matches = re.findall(code_pattern, cleaned, re.DOTALL)
        if matches:
            for match in matches:
                try:
                    json.loads(match.strip())
                    return match.strip()
                except json.JSONDecodeError:
                    continue
        
        # Try parsing as-is
        try:
            json.loads(cleaned)
            return cleaned
        except json.JSONDecodeError:
            pass
        
        return None
    
    def _process_single_batch(self, courses_batch: List[Tuple[str, str]]) -> Tuple[bool, str]:
        """Process a single batch of courses using Groq."""
        try:
            batch_input = {
                "courses": [
                    {"code": code, "requirements": requirements}
                    for code, requirements in courses_batch
                ]
            }
            
            prompt = json.dumps(batch_input, indent=2)
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": PREREQ_PARSER_CONTEXT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=8192
            )
            raw_response = (
                response.choices[0].message.content
                if response.choices and response.choices[0].message
                else ""
            )

            # Save raw response for debugging (before any parsing)
            _save_raw_response_debug(raw_response, courses_batch)

            response_text = self._clean_json_response(raw_response)
            
            if not response_text:
                return False, "Failed to extract valid JSON from response"
            
            # Validate JSON structure
            try:
                parsed = json.loads(response_text)
                
                if not isinstance(parsed, dict):
                    return False, "Invalid JSON structure - expected object"
                
                # Check all expected courses are present
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
            return False, error_str
    
    def parse_batch(self, courses_batch: List[Tuple[str, str]]) -> Optional[Dict[str, Any]]:
        """Parse a batch of courses with automatic retry and batch size reduction."""
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
    
    def parse_single(self, course_code: str, requirements: str) -> Optional[Dict[str, Any]]:
        """Parse a single course's requirements."""
        result = self.parse_batch([(course_code, requirements)])
        if result and course_code in result:
            return result[course_code]
        return None


def create_parser(provider: str = 'groq', **kwargs):
    """
    Factory function to create the appropriate parser.
    
    Args:
        provider: 'gemini' or 'groq' (default: groq)
        **kwargs: Additional arguments passed to the parser constructor
        
    Returns:
        LLMPrereqParser or GroqPrereqParser instance
    """
    if provider == 'groq':
        return GroqPrereqParser(**kwargs)
    elif provider == 'gemini':
        return LLMPrereqParser(**kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'gemini' or 'groq'")


def main():
    """Test the LLM prerequisite parser."""
    parser = LLMPrereqParser()
    
    # Test with a complex example
    test_cases = [
        ("CS371", "Prereq: One of CS 116, CS 136, CS 138, CS 146; One of (CS 114 with a minimum grade of 60%), CS 115, 135, 145; MATH 235 or MATH 245; MATH 237 or MATH 247"),
        ("ECE380", "Prereq: (ECE 207; Level at least 3A Computer Engineering or Electrical Engineering) or (MATH 213; Level at least 3A Software Engineering). Antireq: ME 360, MTE 360, SE 380, SYDE 352"),
        ("ACTSC447", "Prereq: (AMATH 242/CS 371 or CS 370) and (STAT 206 with at least 60% or STAT 231 or STAT 241)"),
    ]
    
    print("Testing LLM Prerequisite Parser")
    print("=" * 60)
    
    for code, requirements in test_cases:
        print(f"\n{code}: {requirements[:80]}...")
        result = parser.parse_single(code, requirements)
        if result:
            print(json.dumps(result, indent=2))
        else:
            print("  Failed to parse")


if __name__ == "__main__":
    main()
