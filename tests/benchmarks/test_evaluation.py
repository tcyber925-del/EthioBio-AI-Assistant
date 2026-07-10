import pytest


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_smoke_scenarios_pass(mock_runner):
    """Smoke-tag scenarios should pass without regressions."""
    report = await mock_runner.run_all(filters=["smoke"])
    assert report.passed == report.total_scenarios, (
        f"Smoke scenarios: {report.passed}/{report.total_scenarios} passed. "
        f"Regressions: {report.regressions}"
    )


@pytest.mark.asyncio
async def test_curriculum_scenarios_load(mock_runner):
    """Curriculum scenarios should load from YAML."""
    curriculum = [s for s in mock_runner.scenarios if "curriculum" in s.get("tags", [])]
    assert len(curriculum) >= 3, f"Expected >=3 curriculum scenarios, got {len(curriculum)}"


@pytest.mark.asyncio
async def test_all_adversarial_scenarios(mock_runner):
    """Adversarial scenarios should not crash the pipeline."""
    report = await mock_runner.run_all(filters=["adversarial"])
    for r in report.results:
        assert r.error is None, f"Unexpected error in {r.scenario_id}: {r.error}"


@pytest.mark.asyncio
async def test_runner_filters_by_tag(mock_runner):
    """Only scenarios matching the filter should run."""
    full_report = await mock_runner.run_all()
    filtered_report = await mock_runner.run_all(filters=["curriculum"])
    assert filtered_report.total_scenarios < full_report.total_scenarios
    assert filtered_report.total_scenarios > 0
