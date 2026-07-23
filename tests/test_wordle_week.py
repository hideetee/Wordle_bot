import pytest

from wordle_bot.scorer import ScoreCalculator

def test_wordle_week_random_wordle_num():
    # Arrange
    # Anchor: Wordle 1860 = Thursday (weekday index 4)
    # Wordle 1865 is 5 days later → weekday = (4 + 5) % 7 = 2 (Tuesday)
    # Sunday index = (2 + 1) % 7 = 3
    # Week start = 1865 - 3 = 1862
    # Week end   = 1862 + 6 = 1868
    expected_start = 1863
    expected_end = 1869

    # Act
    week_start, week_end = ScoreCalculator.wordle_week(1865)

    # Assert
    assert week_start == expected_start
    assert week_end == expected_end


def test_wordle_week_non_int_input():
    # Arrange
    wordle_number = "not_a_number"

    # Act & Assert
    with pytest.raises(TypeError):
        ScoreCalculator.wordle_week(wordle_number)
