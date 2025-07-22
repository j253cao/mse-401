# MSE-401 Course Dependency System

A system for parsing and managing course dependencies from the University of Waterloo course catalog.

## Project Structure

```
MSE-401/
├── data/                          # Data files
│   ├── courses.json              # All courses with PIDs
│   ├── departments.json          # List of departments
│   ├── course-database.json      # Full course database
│   ├── raw-course-data.json      # Raw API data
│   └── course-dependencies.json  # Generated dependencies (output)
├── scripts/
│   └── course-dependencies/      # Course dependency processing scripts
│       ├── main.py               # Main batch processing script
│       ├── test_single_course.py # Single course test script
│       └── utils/                # Utility modules
│           ├── data_loader.py        # Data loading utilities
│           ├── dependency_parser.py  # Dependency parsing logic
│           ├── html_extractors.py    # HTML content extraction
│           ├── validators.py         # Course code validation
│           ├── interfaces.py         # Type definitions
│           └── course_dependency_builder.py # API utilities
├── course-parser.py              # Course data parser
└── requirements.txt              # Python dependencies
```

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Parse course data (if needed):

```bash
python course-parser.py
```

## Usage

### Test a single course:

```bash
cd scripts/course-dependencies
python test_single_course.py
```

### Process all courses:

```bash
cd scripts/course-dependencies
python main.py
```

## Features

- **Rate Limiting**: 1 request every 1.5 seconds to respect API limits
- **Checkpoint System**: Resume processing from where you left off
- **Comprehensive Parsing**: Handles prerequisites, corequisites, and antirequisites
- **Multiple Formats**: Supports course codes with letter suffixes (W, L, R, etc.)
- **Validation**: Validates course codes against known course database
- **Error Handling**: Continues processing even if individual courses fail

## Output

The system generates `course-dependencies.json` in the `data/` directory containing structured dependency information for all courses.

## Running the Backend (FastAPI)

1. Open a terminal in the project root.
2. Run the following commands:

```sh
cd scripts
cd llm-course-parser
uvicorn vectorizer.api_backend:app --reload --host 0.0.0.0 --port 8000
```

- The backend will be available at http://localhost:8000
- Make sure you have all dependencies installed (see requirements.txt).
