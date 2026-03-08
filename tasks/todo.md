# Course Code Search — Implementation Plan

## Goal

Allow users to search directly for courses by course code on the Explore Courses page. If the query looks like a course code or contains 3+ consecutive numbers, return matching courses without semantic search.

---

## Requirements

1. **Course code exact match**: If the user's query looks like a course code (e.g. `MSE446`, `MSE 446`), remove whitespace, normalize, and return the exact matching course(s).

2. **Number sequence match**: If the user searches for 3 or more consecutive digits (e.g. `446`, `123`, `230`), return all courses whose course code contains that number sequence.

3. **Response shape**: Results must match the existing recommend response format so the frontend can display them without changes.

---

## Architecture

**Entry point**: The Explore page search bar calls `api.recommend([search], filters)` → `POST /recommend`.

**Strategy**: Add a pre-check in the `/recommend` flow. Before calling `get_recommendations()` (semantic search), detect if the query qualifies for direct course lookup. If yes, run the lookup and return those courses in the same response shape. Otherwise, fall through to semantic search.

No frontend changes needed if the backend response format stays identical.

---

## Implementation Checklist

### 1. Backend: Course lookup helper

- [ ] **Create `lookup_courses_by_code()` in `backend/api/main.py`** (or a small `course_lookup.py` module)
  - Input: normalized query string (whitespace stripped, uppercase)
  - Load from `course-api-new-data.json` (reuse existing path helpers)
  - Build a canonical code lookup: for each entry, `canonical_code = subjectCode + catalogNumber` (match `courses_search` logic)
  - Return list of course dicts with: `course_code`, `title`, `description`, plus placeholders for `score`, `prereqs`, `coreqs`, `antireqs`
  - Apply ENGINEERING_DEPARTMENTS filter if we want to keep explore restricted to engineering (or make configurable)

### 2. Backend: Query detection helpers

- [ ] **Implement `_is_course_code_query(query: str) -> bool`**
  - Pattern: `[A-Z]{2,}\s*[0-9]{3}[A-Z]*` (letters, optional space, 3+ digits, optional letter suffix)
  - After normalizing: match against `COMPLETE_COURSE_CODE_REGEX` from `course_dependency_parser` or equivalent
  - Examples: `MSE446`, `MSE 446`, `CS 135`, `ECE240` → True

- [ ] **Implement `_has_three_plus_consecutive_digits(query: str) -> bool`**
  - Regex: `\d{3,}` (3 or more consecutive digits)
  - Examples: `446`, `123`, `230` → True; `12`, `4` → False

### 3. Backend: Lookup logic

- [ ] **Exact course code lookup**
  - When `_is_course_code_query(query)` is True:
    - Normalize: `query.strip().upper().replace(' ', '')`
    - Direct key lookup in course JSON (keys are canonical: `MSE446`, `AE392`, etc.)
    - Also check `canonical_code` in case some keys differ
    - Return 1 or more courses (theoretically duplicate offerings; in practice 1 per code)

- [ ] **Number sequence lookup**
  - When `_has_three_plus_consecutive_digits(query)` is True:
    - Extract the 3+ digit sequence(s) via regex
    - Iterate over course data; for each course, `canonical_code` contains the digits?
    - e.g. query `446` → MSE446, ECE446, etc.
    - Cap results (e.g. limit=50) to avoid huge lists
    - Apply ENGINEERING_DEPARTMENTS filter for explore page consistency

### 4. Backend: Integrate into `/recommend`

- [ ] **Modify `recommend()` in `backend/api/main.py`**
  - For each query in `request.queries`:
    1. Normalize: `q_clean = query.strip().upper().replace(' ', '')`
    2. If `_is_course_code_query(query)` → call `lookup_courses_by_code(q_clean)` (exact match)
    3. Else if `_has_three_plus_consecutive_digits(query)` → call `lookup_courses_by_number_sequence(query)`
    4. If either lookup returns non-empty results → use those, skip semantic search for that query
    5. Otherwise → call `get_recommendations()` as today
  - Format lookup results to match existing response: `rank`, `course_code`, `title`, `description`, `score` (e.g. 1.0), `prereqs`, `coreqs`, `antireqs`
  - Enrich with `_enrich_course_with_programs()` and `load_course_dependencies()` so UI gets same fields
  - Ensure `formatted[q]` structure unchanged for the frontend

### 5. Edge cases

- [ ] **Priority**: If both patterns match (e.g. user types `MSE446`), prefer exact course code lookup over number-only lookup
- [ ] **Empty results**: If lookup returns [], fall through to semantic search (existing behavior)
- [ ] **Multiple queries**: Handle per-query; one can be course lookup, another semantic
- [ ] **Case/whitespace**: Always normalize before matching and lookup

---

## Files to Modify / Create

| File | Change |
|------|--------|
| `backend/api/main.py` | Add detection helpers, lookup functions, and integration in `recommend()` |
| (Optional) `backend/api/course_lookup.py` | Extract lookup logic if `main.py` gets too large |

---

## Verification

- [x] Search `MSE446` → returns MSE446 only
- [x] Search `MSE 446` (with space) → same result
- [x] Search `446` → returns courses with 446 in code (e.g. MSE446)
- [x] Search `123` → returns GEOE123, ENVE123, AE123, etc.
- [x] Search `machine learning` → unchanged; uses semantic search
- [x] Search `12` (2 digits) → uses semantic search, not number lookup
- [x] Response shape matches existing recommend format; no frontend changes

**Implementation complete.** Run `python scripts/test_course_lookup.py` to verify (backend must be running).

---

## Notes

- Reuse `COMPLETE_COURSE_CODE_REGEX` from `backend/parsers/course_dependency_parser.py` for detection if convenient
- Course data: `course-api-new-data.json` keys are canonical (e.g. `MSE446`); `subjectCode` + `catalogNumber` yields same
- ENGINEERING_DEPARTMENTS filter: align with `/courses/search` and explore page expectations
