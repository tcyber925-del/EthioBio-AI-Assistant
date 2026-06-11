"""Unit tests for evaluation scorers (deterministic, no DB/LLM)."""

from evaluation.scorers.accuracy_scorer import score_batch_accuracy, score_binary_accuracy
from evaluation.scorers.diversity_scorer import (
    score_query_count,
    score_redundancy,
    score_source_diversity,
)
from evaluation.scorers.grounding_scorer import (
    score_citation_fidelity,
    score_hallucination_absence,
)
from evaluation.scorers.plan_scorer import (
    score_complexity_estimation,
    score_task_f1,
    score_task_precision,
    score_task_recall,
)


class TestAccuracyScorer:
    def test_binary_exact_match(self):
        assert score_binary_accuracy(True, True) == 1.0
        assert score_binary_accuracy(False, False) == 1.0

    def test_binary_mismatch(self):
        assert score_binary_accuracy(True, False) == 0.0
        assert score_binary_accuracy(False, True) == 0.0

    def test_batch_all_correct(self):
        preds = [True, False, True]
        exps = [True, False, True]
        assert score_batch_accuracy(preds, exps) == 1.0

    def test_batch_half_correct(self):
        preds = [True, False, True]
        exps = [True, True, False]
        assert score_batch_accuracy(preds, exps) == 1.0 / 3.0

    def test_batch_empty(self):
        assert score_batch_accuracy([], []) == 0.0


class TestPlanScorer:
    def test_task_precision_full(self):
        pred = ["retrieve_mitosis", "retrieve_meiosis"]
        exp = ["retrieve_mitosis", "retrieve_meiosis", "compare"]
        assert score_task_precision(pred, exp) == 1.0

    def test_task_precision_partial(self):
        pred = ["retrieve_mitosis", "extra_task"]
        exp = ["retrieve_mitosis"]
        assert score_task_precision(pred, exp) == 0.5

    def test_task_recall_full(self):
        pred = ["retrieve_mitosis", "retrieve_meiosis", "compare"]
        exp = ["retrieve_mitosis", "retrieve_meiosis"]
        assert score_task_recall(pred, exp) == 1.0

    def test_task_recall_partial(self):
        pred = ["retrieve_mitosis"]
        exp = ["retrieve_mitosis", "retrieve_meiosis"]
        assert score_task_recall(pred, exp) == 0.5

    def test_task_f1_perfect(self):
        pred = ["a", "b"]
        exp = ["a", "b"]
        assert score_task_f1(pred, exp) == 1.0

    def test_task_f1_no_overlap(self):
        pred = ["a"]
        exp = ["b"]
        assert score_task_f1(pred, exp) == 0.0

    def test_complexity_match(self):
        assert score_complexity_estimation(True, True) == 1.0
        assert score_complexity_estimation(False, False) == 1.0

    def test_complexity_mismatch(self):
        assert score_complexity_estimation(True, False) == 0.0
        assert score_complexity_estimation(False, True) == 0.0


class TestDiversityScorer:
    def test_query_count_sufficient(self):
        assert score_query_count(3, 2) == 1.0

    def test_query_count_insufficient(self):
        assert score_query_count(1, 3) == 1.0 / 3.0

    def test_query_count_zero_min(self):
        assert score_query_count(0, 0) == 1.0

    def test_redundancy_within_limit(self):
        assert score_redundancy(0.1, 0.3) == 1.0

    def test_redundancy_exceeds(self):
        assert score_redundancy(0.5, 0.3) < 1.0

    def test_source_diverse_expected(self):
        assert score_source_diversity(["curriculum", "memory"], True) == 1.0

    def test_source_not_diverse_expected(self):
        assert score_source_diversity(["curriculum"], True) == 0.0


class TestGroundingScorer:
    def test_citation_fidelity_perfect(self):
        resp = ["e1", "e2"]
        exp = ["e1", "e2"]
        assert score_citation_fidelity(resp, exp) == 1.0

    def test_citation_fidelity_missing(self):
        resp = ["e1"]
        exp = ["e1", "e2"]
        score = score_citation_fidelity(resp, exp)
        assert 0.0 < score < 1.0

    def test_no_expected_citations(self):
        assert score_citation_fidelity([], []) == 1.0

    def test_no_response_citations(self):
        assert score_citation_fidelity([], ["e1"]) == 0.0

    def test_hallucination_clean(self):
        assert score_hallucination_absence(0, 10) == 1.0

    def test_hallucination_exceeds(self):
        assert score_hallucination_absence(5, 10) < 1.0

    def test_hallucination_no_claims(self):
        assert score_hallucination_absence(0, 0) == 1.0
