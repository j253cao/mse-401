# Cursor Batch Processing Prompt

Parse the course-api-data.json file which contains a mapping of course codes to their complete API data including prerequisites, corequisites, and antirequisites.

## Expected JSON Format for Each Course:
```json
{
  "prerequisite": {
    "type": "all|one_of",
    "rules": [
      {
        "type": "course_requirement",
        "code": "CS135",
        "description": "CS135 - Introduction to Computer Science (0.50)"
      },
      {
        "type": "program_requirement", 
        "description": "H-Computer Science"
      }
    ]
  },
  "corequisite": {
    "type": "one_of",
    "rules": [...]
  },
  "antirequisite": {
    "type": "all",
    "rules": [...]
  }
}
```

## Instructions:
1. Parse the course-api-data.json file
2. For each course code and its API data, extract prerequisite, corequisite, and antirequisite information from the api_data field
3. Identify course codes, titles, and credits where available
4. Handle nested structures like "Complete all of the following" and "Complete 1 of the following"
5. Extract program requirements like "Enrolled in" statements
6. Group program requirements into "one_of" structures (since you can only be in one program)
7. Use only "one_of" or "all" as outer types
8. Return a JSON object mapping course codes to their parsed requirement structures

## Expected Output Format:
```json
{
  "MSE436": {
    "prerequisite": {
      "type": "one_of",
      "rules": [...]
    },
    "corequisite": null,
    "antirequisite": null
  }
}
```

## File Processing:
- Process the course-api-data.json file
- Extract requirement data from the api_data field for each course
- Return the complete mapping of course codes to parsed requirement structures
- Handle all course codes in the file
- Follow the interface structure with prerequisite, corequisite, and antirequisite fields
