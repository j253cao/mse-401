from dataclasses import dataclass
from enum import Enum
import re
from typing import List, Optional, Union, Any, Dict

# Enums for type safety
class LogicalOperator(Enum):
    AND = "AND"
    OR = "OR"

class ComparisonOperator(Enum):
    GREATER_THAN = ">"
    GREATER_EQUAL = ">="
    LESS_THAN = "<"
    LESS_EQUAL = "<="
    EQUAL = "="
    MINIMUM = "minimum"

class ProgramType(Enum):
    HONOURS = "honours"
    REGULAR = "regular"
    MINOR = "minor"
    MAJOR = "major"
    SPECIALIZATION = "specialization"
    OPTION = "option"

class LevelComparison(Enum):
    AT_LEAST = "at_least"
    EXACTLY = "exactly"
    BEFORE = "before"
    AFTER = "after"

# Base class for all data structure types
@dataclass
class BaseDataStructure:
    type: str

# Grade requirement class
@dataclass
class GradeRequirement(BaseDataStructure):
    type: str = "grade_requirement"
    value: float
    operator: ComparisonOperator
    unit: str  # Usually "%", but could be "GPA", "letter", etc.

# Level requirement class
@dataclass
class LevelRequirement(BaseDataStructure):
    type: str = "level_requirement"
    level: str  # e.g., "2A", "3B", "4A"
    comparison: LevelComparison

# Program requirement class
@dataclass
class ProgramRequirement(BaseDataStructure):
    type: str = "program_requirement"
    program_name: str
    program_type: Optional[ProgramType] = None
    faculty: Optional[str] = None
    level_requirement: Optional[LevelRequirement] = None

# Course class
@dataclass
class Course(BaseDataStructure):
    type: str = "course"
    code: str
    name: Optional[str] = None
    grade_requirement: Optional[GradeRequirement] = None

# Prerequisite group class
@dataclass
class PrerequisiteGroup(BaseDataStructure):
    type: str = "prerequisite_group"
    courses: List['Course']
    operator: LogicalOperator
    quantity: Optional[int] = None  # For "one of", "two of", etc.

# Main prerequisites container
@dataclass
class Prerequisites(BaseDataStructure):
    type: str = "prerequisites"
    groups: List[Union['PrerequisiteGroup', 'Course']]
    program_requirements: List[ProgramRequirement]
    root_operator: LogicalOperator

# Union type for all possible prerequisite elements
PrerequisiteElement = Union[Course, PrerequisiteGroup]

# Input class for the LLM
@dataclass
class PrerequisiteParseInput:
    prerequisite_string: str
    course_code: Optional[str] = None  # Optional context about which course this is for
    additional_context: Optional[str] = None  # Any additional parsing hints

# Output class from the LLM
@dataclass
class PrerequisiteParseOutput:
    success: bool
    data: Optional[Prerequisites] = None
    error: Optional[str] = None
    confidence: Optional[float] = None  # Optional confidence score from 0-1

# Utility classes for validation and processing
@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]

@dataclass
class CourseValidationOptions:
    validate_course_codes: Optional[bool] = None
    allowed_faculties: Optional[List[str]] = None
    allowed_programs: Optional[List[str]] = None
    max_grade_value: Optional[float] = None
    min_grade_value: Optional[float] = None

# Type checking functions
def is_grade_requirement(obj: Any) -> bool:
    return (isinstance(obj, dict) and 
            obj.get('type') == "grade_requirement" and 
            isinstance(obj.get('value'), (int, float)) and
            obj.get('operator') in ComparisonOperator.__members__.values() and
            isinstance(obj.get('unit'), str))

def is_level_requirement(obj: Any) -> bool:
    return (isinstance(obj, dict) and 
            obj.get('type') == "level_requirement" and
            isinstance(obj.get('level'), str) and
            obj.get('comparison') in LevelComparison.__members__.values()
            )

def is_program_requirement(obj: Any) -> bool:
    return (isinstance(obj, dict) and 
            obj.get('type') == "program_requirement" and
            isinstance(obj.get('program_name'), str))

def is_course(obj: Any) -> bool:
    return (isinstance(obj, dict) and 
            obj.get('type') == "course" and
            isinstance(obj.get('code'), str))

def is_prerequisite_group(obj: Any) -> bool:
    return (isinstance(obj, dict) and 
            obj.get('type') == "prerequisite_group" and
            isinstance(obj.get('courses'), list) and
            obj.get('operator') in LogicalOperator.__members__.values())

def is_prerequisites(obj: Any) -> bool:
    return (isinstance(obj, dict) and 
            obj.get('type') == "prerequisites" and
            isinstance(obj.get('groups'), list) and
            isinstance(obj.get('program_requirements'), list) and
            obj.get('root_operator') in LogicalOperator.__members__.values())

class PrerequisiteUtils:
    """
    Utility functions for working with prerequisites
    """
    
    @staticmethod
    def validate(prereqs: Prerequisites, options: Optional[CourseValidationOptions] = None) -> ValidationResult:
        errors: List[str] = []
        warnings: List[str] = []
        
        # Validate structure
        if not is_prerequisites(prereqs.__dict__):
            errors.append("Invalid prerequisites structure")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        # Validate groups
        for group in prereqs.groups:
            if is_course(group.__dict__):
                course_validation = PrerequisiteUtils.validate_course(group, options)
                errors.extend(course_validation.errors)
                warnings.extend(course_validation.warnings)
            elif is_prerequisite_group(group.__dict__):
                group_validation = PrerequisiteUtils.validate_group(group, options)
                errors.extend(group_validation.errors)
                warnings.extend(group_validation.warnings)
            else:
                errors.append(f"Invalid group type: {getattr(group, 'type', 'unknown')}")
        
        # Validate program requirements
        for prog in prereqs.program_requirements:
            if not is_program_requirement(prog.__dict__):
                errors.append(f"Invalid program requirement: {prog}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    @staticmethod
    def validate_course(course: Course, options: Optional[CourseValidationOptions] = None) -> ValidationResult:
        errors: List[str] = []
        warnings: List[str] = []
        
        # Validate course code format (basic check)
        if not re.match(r'^[A-Z]{2,4}\s?\d{3}[A-Z]?$', course.code):
            warnings.append(f"Course code format may be invalid: {course.code}")
        
        # Validate grade requirement
        if course.grade_requirement:
            grade_val = course.grade_requirement.value
            max_grade = options.max_grade_value if options and options.max_grade_value else 100
            min_grade = options.min_grade_value if options and options.min_grade_value else 0
            
            if grade_val < min_grade or grade_val > max_grade:
                errors.append(f"Grade value out of range: {grade_val}")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    @staticmethod
    def validate_group(group: PrerequisiteGroup, options: Optional[CourseValidationOptions] = None) -> ValidationResult:
        errors: List[str] = []
        warnings: List[str] = []
        
        if len(group.courses) == 0:
            errors.append("Prerequisite group cannot be empty")
        
        # Validate quantity makes sense with operator
        if group.quantity is not None:
            if group.operator == LogicalOperator.AND:
                warnings.append("Quantity specified with AND operator - this may be unusual")
            if group.quantity > len(group.courses):
                errors.append(f"Quantity ({group.quantity}) exceeds number of courses ({len(group.courses)})")
        
        # Validate each course in the group
        for course in group.courses:
            course_validation = PrerequisiteUtils.validate_course(course, options)
            errors.extend(course_validation.errors)
            warnings.extend(course_validation.warnings)
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    @staticmethod
    def extract_course_codes(prereqs: Prerequisites) -> List[str]:
        codes: List[str] = []
        
        for group in prereqs.groups:
            if is_course(group.__dict__):
                codes.append(group.code)
            elif is_prerequisite_group(group.__dict__):
                codes.extend([c.code for c in group.courses])
        
        return list(set(codes))  # Remove duplicates
    
    @staticmethod
    def to_string(prereqs: Prerequisites) -> str:
        group_strings = []
        for group in prereqs.groups:
            if is_course(group.__dict__):
                group_strings.append(PrerequisiteUtils.course_to_string(group))
            elif is_prerequisite_group(group.__dict__):
                group_strings.append(PrerequisiteUtils.group_to_string(group))
        
        course_reqs = " and ".join(group_strings) if prereqs.root_operator == LogicalOperator.AND else " or ".join(group_strings)
        
        program_reqs = ""
        if prereqs.program_requirements:
            program_reqs = "; " + " and ".join([PrerequisiteUtils.program_to_string(p) for p in prereqs.program_requirements])
        
        return course_reqs + program_reqs
    
    @staticmethod
    def course_to_string(course: Course) -> str:
        result = course.code
        if course.name:
            result += f" ({course.name})"
        if course.grade_requirement:
            result += f" with {course.grade_requirement.operator.value} {course.grade_requirement.value}{course.grade_requirement.unit}"
        return result
    
    @staticmethod
    def group_to_string(group: PrerequisiteGroup) -> str:
        prefix = f"{group.quantity} of " if group.quantity else ""
        operator = " or " if group.operator == LogicalOperator.OR else " and "
        course_str = operator.join([PrerequisiteUtils.course_to_string(c) for c in group.courses])
        return f"{prefix}{course_str}"
    
    @staticmethod
    def program_to_string(prog: ProgramRequirement) -> str:
        result = ""
        if prog.program_type:
            result += f"{prog.program_type.value} "
        result += prog.program_name
        if prog.faculty:
            result += f" ({prog.faculty})"
        if prog.level_requirement:
            result += f", Level {prog.level_requirement.comparison.value} {prog.level_requirement.level}"
        return result

class PrerequisiteFactory:
    """
    Factory functions for creating prerequisite objects
    """
    
    @staticmethod
    def create_course(
        code: str,
        name: Optional[str] = None,
        grade_value: Optional[float] = None,
        grade_operator: Optional[ComparisonOperator] = None
    ) -> Course:
        grade_requirement = None
        if grade_value is not None:
            grade_requirement = GradeRequirement(
                value=grade_value,
                operator=grade_operator or ComparisonOperator.MINIMUM,
                unit="%"
            )
        
        return Course(
            code=code,
            name=name,
            grade_requirement=grade_requirement
        )
    
    @staticmethod
    def create_group(
        courses: List[Course],
        operator: LogicalOperator,
        quantity: Optional[int] = None
    ) -> PrerequisiteGroup:
        return PrerequisiteGroup(
            courses=courses,
            operator=operator,
            quantity=quantity
        )
    
    @staticmethod
    def create_program_requirement(
        program_name: str,
        program_type: Optional[ProgramType] = None,
        faculty: Optional[str] = None,
        level: Optional[str] = None,
        level_comparison: Optional[LevelComparison] = None
    ) -> ProgramRequirement:
        level_requirement = None
        if level:
            level_requirement = LevelRequirement(
                level=level,
                comparison=level_comparison or LevelComparison.AT_LEAST
            )
        
        return ProgramRequirement(
            program_name=program_name,
            program_type=program_type,
            faculty=faculty,
            level_requirement=level_requirement
        )
    
    @staticmethod
    def create_prerequisites(
        groups: List[Union[PrerequisiteGroup, Course]],
        program_requirements: Optional[List[ProgramRequirement]] = None,
        root_operator: LogicalOperator = LogicalOperator.AND
    ) -> Prerequisites:
        return Prerequisites(
            groups=groups,
            program_requirements=program_requirements or [],
            root_operator=root_operator
        )