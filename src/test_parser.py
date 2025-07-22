from resume_parser import ResumeParser
import sys
import os
from pathlib import Path

def main():
    # Get all PDF files in the current directory
    current_dir = Path('.')
    pdf_files = list(current_dir.glob('*.pdf'))
    
    if not pdf_files:
        print("Error: No PDF files found in the current directory.")
        print("Please place your resume PDF in the same directory as this script.")
        sys.exit(1)
    
    # If there's only one PDF, use it automatically
    if len(pdf_files) == 1:
        resume_path = pdf_files[0]
    else:
        # If there are multiple PDFs, let the user choose
        print("\nFound multiple PDF files:")
        for i, pdf in enumerate(pdf_files, 1):
            print(f"{i}. {pdf.name}")
        
        while True:
            try:
                choice = input("\nEnter the number of your resume PDF: ")
                index = int(choice) - 1
                if 0 <= index < len(pdf_files):
                    resume_path = pdf_files[index]
                    break
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
    
    print(f"\nParsing resume: {resume_path}")
    parser = ResumeParser()
    
    try:
        resume = parser.parse(str(resume_path))
        
        # Print parsed information in a structured format
        print("\n=== Basic Information ===")
        print(f"Name: {resume.name}")
        print(f"Email: {resume.email}")
        print(f"Phone: {resume.phone}")
        
        print("\n=== Education ===")
        if resume.education:
            for edu in resume.education:
                print(f"\nInstitution: {edu.institution}")
                print(f"Degree: {edu.degree}")
                print(f"Major: {edu.major}")
                if edu.graduation_date:
                    print(f"Graduation Date: {edu.graduation_date.strftime('%B %Y')}")
                if edu.gpa:
                    print(f"GPA: {edu.gpa}")
        else:
            print("No education information found")
        
        print("\n=== Experience ===")
        if resume.experience:
            for exp in resume.experience:
                print(f"\nCompany: {exp.company}")
                print(f"Title: {exp.title}")
                if exp.start_date:
                    start = exp.start_date.strftime('%B %Y')
                    end = exp.end_date.strftime('%B %Y') if exp.end_date else "Present"
                    print(f"Duration: {start} - {end}")
                if exp.description:
                    print("Description:")
                    for desc in exp.description:
                        print(f"  • {desc}")
        else:
            print("No experience information found")
        
        print("\n=== Skills ===")
        if resume.skills:
            for skill in resume.skills:
                print(f"\n{skill.category}:")
                print(f"  {', '.join(skill.skills)}")
        else:
            print("No skills information found")
                
    except FileNotFoundError:
        print(f"Error: Could not find the resume file: {resume_path}")
    except Exception as e:
        print(f"Error parsing resume: {str(e)}")
        raise

if __name__ == "__main__":
    main() 