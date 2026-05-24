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


def test_quiz_xp_calculation():
    from src.telegram.bot import _calculate_quiz_xp
    assert _calculate_quiz_xp(50) == 10
    assert _calculate_quiz_xp(80) == 20
    assert _calculate_quiz_xp(90) == 20
    assert _calculate_quiz_xp(100) == 35


def test_streak_bonus_thresholds():
    from src.api.gamification import STREAK_BONUS_THRESHOLDS
    assert STREAK_BONUS_THRESHOLDS[7] == 20
    assert STREAK_BONUS_THRESHOLDS[14] == 50
    assert STREAK_BONUS_THRESHOLDS[21] == 100
    assert STREAK_BONUS_THRESHOLDS[30] == 200
