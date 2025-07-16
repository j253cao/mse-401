import google.generativeai as genai
import os
import json
from .llm_context import pre_req_context  # Make sure this import works

class LLMClient:
    def __init__(self):
        # Configure the API key
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        genai.configure(api_key=api_key)
        
        # Initialize the model with your context
        self.model = genai.GenerativeModel(
            'gemini-2.0-flash-exp',
            system_instruction=pre_req_context
        )
        
        # Constants for batch handling
        self.MIN_BATCH_SIZE = 1
        self.REDUCTION_FACTOR = 2  # Reduce batch size by half on retry
        
        # Load valid course codes from courses.json
        self.valid_course_codes = self._load_course_codes()
        
    def _load_course_codes(self):
        """
        Load course codes from courses.json.
        Returns a list of valid course codes.
        """
        try:
            with open('data/courses.json', 'r') as f:
                courses = json.load(f)
            return [course['courseCode'] for course in courses]
        except Exception as e:
            print(f"Warning: Failed to load courses.json: {e}")
            return []

    def _split_batch(self, courses_batch, new_size):
        """
        Split a batch into smaller sub-batches.
        
        Args:
            courses_batch: List of tuples [(course_code, requirements_description), ...]
            new_size: Size of each sub-batch
            
        Returns:
            List of sub-batches
        """
        return [courses_batch[i:i + new_size] for i in range(0, len(courses_batch), new_size)]

    def _process_single_batch(self, courses_batch):
        """
        Process a single batch and get LLM response.
        
        Args:
            courses_batch: List of tuples [(course_code, requirements_description), ...]
            
        Returns:
            Tuple of (success, response_text)
            - success: Boolean indicating if processing was successful
            - response_text: The response text if successful, error message if not
        """
        try:
            batch_input = {
                "courses": [
                    {
                        "code": code,
                        "requirements": requirements
                    }
                    for code, requirements in courses_batch
                ]
            }
            
            prompt = json.dumps(batch_input, indent=2)
            
            generation_config = {
                "temperature": 0.1,
                "max_output_tokens": 8192
            }
            
            response = self.model.generate_content(prompt, generation_config=generation_config)
            
            # Print debug information
            print("\nRaw LLM Response:")
            print("=" * 80)
            print(response.text)
            print("=" * 80)
            
            print("\nResponse Metadata:")
            print(f"Batch size: {len(courses_batch)}")
            print(f"Prompt tokens: {response.prompt_token_count if hasattr(response, 'prompt_token_count') else 'Not available'}")
            print(f"Response tokens: {response.candidates[0].token_count if hasattr(response, 'candidates') else 'Not available'}")
            print(f"Safety ratings: {response.candidates[0].safety_ratings if hasattr(response, 'candidates') else 'Not available'}")
            
            # Extract JSON content from response
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Check if response seems truncated
            if not (response_text.endswith('}') and response_text.startswith('{')):
                return False, "Response appears truncated"
                
            try:
                # Parse and validate the JSON response
                parsed_json = json.loads(response_text)
                
                # Validate it's an object with course keys
                if not isinstance(parsed_json, dict):
                    return False, "Invalid JSON structure - expected object"
                
                # Get the expected course codes for this batch
                expected_codes = {code for code, _ in courses_batch}
                
                # Check each course in the response
                for code in expected_codes:
                    if code not in parsed_json:
                        return False, f"Missing results for {code}"
                    
                    data = parsed_json[code]
                    if not isinstance(data, dict):
                        return False, f"Invalid course data for {code}"
                    if "type" not in data or data["type"] != "prerequisites":
                        return False, f"Missing or invalid type field for {code}"
                
                # Return the original response
                return True, response_text
                
            except json.JSONDecodeError:
                return False, "Invalid JSON response"
                
        except Exception as e:
            return False, str(e)

    def generate_content(self, courses_batch):
        """
        Process a batch of courses with automatic retry and batch size reduction.
        
        Args:
            courses_batch: List of tuples [(course_code, requirements_description), ...]
        
        Returns:
            JSON string containing parsed prerequisites for all courses in the batch,
            or None if processing failed even with minimum batch size
        """
        current_batch_size = len(courses_batch)
        
        while current_batch_size >= self.MIN_BATCH_SIZE:
            print(f"\nAttempting to process with batch size: {current_batch_size}")
            
            if current_batch_size == len(courses_batch):
                # Try processing the entire batch first
                success, result = self._process_single_batch(courses_batch)
                if success:
                    return result
            else:
                # Process smaller sub-batches and combine results
                sub_batches = self._split_batch(courses_batch, current_batch_size)
                all_results = {}
                all_successful = True
                
                for sub_batch in sub_batches:
                    success, result = self._process_single_batch(sub_batch)
                    if not success:
                        all_successful = False
                        break
                    try:
                        # Parse the JSON result and merge the course objects
                        result_json = json.loads(result)
                        all_results.update(result_json)
                    except json.JSONDecodeError:
                        all_successful = False
                        break
                
                if all_successful:
                    # Return the combined object format
                    return json.dumps(all_results, indent=2)
            
            # If we get here, the current batch size failed
            # Reduce batch size and try again
            current_batch_size = current_batch_size // self.REDUCTION_FACTOR
            print(f"Reducing batch size to: {current_batch_size}")
        
        print("Failed to process even with minimum batch size")
        return None