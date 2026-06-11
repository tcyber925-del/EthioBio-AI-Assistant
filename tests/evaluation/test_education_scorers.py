"""Unit tests for education and grounding scorers (PRD-010C)."""

from evaluation.scorers.education import (
    EDUCATION_WEIGHTS,
    score_accuracy,
    score_clarity,
    score_completeness,
    score_personalization,
    score_relevance,
    score_weighted_education,
)
from evaluation.scorers.grounding import (
    score_coherence,
    score_factual_grounding,
    score_topic_coverage,
)


class TestEducationAccuracy:
    def test_all_topics_covered(self):
        text = "The cell membrane is a selective barrier that controls transport."
        topics = ["cell membrane", "cell transport"]
        assert score_accuracy(text, topics) == 1.0

    def test_partial_coverage(self):
        text = "The cell membrane surrounds the cell."
        topics = ["cell membrane", "cell transport", "selective barrier"]
        score = score_accuracy(text, topics)
        assert 0.0 < score < 1.0

    def test_no_topics_expected(self):
        assert score_accuracy("anything", []) == 1.0

    def test_no_coverage(self):
        text = "Photosynthesis happens in chloroplasts."
        topics = ["cell membrane", "mitosis"]
        assert score_accuracy(text, topics) == 0.0


class TestEducationClarity:
    def test_optimal_sentences(self):
        text = (
            "The cell membrane controls what enters and leaves the cell body. "
            "It is a selective barrier protecting the interior environment. "
            "This passive transport process requires no cellular energy."
        )
        assert score_clarity(text) > 0.2

    def test_very_long_sentences(self):
        text = (
            "The cell membrane is a biological membrane that separates "
            "and protects the interior of all cells from the external "
            "environment and controls the movement of substances in and "
            "out of cells through various mechanisms."
        )
        assert score_clarity(text) < 0.8

    def test_empty_text(self):
        assert score_clarity("") == 0.0


class TestEducationRelevance:
    def test_high_relevance(self):
        text = "Mitosis has four stages: prophase, metaphase, anaphase, telophase."
        topics = ["mitosis", "prophase", "metaphase"]
        question = "What are the stages of mitosis?"
        score = score_relevance(text, topics, question)
        assert score > 0.5

    def test_low_relevance(self):
        text = "Photosynthesis converts light energy to chemical energy."
        topics = ["mitosis", "cell division"]
        question = "What is photosynthesis?"
        score = score_relevance(text, topics, question)
        assert score < 0.5


class TestEducationCompleteness:
    def test_high_completeness(self):
        text = "DNA is transcribed into mRNA. Then translation occurs. Finally proteins fold."
        topics = ["transcription", "translation", "protein folding"]
        traits = ["sequential"]
        score = score_completeness(text, topics, traits)
        assert score > 0.5

    def test_low_completeness(self):
        text = "DNA is important."
        topics = ["transcription", "translation", "protein folding"]
        traits = ["sequential"]
        score = score_completeness(text, topics, traits)
        assert score < 0.5


class TestEducationPersonalization:
    def test_grade_appropriate_elementary(self):
        text = "The heart pumps blood through your body. Think of it as a pump."
        score = score_personalization(text, 7, ["simple"])
        assert score > 0.3

    def test_grade_appropriate_advanced(self):
        text = "The cardiac cycle involves SA node depolarization and AV node conduction."
        score = score_personalization(text, 12, ["detailed", "technical"])
        assert score > 0.3

    def test_remedial_trait(self):
        text = (
            "Simply put, the cell membrane is like a gate. "
            "In other words, it controls what goes in and out."
        )
        score = score_personalization(text, 8, ["remedial", "patient"])
        assert score > 0.3


class TestWeightedEducation:
    def test_high_quality_response(self):
        text = (
            "Photosynthesis has two main stages: light-dependent and light-independent. "
            "First, light energy is captured by chlorophyll. Then, the Calvin cycle uses "
            "that energy to make glucose. This process happens in chloroplasts. "
            "Think of it as the plant making its own food using sunlight."
        )
        result = score_weighted_education(
            response_text=text,
            expected_topics=["photosynthesis", "light reactions", "Calvin cycle", "chloroplast"],
            expected_answer_traits=["accurate", "sequential", "curriculum_aligned"],
            question="Explain photosynthesis.",
            grade_level=10,
        )
        assert result["weighted_score"] > 0.5
        assert all(0.0 <= v <= 1.0 for v in [result["accuracy"], result["clarity"]])
        assert set(result["weights"].keys()) == set(EDUCATION_WEIGHTS.keys())

    def test_low_quality_response(self):
        text = "Plants are green."
        result = score_weighted_education(
            response_text=text,
            expected_topics=["photosynthesis", "Calvin cycle", "chloroplast"],
            expected_answer_traits=["accurate", "comprehensive"],
            question="Explain photosynthesis in detail.",
            grade_level=10,
        )
        assert result["weighted_score"] < 0.5

    def test_empty_response(self):
        result = score_weighted_education(
            response_text="",
            expected_topics=["photosynthesis"],
            expected_answer_traits=["accurate"],
            question="What is photosynthesis?",
            grade_level=8,
        )
        assert result["weighted_score"] < 0.3


class TestGroundingTopicCoverage:
    def test_full_coverage(self):
        text = "DNA has a double helix structure. Nucleotides form base pairs."
        result = score_topic_coverage(text, ["DNA structure", "double helix", "nucleotides"])
        assert result["coverage"] == 1.0
        assert len(result["covered"]) == 3
        assert len(result["missed"]) == 0

    def test_partial_coverage(self):
        text = "DNA stores genetic information."
        result = score_topic_coverage(text, ["DNA structure", "double helix", "base pairing"])
        assert result["coverage"] < 1.0
        assert len(result["missed"]) > 0

    def test_no_expected_topics(self):
        result = score_topic_coverage("anything", [])
        assert result["coverage"] == 1.0


class TestGroundingCoherence:
    def test_well_structured(self):
        text = (
            "First, DNA replication occurs during S phase.\n\n"
            "Then, mitosis divides the nucleus.\n\n"
            "Finally, cytokinesis splits the cell."
        )
        result = score_coherence(text)
        assert result["paragraphs"] >= 2
        assert result["coherence"] > 0.3

    def test_single_sentence(self):
        result = score_coherence("DNA replication occurs during S phase.")
        assert result["coherence"] > 0.0
        assert result["sentences"] == 1

    def test_empty_text(self):
        result = score_coherence("")
        assert result["coherence"] == 0.0


class TestGroundingFactual:
    def test_good_grounding(self):
        text = "Enzymes catalyze reactions by binding to substrates at the active site."
        result = score_factual_grounding(text, ["enzymes", "catalysis", "active site", "substrate"])
        assert result["factual_grounding"] > 0.3

    def test_poor_grounding(self):
        text = "Enzymes are proteins."
        result = score_factual_grounding(
            text,
            ["enzymes", "catalysis", "active site", "substrate", "activation energy"],
        )
        assert result["factual_grounding"] < 0.5
        assert len(result["missed_topics"]) > 0
