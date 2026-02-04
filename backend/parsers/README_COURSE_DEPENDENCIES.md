# Course Dependency Parser

This module parses course prerequisites, corequisites, and antirequisites from `course-api-data.json` and generates structured dependency data.

## Overview

The parsing workflow consists of two steps:

### Step 1: `course_dependency_parser.py`

Extracts raw prerequisite/corequisite/antirequisite data from course HTML and outputs to `course_expanded.json`.

1. Loads course data from `data/courses/course-api-data.json`
2. Filters courses by department (default: engineering departments)
3. Extracts prerequisite HTML/text from each course
4. Parses prerequisites into an expanded format with:
   - `courses[]` - Course metadata with prereq/coreq/antireq text
   - `prereqs[]` - Individual prerequisite relationships (with `is_coreq` flag)
   - `antireqs[]` - Individual antirequisite relationships
5. Saves results to `data/dependencies/course_expanded.json`
6. Supports checkpoint/resume functionality for long-running jobs

### Step 2: `build_course_dependencies.py`

Converts the expanded format into a structured dependency format.

1. Loads `course_expanded.json`
2. Groups prerequisites and corequisites (OR/AND relationships)
3. Extracts program requirements (enrollment, level requirements)
4. Extracts program restrictions
5. Saves results to `data/dependencies/course_dependencies_2.json`

## Prerequisites

1. Install dependencies:

   ```bash
   pip install -r backend/requirements.txt
   ```

2. (Optional) Set up virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On macOS/Linux
   pip install -r backend/requirements.txt
   ```

## Usage

### Step 1: Generate Expanded Data

```bash
python backend/parsers/course_dependency_parser.py
```

**Output**: `data/dependencies/course_expanded.json`

### Step 2: Build Structured Dependencies

```bash
python backend/parsers/build_course_dependencies.py
```

**Output**: `data/dependencies/course_dependencies_2.json`

### Full Workflow

```bash
# Delete checkpoint to start fresh (optional)
rm -f data/dependencies/checkpoint.json

# Run both steps
python backend/parsers/course_dependency_parser.py
python backend/parsers/build_course_dependencies.py
```

## Engineering Departments

By default, the parser processes these engineering departments:

- BME (Biomedical Engineering)
- CHE (Chemical Engineering)
- CIVE (Civil Engineering)
- ECE (Electrical and Computer Engineering)
- ENVE (Environmental Engineering)
- GEOE (Geological Engineering)
- ME (Mechanical Engineering)
- MTE (Mechatronics Engineering)
- MSE (Management Science and Engineering)
- NE (Nanotechnology Engineering)
- SE (Software Engineering)
- SYDE (Systems Design Engineering)

## Output Files

### `course_expanded.json` (Intermediate)

```json
{
  "courses": [
    {
      "code": "mse401",
      "name": "Systems Models and Simulation",
      "prereqs": "Completed MSE302...",
      "coreqs": "",
      "antireqs": ""
    }
  ],
  "prereqs": [
    { "course_code": "mse401", "prereq_code": "mse302", "is_coreq": false }
  ],
  "antireqs": [{ "course_code": "bme101", "antireq_code": "syde101" }]
}
```

### `course_dependencies_2.json` (Final)

```json
{
  "MSE401": {
    "prerequisites": {
      "groups": [
        {
          "type": "course",
          "code": "MSE302",
          "name": null,
          "grade_requirement": null
        }
      ],
      "program_requirements": [
        {
          "type": "program_requirement",
          "program_name": "Management Engineering",
          "level_requirement": {
            "type": "level_requirement",
            "level": "4A",
            "comparison": "at_least"
          }
        }
      ],
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
```

See `COURSE_DEPENDENCIES_STRUCTURE.md` for detailed structure documentation.

## Checkpoint/Resume

The `course_dependency_parser.py` script supports checkpointing:

- Saves progress every 10 courses (configurable)
- Creates checkpoint at `data/dependencies/checkpoint.json`
- Resumes from last checkpoint when run again

To start fresh:

```bash
rm data/dependencies/checkpoint.json
```

## Customization

### Change Departments

Edit the `departments` list in `course_dependency_parser.py` `main()`:

```python
departments = ['BME', 'CHE', 'CIVE', 'ECE', ...]  # Or None for all
```

### Change Output Files

- `course_dependency_parser.py`: Edit `output_path` in `main()`
- `build_course_dependencies.py`: Edit `output_path` in `main()`

## Error Handling

- Failed courses are logged to `data/dependencies/error_log.json`
- Failed courses still get entries with empty prerequisites
- Scripts continue processing even if individual courses fail

## Notes

- Processing all engineering courses takes a few minutes
- The parsing may not be 100% accurate - review output and fix manually if needed
- The `course_dependencies.json` file contains legacy LLM-parsed data (kept for reference)
- The `course_dependencies_2.json` file contains the new structured data
