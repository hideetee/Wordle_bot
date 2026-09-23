import pytest
from game_bot.scorer import ScoreCalculator as SC
import polars as pl

def test_score_cleaner_converts_X_to_max_players_plus_1():
    # Arrange
    scores = [
        ["Alice", 1, 'X'],
        ["Bob", 1, 3],
        ["Charlie", 1, 'X']
    ]

    sc_list = [SC(player, wordle_num, score) for player, wordle_num, score in scores]


    # Act
    df = SC.score_cleaner(data = sc_list, game = 'wordle')


    # Assert
    # 7 is the WORDLE_FAIL_PENALTY_SCORE
    expected_df = pl.DataFrame({
        "player": ["A", "B", "C"],
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
    sc_list = [SC(player, wordle_num, score) for player, wordle_num, score in scores]

    # Act
    df = SC.score_cleaner(data = sc_list, game = 'wordle')

    # Assert
    expected_df = pl.DataFrame({
        "player": ["A", "A", "A"],
        "wordle_num": [1, 2, 3],
        "score": [2, 7, 2]
    })

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
    df = SC.score_cleaner(data = sc_list, game = 'wordle')

    # Assert
    expected_df = pl.DataFrame({
        "player": ["A", "B", "A", "B", "A", "B"],
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
    df = SC.score_cleaner(data = sc_list, game = 'wordle', wordle_start=101)

    expected_df = pl.DataFrame({
        "player": ["A", "B", "A", "B", "A", "B"],
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

    df = SC.score_cleaner(data = sc_list, game = 'wordle', wordle_start=105)
    assert df.height == 0


### Pips Tests ###
    
def test_score_cleaner_add_missing_rows_keeps_nulls():
    # Arrange
    scores = [
        ["Alice", 1, '5:00'],
        ["Bob", 1, "3:00"],
        ["Charlie", 1, '2:00'],
        ["Alice", 2, "1:00"],
    ]

    sc_list = [SC(player, pips_num, score) for player, pips_num, score in scores]


    # Act
    df = SC.score_cleaner(data = sc_list, game = 'pips')


    # Assert
    expected_df = pl.DataFrame({
        "player": ["A", "B", "C"]*2,
        "pips_num": [1, 1, 1, 2, 2, 2],
        "time_str": ["5:00", "3:00", "2:00", "1:00", None, None],
        "time_seconds": [300, 180, 120, 60, None, None]
    })
    

    assert df.equals(expected_df)


def test_score_cleaner_fills_incompletes_pips():
    # Arrange
    scores = [
        ["Alice", 1, "2:00"],
        ["Alice", 3, "2:00"]
    ]
    sc_list = [SC(player, pips_num, score) for player, pips_num, score in scores]

    # Act
    df = SC.score_cleaner(data = sc_list, game = 'pips')

    # Assert
    expected_df = pl.DataFrame({
        "player": ["A", "A", "A"],
        "pips_num": [1, 2, 3],
        "time_str": ["2:00", None, "2:00"],
        "time_seconds": [120, None, 120]
    })

    assert df.equals(expected_df)


def test_score_cleaner_with_pips_start_limits_pips():
    # Scores before and after pips_start
    scores = [
        ["Alice", 100, "3:00"],
        ["Bob", 100, "4:00"],
        ["Alice", 101, "2:00"],
        ["Bob", 102, "5:00"],
    ]
    sc_list = [SC(player, pips_num, score) for player, pips_num, score in scores]

    df = SC.score_cleaner(data = sc_list, game = 'pips', pips_start=101)
    expected_df = pl.DataFrame({
        "player": ["A", "B", "A", "B"],
        "pips_num": [101, 101, 102, 102],
        "time_str": ["2:00", None,  None, "5:00"],
        "time_seconds": [120, None, None, 300]
    }).sort(["pips_num", "player"])
    assert df.equals(expected_df)


def test_score_cleaner_pips_start_exceeds_max():
    scores = [
        ["Alice", 100, "3:00"],
        ["Bob", 100, "4:00"],
    ]
    sc_list = [SC(player, pips_num, score) for player, pips_num, score in scores]

    df = SC.score_cleaner(data = sc_list, game = 'pips', pips_start=105)
    assert df.height == 0