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
