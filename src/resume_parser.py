import pdfplumber
import re
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from resume_llm_client import ResumeLLMClient

class ResumeParser:
    def __init__(self, output_file: str = "parsed_resumes.json"):
        self.llm_client = ResumeLLMClient()
        self.output_file = output_file
        self.parsed_resumes = self._load_existing_resumes()
    
    def _load_existing_resumes(self) -> List[Dict[str, Any]]:
        """Load existing parsed resumes if any."""
        try:
            if Path(self.output_file).exists():
                with open(self.output_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"Warning: Could not load existing resumes: {e}")
            return []
    
    def _save_resumes(self):
        """Save parsed resumes to JSON file."""
        try:
            with open(self.output_file, 'w') as f:
                json.dump(self.parsed_resumes, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save resumes: {e}")

    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove multiple newlines while preserving structure
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Ensure section headers are properly separated
        common_headers = ['EDUCATION', 'EXPERIENCE', 'SKILLS', 'PROJECTS', 'ACHIEVEMENTS', 'PUBLICATIONS']
        for header in common_headers:
            text = re.sub(f'([^\n]){header}([^\n])', f'\\1\n\n{header}\n', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    def _extract_text_from_page(self, page) -> str:
        """Extract and clean text from a single page."""
        try:
            # Extract text with layout preservation
            text = page.extract_text(x_tolerance=3, y_tolerance=3)
            
            # Get page dimensions
            height = page.height
            width = page.width
            
            # Extract text in columns if detected
            if width > height:  # Landscape orientation
                left_text = page.crop((0, 0, width/2, height)).extract_text()
                right_text = page.crop((width/2, 0, width, height)).extract_text()
                text = f"{left_text}\n\n{right_text}"
            
            return text
        except Exception as e:
            print(f"Warning: Error extracting text from page: {str(e)}")
            return ""

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text content from PDF file with improved handling."""
        all_text = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Process each page
                for page in pdf.pages:
                    text = self._extract_text_from_page(page)
                    if text:
                        all_text.append(text)
                
                # Join all pages
                full_text = '\n\n'.join(all_text)
                
                # Clean and normalize the text
                cleaned_text = self._clean_text(full_text)
                
                # Debug output
                print("\nExtracted Text Preview:")
                print("=" * 80)
                print(cleaned_text[:500] + "..." if len(cleaned_text) > 500 else cleaned_text)
                print("=" * 80)
                print(f"Total characters: {len(cleaned_text)}")
                print(f"Approximate tokens: {len(cleaned_text.split())}")
                
                return cleaned_text
                
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
            raise

    def parse(self, pdf_path: str) -> Optional[Dict[str, Any]]:
        """
        Parse a resume PDF and return structured information.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing parsed resume information,
            or None if processing failed
        """
        try:
            # Extract and clean text from PDF
            text = self.extract_text_from_pdf(pdf_path)
            
            # Validate text length
            if not text or len(text.split()) < 50:  # Arbitrary minimum length
                raise ValueError("Extracted text is too short or empty")
            
            # Use LLM client to parse the resume
            result = self.llm_client.parse_resume(text)
            
            if result:
                # Add metadata to the result
                result['file_name'] = Path(pdf_path).name
                result['file_path'] = str(Path(pdf_path).absolute())
                
                # Add to parsed resumes list
                self.parsed_resumes.append(result)
                
                # Save updated list
                self._save_resumes()
            
            return result
            
        except Exception as e:
            print(f"Error parsing resume: {str(e)}")
            return None

def main():
    import sys
    import json
    from pathlib import Path
    
    parser = ResumeParser()
    
    # Process each resume
    
    result = parser.parse("Finance Sample Resume.pdf")

    # Show all parsed resumes
    print("\nAll Parsed Resumes:")
    print(json.dumps(parser.parsed_resumes, indent=2))
    print(f"\nResults saved to: {parser.output_file}")

if __name__ == "__main__":
    main()
