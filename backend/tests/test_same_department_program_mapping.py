"""Mapping used only for course-search same-department boost (recommend_cosine)."""

from recommender.recommenders import _subject_prefixes_for_same_dept_search_boost


def test_management_engineering_maps_to_mse():
    assert _subject_prefixes_for_same_dept_search_boost("MGTE") == frozenset({"MSE"})
    assert _subject_prefixes_for_same_dept_search_boost("mgte") == frozenset({"MSE"})


def test_compe_and_ele_map_to_ece():
    assert _subject_prefixes_for_same_dept_search_boost("COMPE") == frozenset({"ECE"})
    assert _subject_prefixes_for_same_dept_search_boost("ELE") == frozenset({"ECE"})


def test_one_to_one_programs_use_self_as_prefix():
    assert _subject_prefixes_for_same_dept_search_boost("SYDE") == frozenset({"SYDE"})
    assert _subject_prefixes_for_same_dept_search_boost("ME") == frozenset({"ME"})
    assert _subject_prefixes_for_same_dept_search_boost("MSE") == frozenset({"MSE"})


def test_empty_program():
    assert _subject_prefixes_for_same_dept_search_boost("") == frozenset()
    assert _subject_prefixes_for_same_dept_search_boost("   ") == frozenset()
