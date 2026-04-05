# Dual-benchmark comparison (internal vs academic calendar)

This document defines how [`compare_methods_dual_benchmark.py`](compare_methods_dual_benchmark.py) compares retrieval methods on two tracks.

## Track A — Graded internal eval (`queries.json`)

- **Population:** Cases with **non-empty** `graded_relevance` only.
- **Metrics (same as [`run_weight_sweep.py`](run_weight_sweep.py)):** NDCG@k, Recall@k, MRR.
- **Aggregation:** Macro average; segment breakdown; non‑STEM labeled slice (`non_stem`, `breadth`, `test_plan_402_nonstem`).
- **Filters:** Each case uses its JSON `filters` (department, `include_other_depts`, etc.).

## Track B — Calendar export (`uw_calendar_top10.csv`)

The calendar list is a **weak, unpersonalized baseline** (no major/term in the scraped UI query). Treat overlap as a **diagnostic**, not ground truth.

For each query, let **M** = distinct method top‑k codes, **C** = distinct calendar top‑k codes (order preserved for ranking signals).

### Diagnostic scores (interpretable without “beating” the calendar)

1. **Jaccard@k:** \(|M \cap C| / |M \cup C|\) — symmetric set agreement in [0, 1].
2. **Calendar set recall:** \(|M \cap C| / |C|\) — share of the calendar bag you recover in your top‑k (high = your list covers more of what the calendar showed for that keyword).
3. **Method set recall vs calendar:** \(|M \cap C| / |M|\) — share of your top‑k that also appeared in the calendar bag.
4. **Lexical intent coverage:** average query–(title+description) token overlap for courses in your top‑k (same idea for the calendar list in the head‑to‑head).

Macros **mean_jaccard_at_k** and **mean_calendar_set_recall** (plus non‑STEM slices) are reported per method in the summary JSON and leaderboard CSV.

### Head‑to‑head composite (symmetric, fixed bias)

Older versions scored the calendar with **overlap(C, C)**, which inflated the calendar side. The current composite uses:

- The **same Jaccard@k** term for method and calendar.
- **Symmetric MROR:** mean reciprocal rank **over shared codes**—once in **M**’s order, once in **C**’s order.

```
composite = w_overlap * jaccard + w_mror * MROR + w_lex * lex_avg
```

**Win** if `composite_method > composite_calendar + epsilon`. Wins are still **proxy wins**; prefer **graded Track A** and the **coverage metrics** above for product decisions.

### Non‑STEM emphasis

- `segment == non_stem` rows get a weight multiplier in weighted win rate (default 1.5).

### Pass / fail gates (defaults)

- **Calendar:** `non_stem_win_rate >= 0.55`, overall `win_rate >= 0.50` (tune thresholds as needed).

### Internal quality gate (no regression vs baseline)

Default baseline **`cosine`:** macro NDCG, MRR, and non‑STEM labeled NDCG must not drop vs baseline beyond `--internal-tolerance`.

## Recommended interpretation

- **Track A** = quality vs your labels.
- **Track B** = (1) **coverage of an external keyword bag** and (2) **proxy ranking** under your filters. Do not equate calendar lists with “correct” courses.

Run all eval backends (calendar + internal):  
`python recommender/eval/compare_methods_dual_benchmark.py --all-eval-methods --output-dir recommender/eval/reports`
