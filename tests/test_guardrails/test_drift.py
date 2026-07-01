import pytest

from src.guardrails.drift import DriftMonitor


def test_drift_monitor_records():
    d = DriftMonitor()
    for _ in range(7):
        d.record_check("input", triggered=False)
    for _ in range(3):
        d.record_check("input", triggered=True)
    rate = d.get_trigger_rate("input")
    assert rate is not None
    assert rate == pytest.approx(0.3, rel=0.1)


def test_drift_monitor_insufficient_data():
    d = DriftMonitor()
    d.record_check("new_layer", triggered=False)
    rate = d.get_trigger_rate("new_layer")
    assert rate is None


def test_drift_alert_fires():
    d = DriftMonitor()
    for _ in range(20):
        d.record_check("test", triggered=True)
    d._baselines["test"] = 0.1
    alert = d.check_drift("test")
    assert alert is not None
    assert alert.drift > 0.05


def test_rebaseline():
    d = DriftMonitor()
    for _ in range(20):
        d.record_check("test", triggered=True)
    d._baselines["test"] = 0.5
    d.rebaseline("test")
    assert d._baselines["test"] == pytest.approx(1.0, rel=0.1)


def test_get_alerts_clear():
    d = DriftMonitor()
    for _ in range(20):
        d.record_check("test", triggered=True)
    d._baselines["test"] = 0.1
    d.check_drift("test")
    alerts = d.get_alerts(clear=True)
    assert len(alerts) >= 0
    assert len(d.get_alerts(clear=False)) == 0
