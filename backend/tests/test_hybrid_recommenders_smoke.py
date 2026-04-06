"""Smoke tests for BM25+dense hybrid and cross-encoder recommenders."""

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from recommender.main import get_recommendations  # noqa: E402


def _has_sentence_transformers() -> bool:
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


MIN_FILTERS = {
    "include_undergrad": True,
    "ignore_dependencies": True,
}


@unittest.skipUnless(_has_sentence_transformers(), "sentence-transformers is not installed")
class HybridRecommendersSmokeTests(unittest.TestCase):
    def test_hybrid_bm25_dense_returns_results(self):
        with redirect_stdout(io.StringIO()):
            out = get_recommendations(
                ["machine learning statistics"],
                method="hybrid_bm25_dense",
                filters=MIN_FILTERS,
            )
        self.assertEqual(len(out), 1)
        rows = [r for r in out[0] if r.get("method") == "hybrid_bm25_dense"]
        self.assertGreater(len(rows), 0)
        self.assertIn("course_code", rows[0])

    def test_cross_encoder_rerank_returns_results(self):
        with redirect_stdout(io.StringIO()):
            out = get_recommendations(
                ["machine learning statistics"],
                method="cross_encoder_rerank",
                filters=MIN_FILTERS,
            )
        rows = [r for r in out[0] if r.get("method") == "cross_encoder_rerank"]
        self.assertGreater(len(rows), 0)

    def test_hybrid_rerank_graph_returns_results(self):
        with redirect_stdout(io.StringIO()):
            out = get_recommendations(
                ["machine learning statistics"],
                method="hybrid_rerank_graph",
                filters=MIN_FILTERS,
            )
        rows = [r for r in out[0] if r.get("method") == "hybrid_rerank_graph"]
        self.assertGreater(len(rows), 0)


if __name__ == "__main__":
    unittest.main()
