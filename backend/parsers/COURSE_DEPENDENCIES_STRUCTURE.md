# Course Dependencies JSON Structure

This document explains the structure of `course_dependencies_2.json` and how each component works.

## Overall Structure

The file is a JSON object where each key is a **course code** (uppercase, e.g., `"MSE401"`), and each value contains three sections: **prerequisites**, **corequisites**, and **antirequisites**.

```json
{
  "COURSE_CODE": {
    "prerequisites": {
      "groups": [...],
      "program_requirements": [...],
      "root_operator": "AND"
    },
    "corequisites": {
      "groups": [...],
      "root_operator": "AND"
    },
    "antirequisites": {
      "courses": [...],
      "program_restrictions": [...]
    }
  }
}
```

---

## Prerequisites Section

Describes what courses/requirements must be completed **before** taking the course.

```json
"prerequisites": {
  "groups": [...],
  "program_requirements": [...],
  "root_operator": "AND"
}
```

### `groups`

- **Type**: Array of course/group objects
- **Purpose**: Lists course prerequisites (individual courses or OR groups)
- **Can be**: Empty array `[]` or array of objects

### `program_requirements`

- **Type**: Array of program requirement objects
- **Purpose**: Lists program-level requirements (enrollment, level requirements)
- **Can be**: Empty array `[]` or array of requirement objects

### `root_operator`

- **Value**: `"AND"` (all groups must be satisfied)
- **Purpose**: Defines how groups are combined

---

## Corequisites Section

Describes courses that must be taken **concurrently** (or already completed).

```json
"corequisites": {
  "groups": [...],
  "root_operator": "AND"
}
```

### `groups`

- **Type**: Array of course/group objects
- **Purpose**: Lists corequisite courses (must be taken at the same time or before)
- **Structure**: Same as prerequisite groups

### `root_operator`

- **Value**: `"AND"` (all groups must be satisfied)

---

## Antirequisites Section

Describes courses that **cannot** be taken if you've completed them, and program restrictions.

```json
"antirequisites": {
  "courses": [...],
  "program_restrictions": [...]
}
```

### `courses`

- **Type**: Array of course objects
- **Purpose**: Lists courses that block enrollment (if you've taken any of these, you cannot take this course)

### `program_restrictions`

- **Type**: Array of program restriction objects
- **Purpose**: Lists programs that cannot take this course

---

## Groups Structure

The `groups` array (in prerequisites and corequisites) contains two types of objects:

### 1. Single Course Entry

Used for individual required courses.

```json
{
  "type": "course",
  "code": "MSE302",
  "name": null,
  "grade_requirement": null
}
```

**Fields:**

- `type`: Always `"course"`
- `code`: Course code in uppercase (e.g., `"MSE302"`)
- `name`: Course name (usually `null`)
- `grade_requirement`: Minimum grade requirement (usually `null`)

### 2. Prerequisite Group (OR Relationship)

Used when **at least one** course from a list is required.

```json
{
  "type": "prerequisite_group",
  "courses": [
    {
      "type": "course",
      "code": "BIOL273",
      "name": null,
      "grade_requirement": null
    },
    {
      "type": "course",
      "code": "BME284",
      "name": null,
      "grade_requirement": null
    },
    {
      "type": "course",
      "code": "SYDE584",
      "name": null,
      "grade_requirement": null
    }
  ],
  "operator": "OR"
}
```

**Fields:**

- `type`: Always `"prerequisite_group"`
- `courses`: Array of course objects
- `operator`: Always `"OR"` (at least one of these courses)

---

## Multiple Groups (AND Between Groups)

When there are multiple groups, they are combined with AND logic.

**Example - BME550:**

```json
"prerequisites": {
  "groups": [
    {
      "type": "prerequisite_group",
      "courses": [
        {"type": "course", "code": "BME182", ...},
        {"type": "course", "code": "ME212", ...}
      ],
      "operator": "OR"
    },
    {
      "type": "course",
      "code": "ME219",
      ...
    }
  ],
  "root_operator": "AND"
}
```

**Meaning**: BME550 requires:

- (BME182 OR ME212) **AND**
- ME219

---

## Program Requirements Structure

Specifies who can take the course based on program enrollment and academic level.

```json
{
  "type": "program_requirement",
  "program_name": "Management Engineering",
  "program_type": null,
  "faculty": null,
  "level_requirement": {
    "type": "level_requirement",
    "level": "4A",
    "comparison": "at_least"
  }
}
```

**Fields:**

- `type`: Always `"program_requirement"`
- `program_name`: Name of the program (can be `null` if only level applies)
- `program_type`: Program type (usually `null`)
- `faculty`: Faculty name (usually `null`)
- `level_requirement`: Object describing academic level requirement (can be `null`)

### Level Requirement Object

```json
{
  "type": "level_requirement",
  "level": "4A",
  "comparison": "at_least"
}
```

**Fields:**

- `type`: Always `"level_requirement"`
- `level`: Academic level (e.g., `"1A"`, `"2B"`, `"4A"`)
- `comparison`: How to compare
  - `"exact"`: Must be exactly this level
  - `"at_least"`: Must be at this level or higher

---

## Program Restrictions Structure

Specifies who **cannot** take the course.

```json
{
  "type": "program_restriction",
  "program_name": "Accounting and Financial Management",
  "program_type": null,
  "faculty": null,
  "restriction_type": "not_open"
}
```

**Fields:**

- `type`: Always `"program_restriction"`
- `program_name`: Name of the restricted program
- `program_type`: Program type (usually `null`)
- `faculty`: Faculty name (usually `null`)
- `restriction_type`: Type of restriction (`"not_open"`)

---

## Antirequisite Course Structure

```json
{
  "type": "course",
  "code": "SYDE101",
  "name": null
}
```

**Fields:**

- `type`: Always `"course"`
- `code`: Course code in uppercase
- `name`: Course name (usually `null`)

---

## Complete Examples

### Example 1: Course with Prerequisites + Program Requirement

```json
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
        "program_type": null,
        "faculty": null,
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
```

**Interpretation**:

- Prerequisites: MSE302
- Must be: Management Engineering, level 4A or higher
- No corequisites
- No antirequisites

---

### Example 2: Course with Corequisites (OR Group)

```json
"CIVE230": {
  "prerequisites": {
    "groups": [
      {
        "type": "prerequisite_group",
        "courses": [
          {"type": "course", "code": "CIVE224", "name": null, "grade_requirement": null},
          {"type": "course", "code": "GEOE224", "name": null, "grade_requirement": null}
        ],
        "operator": "OR"
      }
    ],
    "program_requirements": [...],
    "root_operator": "AND"
  },
  "corequisites": {
    "groups": [
      {
        "type": "prerequisite_group",
        "courses": [
          {"type": "course", "code": "AE392", "name": null, "grade_requirement": null},
          {"type": "course", "code": "CIVE392", "name": null, "grade_requirement": null},
          {"type": "course", "code": "ENVE392", "name": null, "grade_requirement": null},
          {"type": "course", "code": "GEOE392", "name": null, "grade_requirement": null}
        ],
        "operator": "OR"
      }
    ],
    "root_operator": "AND"
  },
  "antirequisites": {
    "courses": [],
    "program_restrictions": []
  }
}
```

**Interpretation**:

- Prerequisites: CIVE224 OR GEOE224
- Corequisites: AE392 OR CIVE392 OR ENVE392 OR GEOE392 (take concurrently)
- No antirequisites

---

### Example 3: Course with Antirequisites

```json
"BME101": {
  "prerequisites": {
    "groups": [],
    "program_requirements": [
      {
        "type": "program_requirement",
        "program_name": "Biomedical Engineering",
        "program_type": null,
        "faculty": null,
        "level_requirement": {
          "type": "level_requirement",
          "level": "1A",
          "comparison": "exact"
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
    "courses": [
      {
        "type": "course",
        "code": "SYDE101",
        "name": null
      }
    ],
    "program_restrictions": []
  }
}
```

**Interpretation**:

- No course prerequisites
- Must be: Biomedical Engineering, exactly level 1A
- No corequisites
- Antirequisite: SYDE101 (cannot take BME101 if you've taken SYDE101)

---

### Example 4: Course with Program Restriction

```json
"MSE211": {
  "prerequisites": {
    "groups": [],
    "program_requirements": [],
    "root_operator": "AND"
  },
  "corequisites": {
    "groups": [],
    "root_operator": "AND"
  },
  "antirequisites": {
    "courses": [],
    "program_restrictions": [
      {
        "type": "program_restriction",
        "program_name": "Accounting and Financial Management",
        "program_type": null,
        "faculty": null,
        "restriction_type": "not_open"
      }
    ]
  }
}
```

**Interpretation**:

- No prerequisites or corequisites
- Not open to: Accounting and Financial Management students

---

## Summary

| Section          | Purpose                           | Key Fields                        |
| ---------------- | --------------------------------- | --------------------------------- |
| `prerequisites`  | Courses to complete **before**    | `groups`, `program_requirements`  |
| `corequisites`   | Courses to take **concurrently**  | `groups`                          |
| `antirequisites` | Courses that **block** enrollment | `courses`, `program_restrictions` |

### Logic Rules

1. **Groups** within a section: Combined with `root_operator` (usually AND)
2. **Courses within a group**: Combined with `operator` (usually OR)
3. **Antirequisite courses**: Any one blocks enrollment (implicit OR)
4. **All sections**: Must satisfy prerequisites AND corequisites AND not have antirequisites
