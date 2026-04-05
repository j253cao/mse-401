# Search Weight Inventory

This folder holds versioned artifacts for tuning and validating course-search
weights.

## Production baseline

`baseline_weights.json` is the frozen baseline config for all active search
weights.

## Weight ownership

- `global_weight` (global): combines prereq outdegree, depth, and option/minor
  membership via gamma coefficients.
- `ranking` (search): controls cosine ranking behavior, lexical boosts, and
  personalization boost strength.
- `option_boost` (personal): tiered multipliers derived from option progress.
- `explore` (explore-high-value endpoint): depth penalty and sampling
  temperature.

## Source of truth in code

The runtime source of truth is `backend/recommender/search_weight_config.py`.
This file mirrors the baseline values for versioned evaluation and reporting.

## Evaluation commands

- Weight sweep (default **cosine** = TF-IDF+SVD):

  `python recommender/eval/run_weight_sweep.py`

- Same sweep with **dense** retrieval (sentence-transformer):

  `python recommender/eval/run_weight_sweep.py --method dense`

- Compare **cosine** vs **dense** on baseline weights only (pair quick metrics):

  `python recommender/eval/run_weight_sweep.py --compare-methods --num-random 0`

- **Eval filter policy:** `run_weight_sweep.py` validates that `breadth`,
  `non_stem`, and `test_plan_402_nonstem` cases set
  `filters.include_other_depts=true`. Use `--skip-filter-validation` only for
  ad-hoc experiments.

- **Method-specific candidate packs** (hybrid / CE handoff, lexical/dense tuning):

  `python recommender/eval/run_weight_sweep.py --method hybrid_bm25_dense --append-method-candidates --num-random 12`

  Optional local jitter around hybrid candidates:

  `python recommender/eval/run_weight_sweep.py --method cross_encoder_rerank --append-method-candidates --local-search-replicas 8`

- **Frozen graded baselines** (macro + per-segment, both `queries.json` and
  `test_plan_402.json`):

  `python recommender/eval/compute_graded_baselines.py --top-k 15`

  Output: `graded_method_baselines.json`.

- **Per-query diagnostics** (missed positives, first-hit rank):

  `python recommender/eval/export_eval_diagnostics.py --eval-set recommender/eval/queries.json --method cross_encoder_rerank --output recommender/eval/reports/diag.json`

## Dual-benchmark method comparison

Runs **Track A** (graded `queries.json` → NDCG / Recall / MRR, same helpers as
`run_weight_sweep.py`) and **Track B** (24 calendar-aligned queries +
`uw_calendar_top10.csv` head-to-head with a documented relevance proxy).

Metric definitions, gates, and interpretation: [`DUAL_BENCHMARK.md`](DUAL_BENCHMARK.md).

From `backend/`:

```bash
python recommender/eval/compare_methods_dual_benchmark.py \
  --output-dir recommender/eval/reports
```

Common options:

| Flag | Purpose |
|------|---------|
| `--methods …` | Comma-separated backends (default: cosine, dense, hybrid_bm25_dense, cross_encoder_rerank, hybrid_ce_rrf_fused, hybrid_rerank_graph) |
| `--all-eval-methods` | Run every backend in `run_weight_sweep.EVAL_BACKEND_METHODS` (incl. faiss, mmr, graph, fuzzy_multi, keyword_overlap) |
| `--top-k 10` | Same cutoff for both tracks |
| `--threshold-non-stem-win-rate 0.55` | Calendar gate on non-STEM win rate |
| `--threshold-overall-win-rate 0.50` | Calendar gate on overall win rate |
| `--internal-baseline cosine` | No-regression baseline for Track A |
| `--internal-tolerance 0.0` | Allowed drop vs baseline on NDCG / MRR / non‑STEM NDCG |
| `--non-stem-query-weight 1.5` | Weight for `segment=non_stem` rows in weighted win rate |
| `--w-overlap`, `--w-mror`, `--w-lex` | Calendar composite weights (**symmetric** Jaccard + MROR on shared codes + lex; see `DUAL_BENCHMARK.md`) |
| `--skip-internal` / `--skip-calendar` | Run only one track |
| `--weights-json recommender/eval/baseline_weights.json` | Optional weight override blob |

Artifacts (under `--output-dir`):

- `dual_benchmark_summary.json` — macro metrics, per-method **internal + calendar** gates, non‑STEM loss lists, `recommended_winner`.
- `dual_benchmark_leaderboard.csv` — one row per method (includes **mean_jaccard_at_k**, **mean_calendar_set_recall**, and non‑STEM means for calendar diagnostics).
- `dual_benchmark_calendar_per_query.csv` — query-level calendar comparisons.
- `dual_benchmark_internal_per_case.csv` — labeled-eval per-case rows.

**How to read the winner:** Prefer a method that passes the **internal**
no-regression gate (vs `--internal-baseline`), **and** both calendar gates
(overall + non‑STEM win rates). Among those, macro **NDCG@k** on Track A breaks
ties; if every method fails a gate, the script still picks a fallback by NDCG
(see `recommended_winner` and per-method flags in the JSON).
