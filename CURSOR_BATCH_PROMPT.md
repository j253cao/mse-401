# Cursor Batch Processing Prompt

Parse the course-html.json file which contains a mapping of course codes to their prerequisite HTML.

## Expected JSON Format for Each Course:
```json
{
  "type": "all|one",
  "rules": [
    {
      "type": "course_requirement",
      "code": "CS135",
      "description": "CS135 - Introduction to Computer Science (0.50)"
    },
    {
      "type": "program_requirement", 
      "description": "Enrolled in: Computer Science"
    }
  ]
}
```

## Instructions:
1. Parse the course-html.json file
2. For each course code and its HTML, extract prerequisite information
3. Identify course codes, titles, and credits where available
4. Handle nested structures like "Complete all of the following" and "Complete 1 of the following"
5. Extract program requirements like "Enrolled in" statements
6. Return a JSON object mapping course codes to their parsed prerequisite structures

## Expected Output Format:
```json
{
  "MSE436": {
    "type": "all",
    "rules": [...]
  },
  "CS135": {
    "type": "one", 
    "rules": [...]
  }
}
```

## File Processing:
- Process the course-html.json file
- Return the complete mapping of course codes to parsed prerequisite structures
- Handle all course codes in the file
