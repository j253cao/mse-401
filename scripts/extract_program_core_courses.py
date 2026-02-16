#!/usr/bin/env python3
"""
Extract required core courses per engineering program and term from degree_requirements.

Logic:
- program = root
- group = contains other nodes
- choice = contains courses (leaves). RequiredCount = "NA" or missing = all required.
  RequiredCount = "1", "2", etc. = pick N from list (elective, exclude)
- specialization = optional specialization (exclude)

Required core = term nodes (1A, 1B, 2A, 2B, 3A, 3B, 4A, 4B) and their CORE sub-nodes.
Exclude: CSE, TE, PD_ADD, Ethics, COOP, WKRPT, NS, specialization.
Include: PD_CORE (all required for PD).

Output: { programCode: { term: [courseCodes] } }
Course format: "MATH115" (uppercase, no space) to match backend.
"""

import json
import os
import re
from collections import defaultdict

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NODE_PATH = os.path.join(PROJECT_ROOT, "data", "degree_requirements", "node.json")
COURSE_PATH = os.path.join(PROJECT_ROOT, "data", "degree_requirements", "course.json")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "data", "degree_requirements", "program_core_courses.json")

# Program code mapping: NodeID prefix -> display code
# 2025_CHE -> CHE, 2025_NE_1 -> NE (consolidate NE streams)
PROGRAM_PREFIXES = [
    "2025_AE",
    "2025_BME",
    "2025_CHE",
    "2025_CIVE",
    "2025_COMPE",
    "2025_ELE",
    "2025_ENVE",
    "2025_GEOE",
    "2025_ME",
    "2025_MGTE",
    "2025_MTE",
    "2025_NE_1",  # NE streams 1-9 share structure; use first for canonical
    "2025_NE_2",
    "2025_NE_3",
    "2025_NE_4",
    "2025_NE_5",
    "2025_NE_6",
    "2025_NE_7",
    "2025_NE_8",
    "2025_NE_9",
    "2025_SE",
    "2025_SYDE",
]

TERM_PATTERN = re.compile(r"^(\d)[AB]$")  # 1A, 1B, 2A, 2B, 3A, 3B, 4A, 4B

# NodeIDs to exclude (electives, non-core)
EXCLUDE_PREFIXES = (
    "CSE",      # Complementary studies electives
    "TE",       # Technical electives
    "Ethics",   # Pick 1
    "COOP",     # Work term reports
    "WKRPT",    # Work report
    "NS",       # Natural science elective
    "SPE_",     # Specialization
)
# PD_ADD is elective (pick 2), PD_CORE is required
EXCLUDE_PATTERNS = ("_PD_ADD", "_Ethics", "_COOP", "_WKRPT", "_NS")


def get_program_code(node_id: str) -> str | None:
    """Map NodeID to program code for output."""
    for prefix in PROGRAM_PREFIXES:
        if node_id.startswith(prefix + "_") or node_id == prefix:
            if prefix.startswith("2025_NE_"):
                return "NE"
            return prefix.replace("2025_", "")
    return None


def is_required_core_node(node: dict) -> bool:
    """True if this choice node is required (all courses must be taken)."""
    if node.get("NodeType") != "choice":
        return False
    rc = node.get("RequiredCount")
    if rc is None or rc == "" or rc == "NA":
        return True
    try:
        return int(rc) <= 0  # 0 might mean "all" in some cases
    except (ValueError, TypeError):
        return False


def is_required_child_group(node: dict) -> bool:
    """True if this group's children are term-level (1A, 1B, etc.) or CORE."""
    node_id = node.get("NodeID", "")
    return bool(TERM_PATTERN.search(node_id)) or "_CORE" in node_id or "_ADD" in node_id


def should_exclude_node(node_id: str) -> bool:
    """Exclude elective / non-core nodes."""
    for pat in EXCLUDE_PATTERNS:
        if pat in node_id:
            return True
    parts = node_id.split("_")
    for i, part in enumerate(parts):
        if part in ("CSE", "TE", "COOP", "WKRPT", "NS"):
            return True
        if part == "Ethics":
            return True
        if part == "SPE":
            return True
    return False


def collect_required_node_ids(nodes_by_id: dict, program_id: str) -> set[str]:
    """Collect all NodeIDs that represent required core for a program."""
    required = set()
    program_node = nodes_by_id.get(program_id)
    if not program_node or program_node.get("NodeType") != "program":
        return required

    children = [n for n in nodes_by_id.values() if n.get("ParentID") == program_id]

    for child in children:
        if should_exclude_node(child["NodeID"]):
            continue
        if child["NodeType"] == "choice" and is_required_core_node(child):
            required.add(child["NodeID"])
            # InheritedLists: add those NodeIDs too
            inherited = child.get("InheritedLists", "").strip()
            if inherited:
                for nid in inherited.replace(",", " ").split():
                    nid = nid.strip()
                    if nid and not should_exclude_node(nid):
                        required.add(nid)
        elif child["NodeType"] == "group":
            # Recurse into group for CORE / ADD (only CORE is required)
            for grandchild in nodes_by_id.values():
                if grandchild.get("ParentID") != child["NodeID"]:
                    continue
                if grandchild["NodeType"] != "choice":
                    continue
                if should_exclude_node(grandchild["NodeID"]):
                    continue
                if "_ADD" in grandchild["NodeID"] and grandchild.get("RequiredCount"):
                    continue  # ADD with RequiredCount = elective
                if is_required_core_node(grandchild):
                    required.add(grandchild["NodeID"])
                    inherited = grandchild.get("InheritedLists", "").strip()
                    if inherited:
                        for nid in inherited.replace(",", " ").split():
                            nid = nid.strip()
                            if nid and not should_exclude_node(nid):
                                required.add(nid)

    return required


def extract_term_from_node_id(node_id: str, program_id: str) -> str | None:
    """Extract term (1A, 1B, etc.) from a node ID."""
    # e.g. 2025_CHE_1A -> 1A, 2025_CHE_1B_CORE -> 1B
    suffix = node_id.replace(program_id + "_", "")
    m = re.match(r"^(\d)[AB]", suffix)
    if m:
        return m.group(0)
    return None


def normalize_course(course_str: str) -> str:
    """Normalize to uppercase, no spaces (e.g. MATH115)."""
    return course_str.upper().replace(" ", "")


def main():
    with open(NODE_PATH, encoding="utf-8") as f:
        nodes = json.load(f)
    with open(COURSE_PATH, encoding="utf-8") as f:
        courses = json.load(f)

    nodes_by_id = {n["NodeID"]: n for n in nodes}

    # Build NodeID -> set of course codes
    node_to_courses: dict[str, set[str]] = defaultdict(set)
    for entry in courses:
        course_code = normalize_course(entry["course"])
        # Skip 0-credit (work reports, etc.)
        if entry.get("credit", 0) == 0:
            continue
        node_ids = [x.strip() for x in entry.get("NodeIDs", "").split(",") if x.strip()]
        for nid in node_ids:
            node_to_courses[nid].add(course_code)

    # Programs to process (exclude NE_2..NE_9 for now; we'll use NE_1 as canonical)
    program_ids = set()
    for n in nodes:
        if n.get("NodeType") != "program":
            continue
        nid = n["NodeID"]
        if nid.startswith("2025_NE_"):
            program_ids.add("2025_NE_1")  # Use NE_1 as canonical
        else:
            program_ids.add(nid)

    result: dict[str, dict[str, list[str]]] = {}

    for program_id in sorted(program_ids):
        if program_id.startswith("2025_NE_") and program_id != "2025_NE_1":
            continue
        required_node_ids = collect_required_node_ids(nodes_by_id, program_id)


        # Map node IDs to terms
        term_to_courses: dict[str, set[str]] = defaultdict(set)
        for nid in required_node_ids:
            term = extract_term_from_node_id(nid, program_id)
            if not term:
                continue
            for course in node_to_courses.get(nid, []):
                term_to_courses[term].add(course)

        if not term_to_courses:
            continue

        program_code = get_program_code(program_id)
        if not program_code:
            continue
        result[program_code] = {
            term: sorted(courses) for term, courses in term_to_courses.items()
        }

    # Sort terms for output
    term_order = ["1A", "1B", "2A", "2B", "3A", "3B", "4A", "4B"]
    for prog in result:
        result[prog] = dict(
            sorted(
                result[prog].items(),
                key=lambda x: (term_order.index(x[0]) if x[0] in term_order else 99, x[0]),
            )
        )

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    # Also copy to frontend for build
    frontend_path = os.path.join(PROJECT_ROOT, "frontend", "src", "data", "program_core_courses.json")
    os.makedirs(os.path.dirname(frontend_path), exist_ok=True)
    with open(frontend_path, "w", encoding="utf-8") as f:
        json.dump(result, f)

    print(f"Wrote {OUTPUT_PATH}")
    print(f"Wrote {frontend_path}")
    for prog, terms in result.items():
        total = sum(len(c) for c in terms.values())
        print(f"  {prog}: {total} core courses across {len(terms)} terms")


if __name__ == "__main__":
    main()
