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

def test_score_cleaner_fills_incompletes_recents_unfilled():
    # Arrange
    scores = [
        ["Alice", 1, "2"],
        ['Bob', 1, "3"],
        ["Bob", 2, "X"], # converted to 7
        ["Bob", 3, None], # remains NULL
        ["Alice", 3, "2"]]


    sc_list = [SC(player, wordle, score) for player, wordle, score in scores]

    # Act 
    df = SC.score_cleaner(sc_list)

    # Assert
    expected_df = pl.DataFrame({
        "player": ["Alice", "Bob", "Alice", "Bob", "Alice", "Bob"],
        "wordle_num": [1, 1, 2, 2, 3, 3],
        "score": [2, 3, 7, 7, 2, None]
    }).sort(["wordle_num", "player"])

    assert df.equals(expected_df)


def test_score_cleaner_with_wordle_start_limits_and_fills():
    # Scores before and after wordle_start
    scores = [
        ["Alice", 100, "3"],
        ["Bob", 100, "4"],
        ["Alice", 101, "2"],
        ["Bob", 103, "5"],
    ]
    sc_list = [SC(player, wordle, score) for player, wordle, score in scores]

    # wordle_start = 101: 100 is omitted, 102 is filled with 7, 103 is max (Bob=5, Alice unplayed on current day -> None)
    df = SC.score_cleaner(sc_list, wordle_start=101)

    expected_df = pl.DataFrame({
        "player": ["Alice", "Bob", "Alice", "Bob", "Alice", "Bob"],
        "wordle_num": [101, 101, 102, 102, 103, 103],
        "score": [2, 7, 7, 7, None, 5]
    }).sort(["wordle_num", "player"])

    assert df.equals(expected_df)


def test_score_cleaner_wordle_start_exceeds_max():
    scores = [
        ["Alice", 100, "3"],
        ["Bob", 100, "4"],
    ]
    sc_list = [SC(player, wordle, score) for player, wordle, score in scores]

    df = SC.score_cleaner(sc_list, wordle_start=105)
    assert df.height == 0



    
