import pytest
from wordle_bot.scorer import ScoreCalculator as SC
import polars as pl

def test_score_cleaner_converts_X_to_7():
    # Arrange
    scores = [
        ["Alice", 1, 'X'],
        ["Bob", 1, 3],
        ["Charlie", 1, 'X']
    ]

    sc_list = [SC(player, wordle, score) for player, wordle, score in scores]


    # Act
    df = SC.score_cleaner(sc_list)


    # Assert
    expected_df = pl.DataFrame({
        "player": ["Alice", "Bob", "Charlie"],
        "wordle_num": [1, 1, 1],
        "score": [7, 3, 7]
    })

    assert df.equals(expected_df)

def test_score_cleaner_fills_incompletes():
    # Arrange
    scores = [
        ["Alice", 1, "2"],
        ["Alice", 3, "2"]
    ]
    sc_list = [SC(player, wordle, score) for player, wordle, score in scores]

    # Act
    df = SC.score_cleaner(sc_list)

    # Assert
    expected_df = pl.DataFrame({
        "player": ["Alice", "Alice", "Alice"],
        "wordle_num": [1, 2, 3],
        "score": [2, 7, 2]
    })

    print(sc_list)
    print(df)
    print(expected_df)

    assert df.equals(expected_df)
