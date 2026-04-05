# Test all recommendation methods (workflow)

Compare backends the app actually runs inside `get_recommendations(..., method=...)`.

## 1) Quick CSV (human review)

From the **repo root**:

```bash
python scripts/run_search_evaluation_queries.py --top-k 10 --output eval_results_all_methods.csv --summary
```

- Writes one row per rank per query per method.
- `--summary` prints how many query×method pairs succeeded vs failed (stderr).
- Default query bank: [tasks/search-evaluation-queries.txt](search-evaluation-queries.txt).
- Optional: include non-engineering departments like the API flag:

```bash
python scripts/run_search_evaluation_queries.py --top-k 10 --include-other-depts --output eval_results_wide.csv --summary
```

**Inspect:** open the CSV in Excel/Sheets; filter by `query_id` and compare `method` columns side-by-side (course_code / title / score).

## 2) Labeled metrics (NDCG / Recall / MRR)

From **`backend/`** (needs eval set `recommender/eval/queries.json`):

```bash
cd backend
python recommender/eval/run_weight_sweep.py --compare-methods --num-random 0 --top-k 15
```

- Prints one line per backend with macro NDCG@k, Recall@k, MRR.
- Run a single backend + weight sweep:

```bash
python recommender/eval/run_weight_sweep.py --method cosine --num-random 48
```

`--method` accepts every name in `EVAL_BACKEND_METHODS` inside [backend/recommender/eval/run_weight_sweep.py](../backend/recommender/eval/run_weight_sweep.py).

## 3) Dependencies

- **dense**, **hybrid_bm25_dense**, **cross_encoder_rerank**, **hybrid_rerank_graph**: `sentence-transformers`, `rank-bm25` (see [backend/requirements.txt](../backend/requirements.txt)).
- **faiss**: `faiss-cpu`.
- **graph**: `networkx`.

## 4) Tips

- Keep the same query file and filters between runs so comparisons are fair.
- If sklearn logs `InconsistentVersionWarning` for TF-IDF pickles, compare methods on the same machine before/after changes; regenerate embeddings pickles if you need stable historical metrics.
