"""Global course weighting utilities.

This module computes universal (user-independent) weights for courses based on:
- Prerequisite graph structure (how often a course is a prerequisite, and depth)
- Presence in minors/options
- Faculty/subject-normalized versions of those features

The resulting weights are attached to the main course DataFrame as a
`global_weight` column and consumed by recommendation algorithms.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

import json
import math
import os

import numpy as np
import pandas as pd

from .search_weight_config import DEFAULT_SEARCH_WEIGHTS


@dataclass
class CourseGraph:
    """Directed prerequisite graph."""

    # prereq -> set of dependents (courses that list this as a prerequisite)
    children: Dict[str, set]
    # course -> set of direct prerequisites
    parents: Dict[str, set]


def _normalize_code(code: str) -> str:
    """Normalize course code to canonical uppercase/no-space form."""
    result = (code or "").strip().upper().replace(" ", "")
    if result.startswith("MSCI"):
        result = "MSE" + result[4:]
    return result


def build_dependency_graph(deps_json_path: str) -> CourseGraph:
    """
    Build prerequisite graph from course_dependencies_llm.json (canonical).

    The JSON shape is:
        {
          "AE392": {
            "prerequisites": {
              "groups": [ ... ],
              "program_requirements": [],
              "root_operator": "AND"
            },
            ...
          },
          ...
        }
    We treat every course code that appears inside prerequisite groups for
    a target course T as an edge prereq -> T.
    """
    if not os.path.exists(deps_json_path):
        return CourseGraph(children={}, parents={})

    with open(deps_json_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    children: Dict[str, set] = {}
    parents: Dict[str, set] = {}

    def add_edge(prereq: str, target: str) -> None:
        p = _normalize_code(prereq)
        t = _normalize_code(target)
        if not p or not t or p == t:
            return
        children.setdefault(p, set()).add(t)
        parents.setdefault(t, set()).add(p)
        children.setdefault(t, children.get(t, set()))
        parents.setdefault(p, parents.get(p, set()))

    def walk_groups(groups: list, target_code: str) -> None:
        for g in groups or []:
            if isinstance(g, str):
                add_edge(g, target_code)
                continue
            g_type = g.get("type")
            if g_type == "course":
                code = g.get("code") or ""
                add_edge(code, target_code)
            elif g_type == "prerequisite_group":
                walk_groups(g.get("courses") or [], target_code)

    for raw_code, info in raw.items():
        target_code = _normalize_code(raw_code)
        prereq_section = (info or {}).get("prerequisites")
        if isinstance(prereq_section, list):
            for item in prereq_section:
                if isinstance(item, str):
                    add_edge(item, target_code)
            continue
        groups = (prereq_section or {}).get("groups") or []
        walk_groups(groups, target_code)
        # Ensure every course appears in the dicts even if it has no edges
        children.setdefault(target_code, set())
        parents.setdefault(target_code, set())

    return CourseGraph(children=children, parents=parents)


def compute_graph_features(df: pd.DataFrame, graph: CourseGraph) -> pd.DataFrame:
    """
    Compute prerequisite outdegree and depth for each course in df.

    - prereq_outdegree: number of courses that list this course as a prereq
    - depth: longest prerequisite chain ending at this course
    """
    codes = df["courseCode"].astype(str).map(_normalize_code)
    children = graph.children
    parents = graph.parents

    # Outdegree: how many dependents this course has
    outdegree = []
    for code in codes:
        outdegree.append(len(children.get(code, set())))

    # Depth via DFS with memoization. Graph may not be a perfect DAG; guard cycles.
    memo: Dict[str, int] = {}
    visiting: set = set()

    def depth(code: str) -> int:
        if code in memo:
            return memo[code]
        if code in visiting:
            # Cycle detected; treat as depth 0 to avoid infinite recursion
            return 0
        visiting.add(code)
        preds = parents.get(code, set())
        if not preds:
            d = 0
        else:
            d = 1 + max(depth(p) for p in preds)
        visiting.remove(code)
        memo[code] = d
        return d

    depths = [depth(code) for code in codes]

    df = df.copy()
    df["prereq_outdegree"] = np.array(outdegree, dtype=int)
    df["depth"] = np.array(depths, dtype=int)
    return df


def load_minor_option_counts(programs_paths: Iterable[str]) -> Dict[str, int]:
    """
    Load minors/options JSON files and return per-course counts.

    Each file is an array of:
      {
        "program_name" | "option_name": "...",
        "course_lists": [
          {
            "list_description": "...",
            "required_count": int,
            "courses": [ "MSE546", ... ]
          },
          ...
        ]
      }
    We simply count how many course_lists any given course code appears in
    across all files.
    """
    counts: Dict[str, int] = {}

    for path in programs_paths:
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            items = json.load(f)

        for item in items:
            for cl in item.get("course_lists") or []:
                for code in cl.get("courses") or []:
                    norm = _normalize_code(code)
                    if not norm:
                        continue
                    counts[norm] = counts.get(norm, 0) + 1

    return counts


def _extract_codes_from_requirements(node: dict) -> List[str]:
    """Recursively extract course codes from a course_requirements tree."""
    if not isinstance(node, dict):
        return []
    if node.get("type") == "course":
        code = node.get("code", "")
        return [code] if code else []
    codes = []
    for child in node.get("children") or []:
        codes.extend(_extract_codes_from_requirements(child))
    return codes


def load_course_to_programs(
    programs_paths: Iterable[Tuple[str, str]],
) -> Dict[str, List[Dict[str, str]]]:
    """
    Load minors/options JSON files and return per-course program membership.

    Each path is (file_path, program_type) where program_type is "option" or "minor".
    Options use "option_name" and "course_requirements" (nested children tree).
    Minors use "program_name" and "course_lists".

    Returns:
        Dict mapping normalized course_code -> [{ "name": str, "type": "option"|"minor" }]
    """
    result: Dict[str, List[Dict[str, str]]] = {}

    for path, prog_type in programs_paths:
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            items = json.load(f)

        for item in items:
            name = item.get("option_name") or item.get("program_name") or ""
            if not name:
                continue
            entry = {"name": name, "type": prog_type}

            # Collect codes from flat course_lists (minors format)
            codes: List[str] = []
            for cl in item.get("course_lists") or []:
                codes.extend(cl.get("courses") or [])

            # Collect codes from nested course_requirements tree (options format)
            course_reqs = item.get("course_requirements")
            if isinstance(course_reqs, dict):
                codes.extend(_extract_codes_from_requirements(course_reqs))

            for code in codes:
                norm = _normalize_code(code)
                if not norm:
                    continue
                if norm not in result:
                    result[norm] = []
                # Avoid duplicate entries for same course in same program
                existing = {(e["name"], e["type"]) for e in result[norm]}
                if (name, prog_type) not in existing:
                    result[norm].append(entry)

    return result


def _bucket_normalize_series(
    s: pd.Series,
    method: str = "zscore",
    eps: float = 1e-6,
) -> pd.Series:
    """Normalize a numeric Series using either z-score or min-max."""
    values = s.to_numpy(dtype=float)
    if method == "zscore":
        mean = float(np.mean(values)) if len(values) > 0 else 0.0
        std = float(np.std(values)) if len(values) > 0 else 0.0
        if std < eps:
            return pd.Series(np.zeros_like(values), index=s.index)
        normed = (values - mean) / (std + eps)
        # Clip extreme z-scores to keep weights stable
        normed = np.clip(normed, -3.0, 3.0)
        return pd.Series(normed, index=s.index)
    # min-max
    v_min = float(np.min(values)) if len(values) > 0 else 0.0
    v_max = float(np.max(values)) if len(values) > 0 else 0.0
    if abs(v_max - v_min) < eps:
        return pd.Series(np.zeros_like(values), index=s.index)
    normed = (values - v_min) / (v_max - v_min + eps)
    return pd.Series(normed, index=s.index)


def _numeric_series_column(df: pd.DataFrame, col: str) -> pd.Series:
    """Return a single numeric Series for ``col``, tolerating duplicate column names."""
    if col not in df.columns:
        raise KeyError(col)
    s = df[col]
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    return pd.to_numeric(s, errors="coerce")


def apply_bucket_normalization(
    df: pd.DataFrame,
    bucket_col: str = "subjectCode",
    eps: float = 1e-6,
) -> pd.DataFrame:
    """
    Normalize graph/program features within faculty/subject buckets.

    For each bucket value (e.g., subjectCode):
      - f_prereq_norm: z-score of log(1 + prereq_outdegree)
      - f_depth_norm:  z-score of depth
      - f_minor_norm:  z-score of minor_count
    """
    df = df.copy()
    # Prepare raw features with safe defaults (avoid DataFrame.get, which can confuse dtypes)
    for _feat_col, _default in (("prereq_outdegree", 0), ("depth", 0), ("minor_count", 0)):
        if _feat_col in df.columns:
            df[_feat_col] = _numeric_series_column(df, _feat_col).fillna(_default).astype(int)
        else:
            df[_feat_col] = _default

    log_prereq = df["prereq_outdegree"].apply(lambda x: math.log1p(max(int(x), 0)))
    depth = df["depth"].astype(float)
    minor_count = df["minor_count"].astype(float)

    bucket_vals = df[bucket_col].fillna("UNKNOWN").astype(str)
    df["bucket"] = bucket_vals

    f_prereq_norm = np.zeros(len(df), dtype=float)
    f_depth_norm = np.zeros(len(df), dtype=float)
    f_minor_norm = np.zeros(len(df), dtype=float)

    for bucket_value, idxs in df.groupby("bucket").groups.items():
        idxs_list = list(idxs)
        f_prereq_norm[idxs_list] = _bucket_normalize_series(
            log_prereq.iloc[idxs_list], method="zscore", eps=eps
        ).to_numpy()
        f_depth_norm[idxs_list] = _bucket_normalize_series(
            depth.iloc[idxs_list], method="zscore", eps=eps
        ).to_numpy()
        f_minor_norm[idxs_list] = _bucket_normalize_series(
            minor_count.iloc[idxs_list], method="zscore", eps=eps
        ).to_numpy()

    df["prereq_score_norm"] = f_prereq_norm
    df["depth_score_norm"] = f_depth_norm
    df["minor_score_norm"] = f_minor_norm
    return df


def _evaluate_node(node: dict, completed_set: set) -> tuple:
    """Recursively evaluate a requirement tree node.

    Returns (satisfied: bool, completed_courses: list[str])
    """
    if node.get("type") == "course":
        code = (node.get("code") or "").upper().replace(" ", "")
        satisfied = code in completed_set
        return satisfied, ([node["code"]] if satisfied else [])

    children = node.get("children") or []
    child_results = [_evaluate_node(c, completed_set) for c in children]
    all_completed = [course for _, courses in child_results for course in courses]

    if node.get("type") == "AND":
        satisfied = all(r[0] for r in child_results)
        return satisfied, all_completed

    # OR node
    required = node.get("required_count")
    if required is None:
        required = len(children)
    satisfied_count = sum(1 for r in child_results if r[0])
    return satisfied_count >= required, all_completed


def _count_leaf_courses(node: dict) -> int:
    """Count the number of leaf course nodes in a requirement subtree."""
    if node.get("type") == "course":
        return 1
    return sum(_count_leaf_courses(c) for c in (node.get("children") or []))


def compute_options_progress(
    completed_courses: List[str],
    options_data: List[dict],
) -> List[dict]:
    """
    Compute per-option progress for a student's completed courses.

    Args:
        completed_courses: List of course codes the student has completed.
        options_data: Parsed contents of all_options.json.

    Returns:
        List of dicts matching the frontend OptionProgress shape, sorted
        descending by completion_ratio.
    """
    completed_set = {c.upper().replace(" ", "") for c in completed_courses}

    results = []
    for option in options_data:
        course_requirements = option.get("course_requirements") or {}
        children = course_requirements.get("children") or []
        if not children:
            continue

        lists = []
        for child in children:
            satisfied, completed = _evaluate_node(child, completed_set)
            if child.get("type") == "course":
                required_count = 1
                list_name = child.get("code", "")
            elif child.get("type") == "AND":
                required_count = len(child.get("children") or [])
                list_name = child.get("description", "")
            else:  # OR
                required_count = child.get("required_count") or len(child.get("children") or [])
                list_name = child.get("description", "")

            lists.append({
                "list_name": list_name,
                "required_count": required_count,
                "total_courses": _count_leaf_courses(child),
                "completed_courses": completed,
                "is_satisfied": satisfied,
            })

        satisfied_count = sum(1 for lst in lists if lst["is_satisfied"])
        total_lists = len(lists)
        results.append({
            "option_name": option.get("option_name", ""),
            "lists": lists,
            "satisfied_count": satisfied_count,
            "total_lists": total_lists,
            "completion_ratio": satisfied_count / total_lists if total_lists > 0 else 0.0,
        })

    results.sort(key=lambda x: x["completion_ratio"], reverse=True)
    return results


def _option_list_courses(options_data: List[dict]) -> List[tuple]:
    """Build (option_name, list_name, set of normalized course codes) for each list in each option."""
    out = []
    for option in options_data:
        option_name = option.get("option_name", "")
        course_requirements = option.get("course_requirements") or {}
        children = course_requirements.get("children") or []
        for child in children:
            list_name = (child.get("description") or child.get("code") or "").strip()
            codes = _extract_codes_from_requirements(child)
            norm_set = {_normalize_code(c) for c in codes if _normalize_code(c)}
            if option_name and norm_set:
                out.append((option_name, list_name, norm_set))
    return out


# Option-completion boost tiers: (option_lists_remaining, list_remaining) -> multiplier (1 + boost)
# Only options with at least one list completed are considered.
# Tier 1: one list left for option AND that list has ≤2 courses left (biggest boost).
# Tier 2: one list left for option OR list has ≤2 courses left.
# Tier 3: any other incomplete list in an option with ≥1 list done.
OPTION_BOOST_TIER1 = DEFAULT_SEARCH_WEIGHTS["option_boost"]["tier1"]   # 15% — last list to finish option, list almost done
OPTION_BOOST_TIER2 = DEFAULT_SEARCH_WEIGHTS["option_boost"]["tier2"]  # 10% — last list for option, or list almost done
OPTION_BOOST_TIER3 = DEFAULT_SEARCH_WEIGHTS["option_boost"]["tier3"]  # 5%  — other incomplete lists in started options


def get_option_boost_multipliers(
    options_data: List[dict],
    completed_courses: List[str],
    tier1: float = OPTION_BOOST_TIER1,
    tier2: float = OPTION_BOOST_TIER2,
    tier3: float = OPTION_BOOST_TIER3,
) -> Dict[str, float]:
    """
    Return per-course multipliers (1.0 + boost) for option-completion boosting.

    Only considers options where the user has completed at least one list.
    Boosts combine option-level progress (how many lists left for the option)
    and list-level progress (how many courses left in that list). Completed
    lists are ignored. If a course appears in multiple lists, the highest
    multiplier is used.
    """
    progress = compute_options_progress(completed_courses, options_data)
    option_list_courses = _option_list_courses(options_data)
    list_codes_map = {(opt, lst): codes for opt, lst, codes in option_list_courses}

    multipliers: Dict[str, float] = {}

    for opt in progress:
        option_name = opt.get("option_name", "")
        satisfied_count = opt.get("satisfied_count", 0)
        total_lists = opt.get("total_lists", 0)
        # Only options where user has completed at least one list
        if satisfied_count < 1 or total_lists < 1:
            continue
        option_lists_remaining = total_lists - satisfied_count

        for lst in opt.get("lists") or []:
            if lst.get("is_satisfied"):
                continue
            required = lst.get("required_count", 0)
            completed_list = lst.get("completed_courses") or []
            completed_count = min(required, len(completed_list))
            list_remaining = max(0, required - completed_count)
            list_name = lst.get("list_name", "")

            # Tier: bigger boost when option is 1 list away and list is almost done
            if option_lists_remaining == 1 and list_remaining <= 2:
                mult = 1.0 + tier1
            elif option_lists_remaining == 1 or list_remaining <= 2:
                mult = 1.0 + tier2
            else:
                mult = 1.0 + tier3

            key = (option_name, list_name)
            if key not in list_codes_map:
                continue
            for code in list_codes_map[key]:
                multipliers[code] = max(multipliers.get(code, 1.0), mult)

    return multipliers


def compute_global_weight(
    df: pd.DataFrame,
    gamma_prereq: float = DEFAULT_SEARCH_WEIGHTS["global_weight"]["gamma_prereq"],
    gamma_depth: float = DEFAULT_SEARCH_WEIGHTS["global_weight"]["gamma_depth"],
    gamma_minor: float = DEFAULT_SEARCH_WEIGHTS["global_weight"]["gamma_minor"],
) -> pd.Series:
    """
    Combine normalized features into a single global_weight Series:

        global_weight = γ1 * prereq_score_norm
                      + γ2 * depth_score_norm
                      + γ3 * minor_score_norm

    The result is loosely in a bounded range because we clip z-scores.
    """
    def _feat(name: str) -> pd.Series:
        if name not in df.columns:
            return pd.Series(0.0, index=df.index, dtype=float)
        s = _numeric_series_column(df, name).astype(float)
        return s.fillna(0.0)

    prereq = _feat("prereq_score_norm")
    depth = _feat("depth_score_norm")
    minor = _feat("minor_score_norm")
    weights = (
        gamma_prereq * prereq
        + gamma_depth * depth
        + gamma_minor * minor
    )
    return pd.Series(weights, index=df.index, name="global_weight")

