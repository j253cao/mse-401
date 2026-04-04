# Hybrid retrieval and cross-encoder methods

Three search backends live in standalone modules and are registered in `recommender/main.py`:

| `method` value              | Module                       | Description |
|----------------------------|------------------------------|-------------|
| `hybrid_bm25_dense`        | `recommend_bm25_dense_rrf.py` | BM25 (lexical) + dense cosine, fused with RRF; then global/dept/option multipliers. |
| `cross_encoder_rerank`     | `recommend_cross_encoder_rerank.py` | RRF retrieval pool, MS MARCO MiniLM cross-encoder rerank (no graph multipliers). |
| `hybrid_rerank_graph`      | `recommend_hybrid_rerank_graph.py` | Cross-encoder scores, then same global/dept/option fusion as cosine/dense. |

Tunables are under `DEFAULT_SEARCH_WEIGHTS["hybrid"]` in `recommender/search_weight_config.py` (`rrf_k`, retrieval sizes, etc.).

## Commands

From repo root or `backend/`:

```bash
cd backend
python recommender/eval/run_weight_sweep.py --compare-methods --num-random 0
```

Batch query dump:

```bash
python ../scripts/run_search_evaluation_queries.py --methods cosine,dense,hybrid_bm25_dense,cross_encoder_rerank,hybrid_rerank_graph --top-k 10
```

## Metrics and baselines

Re-run `run_weight_sweep.py --compare-methods --num-random 0` after changing weights; numbers depend on catalog, sklearn/pickle versions, and CPU/GPU.

The eval segment floor for `include_other_departments` in `baseline_metrics.json` is set conservatively for environments where TF-IDF/SVD pickles were built with an older scikit-learn than the runtime (unpickle warnings). Regenerating `data/embeddings/tfidf_vectorizer.pkl` and `svd_model.pkl` with your current sklearn restores full parity with historical segment NDCG.

### Example: `run_weight_sweep.py --compare-methods --num-random 0` (top_k=15, one dev machine)

| Method | NDCG@15 | Recall@15 | MRR |
|--------|---------|-----------|-----|
| cosine | 0.8249 | 0.9792 | 0.9028 |
| dense | 0.6145 | 0.7917 | 0.7069 |
| hybrid_bm25_dense | 0.4867 | 0.6458 | 0.7362 |
| cross_encoder_rerank | 0.3467 | 0.5000 | 0.4333 |
| hybrid_rerank_graph | 0.3288 | 0.4583 | 0.4708 |

Rerankers can underperform raw bi-encoder scores on this small labeled set until pools, cross-encoder model, and hybrid weights are tuned; use your own queries and A/B goals to choose a backend.
