import pytest
import polars as pl
from game_bot.scorer import ScoreCalculator as SC
from polars.testing import assert_frame_equal, assert_frame_not_equal

def test_compute_weekly_score_full_weeks_wordle():
    ## Arrange ##
    scores_df = pl.DataFrame({
        "player": ["Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob","Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob"],
        "wordle_num": [1870, 1870, 1871, 1871, 1872, 1872, 1873, 1873, 1874, 1874, 1875,1875, 1876, 1876, 1877, 1877, 1878, 1878, 1879, 1879, 1880, 1880, 1881, 1881, 1882,1882, 1883, 1883],
        "score": [3, 4, 5, 2, 3, 4, 1, 2, 3,2, 3, 4, 5, 2, 3, 4, 5, 2, 3, 4, 1, 2, 3,2, 3, 4, 5, 2]
        })
    
    
    scores_df = scores_df.with_columns(
        pl.col("wordle_num").cast(pl.Int32),
        pl.col("score").cast(pl.Int64)
    )

    
        ## Act ##

  
    scores_rank = SC.compute_weekly_score(scores_df, game = 'wordle')
    
    ## Assert
    scores_rank_expected = [
        pl.DataFrame({
        "player": ["Bob", "Alice"],
        "score": [20, 23],
        "week_start": [1870, 1870],
        "week_end": [1876, 1876]
        }),
        pl.DataFrame({
        "player": ["Bob", "Alice"],
        "score": [20, 23],
        "week_start": [1877, 1877],
        "week_end": [1883, 1883]
        })
    ]


    for df_actual, df_expected in zip(scores_rank, scores_rank_expected):
        assert_frame_equal(df_actual, df_expected)


def test_compute_weekly_score_full_weeks_pips():
    ## Arrange ##
    scores_df = pl.DataFrame({
        "player": ["Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob","Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob"],
        "pips_num": [391, 391, 392, 392, 393, 393, 394, 394, 395, 395, 396, 396, 397, 397, 398, 398, 399, 399, 400, 400, 401, 401, 402, 402, 403, 403, 404, 404],
        "time_str": ["3:40", "4:00", "5:53", "2:00", "3:00", "4:00", "1:12", "2:00", "3:00", "2:00", "3:00", "4:00", "5:00", "2:00", "3:00", "4:00", "5:00", "2:00", "3:00", "4:00", "1:00", "2:00", "3:00", "2:00", "3:42", "4:00", "5:00", "2:10"] 
    })
    
    scores_df = scores_df.with_columns(
        pl.col("pips_num").cast(pl.Int32),
        pl.col("time_str").cast(pl.String)
    )

    ## Act ##
    scores_rank = SC.compute_weekly_score(scores_df, game='pips')
    
    ## Assert
    scores_rank_expected = [
        pl.DataFrame({
            "player": ["Bob", "Alice"],
            "time_seconds": [1200, 1485],
            "week_start": [391, 391],
            "week_end": [397, 397]
        }),
        pl.DataFrame({
            "player": ["Bob", "Alice"],
            "time_seconds": [1210, 1422],
            "week_start": [398, 398],
            "week_end": [404, 404]
        })
    ]


    for df_actual, df_expected in zip(scores_rank, scores_rank_expected):
        assert_frame_equal(df_actual, df_expected)


        

def test_compute_weekly_score_1_incomplete_week():
    ## Arrange ##
    scores_df = pl.DataFrame({
        "player": ["Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob"],
        "wordle_num": [1870, 1870, 1871, 1871, 1872, 1872, 1873, 1873, 1874, 1874],
        "score": [3, 4, 5, 2, 3, 4, 1, 2, 3, 2]
    })

    ## Act ##

    scores_rank = SC.compute_weekly_score(scores_df, game = 'wordle')

    assert scores_rank == []


def test_compute_weekly_score_1_complete_week_and_1_incomplete_week():
    ## Arrange ##
    scores_df = pl.DataFrame({
        "player": ["Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob","Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob"],
        "wordle_num": [1870, 1870, 1871, 1871, 1872, 1872, 1873, 1873, 1874, 1874, 1875,1875, 1876, 1876, 1877, 1877, 1878, 1878, 1879, 1879, 1880, 1880, 1881, 1881, 1882,1882],
        "score": [3, 4, 5, 2, 3, 4, 1, 2, 3,2, 3, 4, 5, 2, 3, 4, 5, 2, 3, 4, 1, 2, 3,2, 3, 4]
        })
    
    scores_df = scores_df.with_columns(
        pl.col("wordle_num").cast(pl.Int32),
        pl.col("score").cast(pl.Int64)
    )

    ## Act ##
    scores_rank = SC.compute_weekly_score(scores_df, game = 'wordle')

    scores_rank_expected = [
        pl.DataFrame({
        "player": ["Bob", "Alice"],
        "score": [20, 23],
        "week_start": [1870, 1870],
        "week_end": [1876, 1876]
        }),
        pl.DataFrame()
    ]

    ## Assert
    for df_actual, df_expected in zip(scores_rank, scores_rank_expected):
        assert_frame_equal(df_actual, df_expected)


def test_compute_weekly_score_with_wordle_start():
    # 2 full weeks: 1870-1876 and 1877-1883
    scores_df = pl.DataFrame({
        "player": ["Alice", "Bob"] * 14,
        "wordle_num": [w for w in range(1870, 1884) for _ in range(2)],
        "score": [3, 4] * 14,
    })

    # wordle_start = 1877 limits to only the second week
    scores_rank = SC.compute_weekly_score(scores_df, wordle_start=1877, game='wordle')
    assert len(scores_rank) == 1
    assert scores_rank[0]["week_start"][0] == 1877
    assert scores_rank[0]["week_end"][0] == 1883

    
def test_compute_weekly_score_pips_1_incomplete_week():
    # Arrange: only 5 days → incomplete week (needs 7)
    df = pl.DataFrame({
        "player": ["Alice", "Bob"] * 5,
        "pips_num": [391, 391, 392, 392, 393, 393, 394, 394, 395, 395],
        "time_str": ["1:00", "2:00"] * 5,
    })

    # Act
    scores_rank = SC.compute_weekly_score(df, game="pips")

    # Assert
    assert scores_rank == []


def test_compute_weekly_score_pips_1_complete_week_and_1_incomplete_week():
    # Arrange: 13 days → week1 complete, week2 incomplete
    df = pl.DataFrame({
        "player": ["Alice", "Bob"] * 13,
        "pips_num": [w for w in range(391, 404) for _ in range(2)],
        "time_str": ["1:00", "2:00"] * 13,   # Alice=60s, Bob=120s
    }).with_columns(
        pl.col("pips_num").cast(pl.Int32)
    )

    # Act
    scores_rank = SC.compute_weekly_score(df, game="pips")


    expected_week1 = pl.DataFrame({
        "player": ["Alice", "Bob"],
        "time_seconds": [420, 840],
        "week_start": [391, 391],
        "week_end": [397, 397],
    }).sort("time_seconds")

    expected = [expected_week1, pl.DataFrame()]

    # Assert
    for df_actual, df_expected in zip(scores_rank, expected):
        assert_frame_equal(df_actual, df_expected)


def test_compute_weekly_score_pips_with_start():
    # Arrange: 14 days → 2 full weeks
    df = pl.DataFrame({
        "player": ["Alice", "Bob"] * 14,
        "pips_num": [w for w in range(391, 405) for _ in range(2)],
        "time_str": ["1:00", "2:00"] * 14,
    })

    # Act
    scores_rank = SC.compute_weekly_score(df, pips_start=392, game="pips")

    # Assert: only second week
    assert len(scores_rank) == 1
    assert scores_rank[0]["week_start"][0] == 398
    assert scores_rank[0]["week_end"][0] == 404
