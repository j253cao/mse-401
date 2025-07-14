import json
import os
import asyncio
import time
from pathlib import Path
from dotenv import load_dotenv
from util.llm_client import LLMClient
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

class RateLimitedLLMClient:
    def __init__(self, requests_per_minute=30, batch_size=10):
        self.llm_client = LLMClient()
        self.requests_per_minute = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute  # seconds between requests
        self.last_request_time = 0
        self.batch_size = batch_size
    
    async def generate_content(self, courses_batch):
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            print(f"Rate limiting: waiting {wait_time:.2f} seconds...")
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
        
        # Run the LLM call in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.llm_client.generate_content, courses_batch)

def clean_json_response(response):
    """Clean markdown code blocks from LLM response"""
    if not response:
        return None
    
    cleaned_response = response.strip()
    if cleaned_response.startswith('```json'):
        cleaned_response = cleaned_response[7:]  # Remove ```json
    if cleaned_response.startswith('```'):
        cleaned_response = cleaned_response[3:]  # Remove ```
    if cleaned_response.endswith('```'):
        cleaned_response = cleaned_response[:-3]  # Remove trailing ```
    
    return cleaned_response.strip()

class CourseProcessor:
    def __init__(self, api_data_path, output_dir='data/course_dependencies'):
        self.api_data_path = Path(api_data_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file = self.output_dir / 'checkpoint.json'
        self.output_file = self.output_dir / 'course_dependencies.json'
        self.error_log_file = self.output_dir / 'error_log.json'
        self.llm_client = RateLimitedLLMClient(requests_per_minute=30, batch_size=10)
        
        # Initialize or load checkpoint
        self.checkpoint = self._load_checkpoint()
        
        # Load or initialize results
        self.results = self._load_results()
        
        # Initialize error log
        self.error_log = {
            'last_error_timestamp': None,
            'last_error_batch': None,
            'error_type': None,
            'error_details': None,
            'failed_courses': [],
            'checkpoint_state': self.checkpoint
        }
    
    def _load_checkpoint(self):
        """Load or initialize checkpoint data"""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        return {
            'last_processed_index': 0,
            'successful': 0,
            'failed': 0,
            'total_courses': 0
        }
    
    def _load_results(self):
        """Load or initialize results"""
        if self.output_file.exists():
            with open(self.output_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_checkpoint(self):
        """Save current checkpoint data"""
        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.checkpoint, f, indent=2)
    
    def _update_results(self, new_results):
        """Update results file with new results"""
        self.results.update(new_results)
        with open(self.output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
    
    def _log_error(self, batch_num, error_type, error_details, affected_courses):
        """Log error details to error log file"""
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
        
        print("\n=== Error Details ===")
        print(f"Error Type: {error_type}")
        print(f"Error Details: {error_details}")
        print(f"Failed Courses: {affected_courses}")
        print(f"Error log saved to: {self.error_log_file}")

    async def process_courses(self):
        """Process all courses with checkpointing"""
        # Load API data
        if not self.api_data_path.exists():
            print(f"API data file not found: {self.api_data_path}")
            return
        
        with open(self.api_data_path, 'r') as f:
            api_data = json.load(f)
        
        print(f"Loaded {len(api_data)} courses from API data")
        
        # Get all courses with requirements description
        courses_with_requirements = []
        for course_code, course_data in api_data.items():
            if course_data.get('requirementsDescription'):
                courses_with_requirements.append((course_code, course_data['requirementsDescription']))
        
        if not courses_with_requirements:
            print("No courses found with requirements description")
            return
        
        # Update total courses count if starting fresh
        if self.checkpoint['total_courses'] == 0:
            self.checkpoint['total_courses'] = len(courses_with_requirements)
            self._save_checkpoint()
        
        print(f"\n=== Resuming Processing ===")
        print(f"Total courses: {self.checkpoint['total_courses']}")
        print(f"Starting from index: {self.checkpoint['last_processed_index']}")
        print(f"Previously successful: {self.checkpoint['successful']}")
        print(f"Previously failed: {self.checkpoint['failed']}")
        
        # Split remaining courses into batches
        remaining_courses = courses_with_requirements[self.checkpoint['last_processed_index']:]
        batches = [
            remaining_courses[i:i + self.llm_client.batch_size]
            for i in range(0, len(remaining_courses), self.llm_client.batch_size)
        ]
        
        print(f"\nProcessing {len(batches)} remaining batches...")
        
        for batch_num, batch in enumerate(batches, 1):
            current_batch_num = batch_num + (self.checkpoint['last_processed_index'] // self.llm_client.batch_size)
            print(f"\nProcessing batch {current_batch_num}...")
            print(f"Courses in batch: {[code for code, _ in batch]}")
            
            batch_results = {}
            try:
                # Process the batch
                response = await self.llm_client.generate_content(batch)
                
                if response is None:
                    error_msg = "No response from LLM"
                    self._log_error(
                        current_batch_num,
                        "LLM_NO_RESPONSE",
                        error_msg,
                        [code for code, _ in batch]
                    )
                    print("\n⚠️  Critical error - stopping processing")
                    return
                
                # Parse response
                cleaned_response = clean_json_response(response)
                if not cleaned_response:
                    error_msg = "Empty response from LLM"
                    self._log_error(
                        current_batch_num,
                        "LLM_EMPTY_RESPONSE",
                        error_msg,
                        [code for code, _ in batch]
                    )
                    print("\n⚠️  Critical error - stopping processing")
                    return
                
                try:
                    parsed_response = json.loads(cleaned_response)
                    
                    # Track missing courses for error logging
                    missing_courses = []
                    
                    # Validate that we got results for all courses in the batch
                    for code, _ in batch:
                        if code not in parsed_response:
                            print(f"✗ Missing results for {code} in batch response")
                            batch_results[code] = {"error": "Missing from batch response"}
                            self.checkpoint['failed'] += 1
                            missing_courses.append(code)
                        else:
                            batch_results[code] = parsed_response[code]
                            print(f"✓ Successfully parsed dependencies for {code}")
                            self.checkpoint['successful'] += 1
                    
                    # If more than 50% of courses are missing, consider it a critical error
                    if len(missing_courses) > len(batch) / 2:
                        error_msg = f"More than 50% of courses missing from response ({len(missing_courses)}/{len(batch)})"
                        self._log_error(
                            current_batch_num,
                            "BATCH_MAJORITY_MISSING",
                            error_msg,
                            missing_courses
                        )
                        print("\n⚠️  Critical error - stopping processing")
                        return
                    
                except json.JSONDecodeError as e:
                    error_msg = f"Failed to parse JSON response: {str(e)}"
                    self._log_error(
                        current_batch_num,
                        "JSON_PARSE_ERROR",
                        error_msg,
                        [code for code, _ in batch]
                    )
                    print("\n⚠️  Critical error - stopping processing")
                    return
                    
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                self._log_error(
                    current_batch_num,
                    "UNEXPECTED_ERROR",
                    error_msg,
                    [code for code, _ in batch]
                )
                print("\n⚠️  Critical error - stopping processing")
                return
            
            # Update results and checkpoint
            self._update_results(batch_results)
            
            # Update checkpoint
            self.checkpoint['last_processed_index'] += len(batch)
            self._save_checkpoint()
            
            # Print progress
            progress = (self.checkpoint['last_processed_index'] / self.checkpoint['total_courses']) * 100
            print(f"\nProgress: {progress:.1f}% ({self.checkpoint['last_processed_index']}/{self.checkpoint['total_courses']} courses)")
            print(f"Successful: {self.checkpoint['successful']}")
            print(f"Failed: {self.checkpoint['failed']}")
        
        print(f"\n=== Processing Complete ===")
        print(f"Total courses processed: {self.checkpoint['total_courses']}")
        print(f"Final successful: {self.checkpoint['successful']}")
        print(f"Final failed: {self.checkpoint['failed']}")
        print(f"Results file: {self.output_file}")

async def test_three_batches(processor):
    """Test function to process exactly 3 batches (30 courses)"""
    # Load API data
    if not processor.api_data_path.exists():
        print(f"API data file not found: {processor.api_data_path}")
        return
    
    with open(processor.api_data_path, 'r') as f:
        api_data = json.load(f)
    
    print(f"Loaded {len(api_data)} courses from API data")
    
    # Get courses with requirements description (limit to 30 for 3 batches)
    courses_with_requirements = []
    for course_code, course_data in api_data.items():
        if course_data.get('requirementsDescription'):
            courses_with_requirements.append((course_code, course_data['requirementsDescription']))
            if len(courses_with_requirements) >= 30:  # Limit to 30 courses (3 batches)
                break
    
    if not courses_with_requirements:
        print("No courses found with requirements description")
        return
    
    print(f"\n=== Starting 3-Batch Test ===")
    print(f"Processing {len(courses_with_requirements)} courses in 3 batches")
    
    # Override checkpoint to start fresh
    processor.checkpoint = {
        'last_processed_index': 0,
        'successful': 0,
        'failed': 0,
        'total_courses': len(courses_with_requirements)
    }
    processor._save_checkpoint()
    
    # Process courses in batches
    remaining_courses = courses_with_requirements[processor.checkpoint['last_processed_index']:]
    batches = [
        remaining_courses[i:i + processor.llm_client.batch_size]
        for i in range(0, len(remaining_courses), processor.llm_client.batch_size)
    ]
    
    print(f"\nProcessing {len(batches)} batches of up to {processor.llm_client.batch_size} courses each...")
    
    for batch_num, batch in enumerate(batches, 1):
        current_batch_num = batch_num + (processor.checkpoint['last_processed_index'] // processor.llm_client.batch_size)
        print(f"\nProcessing batch {current_batch_num}...")
        print(f"Courses in batch: {[code for code, _ in batch]}")
        
        batch_results = {}
        try:
            # Process the batch
            response = await processor.llm_client.generate_content(batch)
            
            if response is None:
                error_msg = "No response from LLM"
                processor._log_error(
                    current_batch_num,
                    "LLM_NO_RESPONSE",
                    error_msg,
                    [code for code, _ in batch]
                )
                print("\n⚠️  Critical error - stopping processing")
                return
            
            # Parse response
            cleaned_response = clean_json_response(response)
            if not cleaned_response:
                error_msg = "Empty response from LLM"
                processor._log_error(
                    current_batch_num,
                    "LLM_EMPTY_RESPONSE",
                    error_msg,
                    [code for code, _ in batch]
                )
                print("\n⚠️  Critical error - stopping processing")
                return
            
            try:
                parsed_response = json.loads(cleaned_response)
                
                # Track missing courses for error logging
                missing_courses = []
                
                # Validate that we got results for all courses in the batch
                for code, _ in batch:
                    if code not in parsed_response:
                        print(f"✗ Missing results for {code} in batch response")
                        batch_results[code] = {"error": "Missing from batch response"}
                        processor.checkpoint['failed'] += 1
                        missing_courses.append(code)
                    else:
                        batch_results[code] = parsed_response[code]
                        print(f"✓ Successfully parsed dependencies for {code}")
                        processor.checkpoint['successful'] += 1
                
                # If more than 50% of courses are missing, consider it a critical error
                if len(missing_courses) > len(batch) / 2:
                    error_msg = f"More than 50% of courses missing from response ({len(missing_courses)}/{len(batch)})"
                    processor._log_error(
                        current_batch_num,
                        "BATCH_MAJORITY_MISSING",
                        error_msg,
                        missing_courses
                    )
                    print("\n⚠️  Critical error - stopping processing")
                    return
                
            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse JSON response: {str(e)}"
                processor._log_error(
                    current_batch_num,
                    "JSON_PARSE_ERROR",
                    error_msg,
                    [code for code, _ in batch]
                )
                print("\n⚠️  Critical error - stopping processing")
                return
                
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            processor._log_error(
                current_batch_num,
                "UNEXPECTED_ERROR",
                error_msg,
                [code for code, _ in batch]
            )
            print("\n⚠️  Critical error - stopping processing")
            return
        
        # Update results and checkpoint
        processor._update_results(batch_results)
        
        # Update checkpoint
        processor.checkpoint['last_processed_index'] += len(batch)
        processor._save_checkpoint()
        
        # Print progress
        progress = (processor.checkpoint['last_processed_index'] / processor.checkpoint['total_courses']) * 100
        print(f"\nProgress: {progress:.1f}% ({processor.checkpoint['last_processed_index']}/{processor.checkpoint['total_courses']} courses)")
        print(f"Successful: {processor.checkpoint['successful']}")
        print(f"Failed: {processor.checkpoint['failed']}")
    
    print(f"\n=== Test Complete ===")
    print(f"Total courses processed: {processor.checkpoint['total_courses']}")
    print(f"Final successful: {processor.checkpoint['successful']}")
    print(f"Final failed: {processor.checkpoint['failed']}")
    print(f"Results directory: {processor.output_dir}")
    print(f"Merged results file: {processor.output_file}")

async def main():
    """Main entry point"""
    # Get the project root directory (2 levels up from this script)
    project_root = Path(__file__).resolve().parent.parent.parent
    
    # Use relative path from project root
    api_data_path = project_root / 'data' / 'waterloo-open-api-data.json'
    
    print(f"Project root: {project_root}")
    print(f"Using API data from: {api_data_path}")
    
    # For testing 3 batches
    processor = CourseProcessor(
        api_data_path=api_data_path,
        output_dir=project_root / 'data' / 'course_dependencies_test'
    )
    await test_three_batches(processor)
    
    # For processing all courses, uncomment this:
    # processor = CourseProcessor(
    #     api_data_path=api_data_path,
    #     output_dir=project_root / 'data' / 'course_dependencies'
    # )
    # await processor.process_courses()

if __name__ == "__main__":
    asyncio.run(main())
