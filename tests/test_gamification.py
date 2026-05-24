from src.schemas.gamification import calculate_level, xp_for_next_level


def test_calculate_level_starts_at_one():
    assert calculate_level(0) == 1
    assert calculate_level(50) == 1


def test_calculate_level_thresholds():
    assert calculate_level(100) == 2
    assert calculate_level(250) == 3
    assert calculate_level(500) == 4
    assert calculate_level(1000) == 5
    assert calculate_level(1750) == 6


def test_calculate_level_high_values():
    assert calculate_level(10000) >= 11


def test_xp_for_next_level():
    assert xp_for_next_level(0) == 100
    assert xp_for_next_level(50) == 50
    assert xp_for_next_level(100) == 150


def test_xp_for_next_level_max_level():
    assert xp_for_next_level(100000) == 0
