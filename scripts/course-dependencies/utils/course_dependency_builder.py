import requests
import json
import os


def get_course_data(course_code, course_api_data):
    # Special rule: map MSCIxxxx to MSExxxx
    if course_code.startswith("MSCI"):
        mapped_code = "MSE" + course_code[4:]
        course_code = mapped_code
    return course_api_data[course_code].get('api_data')
