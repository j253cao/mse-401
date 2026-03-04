# Feature Plan: Cold Start Experience for First-Year Students

## Overview

- **Objective**: Solve the cold start problem—when first-year students have no resume, transcript, or search query, provide an immediate, valuable experience that jumpstarts their course exploration.
- **Users**: First-year engineering students (1A, 1B) and any new user with minimal profile data.
- **Success Criteria**:
  - Users see relevant courses without typing a search query or uploading a resume
  - First-time visitors can explore and discover courses within seconds
  - Experience feels personalized when program + incoming level are set (Profile)
  - Reduces bounce rate and increases engagement on the Recommendation page

---

## Problem Statement

**Current state:**
- **Search tab**: Empty until user types a query → blank state with "Try searching for topics like 'machine learning'"
- **Recommended tab**: Empty until resume upload → "No Recommendations Yet" with CTA to upload resume
- **Random Course**: Single random course in sidebar—helpful but not enough to "jumpstart" exploration

**Cold start**: First-year students typically have:
- No resume or minimal work experience
- No transcript or few completed courses
- May not know what to search for
- Need guidance to discover electives, options, and interesting courses

---

## Scope

### Included

- **Explore / Discovery section** on Recommendation page that shows courses without requiring search or resume
- **High-value courses** (primary feature): Courses that keep options open—quantitatively ranked by:
  - **prereq_outdegree**: How many courses list this as a prerequisite (common prereq = unlocks many paths)
  - **minor_count**: How many options/minors include this course (contributes to many pathways)
  - **global_weight**: Already computed in `weights.py`—combines these with depth
- **Topic-based discovery** (secondary): Clickable categories derived **systematically** from curriculum data—option and minor names from `all_options.json` and `all_programs.json` (e.g., "Artificial Intelligence", "Entrepreneurship", "Environmental Engineering")
- **First-year friendly filter**: Restrict to 100-level courses when `incomingLevel` is 1A or 1B
- **Backend endpoint** to serve explore courses (no query required)

### Excluded (for now)

- **Program-aware suggestions** (e.g., "Electives popular in SYDE")—we have no popularity, engagement, or enrollment data to support this. Defer until such data exists.
- Full onboarding wizard
- Personalized ML-based cold start
- Gamification or progress tracking

### Constraints

- Must work with existing data (no new data pipelines)
- Use existing API patterns and `RecommendationsContext`
- No database—data from JSON files and embeddings

---

## Design

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  RecommendationPage                                             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  NEW: "Explore" / "Get Started" section                      ││
│  │  - "Courses that keep options open" (high-value by weight)   ││
│  │  - Topic chips (option/minor names: AI, Entrepreneurship…)   ││
│  │  - First-year filter (100-level when 1A/1B)                  ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ Search Tab   │  │ Recommended  │  │ Random Course (sidebar) │ │
│  └──────────────┘  └──────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Backend: NEW /explore endpoint                                  │
│  - GET /explore?program=SYDE&level=1A&topics=ml,design           │
│  - Returns curated courses from pre-defined queries + filters    │
│  - Uses existing get_recommendations() with topic queries         │
└─────────────────────────────────────────────────────────────────┘
```

### Data Model

- **High-value courses**: Use existing `global_weight` from recommender pipeline. Courses with high weight = common prereqs and/or appear in many options/minors. No new data needed.
- **Topic categories**: Derived from `all_options.json` and `all_programs.json`—option/minor names are curriculum-defined pathways (e.g., "Artificial Intelligence", "Entrepreneurship", "Environmental Engineering"). Not arbitrary; they reflect actual degree structure. For each option/minor name, we can either:
  - Use the name as a search query (e.g., "Artificial Intelligence" → query), or
  - Return courses that appear in that option/minor's course lists (direct lookup)
- **First-year filter**: Restrict to 100-level courses (catalogNumber starts with 1) when `incomingLevel` is 1A or 1B

### API Design

**Primary: `GET /explore-high-value`** (no query needed; uses quantitative data)

| Param   | Type   | Description                                                |
|---------|--------|------------------------------------------------------------|
| `level` | string | Incoming level (e.g., `1A`). If 1A/1B, filter to 100-level |
| `limit` | int    | Max courses (default 12)                                   |

**Logic**: Sort courses by `global_weight` (desc), apply filters (engineering depts, undergrad, optionally 100-level), return top N. Uses existing recommender pipeline.

---

**Secondary: `GET /explore/by-topic`** (topic from curriculum)

| Param   | Type   | Description                                            |
|---------|--------|--------------------------------------------------------|
| `topic` | string | Option or minor name (e.g., `Artificial Intelligence`) |
| `level` | string | Incoming level (1A/1B → 100-level filter)             |
| `limit` | int    | Max courses (default 12)                               |

**Logic**: Look up courses in that option/minor's `course_lists` from `all_options.json` / `all_programs.json`. Return enriched course objects. Alternative: use option name as search query for semantic match.

**Response** (both): `{ "courses": Course[] }` (same shape as `/recommend`)

### UI/UX

- **Placement**: New "Explore" or "Get Started" section visible when Search tab is active and no search has been run
- **High-value block** (primary): "Courses that keep options open" — sorted by `global_weight`. Copy: e.g., "These courses are common prerequisites or count toward many options and minors."
- **Topic chips** (secondary): Option/minor names from curriculum (e.g., Artificial Intelligence, Entrepreneurship, Environmental Engineering). Click → fetch by-topic.
- **First-year filter**: When `incomingLevel` is 1A/1B, restrict to 100-level courses

---

## Implementation Phases

### Phase 1: Backend – High-Value Endpoint (primary)

- [ ] Add `GET /explore-high-value` to `backend/api/main.py`
- [ ] Expose `global_weight`-sorted courses from recommender (or add helper)
- [ ] Add filters: engineering depts, undergrad, 100-level when level=1A/1B
- [ ] Add `api.getHighValueCourses()` to frontend `api.ts`
- [ ] Add types to `frontend/src/types/api.ts`

**Deliverables**: Working high-value endpoint, frontend API method

### Phase 2: Frontend – High-Value UI

- [ ] Add "Courses that keep options open" section to `RecommendationPage`
- [ ] Fetch and display high-value courses on load (when no search/resume)
- [ ] Loading and empty states
- [ ] Integrate with existing `CourseCard` and modal
- [ ] Pass `incomingLevel` from context for 100-level filter

**Deliverables**: Visible high-value block, cold start solved

### Phase 3: Topic-Based Discovery (optional)

- [ ] Add `GET /explore/by-topic` (option/minor name → courses from course_lists)
- [ ] Load option/minor names from `/options-and-minors`
- [ ] Topic chips component (click to fetch by-topic)
- [ ] Add `api.getExploreByTopic()` to frontend

**Deliverables**: Topic-based exploration using curriculum-derived categories

### Phase 4: Polish

- [ ] Ensure explore results do not duplicate Random Course
- [ ] Accessibility (keyboard, screen readers)
- [ ] Update CONTEXT.md and README

**Deliverables**: Robust UX, documentation

---

## Scope Clarifications (Q&A)

### 1. Program-aware suggestions — what basis?

**We don't have popularity data.** The original plan assumed "electives popular in SYDE" or similar—we have no enrollment, engagement, or survey data to support that. **Scope change**: Program-aware suggestions are **excluded** for now. Defer until we have popularity or similar data.

### 2. Topic categories — arbitrary or systematic?

**Systematic option**: Use **option and minor names** from `all_options.json` and `all_programs.json`. These are curriculum-defined pathways (e.g., "Artificial Intelligence", "Entrepreneurship", "Environmental Engineering")—not arbitrary. They reflect actual degree structure. We can either:
- Return courses that appear in that option/minor's `course_lists` (direct lookup), or
- Use the option name as a search query for semantic match.

### 3. High-value courses — quantitative, data-driven

**We have the data.** The recommender already computes:
- **prereq_outdegree**: How many courses list this as a prerequisite (common prereq = unlocks many paths)
- **minor_count**: How many option/minor course lists include this course
- **global_weight**: Combines these (see `weights.py`)

Courses with high `global_weight` are quantitatively "high value"—they keep options open. This is the **primary** cold-start feature.

---

## Testing & Validation

| Type            | Scope                                                                 |
|-----------------|-----------------------------------------------------------------------|
| Unit (backend)  | `/explore-high-value` returns courses; 100-level filter when 1A/1B    |
| Integration     | Frontend calls explore, displays courses; topic click triggers fetch  |
| Manual          | New user flow: land on /recommendation → see explore → click topic    |
| Edge cases      | No program, 1A vs 4A, empty topics                                   |

---

## Risks & Mitigations

| Risk                          | Impact | Mitigation                                              |
|-------------------------------|--------|---------------------------------------------------------|
| Topic queries too narrow      | M      | Tune query strings; allow multiple topics per request   |
| Too many courses overwhelm UI | L      | Limit to 12–16; paginate or "Show more" if needed       |
| Performance of multi-query    | M      | Cache topic results; limit to 2–3 topics per request   |

---

## Rollout Strategy

1. **Phase 1**: Deploy backend `/explore-high-value`; verify via curl/Postman
2. **Phase 2**: Deploy frontend; high-value block always-on for /recommendation
3. **Phase 3** (optional): Add topic-based discovery using option/minor names
4. **Phase 4**: Polish; monitor engagement

---

## Topic Categories (Curriculum-Derived)

From `all_options.json` (engineering options):

- Artificial Intelligence, Biomechanics, Computer Engineering, Computing, Entrepreneurship, Environmental Engineering, Life Sciences, Management Science, Mechatronics, Physical Sciences, Quantum Engineering, Software Engineering, Statistics

From `all_programs.json` (minors): subset relevant to engineering (e.g., Computing Minor, Statistics Minor, etc.). Can filter by engineering-related minors or use options only for simplicity.

---

## Success Indicators

- [ ] First-year student can see 6+ relevant courses within 5 seconds of landing on /recommendation
- [ ] High-value block ("Courses that keep options open") surfaces quantitatively justified courses
- [ ] Topic chips (when implemented) use curriculum-derived option/minor names
- [ ] Incoming level 1A/1B restricts to 100-level courses when applicable
- [ ] No regression in existing Search / Recommended / Random flows
