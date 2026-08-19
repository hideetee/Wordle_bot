import pytest
import polars as pl
from wordle_bot.scorer import ScoreCalculator as SC
from polars.testing import assert_frame_equal, assert_frame_not_equal

def test_compute_weekly_score_full_weeks():
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
    
    scores_rank = SC.compute_weekly_score(scores_df)
    
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


        

def test_compute_weekly_score_1_incomplete_week():
    ## Arrange ##
    scores_df = pl.DataFrame({
        "player": ["Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob"],
        "wordle_num": [1870, 1870, 1871, 1871, 1872, 1872, 1873, 1873, 1874, 1874],
        "score": [3, 4, 5, 2, 3, 4, 1, 2, 3, 2]
    })

    ## Act ##

    scores_rank = SC.compute_weekly_score(scores_df)

    print(f'This is scores_rank: {scores_rank}')

    ## Assert
    scores_rank_expected = []

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
    scores_rank = SC.compute_weekly_score(scores_df)

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
    
