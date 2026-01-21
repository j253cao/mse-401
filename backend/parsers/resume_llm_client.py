"""LLM client for resume analysis using Google Gemini."""

import google.generativeai as genai
import os
import json
from typing import Dict, Optional, Any
from dotenv import load_dotenv


class ResumeLLMClient:
    """Client for analyzing resumes using Google's Gemini LLM."""
    
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        
        # Configure the API key
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file")
        genai.configure(api_key=api_key)
        
        # Initialize the model with resume analysis context
        self.system_context = """
        You are a career interest analyzer. Look for patterns in resumes to identify broad academic and career interests.
        Don't list specific jobs or skills - instead, identify general fields of interest and learning patterns.
        
        Output Format:
        {
            "core_interests": {
                "primary_field": "Main field of interest (e.g., Computer Science, Data Science)",
                "subfields": ["2-3 specific areas within the main field"],
                "explanation": "Brief explanation of why these fields match their pattern"
            },
            "learning_patterns": {
                "theoretical_vs_practical": "Whether they lean towards theoretical or hands-on work",
                "preferred_domains": ["2-3 high-level domains they gravitate towards"]
            },
            "suggested_directions": [
                {
                    "field": "Broad academic field",
                    "why": "Brief explanation based on observed patterns"
                }
            ]
        }

        Example interpretation:
        - Someone working with AWS, Docker, Kubernetes → Shows interest in Systems and Infrastructure
        - Full-stack + Mobile dev experience → Interest in Software Engineering and Application Architecture
        - ML projects + Data pipelines → Data Science and Analytics interest

        Focus on patterns and interests, not specific technologies or roles.
        Keep explanations concise (max 2 sentences).
        Limit suggestions to 2-3 most relevant fields.
        """
        
        self.model = genai.GenerativeModel(
            'gemini-2.0-flash-exp',
            system_instruction=self.system_context
        )
        
    def _process_resume(self, resume_text: str) -> Dict[str, Any]:
        """Process a resume and extract high-level interests."""
        try:
            generation_config = {
                "temperature": 0.2,
                "max_output_tokens": 1024,
                "top_p": 0.8
            }
            
            prompt = """
            Analyze this resume to identify broad academic and career interests.
            Focus on patterns that suggest general fields of study, not specific technologies or roles.
            What academic areas would they likely be interested in studying?

            Resume:
            {resume_text}
            """.format(resume_text=resume_text)
            
            response = self.model.generate_content(prompt, generation_config=generation_config)
            
            # Print debug information
            print("\nRaw LLM Response:")
            print("=" * 80)
            print(response.text)
            print("=" * 80)
            
            # Extract and validate JSON response
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            parsed_json = json.loads(response_text)
            
            # Basic validation
            required_sections = ['core_interests', 'learning_patterns', 'suggested_directions']
            for section in required_sections:
                if section not in parsed_json:
                    raise ValueError(f"Missing required section: {section}")
            
            return parsed_json
            
        except Exception as e:
            print(f"Error processing resume: {str(e)}")
            raise
    
    def parse_resume(self, resume_text: str) -> Optional[Dict[str, Any]]:
        """Parse a resume and return structured interests analysis."""
        try:
            return self._process_resume(resume_text)
        except Exception as e:
            print(f"Failed to parse resume: {str(e)}")
            return None


def main():
    """Example usage of ResumeLLMClient."""
    client = ResumeLLMClient()
    
    sample_resume = """
    John Doe
    john.doe@email.com
    
    EDUCATION
    University of Technology
    3rd Year Computer Science
    Relevant Coursework: Data Structures, Algorithms, Database Systems
    
    EXPERIENCE
    Software Engineering Intern - Tech Corp
    June 2023 - August 2023
    • Built microservices using Node.js and MongoDB
    • Implemented real-time data processing pipeline using Apache Kafka
    • Developed automated testing framework with Jest
    
    Full Stack Developer Intern - StartupCo
    Jan 2023 - April 2023
    • Created React components for dashboard visualization
    • Integrated REST APIs using Express.js
    • Implemented user authentication with OAuth
    
    PROJECTS
    Machine Learning Image Classifier
    • Implemented CNN using PyTorch for image classification
    • Achieved 95% accuracy on test dataset
    • Deployed model using Flask and Docker
    
    SKILLS
    Languages: Python, JavaScript, Java, SQL
    Frameworks: React, Node.js, Express, PyTorch
    Tools: Git, Docker, AWS, Kafka
    """
    
    result = client.parse_resume(sample_resume)
    if result:
        print("\nCareer Analysis:")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

