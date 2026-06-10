from src.agents.tutor.personalization import build_personalization_block


def test_with_full_profile():
    block = build_personalization_block(
        learner_profile_block="weak_areas: genetics",
        grade_level=10,
        language="am",
        misconceptions=["confuses dominant and recessive"],
    )
    assert "Grade Level: 10" in block
    assert "Language: am" in block
    assert "weak_areas: genetics" in block
    assert "confuses dominant and recessive" in block


def test_empty_profile_returns_empty():
    block = build_personalization_block(
        learner_profile_block="",
        grade_level=None,
        language="en",
        misconceptions=[],
    )
    assert block == ""


def test_no_misconceptions():
    block = build_personalization_block(
        learner_profile_block="grade_level: 8",
        grade_level=8,
        language="en",
        misconceptions=[],
    )
    assert "Grade Level: 8" in block
    assert "Misconceptions" not in block
