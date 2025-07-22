import json
import pandas as pd
import numpy as np
import os

def load_course_data(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    rows = []
    for code, info in data.items():
        api = info.get('api_data', {})
        rows.append({
            'courseCode': code,
            'title': api.get('title', info.get('title', '')),
            'description': api.get('description', '')
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