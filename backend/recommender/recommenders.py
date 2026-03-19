"""Course recommendation algorithms."""

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from difflib import SequenceMatcher
import faiss
import networkx as nx
import time
import json
import os
import re
from .data_loader import load_undergrad_courses, load_grad_courses, find_project_root
from .weights import load_course_to_programs

_COURSE_TO_PROGRAMS_CACHE = None


def _get_course_to_programs_cached():
    global _COURSE_TO_PROGRAMS_CACHE
    if _COURSE_TO_PROGRAMS_CACHE is None:
        project_root = find_project_root()
        options_path = os.path.join(project_root, 'data', 'programs', 'all_options.json')
        programs_path = os.path.join(project_root, 'data', 'programs', 'all_programs.json')
        _COURSE_TO_PROGRAMS_CACHE = load_course_to_programs([
            (options_path, 'option'),
            (programs_path, 'minor'),
        ])
    return _COURSE_TO_PROGRAMS_CACHE

TERM_ORDER = ["1A", "1B", "2A", "2B", "3A", "3B", "4A", "4B"]

_DEPT_PREFIX_RE = re.compile(r'^([A-Za-z]+)')
# Minimum raw similarity cutoff (before weights). Suggestions: 0.2=permissive, 0.25=moderate, 0.3=stricter, 0.35=strict
MIN_SIMILARITY_CUTOFF = 0.25

def _get_course_dept(course_code: str) -> str:
    """Extract department prefix from a course code (e.g. 'ME101' -> 'ME', 'MEDVL330' -> 'MEDVL')."""
    m = _DEPT_PREFIX_RE.match(course_code)
    return m.group(1).upper() if m else ''


# Filler/stop words: not required to appear in title for word-overlap boost.
# Full-query and phrase-in-title boosts still apply regardless.
_TITLE_BOOST_STOP_WORDS = frozenset({
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'been', 'being', 'by', 'for',
    'from', 'has', 'have', 'had', 'in', 'is', 'it', 'its', 'of', 'on', 'or',
    'that', 'the', 'these', 'they', 'this', 'those', 'to', 'was', 'were',
    'will', 'with', 'would', 'could', 'should', 'may', 'might', 'must', 'can',
    'do', 'does', 'did', 'into', 'through', 'during', 'before', 'after',
})


def _content_words_only(query: str) -> set:
    """Return set of query words excluding stop words (for title-word boost)."""
    words = set(re.findall(r'\w+', query.lower()))
    return words - _TITLE_BOOST_STOP_WORDS


def _query_phrases(query: str) -> list:
    """Return list of non-empty phrase strings (runs of non-stop words) for phrase-in-title boost."""
    tokens = re.findall(r'\w+', query.lower())
    phrases = []
    current = []
    for w in tokens:
        if w in _TITLE_BOOST_STOP_WORDS:
            if current:
                phrases.append(' '.join(current))
                current = []
        else:
            current.append(w)
    if current:
        phrases.append(' '.join(current))
    return phrases


def _title_word_boost(query: str, titles: pd.Series) -> np.ndarray:
    """Return per-row boost when query *content* words appear in course title.

    Filler words (e.g. and, the, of) are ignored: we only require non-stop words
    to appear in the title for this boost. Full-query and phrase-in-title boosts
    are applied separately and do consider the full query/phrases.
    """
    query_words = _content_words_only(query)
    if not query_words:
        return np.zeros(len(titles), dtype=float)
    def overlap_count(title):
        if not isinstance(title, str):
            return 0
        title_words = set(re.findall(r'\w+', title.lower()))
        return len(query_words & title_words)
    overlaps = titles.apply(overlap_count).to_numpy(dtype=float)
    boosts = np.minimum(overlaps * 0.28, 0.75)
    return boosts


def meets_level_requirement(user_level, required_level, comparison="at_least"):
    """Check if user's academic level satisfies a level requirement."""
    if user_level not in TERM_ORDER or required_level not in TERM_ORDER:
        return True
    user_idx = TERM_ORDER.index(user_level)
    req_idx = TERM_ORDER.index(required_level)
    if comparison == "at_least":
        return user_idx >= req_idx
    return user_idx == req_idx


def _normalize_code(code: str) -> str:
    """Normalize course code to canonical uppercase/no-space form."""
    result = (code or "").strip().upper().replace(" ", "")
    if result.startswith("MSCI"):
        result = "MSE" + result[4:]
    return result


def get_valid_course_set(completed_courses, available_courses, incoming_level=None):
    """
    Given a list of completed courses and available courses, return a set of courses 
    from the available courses that are eligible to take based on their prerequisites 
    being satisfied.
    
    Args:
        completed_courses: List of course codes that have been completed (e.g., ['CS135', 'MATH137'])
        available_courses: List/set of course codes to filter from
        incoming_level: User's current academic level (e.g., '1B', '3A') for level requirement checks
        
    Returns:
        set: Set of course codes from available_courses that are eligible to take
    """
    # Load course dependencies
    project_root = find_project_root()
    dependencies_path = os.path.join(project_root, 'data', 'dependencies', 'course_dependencies_llm.json')
    try:
        with open(dependencies_path, 'r', encoding='utf-8') as f:
            dependencies = json.load(f)
    except FileNotFoundError:
        print(f"Warning: Course dependencies file not found at {dependencies_path}")
        return set()
    
    completed_set = {_normalize_code(c) for c in completed_courses} if completed_courses else set()
    available_set = {_normalize_code(c) for c in available_courses} if available_courses else set()
    eligible_courses = set()
    
    def check_prerequisite_group(group, completed_courses_set):
        """Check if a prerequisite group is satisfied by completed courses"""
        if isinstance(group, str):
            return _normalize_code(group) in completed_courses_set
        if group.get('type') == 'course':
            return _normalize_code(group.get('code', '')) in completed_courses_set
        
        elif group.get('type') == 'prerequisite_group':
            courses = group.get('courses', [])
            operator = group.get('operator', 'AND')
            quantity = group.get('quantity')
            
            satisfied_count = 0
            for course in courses:
                if isinstance(course, str):
                    if _normalize_code(course) in completed_courses_set:
                        satisfied_count += 1
                elif course.get('type') == 'course':
                    if _normalize_code(course.get('code', '')) in completed_courses_set:
                        satisfied_count += 1
                elif course.get('type') == 'prerequisite_group':
                    # Nested group - recursively check
                    if check_prerequisite_group(course, completed_courses_set):
                        satisfied_count += 1
            
            if operator == 'OR':
                # For OR, we need at least one (or the specified quantity)
                required = quantity if quantity is not None else 1
                return satisfied_count >= required
            else:  # AND
                # For AND, we need all courses
                return satisfied_count == len(courses)
        
        return False
    
    def is_course_eligible(course_code, course_dep, completed_courses_set):
        """Check if a course is eligible based on its prerequisites and level requirements"""
        prereqs = course_dep.get('prerequisites', course_dep)
        if isinstance(prereqs, list):
            prereqs = {}
        groups = prereqs.get('groups', [])
        root_operator = prereqs.get('root_operator', 'AND')
        program_requirements = prereqs.get('program_requirements', [])

        # Check level requirements from program_requirements
        if incoming_level and program_requirements:
            for req in program_requirements:
                if not isinstance(req, dict):
                    continue
                level_req = req.get('level_requirement')
                if level_req:
                    required_level = level_req.get('level', '')
                    comparison = level_req.get('comparison', 'at_least')
                    if not meets_level_requirement(incoming_level, required_level, comparison):
                        return False

        # If no completed courses provided, skip course prerequisite check
        # (level requirement alone is sufficient when we have no transcript)
        if not completed_courses_set:
            return True

        if not groups:
            return True

        satisfied_groups = 0
        for group in groups:
            if check_prerequisite_group(group, completed_courses_set):
                satisfied_groups += 1

        if root_operator == 'OR':
            return satisfied_groups > 0
        else:
            return satisfied_groups == len(groups)
    
    dependencies_normalized = {_normalize_code(k): v for k, v in dependencies.items()}
    
    # Check each course in the available courses
    for course_code in available_set:
        # Skip if this course is already completed
        if course_code in completed_set:
            continue
            
        # Check if we have dependency data for this course (using normalized key)
        if course_code not in dependencies_normalized:
            # If no dependency data, assume no prerequisites (eligible)
            eligible_courses.add(course_code)
            continue
            
        course_data = dependencies_normalized[course_code]
        # Check if prerequisites are satisfied
        if is_course_eligible(course_code, course_data, completed_set):
            eligible_courses.add(course_code)
    return eligible_courses


_ENG_DEPTS = frozenset({
    'AE', 'BME', 'CHE', 'CIVE', 'ECE', 'ENVE', 'GENE', 'GEOE',
    'ME', 'MTE', 'MSE', 'NE', 'SE', 'SYDE',
})


def _apply_course_filters(filters, df):
    """Apply undergrad/grad, department, options, and prerequisite filters.

    Returns a set of course codes that pass all active filters (empty set means no filtering).
    """
    filters_applied = set()
    if filters and filters.get('include_undergrad'):
        filters_applied.update(load_undergrad_courses())
    if filters and filters.get('include_grad'):
        filters_applied.update(load_grad_courses())
    if filters and filters.get('department'):
        departments = set(filters['department'])
        include_other = filters.get('include_other_depts', False)
        filters_applied = {
            s for s in filters_applied
            if _get_course_dept(s) in departments or (include_other and _get_course_dept(s) not in _ENG_DEPTS)
        }

    # Filter by options/minors when specified
    if filters and filters.get('options'):
        selected_names = set(filters['options'])
        if selected_names:
            course_to_programs = _get_course_to_programs_cached()
            courses_in_options = {
                code for code, progs in course_to_programs.items()
                if any(p['name'] in selected_names for p in progs)
            }
            if filters_applied:
                filters_applied = filters_applied & courses_in_options
            else:
                filters_applied = courses_in_options

    # Apply prerequisite filter last (unless explicitly disabled)
    if filters and not filters.get('ignore_dependencies'):
        has_courses = bool(filters.get('completed_courses'))
        has_level = bool(filters.get('incoming_level'))
        if has_courses or has_level:
            courses_to_check = filters_applied if filters_applied else df['courseCode']
            eligible_courses = get_valid_course_set(
                filters.get('completed_courses', []),
                courses_to_check,
                incoming_level=filters.get('incoming_level'),
            )
            filters_applied = eligible_courses

    return filters_applied


def recommend_cosine(query, tfidf, svd, emb, df, filters=None, top_k=30, min_similarity=None):
    """Recommend courses using cosine similarity."""
    if min_similarity is None:
        min_similarity = MIN_SIMILARITY_CUTOFF
    filters_applied = _apply_course_filters(filters, df)

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
    # Phrase-boost: full query substring in title (no stop-word filtering; whole query matters)
    title_lower = df['title'].str.lower()
    query_lower = query.lower().strip()
    if query_lower:
        phrase_mask = title_lower.str.contains(query_lower, regex=False)
        boost_factor = 0.5  # full query phrase in title gets a strong boost
        sims = sims + boost_factor * phrase_mask.astype(float)
    # Phrase boost: each run of non-filler words from the query that appears in title (e.g. "machine learning")
    for phrase in _query_phrases(query):
        if len(phrase) > 1:  # skip single-word phrases (handled by title-word boost)
            sims = sims + 0.35 * title_lower.str.contains(phrase, regex=False).astype(float)
    # Title-word boost: only content words (filler words like "and", "the" are ignored)
    sims = sims + _title_word_boost(query, df['title'])
    # Replace NaN and inf with 0
    sims = np.nan_to_num(sims, nan=0.0, posinf=0.0, neginf=0.0)

    # Stage 1: Retrieval (semantic + phrase + title-word).
    sims_raw = sims.copy()

    t2 = time.time()

    # Filter by filters_applied if not empty
    if filters_applied:
        mask = df['courseCode'].isin(filters_applied)
        filtered_idxs = np.where(mask)[0]
        sims_filtered = sims_raw[filtered_idxs]

        # Retrieve more than top_k so weighting can re-rank meaningfully.
        retrieval_k = min(len(sims_filtered), max(top_k * 5, top_k))
        if retrieval_k < len(sims_filtered):
            idxs_in_filtered = np.argpartition(-sims_filtered, retrieval_k)[:retrieval_k]
            idxs_in_filtered = idxs_in_filtered[np.argsort(-sims_filtered[idxs_in_filtered])]
        else:
            idxs_in_filtered = np.argsort(-sims_filtered)
        candidate_idxs = filtered_idxs[idxs_in_filtered]
    else:
        sims_all = sims_raw
        retrieval_k = min(len(sims_all), max(top_k * 5, top_k))
        if retrieval_k < len(sims_all):
            candidate_idxs = np.argpartition(-sims_all, retrieval_k)[:retrieval_k]
            candidate_idxs = candidate_idxs[np.argsort(-sims_all[candidate_idxs])]
        else:
            candidate_idxs = np.argsort(-sims_all)
    t3 = time.time()

    # Minimum similarity cutoff (before weights): drop candidates below threshold
    if len(candidate_idxs) > 0:
        above_cutoff = sims_raw[candidate_idxs] >= min_similarity
        candidate_idxs = candidate_idxs[above_cutoff]

    # Stage 2: Ranking (apply universal weights and optional same-department boost).
    if 'global_weight' in df.columns and len(candidate_idxs) > 0:
        global_w = df['global_weight'].to_numpy(dtype=float)
        alpha = 0.3
        weighted_scores = sims_raw[candidate_idxs] * (1.0 + alpha * global_w[candidate_idxs])
    else:
        weighted_scores = sims_raw[candidate_idxs].copy() if len(candidate_idxs) > 0 else np.array([], dtype=float)

    # Same-department boost: uses user's major (profile), not the search page department filter
    user_dept = (filters or {}).get('user_department')
    if user_dept and len(candidate_idxs) > 0:
        user_dept = str(user_dept).strip().upper()
        codes = df['courseCode'].iloc[candidate_idxs]
        same_dept = np.array([_get_course_dept(str(c)) == user_dept for c in codes], dtype=float)
        weighted_scores = weighted_scores * (1.0 + 0.4 * same_dept)

    # Option-completion boost: tiered by option + list progress (multiplier per course)
    option_boost = (filters or {}).get("option_boost_multipliers") or {}
    if option_boost and len(candidate_idxs) > 0:
        codes = df['courseCode'].iloc[candidate_idxs]
        norm = lambda c: (str(c) or "").strip().upper().replace(" ", "")
        mults = np.array([option_boost.get(norm(c), 1.0) for c in codes], dtype=float)
        weighted_scores = weighted_scores * mults

    if len(candidate_idxs) > 0:
        order = np.argsort(-weighted_scores)
        candidate_idxs = candidate_idxs[order]
        weighted_scores = weighted_scores[order]

    # Keep final top_k after weighting re-rank
    idxs = candidate_idxs[:top_k]
    final_scores = weighted_scores[:top_k]

    # Build result DataFrame
    result = df.iloc[idxs][['courseCode', 'title', 'description']].copy()
    # Expose both: raw similarity (retrieval) and final weighted similarity (ranking)
    result['similarity_raw'] = sims_raw[idxs]
    result['similarity_raw'] = np.nan_to_num(result['similarity_raw'], nan=0.0, posinf=0.0, neginf=0.0)
    result['similarity'] = final_scores
    result['similarity'] = np.nan_to_num(result['similarity'], nan=0.0, posinf=0.0, neginf=0.0)
    
    # Final filter: ensure semantic relevance threshold on raw similarity (same as pre-weight cutoff)
    result = result[result['similarity_raw'] >= min_similarity]
    
    print(f"[recommend_cosine] Vectorization: {t1-t0:.4f}s, Cosine: {t2-t1:.4f}s, Top-k: {t3-t2:.4f}s, Total: {t3-t0:.4f}s")
    print(len(result))
    return result


def recommend_filter_only(df, filters=None, top_k=30):
    """Return courses based solely on filters, sorted by global_weight descending.

    Used when the user submits an empty query but has filters (e.g. options) selected.
    """
    filters_applied = _apply_course_filters(filters, df)

    if filters_applied:
        filtered = df[df['courseCode'].isin(filters_applied)]
    else:
        filtered = df

    if 'global_weight' in filtered.columns:
        filtered = filtered.sort_values('global_weight', ascending=False)

    filtered = filtered.head(top_k)

    result = filtered[['courseCode', 'title', 'description']].copy()
    result['score'] = filtered['global_weight'] if 'global_weight' in filtered.columns else 0.0
    return result


def recommend_faiss(query, tfidf, svd, emb, df, top_k=10):
    """Recommend courses using FAISS similarity search."""
    emb = emb.astype('float32')
    faiss.normalize_L2(emb)
    index = faiss.IndexFlatIP(emb.shape[1])
    index.add(emb)
    q = svd.transform(tfidf.transform([query])).astype('float32')
    faiss.normalize_L2(q)
    D, I = index.search(q, top_k)
    return df.iloc[I[0]][['courseCode', 'title', 'description']].assign(similarity=D[0])


def recommend_mmr(query, tfidf, svd, emb, df, top_k=10, lmbda=0.7):
    """Recommend courses using Maximal Marginal Relevance."""
    q_vec = svd.transform(tfidf.transform([query])).flatten()
    sims = cosine_similarity(emb, q_vec.reshape(1, -1)).flatten()
    candidates = list(range(len(sims)))
    selected = []
    for _ in range(top_k):
        if not selected:
            idx = int(np.argmax(sims))
        else:
            mmr_scores = []
            for i in candidates:
                rel = sims[i]
                red = max(cosine_similarity(emb[selected], emb[i].reshape(1, -1)).flatten())
                mmr_scores.append((i, lmbda * rel - (1 - lmbda) * red))
            idx = max(mmr_scores, key=lambda x: x[1])[0]
        selected.append(idx)
        candidates.remove(idx)
    return df.iloc[selected][['courseCode', 'title', 'description']].assign(similarity=sims[selected])


def recommend_graph(query, tfidf, svd, emb, df, top_k=10):
    """Recommend courses using graph-based PageRank."""
    q_vec = svd.transform(tfidf.transform([query]))
    sims = cosine_similarity(emb, q_vec).flatten()
    G = nx.DiGraph()
    G.add_node('query')
    for i, code in enumerate(df['courseCode']):
        G.add_edge('query', code, weight=float(sims[i]))
    pr = nx.pagerank(G, alpha=0.85, personalization={'query': 1.0})
    ranked = sorted(((c, sc) for c, sc in pr.items() if c != 'query'), key=lambda x: x[1], reverse=True)[:top_k]
    codes = [c for c, _ in ranked]
    scores = [s for _, s in ranked]
    return df[df['courseCode'].isin(codes)][['courseCode', 'title', 'description']].assign(score=scores)


def fuzzy_similarity(a, b):
    """Calculate fuzzy string similarity."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def recommend_fuzzy_multi(query, df, top_k=10, weights={'title': 0.4, 'description': 0.5, 'code': 0.1}):
    """Recommend courses using fuzzy string matching."""
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
    return df.iloc[top_indices][['courseCode', 'title', 'description']].assign(fuzzy_score=top_scores)


def extract_keywords(text, min_length=3):
    """Extract keywords from text."""
    import re
    stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'this', 'that', 'these', 'those', 'a', 'an'}
    words = re.findall(r'\b\w+\b', text.lower())
    return [w for w in words if len(w) >= min_length and w not in stop_words]


def recommend_keyword_overlap(query, df, top_k=10):
    """Recommend courses using keyword overlap."""
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
    return df.iloc[top_indices][['courseCode', 'title', 'description']].assign(keyword_score=top_scores)


def recommend_bert(query, model, bert_embeddings, df, top_k=10):
    """Recommend courses using BERT embeddings."""
    query_embed = model.encode([query])
    sims = cosine_similarity(query_embed, bert_embeddings).flatten()
    top_indices = sims.argsort()[::-1][:top_k]
    return df.iloc[top_indices][['courseCode', 'title', 'description']].assign(bert_score=sims[top_indices])


def recommend_hybrid_ensemble(query, df, tfidf, svd, emb, faiss_emb, model, bert_embeddings, top_k=10, method_weights=None):
    """Recommend courses using ensemble of multiple methods."""
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
    return df.iloc[top_indices][['courseCode', 'title', 'description']].assign(hybrid_score=top_scores)

