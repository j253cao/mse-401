# Degree Requirements Data

## Structure

- **node.json** — Tree of program requirements. NodeTypes: `program` (root), `group` (contains nodes), `choice` (contains courses). `RequiredCount` missing or "NA" = all required; `RequiredCount` = "1", "2", etc. = pick N from list (elective).
- **course.json** — Maps courses to NodeIDs. Format: `{ "course": "MATH 115", "credit": 0.5, "NodeIDs": "2025_CHE_1A, 2025_ME_1A" }`.
- **program_core_courses.json** — Generated. Required core courses per program per term. Excludes CSE, TE, PD_ADD, Ethics, COOP, specializations.

## Regenerating program_core_courses.json

From project root:

```bash
python scripts/extract_program_core_courses.py
```

Outputs to:
- `data/degree_requirements/program_core_courses.json`
- `frontend/src/data/program_core_courses.json`
