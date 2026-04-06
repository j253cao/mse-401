import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from recommender.eval.eval_filter_validation import validate_eval_cases_filter_policy  # noqa: E402
from recommender.eval.run_weight_sweep import PRIMARY_GRADED_METHODS, run_sweep  # noqa: E402
from recommender.main import get_recommendations  # noqa: E402


class SearchWeightRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        eval_dir = BACKEND_ROOT / "recommender" / "eval"
        with (eval_dir / "queries.json").open("r", encoding="utf-8") as handle:
            cls.cases = json.load(handle)["cases"]
        with (eval_dir / "baseline_metrics.json").open("r", encoding="utf-8") as handle:
            cls.baseline_floors = json.load(handle)
        cls.top_k = int(cls.baseline_floors["top_k"])

    def _evaluate(self, candidate_overrides, method="cosine"):
        # recommend_cosine logs timings for every call; suppress during test.
        with redirect_stdout(io.StringIO()):
            return run_sweep(
                self.cases,
                top_k=self.top_k,
                candidate_overrides=candidate_overrides,
                method=method,
            )

    def test_macro_metrics_respect_floors(self):
        """Legacy aggregate floor (cosine-scale) for quick smoke."""
        result = self._evaluate([{}])[0]
        metrics = result["metrics"]
        floors = self.baseline_floors["macro_floor"]
        self.assertGreaterEqual(metrics["ndcg_at_k"], floors["ndcg_at_k"])
        self.assertGreaterEqual(metrics["recall_at_k"], floors["recall_at_k"])
        self.assertGreaterEqual(metrics["mrr"], floors["mrr"])

    def test_per_method_macro_floors(self):
        """Each primary graded method must meet method-specific macro floors."""
        method_floors = self.baseline_floors.get("method_macro_floor") or {}
        for method in PRIMARY_GRADED_METHODS:
            with self.subTest(method=method):
                if method not in method_floors:
                    continue
                result = self._evaluate([{}], method=method)[0]
                metrics = result["metrics"]
                floors = method_floors[method]
                self.assertGreaterEqual(metrics["ndcg_at_k"], floors["ndcg_at_k"])
                self.assertGreaterEqual(metrics["recall_at_k"], floors["recall_at_k"])
                self.assertGreaterEqual(metrics["mrr"], floors["mrr"])

    def test_segment_metrics_respect_floors(self):
        result = self._evaluate([{}])[0]
        seg_metrics = result["segment_metrics"]
        seg_floors = self.baseline_floors["segment_ndcg_floor"]
        for segment, floor in seg_floors.items():
            if segment not in seg_metrics:
                continue
            self.assertGreaterEqual(
                seg_metrics[segment]["ndcg_at_k"],
                floor,
                msg=f"Segment {segment} dropped below NDCG floor",
            )

    def test_degraded_profile_is_detected(self):
        degraded = {
            "ranking": {
                "alpha": 0.0,
                "same_department_boost": 0.0,
                "full_query_title_boost": 0.0,
                "phrase_title_boost": 0.0,
                "title_word_boost_per_overlap": 0.0,
                "min_similarity_cutoff": 0.4,
            },
            "global_weight": {
                "gamma_prereq": 0.0,
                "gamma_depth": 0.0,
                "gamma_minor": 0.0,
            },
            "option_boost": {
                "tier1": 0.0,
                "tier2": 0.0,
                "tier3": 0.0,
            },
        }
        results = self._evaluate([{}, degraded])
        baseline_score = max(r["metrics"]["ndcg_at_k"] for r in results if not r["override"])
        degraded_score = max(r["metrics"]["ndcg_at_k"] for r in results if r["override"])
        self.assertGreater(
            baseline_score - degraded_score,
            0.10,
            msg="Degraded profile should underperform baseline by a clear margin",
        )

    def test_eval_cases_include_other_depts_policy(self):
        errs = validate_eval_cases_filter_policy(self.cases)
        self.assertEqual(errs, [], msg="; ".join(errs))

    def test_modern_film_studies_recommendations_no_crash(self):
        case = next(c for c in self.cases if c.get("id") == "tp402_N12_me_3a")
        q, flt = case["query"], case["filters"]
        for method in (
            "cosine",
            "dense",
            "hybrid_bm25_dense",
            "cross_encoder_rerank",
            "hybrid_ce_rrf_fused",
            "hybrid_rerank_graph",
        ):
            with self.subTest(method=method):
                with redirect_stdout(io.StringIO()):
                    batch = get_recommendations([q], method=method, filters=flt)
                self.assertTrue(batch and batch[0], msg=f"{method} returned no rows")

    def test_hybrid_bm25_nonempty_for_tight_dept_filters(self):
        """Regression: hybrid must not return empty when dense cosine alone is weak."""
        case = next(c for c in self.cases if c.get("id") == "ne_2a_foundation")
        with redirect_stdout(io.StringIO()):
            batch = get_recommendations(
                [case["query"]],
                method="hybrid_bm25_dense",
                filters=case["filters"],
            )
        self.assertGreaterEqual(len(batch[0]), 1, msg="hybrid_bm25_dense returned no rows")


if __name__ == "__main__":
    unittest.main()

