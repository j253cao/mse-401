import requests

API = "https://uwaterloocm.kuali.co/api/v1/catalog/course/663290e835aff7001cc62323/{pid}"

def get_api_url(pid):
    return API.format(pid=pid)

def get_course_data(pid):
    url = get_api_url(pid)
    response = requests.get(url)
    return response.json() 