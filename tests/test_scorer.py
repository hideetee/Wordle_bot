import polars as pl
import pytest
from polars.testing import assert_frame_equal

from wordle_bot.models import ScoreRecord
from wordle_bot.scorer import (
    calculate_running_leaderboard,
    clean_and_fill_scores,
    compute_weekly_scores,
    rank_weekly_scores,
)


def test_clean_and_fill_scores_with_dataclasses():
    scores = [
        ScoreRecord(player="Alice", wordle_num=100, score=3),
        ScoreRecord(player="Bob", wordle_num=100, score="X"),
        ScoreRecord(player="Alice", wordle_num=102, score=4),
        ScoreRecord(player="Bob", wordle_num=102, score=2),
    ]

    cleaned = clean_and_fill_scores(scores)
    # Intermediate wordle 101 should be filled with 7 for both players
    assert cleaned.height == 6

    alice_101 = cleaned.filter((pl.col("player") == "Alice") & (pl.col("wordle_num") == 101))
    assert alice_101["score"][0] == 7

    bob_100 = cleaned.filter((pl.col("player") == "Bob") & (pl.col("wordle_num") == 100))
    assert bob_100["score"][0] == 7


def test_calculate_running_leaderboard_two_weeks():
    week1 = pl.DataFrame({
        "player": ["Alice", "Bob"],
        "week_start": [1870, 1870],
        "week_end": [1876, 1876],
        "score": [20, 25],
        "rank": [1.0, 2.0],
    })

    week2 = pl.DataFrame({
        "player": ["Alice", "Bob"],
        "week_start": [1877, 1877],
        "week_end": [1883, 1883],
        "score": [22, 21],
        "rank": [2.0, 1.0],
    })

    running = calculate_running_leaderboard([week1, week2])
    assert len(running) == 2

    # Week 1 overall
    w1_res = running[0]
    alice_w1 = w1_res.filter(pl.col("player") == "Alice")
    assert alice_w1["overall_score"][0] == 20.0
    assert alice_w1["overall_rank"][0] == 1.0

    # Week 2 overall
    w2_res = running[1]
    alice_w2 = w2_res.filter(pl.col("player") == "Alice")
    bob_w2 = w2_res.filter(pl.col("player") == "Bob")
    assert alice_w2["overall_score"][0] == 42.0
    assert bob_w2["overall_score"][0] == 46.0
    assert alice_w2["overall_rank"][0] == 3.0
    assert bob_w2["overall_rank"][0] == 3.0
