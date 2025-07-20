import ijson
import json

input_path = 'raw-course-data.json'
output_path = 'course-database.json'
departments_output_path = 'departments.json'
courses_output_path = 'courses.json'

course_database = {}
departments = []
all_courses = []

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
        
        # Add to departments list if not already present
        if subject_name not in departments:
            departments.append(subject_name)
        
        # Add to all courses list
        all_courses.append({
            "courseCode": course["__catalogCourseId"],
            "title": course["title"],
            "department": subject_name,
            "pid": course["pid"]
        })

# Write the course database
with open(output_path, 'w') as outfile:
    json.dump(course_database, outfile, indent=2)

# Write departments list
with open(departments_output_path, 'w') as outfile:
    json.dump(departments, outfile, indent=2)

# Write all courses list
with open(courses_output_path, 'w') as outfile:
    json.dump(all_courses, outfile, indent=2)

print(f"Finished writing to {output_path}")
print(f"Finished writing departments to {departments_output_path}")
print(f"Finished writing courses to {courses_output_path}")
print(f"Total departments: {len(departments)}")
print(f"Total courses: {len(all_courses)}")
