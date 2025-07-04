import ijson
import json

input_path = 'raw-course-data.json'
output_path = 'course-database.json'

course_database = {}

with open(input_path, 'r') as infile:
    parser = ijson.items(infile, 'item')  # stream each object in the array

    for course in parser:
        subject_name = course["subjectCode"]["name"]
        course_details = {
            "courseCode": course["__catalogCourseId"],
            "courseLevel": course["courseLevel"],
            "dateStart": course["dateStart"],
            "pid": course["pid"],
            "id": course["id"],
            "title": course["title"],
            "subjectCode": course["subjectCode"],
            "score": course["_score"]
        }

        # Append to the list for this subjectCode.name
        if subject_name not in course_database:
            course_database[subject_name] = []
        course_database[subject_name].append(course_details)

# Write the entire result to file at once (only at the end)
with open(output_path, 'w') as outfile:
    json.dump(course_database, outfile, indent=2)

print(f"Finished writing to {output_path}")
