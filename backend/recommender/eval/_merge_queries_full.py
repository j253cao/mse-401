"""
Build unified queries.json: legacy + test_plan_402 + expanded coverage.
Run from repo root: python backend/recommender/eval/_merge_queries_full.py
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
EVAL = Path(__file__).resolve().parent

with (REPO / "data/degree_requirements/program_core_courses.json").open(encoding="utf-8") as f:
    CORE = json.load(f)
with (REPO / "data/courses/course-api-new-data.json").open(encoding="utf-8") as f:
    CAT = json.load(f)


def thru(program: str, incoming: str) -> list[str]:
    order = ["1A", "1B", "2A", "2B", "3A", "3B", "4A", "4B"]
    i = order.index(incoming)
    return [c for j in range(i) for c in CORE.get(program, {}).get(order[j], [])]


def F(
    depts: list[str],
    user_dept: str,
    level: str,
    program: str,
    *,
    grad: bool = False,
    other: bool = False,
    **extra: object,
) -> dict:
    d: dict = {
        "include_undergrad": True,
        "include_grad": grad,
        "include_other_depts": other,
        "department": depts,
        "user_department": user_dept,
        "incoming_level": level,
        "completed_courses": thru(program, level),
    }
    d.update(extra)
    return d


def rat(code: str) -> dict:
    m = CAT.get(code, {})
    return {
        "title": m.get("title", ""),
        "description_excerpt": (m.get("description") or "")[:240].replace("\n", " ").strip(),
    }


_SEGMENT_INTENT = {
    "se_early": "Software Engineering 1B–2B: algorithms, systems, and program foundations.",
    "se_mid": "Software Engineering 3A: software construction, ML, and specialty CS topics.",
    "se_upper": "Software Engineering 3B+: networks, security, architecture.",
    "ece_early": "Computer or Electrical Engineering early terms: circuits, digital logic, math for ECE.",
    "ece_mid": "ECE middle terms: signals, communications, control, analog.",
    "ece_upper": "ECE upper year: ML hardware, advanced electives.",
    "mgte_early": "Management Engineering 2A–2B: optimization, probability, stochastic models.",
    "mgte_mid": "Management Engineering 3A: analytics, project management, HCI.",
    "mgte_upper": "Management Engineering 3B–4A: supply chain, entrepreneurship, decision systems.",
    "syde_early": "Systems Design early terms: modelling, control foundations, linear algebra.",
    "syde_mid": "Systems Design 3A–3B: HCI, AI, biomedical signals, thermofluids.",
    "syde_upper": "Systems Design upper year: nonlinear dynamics, advanced control.",
    "mte_early": "Mechatronics early terms: digital logic, mechatronics intro, signals prep.",
    "mte_mid": "Mechatronics 3A: embedded systems, robotics, modelling.",
    "mte_upper": "Mechatronics 3B–4A: power electronics, integration, advanced control.",
    "me_early": "Mechanical Engineering early terms: statics, dynamics, thermofluids intro.",
    "me_mid": "Mechanical 3A: manufacturing, vibrations, control.",
    "me_upper": "Mechanical 3B+: HVAC, design workshop, professional practice.",
    "cross_dept": "Discipline-specific queries (BME, CHE, CIVE, ENVE) with narrow department filters.",
    "cold_start": "First-year or minimal transcript; broad exploratory queries.",
    "breadth": "Engineering breadth / non-technical electives with expanded department lists.",
    "adversarial": "Short, noisy, or vague queries to test robustness.",
    "option_alignment": "Students with declared options/minors; courses should satisfy option constraints.",
    "rich_transcript": "Heavy completed-course lists; advanced follow-on recommendations.",
    "filter_behavior": "Tests prerequisite toggles, grad-only, or impossible department filters.",
    "career_driven": "Career-aligned natural-language goals (web, chips, autonomy, UX, consulting).",
    "coverage_expanded": "Additional major×term coverage (1A–4B) across programs in the catalog.",
    "test_plan_402_stem": "Test Plan 402 STEM prompts (S1–S12) with strict department filters.",
    "test_plan_402_nonstem": "Test Plan 402 non-STEM prompts (N1–N12); humanities/social breadth.",
}


def add_rationale(case: dict) -> None:
    seg = case.get("segment", "unknown")
    old_r = case.get("rationale") or {}
    intent = old_r.get("prompt_intent")
    is_generic = (
        not intent
        or (
            isinstance(intent, str)
            and intent.startswith("Segment '")
            and "evaluates recommender fit" in intent
        )
    )
    if is_generic:
        intent = _SEGMENT_INTENT.get(
            seg,
            f"Coverage segment '{seg}': align query text with graded courses under active filters.",
        )
    existing_courses = old_r.get("courses") or {}
    if isinstance(existing_courses, list):
        existing_courses = {}
    courses: dict = {}
    for code, grade in case.get("graded_relevance", {}).items():
        base = rat(code)
        ex = existing_courses.get(code) if isinstance(existing_courses.get(code), dict) else {}
        if ex.get("title"):
            base["title"] = ex["title"]
        if ex.get("description_excerpt"):
            base["description_excerpt"] = ex["description_excerpt"]
        why = ex.get("why")
        if not why:
            why = (
                f"Relevance grade {int(grade)}. {intent} "
                f"Course '{base.get('title', code)}' matches the query/topics under the active department and level filters."
            )
        courses[code] = {
            **base,
            "grade": float(grade),
            "why": why,
        }
    case["rationale"] = {"prompt_intent": intent, "courses": courses}


def normalize_filters(c: dict) -> None:
    f = c.get("filters") or {}
    seg = c.get("segment", "")
    # Arts / society / breadth: allow non-engineering departments not in `department` (matches product "explore other depts").
    if seg in ("test_plan_402_nonstem", "breadth", "non_stem"):
        f["include_other_depts"] = True
    elif "include_other_depts" not in f:
        f["include_other_depts"] = False
    c["filters"] = f


# --- Expanded cases (major x term coverage) ---
EXPANDED: list[dict] = []

def ec(
    eid: str,
    segment: str,
    query: str,
    filters: dict,
    graded: dict[str, int],
    intent: str,
) -> None:
    EXPANDED.append(
        {
            "id": eid,
            "segment": segment,
            "query": query,
            "filters": filters,
            "graded_relevance": graded,
            "rationale": {"prompt_intent": intent},
        }
    )


ec(
    "bme_1b_intro",
    "coverage_expanded",
    "biomedical engineering fundamentals anatomy instrumentation",
    F(["BME", "SYDE"], "BME", "1B", "BME"),
    {"BME122": 3, "BME162": 2, "BME186": 2, "SYDE112": 1},
    "Early BME: first-year cell/tissue and measurement foundations.",
)
ec(
    "bme_2a_modelling",
    "coverage_expanded",
    "biomechanics modelling simulation systems",
    F(["BME", "SYDE"], "BME", "2A", "BME"),
    {"BME282": 3, "BME285": 2, "SYDE211": 2, "BME281": 2},
    "BME 2A: core modelling and design workshop sequence.",
)
ec(
    "bme_4b_design_capstone",
    "coverage_expanded",
    "biomedical design capstone senior project",
    F(["BME"], "BME", "4B", "BME", grad=False),
    {"BME462": 3, "BME461": 2},
    "BME 4B: design workshop completion.",
)
ec(
    "ne_2a_foundation",
    "coverage_expanded",
    "nuclear engineering neutron diffusion reactor physics",
    F(["NE", "MATH"], "NE", "2A", "NE"),
    {"NE215": 3, "NE222": 2, "NE241": 2, "MATH211": 1},
    "NE 2A: introductory nuclear science and math tools.",
)
ec(
    "ne_2b_labs",
    "coverage_expanded",
    "nuclear engineering lab radiation detection measurement",
    F(["NE"], "NE", "2B", "NE"),
    {"NE226": 3, "NE226L": 3, "NE242": 2, "NE281": 2},
    "NE 2B: lab-heavy measurement and reactor intro.",
)
ec(
    "ne_4a_design",
    "coverage_expanded",
    "nuclear plant design safety systems engineering",
    F(["NE"], "NE", "4A", "NE"),
    {"NE451": 3, "NE452": 2, "NE453": 2},
    "NE 4A: senior design sequence.",
)
ec(
    "che_1b_material_balance",
    "coverage_expanded",
    "chemical process mass balance energy balance",
    F(["CHE", "MATH"], "CHE", "1B", "CHE"),
    {"CHE101": 3, "CHE161": 2, "MATH118": 1},
    "CHE 1B: introductory process analysis.",
)
ec(
    "che_2a_transport",
    "coverage_expanded",
    "heat transfer mass transfer separations chemical engineering",
    F(["CHE"], "CHE", "2A", "CHE"),
    {"CHE220": 3, "CHE230": 2, "CHE290": 2},
    "CHE 2A: transport phenomena core.",
)
ec(
    "cive_2a_structures_survey",
    "coverage_expanded",
    "civil engineering mechanics statics structures survey",
    F(["CIVE", "ME"], "CIVE", "2A", "CIVE"),
    {"CIVE204": 3, "CIVE224": 2, "CIVE241": 2, "CIVE265": 2},
    "CIVE 2A: structures and surveying fundamentals.",
)
ec(
    "cive_2b_fluids_geo",
    "coverage_expanded",
    "geotechnical fluid mechanics civil hydraulics",
    F(["CIVE"], "CIVE", "2B", "CIVE"),
    {"CIVE205": 3, "CIVE222": 2, "CIVE230": 2, "CIVE280": 2},
    "CIVE 2B: geotech and fluid topics.",
)
ec(
    "cive_4a_integrated",
    "coverage_expanded",
    "civil engineering integrated design capstone",
    F(["CIVE"], "CIVE", "4A", "CIVE"),
    {"CIVE400": 3, "CIVE491": 2},
    "CIVE 4A: integrated design.",
)
ec(
    "enve_3a_process_design",
    "coverage_expanded",
    "environmental engineering process design water quality",
    F(["ENVE", "CIVE", "CHE"], "ENVE", "3A", "ENVE"),
    {"ENVE330": 3, "ENVE375": 2, "ENVE391": 1},
    "ENVE 3A: process and environmental systems.",
)
ec(
    "enve_4b_capstone",
    "coverage_expanded",
    "environmental engineering senior design wastewater",
    F(["ENVE"], "ENVE", "4B", "ENVE"),
    {"ENVE401": 3, "ENVE498": 2},
    "ENVE 4B: capstone design.",
)
ec(
    "ae_2a_structural_fluid",
    "coverage_expanded",
    "architectural engineering structural analysis fluid thermal",
    F(["AE", "ME"], "AE", "2A", "AE"),
    {"AE200": 3, "AE221": 2, "AE280": 3, "AE224": 2},
    "AE 2A: structures and fluid/thermal sciences.",
)
ec(
    "geoe_3b_geotech",
    "coverage_expanded",
    "geological engineering hydrogeology groundwater",
    F(["GEOE", "EARTH", "ENVE"], "GEOE", "3B", "GEOE"),
    {"EARTH333": 3, "EARTH437": 2, "ENVE382": 2},
    "GEOE 3B: geoscience and environmental engineering crossover.",
)
ec(
    "compe_1b_programming_circuits",
    "coverage_expanded",
    "introduction to programming embedded C circuits",
    F(["ECE", "CS", "SE"], "COMPE", "1B", "COMPE"),
    {"ECE150": 3, "ECE124": 2, "ECE140": 2, "CS135": 1},
    "COMPE 1B: digital systems and programming entry.",
)
ec(
    "se_1a_discrete_math",
    "coverage_expanded",
    "discrete mathematics programming first year software",
    F(["SE", "CS", "MATH"], "SE", "1A", "SE"),
    {"MATH135": 3, "CS137": 3, "SE101": 2, "MATH117": 2},
    "SE 1A: core math and CS entry.",
)
ec(
    "ele_1b_linear_circuits",
    "coverage_expanded",
    "linear circuits digital logic first year electrical",
    F(["ECE"], "ELE", "1B", "ELE"),
    {"ECE106": 3, "ECE108": 2, "ECE124": 2, "ECE140": 2},
    "ELE 1B: circuits and programming bridge.",
)
ec(
    "mgte_1a_management_intro",
    "coverage_expanded",
    "management engineering optimization introduction organization",
    F(["MSE", "MATH"], "MGTE", "1A", "MGTE"),
    {"MSE100": 3, "MSE121": 2, "MATH116": 1},
    "MGTE 1A: program orientation and computation.",
)
ec(
    "mgte_4b_leadership_capstone",
    "coverage_expanded",
    "engineering leadership senior seminar management engineering",
    F(["MSE"], "MGTE", "4B", "MGTE"),
    {"MSE311": 3, "MSE411": 2},
    "MGTE 4B: leadership-focused capstone courses.",
)
ec(
    "syde_1b_systems_intro",
    "coverage_expanded",
    "systems design linear algebra introduction modelling",
    F(["SYDE", "MATH"], "SYDE", "1B", "SYDE"),
    {"SYDE223": 3, "SYDE162": 2, "MATH115": 1},
    "SYDE 1B: math and systems foundations.",
)
ec(
    "syde_4b_design_completion",
    "coverage_expanded",
    "systems design engineering capstone completion",
    F(["SYDE"], "SYDE", "4B", "SYDE"),
    {"SYDE462": 3, "SYDE461": 2},
    "SYDE 4B: final design term.",
)
ec(
    "mte_1a_computation_mechanics",
    "coverage_expanded",
    "python computation mechanics introduction mechatronics",
    F(["MTE", "MATH"], "MTE", "1A", "MTE"),
    {"MTE121": 3, "MTE100": 2, "MATH116": 1},
    "MTE 1A: digital computation and program intro.",
)
ec(
    "me_1a_intro_practice",
    "coverage_expanded",
    "mechanical engineering drawing design introduction practice",
    F(["ME"], "ME", "1A", "ME"),
    {"ME100": 3, "ME115": 2, "PHYS115": 2},
    "ME 1A: practice and physics foundations.",
)
ec(
    "me_4b_prof_practice",
    "coverage_expanded",
    "mechanical engineering professional practice law ethics",
    F(["ME"], "ME", "4B", "ME"),
    {"ME482": 3, "ME481": 2},
    "ME 4B: professional practice sequence if calendar lists ME481/482.",
)

# Verify ME481/ME482 exist
for check in ["ME481", "ME482"]:
    if check not in CAT:
        # fallback
        idx = next(i for i, x in enumerate(EXPANDED) if x["id"] == "me_4b_prof_practice")
        EXPANDED[idx]["graded_relevance"] = {"ME380": 3, "ME322": 2, "GENE404": 1}
        EXPANDED[idx]["rationale"]["prompt_intent"] = "ME senior: design workshop and professional electives."
        break

for i, x in enumerate(EXPANDED):
    if x["id"] == "me_4b_prof_practice":
        if "ME481" not in CAT or "ME482" not in CAT:
            x["graded_relevance"] = {"ME380": 3, "ME322": 2, "GENE404": 1}
            x["rationale"]["prompt_intent"] = (
                "ME senior term: design and interdisciplinary project exposure."
            )

# ENVE498 may not exist
if "ENVE498" not in CAT:
    for x in EXPANDED:
        if x["id"] == "enve_4b_capstone":
            x["graded_relevance"] = {"ENVE401": 3, "ENVE497": 2} if "ENVE497" in CAT else {"ENVE401": 3}

# MATH211 for NE - check
if "MATH211" not in CAT:
    for x in EXPANDED:
        if x["id"] == "ne_2a_foundation":
            x["graded_relevance"] = {"NE215": 3, "NE222": 2, "NE241": 2}

# NE226 vs NE226L keys
for x in EXPANDED:
    if x["id"] == "ne_2b_labs":
        gr = {}
        for k, v in x["graded_relevance"].items():
            if k in CAT:
                gr[k] = v
        if "NE226" not in CAT and "NE226L" in CAT:
            gr.pop("NE226", None)
            gr["NE226L"] = 3
        x["graded_relevance"] = gr

# Clean graded keys against catalog
for x in EXPANDED:
    x["graded_relevance"] = {k: v for k, v in x["graded_relevance"].items() if k in CAT}

# --- Load and merge ---
with (EVAL / "queries.json").open(encoding="utf-8") as f:
    legacy = json.load(f)
with (EVAL / "test_plan_402.json").open(encoding="utf-8") as f:
    tp = json.load(f)

by_id: dict[str, dict] = {}
order: list[str] = []

def add_case(c: dict) -> None:
    cid = c["id"]
    if cid in by_id:
        return
    c = deepcopy(c)
    normalize_filters(c)
    add_rationale(c)
    by_id[cid] = c
    order.append(cid)

for c in legacy["cases"]:
    add_case(c)
for c in tp["cases"]:
    add_case(c)
for c in EXPANDED:
    add_case(c)

cases_out = [by_id[i] for i in order]

# Validate
missing = []
for c in cases_out:
    for code in c.get("graded_relevance", {}):
        if code not in CAT:
            missing.append((c["id"], code))
if missing:
    raise SystemExit(f"Missing catalog codes: {missing[:30]}")

segments = sorted({c["segment"] for c in cases_out})

out = {
    "version": 3,
    "description": "Unified evaluation set: legacy matrix + Test Plan 402 (S/N prompts) + expanded major/term coverage. Use --eval-set recommender/eval/queries.json for full-platform recommender assessment.",
    "default_top_k": 15,
    "coverage_notes": (
        f"{len(cases_out)} cases across segments: "
        + ", ".join(segments)
        + ". include_other_depts defaults false (explore off); breadth/adversarial cases may set true where noted. "
        "Each case includes rationale.courses with catalog title, description excerpt, and justification."
    ),
    "cases": cases_out,
}

(EVAL / "queries.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print("Wrote queries.json with", len(cases_out), "cases,", len(segments), "segments")

# Update baseline_metrics.json floors for any new segment
baseline_path = EVAL / "baseline_metrics.json"
baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
floors = baseline.setdefault("segment_ndcg_floor", {})
for s in segments:
    if s not in floors:
        floors[s] = 0.05
baseline_path.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
print("Updated baseline_metrics.json segment floors")
