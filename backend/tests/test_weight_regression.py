import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from recommender.eval.run_weight_sweep import run_sweep  # noqa: E402


class SearchWeightRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        eval_dir = BACKEND_ROOT / "recommender" / "eval"
        with (eval_dir / "queries.json").open("r", encoding="utf-8") as handle:
            cls.cases = json.load(handle)["cases"]
        with (eval_dir / "baseline_metrics.json").open("r", encoding="utf-8") as handle:
            cls.baseline_floors = json.load(handle)
        cls.top_k = int(cls.baseline_floors["top_k"])

    def _evaluate(self, candidate_overrides):
        # recommend_cosine logs timings for every call; suppress during test.
        with redirect_stdout(io.StringIO()):
            return run_sweep(self.cases, top_k=self.top_k, candidate_overrides=candidate_overrides)

    def test_macro_metrics_respect_floors(self):
        result = self._evaluate([{}])[0]
        metrics = result["metrics"]
        floors = self.baseline_floors["macro_floor"]
        self.assertGreaterEqual(metrics["ndcg_at_k"], floors["ndcg_at_k"])
        self.assertGreaterEqual(metrics["recall_at_k"], floors["recall_at_k"])
        self.assertGreaterEqual(metrics["mrr"], floors["mrr"])

    def test_segment_metrics_respect_floors(self):
        result = self._evaluate([{}])[0]
        seg_metrics = result["segment_metrics"]
        seg_floors = self.baseline_floors["segment_ndcg_floor"]
        for segment, floor in seg_floors.items():
            self.assertIn(segment, seg_metrics)
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
            0.15,
            msg="Degraded profile should underperform baseline by a clear margin",
        )


if __name__ == "__main__":
    unittest.main()

