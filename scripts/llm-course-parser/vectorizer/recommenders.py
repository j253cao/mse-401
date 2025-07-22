import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from difflib import SequenceMatcher
import faiss
import networkx as nx
import time

def recommend_cosine(query, tfidf, svd, emb, df, top_k=10):
    t0 = time.time()
    # Vectorize query
    q_vec = svd.transform(tfidf.transform([query]))
    t1 = time.time()
    q_vec = q_vec.reshape(1, -1)
    # Normalize embeddings and query, avoid division by zero
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    norms[norms == 0] = 1
    emb_norm = emb / norms
    q_norm = q_vec / np.linalg.norm(q_vec)
    # Compute cosine similarity (vectorized)
    sims = np.dot(emb_norm, q_norm.flatten())
    # Replace NaN and inf with 0
    sims = np.nan_to_num(sims, nan=0.0, posinf=0.0, neginf=0.0)
    t2 = time.time()
    # Get top_k indices using argpartition (O(N))
    if top_k < len(sims):
        idxs = np.argpartition(-sims, top_k)[:top_k]
        idxs = idxs[np.argsort(-sims[idxs])]
    else:
        idxs = np.argsort(-sims)
    t3 = time.time()
    # Build result DataFrame
    result = df.iloc[idxs][['courseCode', 'title', 'description']].copy()
    result['similarity'] = sims[idxs]
    result['similarity'] = np.nan_to_num(result['similarity'], nan=0.0, posinf=0.0, neginf=0.0)
    print(f"[recommend_cosine] Vectorization: {t1-t0:.4f}s, Cosine: {t2-t1:.4f}s, Top-k: {t3-t2:.4f}s, Total: {t3-t0:.4f}s")
    return result

def recommend_faiss(query, tfidf, svd, emb, df, top_k=10):
    emb = emb.astype('float32')
    faiss.normalize_L2(emb)
    index = faiss.IndexFlatIP(emb.shape[1])
    index.add(emb)
    q = svd.transform(tfidf.transform([query])).astype('float32')
    faiss.normalize_L2(q)
    D, I = index.search(q, top_k)
    return df.iloc[I[0]][['courseCode','title','description']].assign(similarity=D[0])

def recommend_mmr(query, tfidf, svd, emb, df, top_k=10, lmbda=0.7):
    q_vec      = svd.transform(tfidf.transform([query])).flatten()
    sims       = cosine_similarity(emb, q_vec.reshape(1,-1)).flatten()
    candidates = list(range(len(sims)))
    selected   = []
    for _ in range(top_k):
        if not selected:
            idx = int(np.argmax(sims))
        else:
            mmr_scores = []
            for i in candidates:
                rel = sims[i]
                red = max(cosine_similarity(emb[selected], emb[i].reshape(1,-1)).flatten())
                mmr_scores.append((i, lmbda*rel - (1-lmbda)*red))
            idx = max(mmr_scores, key=lambda x: x[1])[0]
        selected.append(idx)
        candidates.remove(idx)
    return df.iloc[selected][['courseCode','title','description']].assign(similarity=sims[selected])

def recommend_graph(query, tfidf, svd, emb, df, top_k=10):
    q_vec = svd.transform(tfidf.transform([query]))
    sims  = cosine_similarity(emb, q_vec).flatten()
    G = nx.DiGraph()
    G.add_node('query')
    for i, code in enumerate(df['courseCode']):
        G.add_edge('query', code, weight=float(sims[i]))
    pr = nx.pagerank(G, alpha=0.85, personalization={'query':1.0})
    ranked = sorted(((c,sc) for c,sc in pr.items() if c!='query'), key=lambda x: x[1], reverse=True)[:top_k]
    codes  = [c for c,_ in ranked]
    scores = [s for _,s in ranked]
    return df[df['courseCode'].isin(codes)][['courseCode','title','description']].assign(score=scores)

def fuzzy_similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def recommend_fuzzy_multi(query, df, top_k=10, weights={'title': 0.4, 'description': 0.5, 'code': 0.1}):
    query_lower = query.lower()
    scores = []
    for idx, row in df.iterrows():
        title_sim = fuzzy_similarity(query_lower, str(row['title']))
        desc_sim = fuzzy_similarity(query_lower, str(row['description']))
        code_sim = fuzzy_similarity(query_lower, str(row['courseCode']))
        total_score = (weights['title'] * title_sim + 
                      weights['description'] * desc_sim + 
                      weights['code'] * code_sim)
        scores.append((idx, total_score))
    scores.sort(key=lambda x: x[1], reverse=True)
    top_indices = [idx for idx, _ in scores[:top_k]]
    top_scores = [score for _, score in scores[:top_k]]
    return df.iloc[top_indices][['courseCode','title','description']].assign(fuzzy_score=top_scores)

def extract_keywords(text, min_length=3):
    import re
    stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'this', 'that', 'these', 'those', 'a', 'an'}
    words = re.findall(r'\b\w+\b', text.lower())
    return [w for w in words if len(w) >= min_length and w not in stop_words]

def recommend_keyword_overlap(query, df, top_k=10):
    query_keywords = set(extract_keywords(query))
    scores = []
    for idx, row in df.iterrows():
        title_keywords = set(extract_keywords(str(row['title'])))
        desc_keywords = set(extract_keywords(str(row['description'])))
        title_overlap = len(query_keywords.intersection(title_keywords))
        desc_overlap = len(query_keywords.intersection(desc_keywords))
        total_keywords = len(title_keywords.union(desc_keywords))
        if total_keywords > 0:
            score = (2 * title_overlap + desc_overlap) / np.sqrt(total_keywords)
        else:
            score = 0
        scores.append((idx, score))
    scores.sort(key=lambda x: x[1], reverse=True)
    top_indices = [idx for idx, _ in scores[:top_k]]
    top_scores = [score for _, score in scores[:top_k]]
    return df.iloc[top_indices][['courseCode','title','description']].assign(keyword_score=top_scores)

def recommend_bert(query, model, bert_embeddings, df, top_k=10):
    query_embed = model.encode([query])
    sims = cosine_similarity(query_embed, bert_embeddings).flatten()
    top_indices = sims.argsort()[::-1][:top_k]
    return df.iloc[top_indices][['courseCode', 'title', 'description']].assign(bert_score=sims[top_indices])

def recommend_hybrid_ensemble(query, df, tfidf, svd, emb, faiss_emb, model, bert_embeddings, top_k=10, method_weights=None):
    if method_weights is None:
        method_weights = {
            'cosine': 0.2,
            'fuzzy': 0.2,
            'keyword': 0.2,
            'faiss': 0.2,
            'bert': 0.2
        }
    cosine_results = recommend_cosine(query, tfidf, svd, emb, df, top_k=len(df))
    fuzzy_results = recommend_fuzzy_multi(query, df, top_k=len(df))
    keyword_results = recommend_keyword_overlap(query, df, top_k=len(df))
    faiss_results = recommend_faiss(query, tfidf, svd, faiss_emb, df, top_k=len(df))
    bert_results = recommend_bert(query, model, bert_embeddings, df, top_k=len(df))
    def get_score(results, code, col):
        row = results[results['courseCode'] == code]
        return row[col].iloc[0] if not row.empty else 0
    combined_scores = {}
    for idx, code in enumerate(df['courseCode']):
        score = (
            method_weights['cosine'] * get_score(cosine_results, code, 'similarity') +
            method_weights['fuzzy'] * get_score(fuzzy_results, code, 'fuzzy_score') +
            method_weights['keyword'] * get_score(keyword_results, code, 'keyword_score') +
            method_weights['faiss'] * get_score(faiss_results, code, 'similarity') +
            method_weights['bert'] * get_score(bert_results, code, 'bert_score')
        )
        combined_scores[idx] = score
    sorted_indices = sorted(combined_scores.keys(), key=lambda x: combined_scores[x], reverse=True)
    top_indices = sorted_indices[:top_k]
    top_scores = [combined_scores[idx] for idx in top_indices]
    return df.iloc[top_indices][['courseCode','title','description']].assign(hybrid_score=top_scores) 