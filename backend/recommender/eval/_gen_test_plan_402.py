"""One-off generator for test_plan_402.json — run from repo root: python backend/recommender/eval/_gen_test_plan_402.py"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
with (REPO / "data/degree_requirements/program_core_courses.json").open(encoding="utf-8") as f:
    CORE = json.load(f)
with (REPO / "data/courses/course-api-new-data.json").open(encoding="utf-8") as f:
    CAT = json.load(f)


def thru(program: str, incoming: str) -> list[str]:
    order = ["1A", "1B", "2A", "2B", "3A", "3B", "4A", "4B"]
    i = order.index(incoming)
    acc: list[str] = []
    for j in range(i):
        acc.extend(CORE.get(program, {}).get(order[j], []))
    return acc


def rat(code: str) -> dict:
    meta = CAT.get(code, {})
    return {
        "title": meta.get("title", ""),
        "description_excerpt": (meta.get("description") or "")[:220].replace("\n", " "),
    }


def F(depts: list[str], user_dept: str, level: str, completed: list[str], **extra: object) -> dict:
    d: dict = {
        "include_undergrad": True,
        "include_grad": False,
        "include_other_depts": False,
        "department": depts,
        "user_department": user_dept,
        "incoming_level": level,
        "completed_courses": completed,
    }
    d.update(extra)
    return d


cases: list[dict] = []


def add(tp_id: str, segment: str, query: str, filters: dict, graded: dict[str, int], intent: str) -> None:
    rc = {}
    for k, g in graded.items():
        rc[k] = {**rat(k), "grade": g, "why": intent}
    cases.append(
        {
            "id": tp_id,
            "segment": segment,
            "test_plan_prompt": tp_id.split("_")[1],
            "query": query,
            "filters": filters,
            "graded_relevance": graded,
            "rationale": {"prompt_intent": intent, "courses": rc},
        }
    )


# STEM
add(
    "tp402_S1_se_3a",
    "test_plan_402_stem",
    "machine learning",
    F(["SE", "ECE", "CS", "SYDE", "MSE"], "SE", "3A", thru("SE", "3A")),
    {"CS480": 3, "CS486": 2, "MSE446": 2, "ECE457C": 2},
    "S1: ML/AI courses whose catalog titles stress machine learning, AI, or advanced learning methods.",
)
add(
    "tp402_S1_compe_3b",
    "test_plan_402_stem",
    "machine learning",
    F(["ECE", "CS", "SE", "SYDE", "MSE"], "COMPE", "3B", thru("COMPE", "3B")),
    {"CS480": 3, "ECE457B": 3, "ECE457C": 2, "MSE446": 2},
    "S1 (COMPE): computational intelligence + deep learning in ECE plus CS ML intro.",
)
add(
    "tp402_S1_mgte_3a",
    "test_plan_402_stem",
    "machine learning",
    F(["MSE", "CS", "STAT", "ECE"], "MGTE", "3A", thru("MGTE", "3A")),
    {"MSE446": 3, "CS480": 3, "STAT441": 2, "CS486": 2},
    "S1 (MGTE): program intro ML and statistical learning electives.",
)
add(
    "tp402_S2_me_2b",
    "test_plan_402_stem",
    "heat transfer and thermodynamics in mechanical systems",
    F(["ME", "MTE", "SYDE"], "ME", "2B", thru("ME", "2B")),
    {"ME353": 3, "ME354": 3, "ME351": 2, "SYDE381": 2},
    "S2: ME heat transfer, thermodynamics, and fluids; SYDE thermodynamics where allowed.",
)
add(
    "tp402_S2_me_3a",
    "test_plan_402_stem",
    "heat transfer and thermodynamics in mechanical systems",
    F(["ME", "MTE", "SYDE"], "ME", "3A", thru("ME", "3A")),
    {"ME456": 3, "ME353": 3, "ME354": 2, "ME362": 2},
    "S2 at 3A: second heat transfer and fluids depth in ME core.",
)
add(
    "tp402_S2_mte_3a",
    "test_plan_402_stem",
    "heat transfer and thermodynamics in mechanical systems",
    F(["MTE", "ME", "SYDE"], "MTE", "3A", thru("MTE", "3A")),
    {"MTE309": 3, "ME353": 2, "ME354": 2, "SYDE381": 2},
    "S2 (MTE): MTE309 Intro Thermodynamics and Heat Transfer title matches prompt.",
)
add(
    "tp402_S3_compe_2a",
    "test_plan_402_stem",
    "digital logic design and computer architecture",
    F(["ECE", "SE", "CS", "MTE"], "COMPE", "2A", thru("COMPE", "2A")),
    {"ECE222": 3, "ECE327": 3, "ECE250": 2, "MTE262": 2},
    "S3: ECE222 Digital Computers; ECE327 Digital Hardware Systems; digital logic MTE262.",
)
add(
    "tp402_S3_se_2a",
    "test_plan_402_stem",
    "digital logic design and computer architecture",
    F(["SE", "ECE", "CS", "MTE"], "SE", "2A", thru("SE", "2A")),
    {"SE212": 3, "ECE222": 3, "ECE327": 2, "CS240": 2},
    "S3 (SE): formal logic/discrete + CE hardware path.",
)
add(
    "tp402_S3_ele_2b",
    "test_plan_402_stem",
    "digital logic design and computer architecture",
    F(["ECE", "MTE", "NE"], "ELE", "2B", thru("ELE", "2B")),
    {"ECE222": 3, "ECE327": 3, "ECE240": 2, "NE344": 2},
    "S3 (ELE): digital + hardware + circuits; NE electronic circuits for nanotech.",
)
add(
    "tp402_S4_che_3b",
    "test_plan_402_stem",
    "materials science",
    F(["CHE", "NE", "ME"], "CHE", "3B", thru("CHE", "3B")),
    {"CHE241": 3, "CHE330": 2, "NE332": 2, "ME230": 2},
    "S4: CHE241 Materials Science and Engineering; thermo/properties CHE330.",
)
add(
    "tp402_S4_ne_3a",
    "test_plan_402_stem",
    "materials science",
    F(["NE", "ECE", "MSE"], "NE", "3A", thru("NE", "3A")),
    {"NE343": 3, "NE332": 2, "NE345": 2, "NE333": 2},
    "S4 (NE): microfabrication, quantum mechanics, photonic materials in nano stream.",
)
add(
    "tp402_S4_me_3a",
    "test_plan_402_stem",
    "materials science",
    F(["ME", "CHE", "MTE"], "ME", "3A", thru("ME", "3A")),
    {"ME230": 3, "ME340": 3, "CHE241": 2, "ME235": 2},
    "S4 (ME): materials/manufacturing and processing electives.",
)
add(
    "tp402_S5_me_2b",
    "test_plan_402_stem",
      "fluid mechanics and aerodynamics",
    F(["ME", "MTE", "SYDE", "AE"], "ME", "2B", thru("ME", "2B")),
    {"ME351": 3, "ME353": 2, "SYDE383": 2, "ME564": 2},
    "S5: ME351 Fluid Mechanics; ME564 Aerodynamics catalog title.",
)
add(
    "tp402_S5_ae_3a",
    "test_plan_402_stem",
    "fluid mechanics and aerodynamics",
    F(["AE", "ME", "MTE"], "AE", "3A", thru("AE", "3A")),
    {"AE280": 3, "ME351": 2, "MTE352": 2, "ME564": 1},
    "S5 (AE): AE280 Fluid Mechanics and Thermal Sciences.",
)
add(
    "tp402_S5_mte_3b",
    "test_plan_402_stem",
    "fluid mechanics and aerodynamics",
    F(["MTE", "ME", "SYDE"], "MTE", "3B", thru("MTE", "3B")),
    {"MTE352": 3, "ME351": 2, "SYDE383": 2, "ME353": 2},
    "S5 (MTE): MTE352 Fluid Mechanics 1.",
)
add(
    "tp402_S6_ele_3a",
    "test_plan_402_stem",
    "signals and systems",
    F(["ECE"], "ELE", "3A", thru("ELE", "3A")),
    {"ECE207": 3, "ECE318": 3, "ECE375": 2},
    "S6: ECE207 Signals and Systems; ECE318 Communication Systems.",
)
add(
    "tp402_S6_mte_2b",
    "test_plan_402_stem",
    "signals and systems",
    F(["MTE", "ECE", "SYDE"], "MTE", "2B", thru("MTE", "2B")),
    {"MTE252": 3, "ECE207": 2, "MTE241": 2},
    "S6 (MTE): linear systems/signals + computer structures.",
)
add(
    "tp402_S6_syde_2b",
    "test_plan_402_stem",
    "signals and systems",
    F(["SYDE", "ECE", "MTE"], "SYDE", "2B", thru("SYDE", "2B")),
    {"SYDE252": 2, "ECE207": 3, "MTE252": 2, "SYDE283": 2},
    "S6 (SYDE): systems/math + shared ECE signals foundation.",
)
add(
    "tp402_S7_se_3a",
    "test_plan_402_stem",
    "neural networks",
    F(["SE", "ECE", "CS", "SYDE"], "SE", "3A", thru("SE", "3A")),
    {"ECE457C": 3, "CS486": 3, "SYDE556": 2, "CS480": 2},
    "S7: reinforcement learning / AI / simulating neurobiological systems.",
)
add(
    "tp402_S7_syde_3a",
    "test_plan_402_stem",
    "neural networks",
    F(["SYDE", "ECE", "CS"], "SYDE", "3A", thru("SYDE", "3A")),
    {"SYDE522": 3, "SYDE556": 3, "ECE457B": 2, "CS486": 2},
    "S7 (SYDE): Foundations of AI + neuro simulation.",
)
add(
    "tp402_S7_compe_3b",
    "test_plan_402_stem",
    "neural networks",
    F(["ECE", "CS", "SE"], "COMPE", "3B", thru("COMPE", "3B")),
    {"ECE457B": 3, "ECE457C": 3, "CS486": 2, "CS480": 2},
    "S7 (COMPE): computational intelligence stack in ECE + CS AI.",
)
add(
    "tp402_S8_che_3b",
    "test_plan_402_stem",
    "chemistry of polymers and composite materials",
    F(["CHE", "NE", "MSE"], "CHE", "3B", thru("CHE", "3B")),
    {"CHE541": 3, "CHE543": 3, "CHE241": 2},
    "S8: CHE541/543 titles and descriptions center on polymer science and reaction engineering.",
)
add(
    "tp402_S8_me_3b",
    "test_plan_402_stem",
    "chemistry of polymers and composite materials",
    F(["ME", "CHE", "NE"], "ME", "3B", thru("ME", "3B")),
    {"ME435": 2, "CHE541": 3, "CHE241": 2, "NE333": 2},
    "S8 (ME): polymer CHE courses plus advanced materials electives.",
)
add(
    "tp402_S8_ne_3b",
    "test_plan_402_stem",
    "chemistry of polymers and composite materials",
    F(["NE", "CHE", "MSE"], "NE", "3B", thru("NE", "3B")),
    {"NE335": 3, "CHE541": 3, "NE343": 2},
    "S8 (NE): soft nanomaterials with polymer engineering.",
)
add(
    "tp402_S9_mgte_2b",
    "test_plan_402_stem",
    "probability and statistics for data-driven design",
    F(["MSE", "STAT", "CO", "CS"], "MGTE", "2B", thru("MGTE", "2B")),
    {"MSE253": 3, "MSE431": 2, "STAT340": 2, "STAT332": 2},
    "S9 (MGTE): probability/stat + stochastic models + simulation.",
)
add(
    "tp402_S9_se_2b",
    "test_plan_402_stem",
    "probability and statistics for data-driven design",
    F(["SE", "STAT", "MATH", "MSE"], "SE", "2B", thru("SE", "2B")),
    {"STAT206": 3, "MSE253": 2, "STAT230": 2, "STAT231": 2},
    "S9 (SE): engineering statistics and probability offerings.",
)
add(
    "tp402_S9_compe_2b",
    "test_plan_402_stem",
    "probability and statistics for data-driven design",
    F(["ECE", "STAT", "MATH", "MSE"], "COMPE", "2B", thru("COMPE", "2B")),
    {"STAT206": 3, "STAT230": 2, "STAT231": 2, "MSE431": 1},
    "S9 (COMPE): stats core for data-driven ECE work.",
)
add(
    "tp402_S10_mte_3b",
    "test_plan_402_stem",
    "control systems and feedback for robotics",
    F(["MTE", "ECE", "ME", "SYDE"], "MTE", "3B", thru("MTE", "3B")),
    {"MTE360": 3, "ECE486": 3, "MTE322": 2, "MTE460": 2},
    "S10 (MTE): automatic control + robot dynamics + integration workshop.",
)
add(
    "tp402_S10_me_3a",
    "test_plan_402_stem",
    "control systems and feedback for robotics",
    F(["ME", "MTE", "ECE", "SYDE"], "ME", "3A", thru("ME", "3A")),
    {"ME360": 3, "ME321": 3, "ECE380": 2, "MTE360": 2},
    "S10 (ME): intro control + dynamics/vibrations.",
)
add(
    "tp402_S10_syde_2b",
    "test_plan_402_stem",
    "control systems and feedback for robotics",
    F(["SYDE", "ECE", "ME", "MTE"], "SYDE", "2B", thru("SYDE", "2B")),
    {"SYDE352": 3, "ECE380": 2, "ME360": 2, "MTE360": 2},
    "S10 (SYDE): SYDE352 Introduction to Control Systems.",
)
add(
    "tp402_S11_compe_3b",
    "test_plan_402_stem",
    "circuits electronics and embedded systems",
    F(["ECE", "MTE", "NE"], "COMPE", "3B", thru("COMPE", "3B")),
    {"ECE350": 3, "ECE327": 3, "MTE325": 2, "ECE240": 2},
    "S11: RTOS/microprocessors + digital hardware + circuits.",
)
add(
    "tp402_S11_mte_3a",
    "test_plan_402_stem",
    "circuits electronics and embedded systems",
    F(["MTE", "ECE", "NE"], "MTE", "3A", thru("MTE", "3A")),
    {"MTE325": 3, "MTE241": 3, "ECE327": 2, "ECE350": 2},
    "S11 (MTE): microprocessor systems + computer structures.",
)
add(
    "tp402_S11_ele_2b",
    "test_plan_402_stem",
    "circuits electronics and embedded systems",
    F(["ECE"], "ELE", "2B", thru("ELE", "2B")),
    {"ECE240": 3, "ECE222": 2, "ECE208": 2, "ECE250": 2},
    "S11 (ELE): electronic circuits + digital + software systems design.",
)
add(
    "tp402_S12_mgte_2a",
    "test_plan_402_stem",
    "optimization and operations research",
    F(["MSE", "CO", "CS"], "MGTE", "2A", thru("MGTE", "2A")),
    {"MSE331": 3, "CO250": 3, "MSE332": 2},
    "S12 (MGTE): intro optimization + CO250 + deterministic models.",
)
add(
    "tp402_S12_mgte_3b",
    "test_plan_402_stem",
    "optimization and operations research",
    F(["MSE", "CO", "STAT"], "MGTE", "3B", thru("MGTE", "3B")),
    {"MSE332": 3, "MSE435": 3, "CO370": 2, "CO351": 2},
    "S12 upper OR: deterministic optimization + network flow.",
)
add(
    "tp402_S12_se_2a",
    "test_plan_402_stem",
    "optimization and operations research",
    F(["SE", "CO", "MSE", "ECE"], "SE", "2A", thru("SE", "2A")),
    {"CO250": 3, "ECE406": 2, "MSE331": 2, "CS341": 2},
    "S12 (SE): discrete optimization + algorithm design + algorithms course.",
)

# Non-STEM
add(
    "tp402_N1_se_3a",
    "test_plan_402_nonstem",
    "ethics of technology and engineering in society",
    F(["PHIL", "GENE"], "SE", "3A", thru("SE", "3A")),
    {"PHIL315": 3, "PHIL226": 2},
    "N1: PHIL315 Ethics and the Engineering Profession.",
)
add(
    "tp402_N1_mgte_3b",
    "test_plan_402_nonstem",
    "ethics of technology and engineering in society",
    F(["PHIL", "SCI"], "MGTE", "3B", thru("MGTE", "3B")),
    {"PHIL315": 3, "PHIL226": 2},
    "N1: same ethics courses; include_other_depts on so non-ENG breadth outside the PHIL/SCI list can surface.",
)
add(
    "tp402_N2_compe_2b",
    "test_plan_402_nonstem",
    "professional communication and technical writing for engineers",
    F(["ENGL", "COMMST"], "COMPE", "2B", thru("COMPE", "2B")),
    {"ENGL210E": 3, "ENGL472": 2, "COMMST111": 2},
    "N2: technical communication + leadership/communication.",
)
add(
    "tp402_N2_syde_2a",
    "test_plan_402_nonstem",
    "professional communication and technical writing for engineers",
    F(["SYDE", "ENGL"], "SYDE", "2A", thru("SYDE", "2A")),
    {"SYDE101": 3, "ENGL210E": 2},
    "N2: SYDE communications core + ENGL technical communication.",
)
add(
    "tp402_N3_se_3a",
    "test_plan_402_nonstem",
    "psychology of decision making and human factors",
    F(["PSYCH", "SYDE"], "SE", "3A", thru("SE", "3A")),
    {"PSYCH342": 3, "PSYCH439": 2, "SYDE543": 3},
    "N3: teams/negotiation psych + SYDE cognitive ergonomics title.",
)
add(
    "tp402_N3_mte_3b",
    "test_plan_402_nonstem",
    "psychology of decision making and human factors",
    F(["PSYCH", "COMMST"], "MTE", "3B", thru("MTE", "3B")),
    {"PSYCH342": 3, "PSYCH230": 2, "COMMST100": 2},
    "N3: psychology + interpersonal communication.",
)
add(
    "tp402_N4_mgte_3a",
    "test_plan_402_nonstem",
    "economics of innovation",
    F(["ECON", "MSE", "BET"], "MGTE", "3A", thru("MGTE", "3A")),
    {"MSE422": 3, "ECON310EW": 3, "BET320": 2, "MSE263": 2},
    "N4: entrepreneurship/tech change + econ of innovation + strategy.",
)
add(
    "tp402_N4_che_2b",
    "test_plan_402_nonstem",
    "economics of innovation",
    F(["ECON", "CHE", "MSE"], "CHE", "2B", thru("CHE", "2B")),
    {"ECON310EW": 3, "MSE422": 2},
    "N4 (CHE): innovation economics + technology entrepreneurship electives.",
)
add(
    "tp402_N5_se_2b",
    "test_plan_402_nonstem",
    "history of science",
    F(["HIST", "SCI"], "SE", "2B", thru("SE", "2B")),
    {"HIST112": 3},
    "N5: global history of science and technology.",
)
add(
    "tp402_N5_cive_3a",
    "test_plan_402_nonstem",
    "history of science",
    F(["HIST", "ERS"], "CIVE", "3A", thru("CIVE", "3A")),
    {"HIST112": 3, "ERS101": 2},
    "N5: history of S&T plus environment/resources survey.",
)
add(
    "tp402_N6_me_2b",
    "test_plan_402_nonstem",
    "sustainability environmental policy and climate justice",
    F(["ERS", "PLAN", "ENVE"], "ME", "2B", thru("ME", "2B")),
    {"PLAN348": 3, "ERS101": 2, "ENVE279": 2, "PLAN419": 2},
    "N6: climate planning courses + ERS/ENVE environment titles.",
)
add(
    "tp402_N6_syde_3b",
    "test_plan_402_nonstem",
    "sustainability environmental policy and climate justice",
    F(["ERS", "ENVE", "PLAN"], "SYDE", "3B", thru("SYDE", "3B")),
    {"PLAN419": 3, "PLAN348": 2, "ERS221": 2},
    "N6 alternate cohort: community climate planning + oceans sustainability.",
)

add(
    "tp402_N7_se_3b",
    "test_plan_402_nonstem",
    "law regulation and intellectual property for technology",
    F(["CIVE", "AE", "GENE"], "SE", "3B", thru("SE", "3B")),
    {"CIVE491": 3, "AE491": 2},
    "N7: Engineering Law and Ethics course titles in CIVE/AE.",
)
add(
    "tp402_N7_me_3b",
    "test_plan_402_nonstem",
    "law regulation and intellectual property for technology",
    F(["CIVE", "ME"], "ME", "3B", thru("ME", "3B")),
    {"CIVE491": 3},
    "N7 (ME): civil engineering law/ethics elective exposure.",
)
add(
    "tp402_N8_mgte_3b",
    "test_plan_402_nonstem",
    "leadership teamwork and project management in organizations",
    F(["MSE", "BET"], "MGTE", "3B", thru("MGTE", "3B")),
    {"MSE411": 3, "BET450": 3, "BET405": 2, "MSE211": 2},
    "N8: leadership and organizational behaviour course titles.",
)
add(
    "tp402_N8_se_3b",
    "test_plan_402_nonstem",
    "leadership teamwork and project management in organizations",
    F(["MSE", "BET", "SE"], "SE", "3B", thru("SE", "3B")),
    {"SE463": 3, "MSE411": 2, "BET450": 2},
    "N8 (SE): software project management + leadership electives.",
)
add(
    "tp402_N9_cive_3b",
    "test_plan_402_nonstem",
    "urban planning and community studies",
    F(["PLAN", "GEOG", "ERS"], "CIVE", "3B", thru("CIVE", "3B")),
    {"PLAN440": 3, "PLAN476": 2, "PLAN432": 2},
    "N9: urban services, mobility, built environment health.",
)
add(
    "tp402_N9_syde_4a",
    "test_plan_402_nonstem",
    "urban planning and community studies",
    F(["PLAN", "ERS"], "SYDE", "4A", thru("SYDE", "4A")),
    {"PLAN453": 3, "PLAN414": 2, "PLAN476": 2, "PLAN380": 2},
    "N9 (SYDE 4A): urban stormwater, heritage, crime and city electives.",
)
add(
    "tp402_N10_compe_3a",
    "test_plan_402_nonstem",
    "philosophy of mind and logic",
    F(["PHIL", "CO"], "COMPE", "3A", thru("COMPE", "3A")),
    {"PHIL255": 3, "PHIL240": 2},
    "N10: PHIL255 Philosophy of Mind + PHIL240 Introduction to Formal Logic.",
)
add(
    "tp402_N10_bme_3b",
    "test_plan_402_nonstem",
    "philosophy of mind and logic",
    F(["PHIL", "PSYCH"], "BME", "3B", thru("BME", "3B")),
    {"PHIL255": 3, "PSYCH207": 2},
    "N10: philosophy of mind + cognitive processes.",
)
add(
    "tp402_N11_se_3b",
    "test_plan_402_nonstem",
    "creative writing",
    F(["ENGL"], "SE", "3B", thru("SE", "3B")),
    {"ENGL335": 3, "ENGL336": 2, "ENGL210C": 2},
    "N11: creative writing sequence titles.",
)
add(
    "tp402_N11_mgte_2b",
    "test_plan_402_nonstem",
    "creative writing",
    F(["ENGL", "ARTS"], "MGTE", "2B", thru("MGTE", "2B")),
    {"ENGL335": 3, "ENGL210C": 2},
    "N11: MGTE breadth creative writing.",
)
add(
    "tp402_N12_me_3a",
    "test_plan_402_nonstem",
    "modern film studies",
    F(["FILM"], "ME", "3A", thru("ME", "3A")),
    {"FILM101W": 3, "FILM240W": 2},
    "N12: film & narrative + film history (WLU) per catalog.",
)
add(
    "tp402_N12_syde_3a",
    "test_plan_402_nonstem",
    "modern film studies",
    F(["FILM", "VCULT"], "SYDE", "3A", thru("SYDE", "3A")),
    {"FILM101W": 3, "FILM252W": 2},
    "N12: intro film + film noir topics.",
)

for c in cases:
    if c.get("segment") == "test_plan_402_nonstem":
        c.setdefault("filters", {})["include_other_depts"] = True

# Rebuild rationale with fresh rat()
for c in cases:
    intent = c["rationale"]["prompt_intent"]
    c["rationale"]["courses"] = {
        k: {
            **rat(k),
            "grade": g,
            "why": f"Relevance grade {g}. {intent} Course title/description in catalog supports match to query.",
        }
        for k, g in c["graded_relevance"].items()
    }

out = {
    "version": 1,
    "description": "Test Plan 402 query bank (STEM S1-S12, non-STEM N1-N12). Non-STEM cases set include_other_depts=true for breadth-style discovery. Compare methods: python -m recommender.eval.run_weight_sweep --eval-set recommender/eval/test_plan_402.json --compare-methods --num-random 0",
    "default_top_k": 15,
    "evaluation_note": "run_weight_sweep merges default_search_weights with [{}] for --compare-methods. cosine/dense/hybrid_bm25_dense test base retrieval scores; cross_encoder_rerank and hybrid_rerank_graph add model-specific reranking or graph multipliers on top.",
    "cases": cases,
}

dest = Path(__file__).resolve().parent / "test_plan_402.json"
dest.write_text(json.dumps(out, indent=2), encoding="utf-8")

missing_codes = []
for c in cases:
    for code in c["graded_relevance"]:
        if code not in CAT:
            missing_codes.append((c["id"], code))
print("Wrote", dest, "cases", len(cases))
print("Missing codes", missing_codes)
