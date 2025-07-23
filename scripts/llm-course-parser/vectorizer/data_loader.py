import json
import pandas as pd
import numpy as np
import os

def load_course_data(json_path):
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
    df['embedding'] = embeddings.tolist()
    df.to_pickle(pkl_path)
    np.save(npy_path, embeddings)

def load_embeddings(pkl_path, npy_path):
    df = pd.read_pickle(pkl_path)
    embeddings = np.load(npy_path)
    return df, embeddings

def embedding_file_exists(path):
    return os.path.exists(path)

def find_project_root(marker='requirements.txt'):
    current = os.path.abspath(os.getcwd())
    while True:
        if os.path.exists(os.path.join(current, marker)):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            raise RuntimeError("Project root not found")
        current = parent

def load_undergrad_courses():
    project_root = find_project_root()
    data_path = os.path.join(project_root, 'data/undergrad-courses.json')
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return set(data)

def load_grad_courses():
    project_root = find_project_root()
    data_path = os.path.join(project_root, 'data/grad-courses.json')
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return set(data)
