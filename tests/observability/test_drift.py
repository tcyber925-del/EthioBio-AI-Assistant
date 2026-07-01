import json

from src.observability.evaluation.drift import DriftDetector, ScoreHistory, WeeklyStats


class TestScoreHistory:
    def test_defaults(self):
        sh = ScoreHistory(dimension="faithfulness")
        assert sh.dimension == "faithfulness"
        assert sh.weeks == []


class TestWeeklyStats:
    def test_defaults(self):
        ws = WeeklyStats(week="2026-W01", avg_score=0.85, n=20)
        assert ws.avg_score == 0.85
        assert ws.n == 20


class TestDriftDetector:
    def _make_detector(self, tmp_path, monkeypatch, threshold=0.1):
        monkeypatch.setattr("src.config.settings.eval_drift_threshold", threshold)
        history_file = tmp_path / ".score_history.json"
        monkeypatch.setattr("src.observability.evaluation.drift.SCORE_HISTORY_PATH", history_file)
        return DriftDetector()

    def test_no_history(self, tmp_path, monkeypatch):
        d = self._make_detector(tmp_path, monkeypatch)
        assert d.get_baseline("faithfulness") is None
        assert d.check_drift("faithfulness", 0.5) is None

    def test_insufficient_history(self, tmp_path, monkeypatch):
        d = self._make_detector(tmp_path, monkeypatch)
        d.record_week("faithfulness", 0.8, 5)
        assert d.get_baseline("faithfulness") is None

    def test_sufficient_history(self, tmp_path, monkeypatch):
        d = self._make_detector(tmp_path, monkeypatch)
        for _ in range(4):
            d.record_week("faithfulness", 0.85, 15)
        baseline = d.get_baseline("faithfulness")
        assert baseline is not None
        assert abs(baseline - 0.85) < 0.01

    def test_check_drift_within_threshold(self, tmp_path, monkeypatch):
        d = self._make_detector(tmp_path, monkeypatch, threshold=0.1)
        for _ in range(4):
            d.record_week("faithfulness", 0.85, 15)
        drift = d.check_drift("faithfulness", 0.88)
        assert drift is not None
        assert drift < 0.1

    def test_check_drift_exceeds_threshold(self, tmp_path, monkeypatch):
        d = self._make_detector(tmp_path, monkeypatch, threshold=0.05)
        for _ in range(4):
            d.record_week("faithfulness", 0.85, 15)
        drift = d.check_drift("faithfulness", 0.5)
        assert drift is not None
        assert drift > 0.05

    def test_persist_to_disk(self, tmp_path, monkeypatch):
        d = self._make_detector(tmp_path, monkeypatch)
        d.record_week("faithfulness", 0.9, 20)
        history_file = tmp_path / ".score_history.json"
        assert history_file.exists()
        data = json.loads(history_file.read_text())
        assert "faithfulness" in data

    def test_clean_slate(self, tmp_path, monkeypatch):
        d = self._make_detector(tmp_path, monkeypatch)
        assert d._history == {}
