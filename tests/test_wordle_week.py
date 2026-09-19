import pytest
import polars as pl

from game_bot.scorer import ScoreCalculator as SC



def test_game_week_random_wordle_num():
    # Arrange
    # Anchor: Wordle 1860 = Thursday (weekday index 4)
    # Wordle 1865 is 5 days later → weekday = (4 + 5) % 7 = 2 (Tuesday)
    # Sunday index = (2 + 1) % 7 = 3
    # Week start = 1865 - 3 = 1862
    # Week end   = 1862 + 6 = 1868
    game = "wordle"
    game_num = 1865

    expected_start = 1863
    expected_end = 1869
    

    # Act
    week_start, week_end = SC.game_week(game, game_num)

    # Assert
    assert week_start == expected_start
    assert week_end == expected_end


def test_game_week_non_int_input():
    # Arrange
    not_number = "not_a_number"
    game = "wordle"
    
    # Act & Assert
    with pytest.raises(TypeError):
        SC.game_week(game, not_number)

