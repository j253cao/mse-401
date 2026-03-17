"""Embedding generation utilities for course recommendations."""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD


def generate_tfidf_svd_embeddings(descriptions, max_features=5000, n_components=100, random_state=42):
    """Generate TF-IDF + SVD embeddings for course descriptions."""
    tfidf = TfidfVectorizer(max_features=max_features, stop_words='english')
    X_tfidf = tfidf.fit_transform(descriptions)
    svd = TruncatedSVD(n_components=n_components, random_state=random_state)
    embeddings = svd.fit_transform(X_tfidf)
    return tfidf, svd, embeddings


def generate_bert_embeddings(descriptions, model_name='all-MiniLM-L6-v2'):
    """Generate BERT embeddings for course descriptions.
    Requires sentence-transformers: pip install sentence-transformers
    """
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_name)
    bert_embeddings = model.encode(descriptions, show_progress_bar=True)
    return model, bert_embeddings

