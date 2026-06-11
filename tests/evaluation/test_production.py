"""Unit tests for production readiness check modules (PRD-010D)."""

from evaluation.certification.certifier import (
    CertificationInput,
    certify_release,
)
from evaluation.production.cost_efficiency import (
    check_model_cost_tracking,
    check_token_budgeting,
    run_cost_efficiency_checks,
)
from evaluation.production.governance import (
    check_source_attribution,
    check_trace_id_flow,
    run_governance_checks,
)
from evaluation.production.reliability import (
    check_graph_error_handling,
    check_iterative_loop_safeguards,
    check_provider_fallback,
    run_reliability_checks,
)
from evaluation.production.runner import (
    check_production_thresholds,
    get_production_scores,
    run_all_production_checks,
)
from evaluation.production.safety_hardening import (
    check_claim_verification,
    check_grounding_enforcement,
    check_hallucination_detection,
    check_misconception_detection,
    check_safety_node_robustness,
    check_teacher_review_threshold,
    run_safety_hardening_checks,
)
from evaluation.production.security import (
    check_cors_configuration,
    check_jwt_secret,
    check_pii_sanitization,
    check_rate_limiting_config,
    check_redis_auth,
    run_security_checks,
)


class TestProductionReliability:
    def test_provider_fallback_check(self):
        result = check_provider_fallback()
        assert "check" in result
        assert "passed" in result
        assert "detail" in result

    def test_graph_error_handling_check(self):
        result = check_graph_error_handling()
        assert "check" in result
        assert "passed" in result
        assert "coverage" in result

    def test_iterative_loop_safeguards_check(self):
        result = check_iterative_loop_safeguards()
        assert "passed" in result

    def test_run_reliability_checks(self):
        result = run_reliability_checks()
        assert "score" in result
        assert "passed" in result
        assert "total" in result
        assert result["total"] > 0
        assert len(result["checks"]) > 0


class TestProductionSecurity:
    def test_jwt_secret_check(self):
        result = check_jwt_secret()
        assert "passed" in result

    def test_cors_check(self):
        result = check_cors_configuration()
        assert "passed" in result

    def test_pii_sanitization_check(self):
        result = check_pii_sanitization()
        assert "passed" in result

    def test_rate_limiting_check(self):
        result = check_rate_limiting_config()
        assert "passed" in result

    def test_redis_auth_check(self):
        result = check_redis_auth()
        assert "passed" in result

    def test_run_security_checks(self):
        result = run_security_checks()
        assert "score" in result
        assert result["total"] > 0


class TestProductionSafety:
    def test_hallucination_detection_check(self):
        result = check_hallucination_detection()
        assert "passed" in result

    def test_safety_node_robustness_check(self):
        result = check_safety_node_robustness()
        assert "passed" in result

    def test_claim_verification_check(self):
        result = check_claim_verification()
        assert "passed" in result

    def test_grounding_enforcement_check(self):
        result = check_grounding_enforcement()
        assert "passed" in result

    def test_misconception_detection_check(self):
        result = check_misconception_detection()
        assert "passed" in result

    def test_teacher_review_threshold_check(self):
        result = check_teacher_review_threshold()
        assert "passed" in result

    def test_run_safety_hardening_checks(self):
        result = run_safety_hardening_checks()
        assert "score" in result
        assert result["total"] > 0


class TestProductionGovernance:
    def test_trace_id_flow_check(self):
        result = check_trace_id_flow()
        assert "passed" in result

    def test_source_attribution_check(self):
        result = check_source_attribution()
        assert "passed" in result

    def test_run_governance_checks(self):
        result = run_governance_checks()
        assert "score" in result
        assert result["total"] > 0


class TestProductionCostEfficiency:
    def test_model_cost_tracking_check(self):
        result = check_model_cost_tracking()
        assert "passed" in result

    def test_token_budgeting_check(self):
        result = check_token_budgeting()
        assert "passed" in result

    def test_run_cost_efficiency_checks(self):
        result = run_cost_efficiency_checks()
        assert "score" in result
        assert result["total"] > 0


class TestProductionRunner:
    def test_run_all_production_checks(self):
        results = run_all_production_checks()
        assert len(results) == 5
        for cat in ["reliability", "security", "safety_hardening", "governance", "cost_efficiency"]:
            assert cat in results
            assert "score" in results[cat]

    def test_get_production_scores(self):
        results = run_all_production_checks()
        scores = get_production_scores(results)
        assert len(scores) == 5
        for cat in ["reliability", "security", "safety_hardening", "governance", "cost_efficiency"]:
            assert cat in scores
            assert 0.0 <= scores[cat] <= 1.0

    def test_check_production_thresholds(self):
        results = run_all_production_checks()
        failures = check_production_thresholds(results)
        assert isinstance(failures, list)

    def test_check_production_thresholds_custom(self):
        results = run_all_production_checks()
        thresholds = {"reliability": 0.0, "security": 0.0, "safety_hardening": 0.0, "governance": 0.0, "cost_efficiency": 0.0}
        failures = check_production_thresholds(results, thresholds)
        assert len(failures) == 0


class TestCertifierProductionIntegration:
    def test_certifier_with_production_scores(self):
        input_data = CertificationInput(
            agent_scores={"planner": 0.85, "tutor": 0.90},
            education_scores={"biology": 0.88},
            factual_grounding={"factual_grounding": 0.80},
            integration_pass_rate=0.95,
            regression_count=0,
            benchmark_scores={"biology": 0.88},
            production_scores={
                "reliability": 0.85,
                "security": 0.90,
                "safety_hardening": 0.88,
                "governance": 0.82,
                "cost_efficiency": 0.75,
            },
        )
        result = certify_release(input_data)
        assert result.passed
        assert result.production_ready
        assert result.production_level != ""
        assert "production_overall" in result.checks

    def test_certifier_with_failing_production(self):
        input_data = CertificationInput(
            agent_scores={"planner": 0.85, "tutor": 0.90},
            education_scores={"biology": 0.88},
            factual_grounding={"factual_grounding": 0.80},
            integration_pass_rate=0.95,
            regression_count=0,
            benchmark_scores={"biology": 0.88},
            production_scores={
                "reliability": 0.30,
                "security": 0.90,
                "safety_hardening": 0.88,
                "governance": 0.82,
                "cost_efficiency": 0.75,
            },
        )
        result = certify_release(input_data)
        assert result.production_ready is False
        assert any("production_reliability" in f for f in result.failures)

    def test_certifier_without_production_scores(self):
        input_data = CertificationInput(
            agent_scores={"planner": 0.85},
            education_scores=None,
            factual_grounding=None,
            integration_pass_rate=None,
            regression_count=0,
            benchmark_scores=None,
        )
        result = certify_release(input_data)
        assert result.production_ready is False
        assert result.production_level == ""

    def test_certifier_deployment_ready(self):
        input_data = CertificationInput(
            agent_scores={"planner": 0.85, "tutor": 0.90},
            education_scores={"biology": 0.88},
            factual_grounding={"factual_grounding": 0.80},
            integration_pass_rate=0.95,
            regression_count=0,
            benchmark_scores={"biology": 0.88},
            production_scores={
                "reliability": 0.85,
                "security": 0.90,
                "safety_hardening": 0.88,
                "governance": 0.82,
                "cost_efficiency": 0.75,
            },
        )
        result = certify_release(input_data)
        deployment_ready = result.passed and result.production_ready
        assert deployment_ready
