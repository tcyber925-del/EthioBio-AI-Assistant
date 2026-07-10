"""Unit tests for the release certification engine (PRD-010C)."""

from evaluation.certification.certifier import (
    CERTIFICATION_LEVELS,
    DEFAULT_THRESHOLDS,
    CertificationInput,
    CertificationResult,
    certify_release,
    write_certification_report,
)


class TestCertifyRelease:
    def test_passes_with_good_scores(self):
        input_data = CertificationInput(
            agent_scores={"planner": 0.85, "tutor": 0.90},
            education_scores={"biology": 0.88, "chemistry": 0.82},
            factual_grounding={"factual_grounding": 0.80},
            integration_pass_rate=0.95,
            regression_count=0,
            benchmark_scores={"biology": 0.88, "chemistry": 0.82},
        )
        result = certify_release(input_data)
        assert result.passed
        assert result.level in CERTIFICATION_LEVELS
        assert result.score >= DEFAULT_THRESHOLDS["min_certification_score"]

    def test_fails_with_low_agent_score(self):
        input_data = CertificationInput(
            agent_scores={"planner": 0.40, "tutor": 0.50},
            education_scores=None,
            factual_grounding=None,
            integration_pass_rate=None,
            regression_count=0,
            benchmark_scores=None,
        )
        result = certify_release(input_data)
        assert not result.passed
        assert result.level == "fail"
        assert len(result.failures) > 0

    def test_fails_with_too_many_regressions(self):
        input_data = CertificationInput(
            agent_scores={"planner": 0.80, "tutor": 0.85},
            education_scores={"biology": 0.80},
            factual_grounding={"factual_grounding": 0.75},
            integration_pass_rate=0.90,
            regression_count=5,
            benchmark_scores={"biology": 0.80},
        )
        result = certify_release(input_data)
        assert not result.passed
        assert any("regressions" in f for f in result.failures)

    def test_fails_with_low_integration_rate(self):
        input_data = CertificationInput(
            agent_scores={"planner": 0.80, "tutor": 0.85},
            education_scores={"biology": 0.80},
            factual_grounding={"factual_grounding": 0.75},
            integration_pass_rate=0.50,
            regression_count=0,
            benchmark_scores={"biology": 0.80},
        )
        result = certify_release(input_data)
        assert not result.passed
        assert any("integration" in f for f in result.failures)

    def test_platinum_level(self):
        input_data = CertificationInput(
            agent_scores={"planner": 0.95, "tutor": 0.97},
            education_scores={"biology": 0.94, "chemistry": 0.92},
            factual_grounding={"factual_grounding": 0.90},
            integration_pass_rate=1.0,
            regression_count=0,
            benchmark_scores={"biology": 0.94, "chemistry": 0.92},
        )
        result = certify_release(input_data)
        assert result.passed
        assert result.level == "platinum"

    def test_silver_level(self):
        input_data = CertificationInput(
            agent_scores={"planner": 0.80, "tutor": 0.75},
            education_scores={"biology": 0.72},
            factual_grounding={"factual_grounding": 0.70},
            integration_pass_rate=0.85,
            regression_count=1,
            benchmark_scores={"biology": 0.72},
        )
        result = certify_release(input_data)
        assert result.passed
        assert result.level == "silver"

    def test_bronze_with_custom_thresholds(self):
        thresholds = {
            **DEFAULT_THRESHOLDS,
            "min_education_score": 0.60,
            "min_certification_score": 0.50,
        }
        input_data = CertificationInput(
            agent_scores={"planner": 0.72, "tutor": 0.70},
            education_scores={"biology": 0.62},
            factual_grounding={"factual_grounding": 0.60},
            integration_pass_rate=0.82,
            regression_count=2,
            benchmark_scores={"biology": 0.62},
        )
        result = certify_release(input_data, thresholds=thresholds)
        assert result.passed
        assert result.level == "bronze"

    def test_empty_input_handling(self):
        input_data = CertificationInput(
            agent_scores={},
            education_scores=None,
            factual_grounding=None,
            integration_pass_rate=None,
            regression_count=0,
            benchmark_scores=None,
        )
        result = certify_release(input_data)
        assert not result.passed

    def test_report_writing(self, tmp_path):
        input_data = CertificationInput(
            agent_scores={"planner": 0.85},
            education_scores=None,
            factual_grounding=None,
            integration_pass_rate=None,
            regression_count=0,
            benchmark_scores=None,
        )
        result = certify_release(input_data)
        path = write_certification_report(result, str(tmp_path))
        assert path.exists()
        assert path.suffix == ".json"

    def test_certification_result_dataclass(self):
        result = CertificationResult(
            passed=True,
            level="gold",
            score=0.85,
            checks={"thing": True},
            failures=[],
            generated_at="now",
        )
        assert result.passed
        assert result.level == "gold"
