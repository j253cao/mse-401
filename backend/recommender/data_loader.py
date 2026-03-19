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
    """Load embeddings from disk.

    The pkl contains a DataFrame with an 'embedding' column (Python lists of floats)
    that duplicates the .npy data at ~10x memory cost. Drop it immediately.
    """
    df = pd.read_pickle(pkl_path)
    if 'embedding' in df.columns:
        df = df.drop(columns=['embedding'])
    embeddings = np.load(npy_path)
    return df, embeddings


def embedding_file_exists(path):
    """Check if embedding file exists."""
    return os.path.exists(path)


def find_project_root():
    """Get project root: two levels up from this file (recommender/ -> backend/ -> root)."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


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

