"""Main recommendation engine module."""

import json
import os
import pickle
import re
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from .data_loader import load_course_data, save_embeddings, load_embeddings, embedding_file_exists
from .embedding_generators import generate_tfidf_svd_embeddings, generate_bert_embeddings
from .recommenders import (
    recommend_cosine, recommend_faiss, recommend_mmr, recommend_graph,
    recommend_fuzzy_multi, recommend_keyword_overlap, recommend_bert, recommend_hybrid_ensemble
)
from .utils import export_results_to_excel
from .weights import (
    build_dependency_graph,
    compute_graph_features,
    load_minor_option_counts,
    apply_bucket_normalization,
    compute_global_weight,
)
from .data_loader import load_undergrad_courses, load_grad_courses


def get_abs_path(*parts):
    """Get absolute path relative to project root."""
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
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
    """Load all required data and models."""
    # Only reload if data_file changes
    if _cached['data_file'] != data_file:
        _cached['df'] = None
        _cached['embeddings'] = None
        _cached['tfidf'] = None
        _cached['svd'] = None
        _cached['model'] = None
        _cached['bert_embeddings'] = None
        _cached['data_file'] = data_file
    
    data_json = get_abs_path('data', 'courses', data_file)
    tfidf_pkl = get_abs_path('data', 'embeddings', 'tfidf_vectorizer.pkl')
    svd_pkl = get_abs_path('data', 'embeddings', 'svd_model.pkl')
    emb_pkl = get_abs_path('data', 'embeddings', 'course_embeddings.pkl')
    emb_npy = get_abs_path('data', 'embeddings', 'course_embeddings.npy')
    bert_npy = get_abs_path('data', 'embeddings', 'course_bert_embeddings.npy')
    
    # Filter function for work terms and seminars
    def is_regular_course(row):
        title = row['title'].lower() if isinstance(row['title'], str) else ""
        code = row['courseCode'].lower() if isinstance(row['courseCode'], str) else ""
        description = row['description'].lower() if isinstance(row['description'], str) else ""
        return not (
            "seminar" in title or "seminar" in code or
            "work term" in title or "work term" in code or
            "coop" in title or "coop" in code or
            "co-op" in title or "co-op" in code or
            description.startswith("Work-term report") or
            description.startswith("General seminar") or
            "seminar" in description or
            "work term" in description or
            "coop" in description or
            "co-op" in description
        )
    
    # DataFrame and embeddings
    if _cached['df'] is None or _cached['embeddings'] is None:
        if not os.path.exists(emb_pkl):
            df = load_course_data(data_json)
            # Apply initial filtering
            df = df[df.apply(is_regular_course, axis=1)].reset_index(drop=True)
            tfidf, svd, embeddings = generate_tfidf_svd_embeddings(df['description'])
            save_embeddings(df, embeddings, emb_pkl, emb_npy)
            with open(tfidf_pkl, 'wb') as f:
                pickle.dump(tfidf, f)
            with open(svd_pkl, 'wb') as f:
                pickle.dump(svd, f)
        else:
            df, embeddings = load_embeddings(emb_pkl, emb_npy)
            # Apply filtering to loaded data as well
            df = df[df.apply(is_regular_course, axis=1)].reset_index(drop=True)
            # Filter embeddings to match filtered dataframe
            embeddings = embeddings[:len(df)]

        # Attach additional metadata and global weights
        # Load full course JSON to enrich df with subject/faculty information
        with open(data_json, 'r', encoding='utf-8') as f:
            raw_courses = json.load(f)
        # Build lookup keyed by courseCode as in df
        meta_rows = []
        for code in df['courseCode']:
            info = raw_courses.get(code, {})
            meta_rows.append({
                'subjectCode': info.get('subjectCode'),
                'associatedAcademicGroupCode': info.get('associatedAcademicGroupCode'),
            })
        meta_df = pd.DataFrame(meta_rows, index=df.index)
        df = pd.concat([df, meta_df], axis=1)

        # Compute graph-based features from dependencies
        deps_path = get_abs_path('data', 'dependencies', 'course_dependencies.json')
        graph = build_dependency_graph(deps_path)
        df = compute_graph_features(df, graph)

        # Load minor/option course counts
        programs_path = get_abs_path('data', 'programs', 'all_programs.json')
        options_path = get_abs_path('data', 'programs', 'all_options.json')
        minor_counts = load_minor_option_counts([programs_path, options_path])
        df['minor_count'] = df['courseCode'].astype(str).map(
            lambda c: minor_counts.get(c.upper().replace(' ', ''), 0)
        ).astype(int)

        # Normalize features within subject buckets and compute final global_weight
        df = apply_bucket_normalization(df, bucket_col='subjectCode')
        df['global_weight'] = compute_global_weight(df)

        _cached['df'] = df
        _cached['embeddings'] = embeddings
    
    # TFIDF and SVD
    if _cached['tfidf'] is None:
        with open(tfidf_pkl, 'rb') as f:
            _cached['tfidf'] = pickle.load(f)
    if _cached['svd'] is None:
        with open(svd_pkl, 'rb') as f:
            _cached['svd'] = pickle.load(f)
    
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
    data_file: str = 'course-api-new-data.json',
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
        ("cosine", lambda q: recommend_cosine(q, tfidf, svd, embeddings, df, filters=filters)),
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


# Engineering departments for high-value course filtering (matches API)
ENGINEERING_DEPARTMENTS = (
    "AE", "BME", "CHE", "CIVE", "ECE", "ENVE", "GENE", "GEOE",
    "ME", "MTE", "MSE", "NE", "SE", "SYDE",
)


def _is_100_level(course_code: str) -> bool:
    """Check if course is 100-level (first year)."""
    match = re.search(r"\d+", str(course_code))
    if match:
        num = int(match.group())
        return 100 <= num <= 199
    return False


def _normalize_course_code(code: str) -> str:
    """Normalize to uppercase, no spaces."""
    return (code or "").strip().upper().replace(" ", "")


def get_high_value_courses(
    level: Optional[str] = None,
    limit: int = 12,
    program: Optional[str] = None,
    depth_penalty: float = 0.15,
    temperature: float = 0.5,
    data_file: str = "course-api-new-data.json",
) -> List[Dict[str, Any]]:
    """
    Get courses ranked by global_weight (common prereqs, many options/minors).
    No search query needed—solves cold start for first-year students.

    Args:
        level: Incoming level (e.g., "1A", "1B"). If 1A or 1B, filter to 100-level only.
        limit: Max courses to return (default 12).
        program: Program code (e.g., "AE", "CHE"). When level is 1A/1B, boosts courses in program's 1A/1B core.
        depth_penalty: Penalty per prerequisite depth level (higher depth = lower score). Default 0.15.
        temperature: Sampling temperature (0=deterministic, higher=more variety). Default 0.5.
        data_file: Course data file name.

    Returns:
        List of course dicts with course_code, title, description, score.
    """
    df, _, _, _, _, _ = _load_all(data_file)
    undergrad = load_undergrad_courses()

    # Filter: engineering depts (subjectCode or courseCode prefix), undergrad only
    codes = df["courseCode"].astype(str)
    dept_match = df["subjectCode"].isin(ENGINEERING_DEPARTMENTS) | codes.str.startswith(
        tuple(ENGINEERING_DEPARTMENTS)
    )
    mask = dept_match & df["courseCode"].isin(undergrad)

    # First-year filter: 100-level only when level is 1A or 1B
    if level in ("1A", "1B"):
        mask = mask & df["courseCode"].apply(_is_100_level)

    filtered = df[mask].copy()
    if filtered.empty:
        return []

    # Load program core courses: exclude from results (they're already in their curriculum)
    core_path = get_abs_path("data", "degree_requirements", "program_core_courses.json")
    program_core_exclude: set[str] = set()
    if program and os.path.exists(core_path):
        with open(core_path, "r", encoding="utf-8") as f:
            core_data = json.load(f)
        prog_data = core_data.get(program.upper(), {})
        for term, courses in prog_data.items():
            for c in courses:
                program_core_exclude.add(_normalize_course_code(c))

    # Exclude courses that are part of the student's core curriculum
    if program_core_exclude:
        exclude_mask = ~filtered["courseCode"].apply(
            lambda c: _normalize_course_code(str(c)) in program_core_exclude
        )
        filtered = filtered[exclude_mask].copy()
        if filtered.empty:
            return []

    # Compute adjusted score: global_weight - depth penalty
    gw = filtered["global_weight"].astype(float)
    depth = filtered.get("depth", 0).fillna(0).astype(float)
    adjusted = gw - depth_penalty * depth

    filtered = filtered.assign(adjusted_score=adjusted)

    # Take a larger pool for temperature sampling (top 3x limit)
    pool_size = min(len(filtered), limit * 3)
    filtered = filtered.sort_values("adjusted_score", ascending=False).head(pool_size)

    if temperature <= 0 or pool_size <= limit:
        # Deterministic: take top limit
        top = filtered.head(limit)
    else:
        # Temperature sampling: softmax over adjusted scores, then sample without replacement
        scores = filtered["adjusted_score"].to_numpy(dtype=float)
        # Shift for numerical stability (softmax is invariant to constant shift)
        scores = scores - np.max(scores)
        probs = np.exp(scores / temperature)
        probs = probs / (probs.sum() + 1e-10)
        probs = np.clip(probs, 1e-10, 1.0)  # Avoid zeros for sampling
        probs = probs / probs.sum()
        indices = np.random.choice(
            len(filtered), size=min(limit, len(filtered)), replace=False, p=probs
        )
        top = filtered.iloc[indices]
        # Re-sort by score for consistent display order
        top = top.sort_values("adjusted_score", ascending=False)

    return [
        {
            "course_code": row["courseCode"],
            "title": row["title"],
            "description": row["description"],
            "score": float(row["adjusted_score"]),
        }
        for _, row in top.iterrows()
    ]


def get_similar_courses(
    course_code: str,
    data_file: str = 'course-api-new-data.json',
    top_k: int = 6,
) -> List[Dict[str, Any]]:
    """
    Find courses most similar to the given course based on TF-IDF/SVD
    description embeddings (cosine similarity).

    Returns a list of dicts: [{course_code, title, description, score}, ...]
    """
    df, embeddings, *_ = _load_all(data_file)

    code_upper = course_code.strip().upper().replace(' ', '')
    matches = df.index[df['courseCode'].str.upper().str.replace(' ', '', regex=False) == code_upper]
    if len(matches) == 0:
        return []
    idx = matches[0]

    query_vec = embeddings[idx].reshape(1, -1)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    emb_norm = embeddings / norms
    q_norm = query_vec / max(np.linalg.norm(query_vec), 1e-10)
    sims = np.dot(emb_norm, q_norm.flatten())

    # Zero out the query course itself
    sims[idx] = -1.0

    top_idxs = np.argsort(-sims)[:top_k]
    results = []
    for i in top_idxs:
        if sims[i] <= 0:
            continue
        row = df.iloc[i]
        results.append({
            'course_code': row['courseCode'],
            'title': row['title'],
            'description': row['description'],
            'score': float(sims[i]),
        })
    return results


def main():
    """CLI entry point for testing recommendations."""
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

