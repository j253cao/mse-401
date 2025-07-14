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

    def generate_content(self, courses_batch):
        """
        Process a batch of courses.
        
        Args:
            courses_batch: List of tuples [(course_code, requirements_description), ...]
        
        Returns:
            JSON string containing parsed prerequisites for all courses in the batch
        """
        try:
            # Format the input according to the new batch format
            batch_input = {
                "courses": [
                    {
                        "code": code,
                        "requirements": requirements
                    }
                    for code, requirements in courses_batch
                ]
            }
            
            # Convert to JSON string
            prompt = json.dumps(batch_input, indent=2)
            
            # Get response from LLM
            response = self.model.generate_content(prompt)
            
            # Print response metadata
            print("\nResponse Metadata:")
            print(f"Prompt tokens: {response.prompt_token_count if hasattr(response, 'prompt_token_count') else 'Not available'}")
            print(f"Response tokens: {response.candidates[0].token_count if hasattr(response, 'candidates') else 'Not available'}")
            print(f"Safety ratings: {response.candidates[0].safety_ratings if hasattr(response, 'candidates') else 'Not available'}")
            
            return response.text
        except Exception as e:
            print(f"Error generating content: {str(e)}")
            return None