import pytest

from src.guardrails.output.toxicity import ToxicityDetector


def test_clean_biology_text():
    d = ToxicityDetector()
    result = d.check("Mitochondria are the powerhouse of the cell.")
    assert not result.flagged


def test_violence_keyword():
    d = ToxicityDetector()
    result = d.check("This experiment could kill and hurt and harm the organism")
    assert result.flagged


def test_hate_speech():
    d = ToxicityDetector()
    result = d.check("That is a hateful and racist statement")
    assert result.flagged
    assert "hate_speech" in result.categories


def test_self_harm_flagged():
    d = ToxicityDetector()
    result = d.check("Thoughts about suicide and self-harm")
    assert result.flagged
    assert "self_harm" in result.categories
