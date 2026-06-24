from src.core.misconception_intelligence.detector import HeuristicDetector


class TestHeuristicDetector:
    def setup_method(self):
        self.detector = HeuristicDetector()

    def test_detects_common_misconception(self):
        text = (
            "That's a common misconception about photosynthesis. "
            "Plants actually use both light and dark reactions."
        )
        detected, correction = self.detector.detect_in_text(text)
        assert detected is True
        assert "common misconception" in correction
        assert "photosynthesis" in correction

    def test_detects_incorrect_statement(self):
        text = "That's not quite right. The mitochondria is not part of the endomembrane system."
        detected, correction = self.detector.detect_in_text(text)
        assert detected is True
        assert "not quite right" in correction

    def test_returns_false_for_normal_text(self):
        text = "Great answer! The cell membrane is selectively permeable."
        detected, correction = self.detector.detect_in_text(text)
        assert detected is False
        assert correction == ""

    def test_extracts_two_sentences_of_correction(self):
        text = (
            "I see a misconception here. DNA replication happens in the S phase. "
            "It is semi-conservative."
        )
        detected, correction = self.detector.detect_in_text(text)
        assert detected is True
        assert "S phase" in correction

    def test_truncates_long_corrections(self):
        text = "That is incorrect. " + ("long text " * 100)
        detected, correction = self.detector.detect_in_text(text)
        assert detected is True
        assert len(correction) <= 300

    def test_detects_not_accurate(self):
        text = "That's not accurate. Ribosomes are not membrane-bound."
        detected, correction = self.detector.detect_in_text(text)
        assert detected is True
        assert "not accurate" in correction

    def test_case_insensitive(self):
        text = "COMMON MISCONCEPTION: All bacteria are harmful."
        detected, correction = self.detector.detect_in_text(text)
        assert detected is True
