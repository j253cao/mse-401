import os
import pickle
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from vectorizer.data_loader import load_course_data, save_embeddings, load_embeddings, embedding_file_exists
from vectorizer.embedding_generators import generate_tfidf_svd_embeddings, generate_bert_embeddings
from vectorizer.recommenders import (
    recommend_cosine, recommend_faiss, recommend_mmr, recommend_graph,
    recommend_fuzzy_multi, recommend_keyword_overlap, recommend_bert, recommend_hybrid_ensemble
)
from vectorizer.utils import export_results_to_excel

def get_abs_path(*parts):
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    return os.path.join(PROJECT_ROOT, *parts)

# Module-level cache
_cached = {
    'df': None,
    'embeddings': None,
    'tfidf': None,
    'svd': None,
    'model': None,
    'bert_embeddings': None,
    'data_file': None
}

def _load_all(data_file):
    # Only reload if data_file changes
    if _cached['data_file'] != data_file:
        _cached['df'] = None
        _cached['embeddings'] = None
        _cached['tfidf'] = None
        _cached['svd'] = None
        _cached['model'] = None
        _cached['bert_embeddings'] = None
        _cached['data_file'] = data_file
    data_json = get_abs_path('data', data_file)
    tfidf_pkl = get_abs_path('data', 'tfidf_vectorizer.pkl')
    svd_pkl = get_abs_path('data', 'svd_model.pkl')
    emb_pkl = get_abs_path('data', 'course_embeddings.pkl')
    emb_npy = get_abs_path('data', 'course_embeddings.npy')
    bert_npy = get_abs_path('data', 'course_bert_embeddings.npy')
    # DataFrame and embeddings
    if _cached['df'] is None or _cached['embeddings'] is None:
        if not os.path.exists(emb_pkl):
            df = load_course_data(data_json)
            tfidf, svd, embeddings = generate_tfidf_svd_embeddings(df['description'])
            save_embeddings(df, embeddings, emb_pkl, emb_npy)
            with open(tfidf_pkl, 'wb') as f: pickle.dump(tfidf, f)
            with open(svd_pkl, 'wb') as f: pickle.dump(svd, f)
        else:
            df, embeddings = load_embeddings(emb_pkl, emb_npy)
        _cached['df'] = df
        _cached['embeddings'] = embeddings
    # TFIDF and SVD
    if _cached['tfidf'] is None:
        with open(tfidf_pkl, 'rb') as f: _cached['tfidf'] = pickle.load(f)
    if _cached['svd'] is None:
        with open(svd_pkl, 'rb') as f: _cached['svd'] = pickle.load(f)
    # BERT model and embeddings
    if _cached['bert_embeddings'] is None:
        if not embedding_file_exists(bert_npy):
            model, bert_embeddings = generate_bert_embeddings(_cached['df']['description'].fillna('').tolist())
            np.save(bert_npy, bert_embeddings)
            _cached['model'] = model
            _cached['bert_embeddings'] = bert_embeddings
        else:
            from sentence_transformers import SentenceTransformer
            _cached['model'] = SentenceTransformer('all-MiniLM-L6-v2')
            _cached['bert_embeddings'] = np.load(bert_npy)
    elif _cached['model'] is None:
        from sentence_transformers import SentenceTransformer
        _cached['model'] = SentenceTransformer('all-MiniLM-L6-v2')
    return _cached['df'], _cached['embeddings'], _cached['tfidf'], _cached['svd'], _cached['model'], _cached['bert_embeddings']

def get_recommendations(
    search_queries: List[str],
    data_file: str = 'course-api-data.json',
    method: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None
) -> List[List[Dict[str, Any]]]:
    """
    Get course recommendations based on search queries and optional filters.
    
    Args:
        search_queries: List of search query strings
        data_file: Name of the data file to use
        method: Specific recommendation method to use (if None, uses all methods)
        filters: Optional dictionary of filters to apply to the results
            Example: {
                "include_undergrad": bool,
                "include_grad": bool,
                "department": str,
                ... other filters as needed ...
            }
    
    Returns:
        List of results for each query, where each result is a list of course recommendations
    """
    df, embeddings, tfidf, svd, model, bert_embeddings = _load_all(data_file)
    
    all_methods = [
        ("cosine", lambda q: recommend_cosine(q, tfidf, svd, embeddings, df)),
        ("faiss", lambda q: recommend_faiss(q, tfidf, svd, embeddings, df)),
        ("mmr", lambda q: recommend_mmr(q, tfidf, svd, embeddings, df)),
        ("graph", lambda q: recommend_graph(q, tfidf, svd, embeddings, df)),
        ("fuzzy_multi", lambda q: recommend_fuzzy_multi(q, df)),
        ("keyword_overlap", lambda q: recommend_keyword_overlap(q, df)),
        ("bert", lambda q: recommend_bert(q, model, bert_embeddings, df)),
        ("hybrid_ensemble", lambda q: recommend_hybrid_ensemble(q, df, tfidf, svd, embeddings, embeddings, model, bert_embeddings)),
    ]
    
    if method is not None:
        methods = [m for m in all_methods if m[0] == method]
        if not methods:
            raise ValueError(f"Unknown method: {method}")
    else:
        methods = all_methods
    
    all_results = []
    for search_query in search_queries:
        query_results = []
        for method_name, method_func in methods:
            try:
                # Get recommendations using the method
                results = method_func(search_query)
                
                # Convert results to list format
                for rank, (_, row) in enumerate(results.iterrows(), 1):
                    score_col = None
                    for col in ['similarity', 'fuzzy_score', 'keyword_score', 'bert_score', 'hybrid_score', 'score']:
                        if col in row.index:
                            score_col = col
                            break
                    
                    result = {
                        "search_query": search_query,
                        "method": method_name,
                        "rank": rank,
                        "course_code": row['courseCode'],
                        "title": row['title'],
                        "description": row['description'],
                        "score": row[score_col] if score_col else 0
                    }
                    
                    # Add any additional fields from the DataFrame that might be needed for filtering
                    for col in row.index:
                        if col not in result and col not in ['similarity', 'fuzzy_score', 'keyword_score', 'bert_score', 'hybrid_score', 'score']:
                            result[col] = row[col]
                    
                    query_results.append(result)
                    
            except Exception as e:
                print(f"Error with method {method_name} on query '{search_query}': {e}")
                continue
        
        all_results.append(query_results)
    
    return all_results

def main():
    search_queries = [
        "machine learning algorithms and data science",
        "analyze financial statements using Python and Excel",
        "a course about dinosaurs, fossils and ancient civilizations"
    ]
    results = get_recommendations(search_queries)
    # Optionally, export to Excel for CLI use
    all_dfs = [pd.DataFrame(r) for r in results]
    excel_out = get_abs_path('recommendations_results.xlsx')
    export_results_to_excel(all_dfs, excel_out, [f"Query{i+1}_Results" for i in range(len(search_queries))])
    print(f"Excel file '{excel_out}' created with {len(search_queries)} sheets, one per query.")

if __name__ == "__main__":
    main() 