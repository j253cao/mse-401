"""
UW Transcript Parser

Parses University of Waterloo unofficial transcripts from PDF files.
Extracts student ID, program name, and term-by-term course history.

Usage:
    from backend.parsers.transcript_parser import parse_transcript_pdf, term_id_to_name
    
    result = parse_transcript_pdf("path/to/transcript.pdf")
    print(result.student_number)
    print(result.program_name)
    for term in result.term_summaries:
        print(f"{term_id_to_name(term.term_id)} ({term.level}): {term.courses}")
"""

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class TermSummary:
    """Summary of courses taken in a single term."""
    # Term IDs are numbers of the form 1189 (Fall 2018)
    # Format: (year - 1900) * 10 + season_id (1=Winter, 5=Spring, 9=Fall)
    term_id: int
    # Academic levels like 1A, 2B, 5C (delayed graduation)
    level: str
    # Course codes like "cs145", "stat920", "pd1", "china120r"
    courses: List[str] = field(default_factory=list)


@dataclass
class TranscriptSummary:
    """Parsed transcript data."""
    student_number: int
    program_name: str
    term_summaries: List[TermSummary]


class TranscriptParseError(Exception):
    """Raised when transcript parsing fails."""
    pass


# Regex patterns for parsing transcript text
COURSE_PATTERN = re.compile(
    r'^([A-Z]{2,})\s+(\d{3}[A-Z]?)\s+([A-Z][A-Za-z0-9\s,:\-&/]+?)(?:\s+(\d\.\d{2})\s+(\d\.\d{2})\s+(\d+))?$',
    re.MULTILINE
)
CREDIT_PATTERN = re.compile(r'\d\.\d{2}')
LEVEL_PATTERN = re.compile(r'Level:\s+(\w{2,})')
STUDENT_ID_PATTERN = re.compile(r'Student ID:\s+(\d+)')
TERM_PATTERN = re.compile(r'^\s*(Fall|Winter|Spring)\s+(\d{4})\s*$', re.MULTILINE)


def term_season_year_to_id(season: str, year: str) -> int:
    """
    Convert term season and year to Quest term ID.
    
    Args:
        season: "Fall", "Winter", or "Spring"
        year: Year as string, e.g. "2019"
    
    Returns:
        Quest term ID (e.g., 1189 for Fall 2018)
    """
    season_to_month = {
        'Fall': 9,
        'Spring': 5,
        'Winter': 1,
    }
    
    if season not in season_to_month:
        raise TranscriptParseError(f'Invalid season: {season}')
    
    try:
        year_int = int(year)
    except ValueError:
        raise TranscriptParseError(f'Invalid year: {year}')
    
    return (year_int - 1900) * 10 + season_to_month[season]


def term_id_to_name(term_id: int) -> str:
    """
    Convert Quest term ID back to human-readable name.
    
    Args:
        term_id: Quest term ID (e.g., 1189)
    
    Returns:
        Human-readable term name (e.g., "Fall 2018")
    """
    year = (term_id // 10) + 1900
    season_id = term_id % 10
    
    month_to_season = {
        1: 'Winter',
        5: 'Spring',
        9: 'Fall',
    }
    
    season = month_to_season.get(season_id, 'Unknown')
    return f'{season} {year}'


def _is_transfer_credit(course_line: str) -> bool:
    """Check if a course line represents a transfer credit (AP/IB/etc)."""
    matches = CREDIT_PATTERN.findall(course_line)
    return len(matches) == 1


def _extract_program_name(text: str) -> str:
    """Extract program name from transcript text."""
    start = text.rfind('Program:')
    if start == -1:
        raise TranscriptParseError('Program name not found')
    
    start += 8  # Skip "Program:"
    
    for end in range(start, len(text)):
        if text[end] in (',', '\n'):
            return text[start:end].strip()
    
    raise TranscriptParseError('Unexpected end of transcript while parsing program name')


def _extract_term_summaries(text: str) -> List[TermSummary]:
    """Extract term-by-term course history from transcript text."""
    terms = list(TERM_PATTERN.finditer(text))
    levels = list(LEVEL_PATTERN.finditer(text))
    courses = list(COURSE_PATTERN.finditer(text))
    
    if len(terms) != len(levels):
        raise TranscriptParseError(
            f'Mismatch: found {len(terms)} terms but {len(levels)} academic levels'
        )
    
    history: List[TermSummary] = []
    course_idx = 0
    
    for i, (term_match, level_match) in enumerate(zip(terms, levels)):
        season = term_match.group(1)
        year = term_match.group(2)
        
        term_id = term_season_year_to_id(season, year)
        level = level_match.group(1)
        
        term_summary = TermSummary(term_id=term_id, level=level)
        
        if i < len(terms) - 1:
            next_term_start = terms[i + 1].start()
        else:
            next_term_start = len(text)
        
        while course_idx < len(courses) and courses[course_idx].start() < next_term_start:
            course_match = courses[course_idx]
            course_line = course_match.group(0)
            
            if _is_transfer_credit(course_line):
                course_idx += 1
                continue
            
            department = course_match.group(1)
            number = course_match.group(2)
            course_code = f'{department}{number}'.upper()
            
            term_summary.courses.append(course_code)
            course_idx += 1
        
        history.append(term_summary)
    
    return history


def parse_transcript(text: str) -> TranscriptSummary:
    """
    Parse a UW unofficial transcript.
    
    Args:
        text: Plain text extracted from a transcript PDF
    
    Returns:
        TranscriptSummary containing student info and course history
    """
    student_match = STUDENT_ID_PATTERN.search(text)
    if not student_match:
        raise TranscriptParseError('Student ID not found')
    
    try:
        student_number = int(student_match.group(1))
    except ValueError:
        raise TranscriptParseError(f'Invalid student number: {student_match.group(1)}')
    
    program_name = _extract_program_name(text)
    term_summaries = _extract_term_summaries(text)
    
    return TranscriptSummary(
        student_number=student_number,
        program_name=program_name,
        term_summaries=term_summaries,
    )


def parse_transcript_pdf(pdf_path: str) -> TranscriptSummary:
    """
    Parse a UW unofficial transcript PDF file.
    
    Args:
        pdf_path: Path to the transcript PDF file
    
    Returns:
        TranscriptSummary containing student info and course history
    """
    text = None
    
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
    except ImportError:
        pass
    
    if text is None:
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            text = '\n'.join(page.extract_text() or '' for page in reader.pages)
        except ImportError:
            pass
    
    if text is None:
        raise ImportError(
            'No PDF library available. Install pdfplumber or pypdf:\n'
            '  pip install pdfplumber\n'
            '  # or\n'
            '  pip install pypdf'
        )
    
    return parse_transcript(text)


def parse_transcript_bytes(pdf_bytes: bytes) -> TranscriptSummary:
    """
    Parse a UW unofficial transcript from raw PDF bytes.
    
    Args:
        pdf_bytes: Raw bytes of the PDF file
    
    Returns:
        TranscriptSummary containing student info and course history
    """
    import io
    text = None
    
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
    except ImportError:
        pass
    
    if text is None:
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(pdf_bytes))
            text = '\n'.join(page.extract_text() or '' for page in reader.pages)
        except ImportError:
            pass
    
    if text is None:
        raise ImportError(
            'No PDF library available. Install pdfplumber or pypdf:\n'
            '  pip install pdfplumber\n'
            '  # or\n'
            '  pip install pypdf'
        )
    
    return parse_transcript(text)


def get_all_courses(result: TranscriptSummary) -> list:
    """Extract all course codes from a transcript as a flat list."""
    courses = []
    for term in result.term_summaries:
        courses.extend(term.courses)
    return courses


def print_transcript_summary(result: TranscriptSummary) -> None:
    """Print a formatted summary of the parsed transcript."""
    print(f'Student Number: {result.student_number}')
    print(f'Program: {result.program_name}')
    print(f'\nCourse History ({len(result.term_summaries)} terms):')
    for term in result.term_summaries:
        term_name = term_id_to_name(term.term_id)
        print(f'  {term_name} (Level {term.level}):')
        if term.courses:
            print(f'    {", ".join(term.courses)}')
        else:
            print('    (no courses)')


if __name__ == '__main__':
    from pathlib import Path
    
    test_dir = Path(__file__).parent.parent.parent / 'tests' / 'test_data' / 'transcripts'
    test_pdfs = list(test_dir.glob('*.pdf')) if test_dir.exists() else []
    
    if test_pdfs:
        pdf_path = test_pdfs[0]
        print(f'Parsing: {pdf_path}\n')
        result = parse_transcript_pdf(str(pdf_path))
        print_transcript_summary(result)
        print(f'\nAll courses taken: {get_all_courses(result)}')
    else:
        print('No test PDFs found. Usage:')
        print('  from backend.parsers.transcript_parser import parse_transcript_pdf')
        print('  result = parse_transcript_pdf("your_transcript.pdf")')

