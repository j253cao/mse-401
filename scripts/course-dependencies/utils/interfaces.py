from typing import List, Union, Literal, Optional, TypedDict

class CourseLevel(TypedDict):
    name: str
    id: str

class SubjectCode(TypedDict):
    name: str
    description: str
    id: str

class CourseRequirement(TypedDict):
    type: Literal["course_requirement"]
    code: str
    description: str
    grade_requirement: Optional[str]

class ProgramRequirement(TypedDict):
    type: Literal["program_requirement"]
    description: str

class CourseDependency(TypedDict):
    prerequisite: Optional[Union[CourseRequirement, ProgramRequirement]]
    corequisite: Optional[Union[CourseRequirement, ProgramRequirement]]
    antirequisite: Optional[Union[CourseRequirement, ProgramRequirement]]
