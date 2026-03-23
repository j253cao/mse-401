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
