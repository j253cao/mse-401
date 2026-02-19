"""
Delete cached embeddings and regenerate them from course-api-new-data.json.

Run from project root:
    python scripts/regenerate_embeddings.py
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'backend'))

EMBEDDING_FILES = [
    'data/embeddings/tfidf_vectorizer.pkl',
    'data/embeddings/svd_model.pkl',
    'data/embeddings/course_embeddings.pkl',
    'data/embeddings/course_embeddings.npy',
    'data/embeddings/course_bert_embeddings.npy',
]


def main():
    deleted = 0
    for rel_path in EMBEDDING_FILES:
        path = os.path.join(PROJECT_ROOT, rel_path)
        if os.path.exists(path):
            os.remove(path)
            print(f"Deleted: {rel_path}")
            deleted += 1

    if deleted == 0:
        print("No cached embeddings found. They will be generated on first recommendation request.")
        return

    print(f"\nDeleted {deleted} file(s). Regenerating embeddings...")

    # Trigger regeneration by running a recommendation
    from recommender.main import get_recommendations

    results = get_recommendations(
        ["machine learning"],
        data_file='course-api-new-data.json',
        method='cosine',
    )
    print(f"Regenerated embeddings. Sample result: {len(results[0])} recommendations returned.")


if __name__ == '__main__':
    main()
