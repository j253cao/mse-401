"""Data loading utilities for course recommendations."""

import json
import pandas as pd
import numpy as np
import os


def load_course_data(json_path):
    """Load course data from JSON file into a DataFrame."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    rows = []

    for code, info in data.items():
        title = info.get('title', '')
        description = info.get('description', '')

        # If description is empty, use the title instead
        if not description or description.strip() == '':
            description = title

        rows.append({
            'courseCode': code,
            'title': title,
            'description': description
        })
    return pd.DataFrame(rows)


def save_embeddings(df, embeddings, pkl_path, npy_path):
    """Save embeddings to disk."""
    df['embedding'] = embeddings.tolist()
    df.to_pickle(pkl_path)
    np.save(npy_path, embeddings)


def load_embeddings(pkl_path, npy_path):
    """Load embeddings from disk."""
    df = pd.read_pickle(pkl_path)
    embeddings = np.load(npy_path)
    return df, embeddings


def embedding_file_exists(path):
    """Check if embedding file exists."""
    return os.path.exists(path)


def find_project_root(marker='README.md'):
    """
    Find project root by looking for marker file.
    Uses the file's location rather than current working directory for reliability.
    """
    # Start from this file's directory and go up
    current = os.path.abspath(os.path.dirname(__file__))
    # Go up from recommender/ to backend/ to project root
    current = os.path.dirname(os.path.dirname(current))
    
    # Verify by checking for marker file
    if os.path.exists(os.path.join(current, marker)):
        return current
    
    # Fallback: search upward from current directory
    search_current = current
    while True:
        if os.path.exists(os.path.join(search_current, marker)):
            return search_current
        parent = os.path.dirname(search_current)
        if parent == search_current:
            raise RuntimeError(f"Project root not found (looking for {marker})")
        search_current = parent


def load_undergrad_courses():
    """Load set of undergraduate course codes."""
    project_root = find_project_root()
    data_path = os.path.join(project_root, 'data', 'courses', 'undergrad-courses.json')
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return set(data)


def load_grad_courses():
    """Load set of graduate course codes."""
    project_root = find_project_root()
    data_path = os.path.join(project_root, 'data', 'courses', 'grad-courses.json')
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return set(data)

