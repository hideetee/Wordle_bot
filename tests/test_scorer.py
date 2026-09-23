import polars as pl
import pytest
from polars.testing import assert_frame_equal

from game_bot.models import ScoreRecord
from game_bot.scorer import (
    calculate_running_leaderboard,
    clean_and_fill_scores_wordle,
    compute_weekly_scores_pips,
    compute_weekly_scores_wordle,
    rank_weekly_scores_wordle,
    rank_weekly_scores_pips,
)


def test_clean_and_fill_scores_with_dataclasses():
    scores = [
        ScoreRecord(player="Alice", wordle_num=100, score=3),
        ScoreRecord(player="Bob", wordle_num=100, score="X"),
        ScoreRecord(player="Alice", wordle_num=102, score=4),
        ScoreRecord(player="Bob", wordle_num=102, score=2),
    ]

    cleaned = clean_and_fill_scores_wordle(scores)
    # Intermediate wordle 101 should be filled with 7 for both players
    assert cleaned.height == 6

    alice_101 = cleaned.filter((pl.col("player") == "A") & (pl.col("wordle_num") == 101))
    assert alice_101["score"][0] == 7

    bob_100 = cleaned.filter((pl.col("player") == "B") & (pl.col("wordle_num") == 100))
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

    running = calculate_running_leaderboard([week1, week2], game = "wordle")
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

def test_compute_weekly_scores_wordle():
    # Arrange: 14 days → 2 full weeks
    df = pl.DataFrame({
        "player": ["A","B"] * 7,
        "wordle_num": list(range(1, 15)),   # 1..14
        "score": [3,4] * 7
    })

    weekly = compute_weekly_scores_wordle(
        df,
        game="wordle",
        wordle_start=1
    )

    # Assert: two full weeks only
    assert len(weekly) == 2

    # Week 1: 1–7
    w1 = weekly[0]
    assert w1["week_start"][0] == 1
    assert w1["week_end"][0] == 7
    assert w1.filter(pl.col("player") == "A")["score"][0] == 3 * 4
    assert w1.filter(pl.col("player") == "B")["score"][0] == 4 * 3

    # Week 2: 8–14
    w2 = weekly[1]
    assert w2["week_start"][0] == 8
    assert w2["week_end"][0] == 14
    assert w2.filter(pl.col("player") == "A")["score"][0] == 3 * 3
    assert w2.filter(pl.col("player") == "B")["score"][0] == 4 * 4


def test_compute_weekly_scores_pips():
    # Arrange: 14 days → 2 full weeks
    df = pl.DataFrame({
        "player": ["A","B"] * 7,
        "pips_num": list(range(391, 405)),
        "time_seconds": [60, 120] * 7   # A=60s, B=120s
    })

    weekly = compute_weekly_scores_pips(
        df,
        game="pips",
        pips_start=1
    )

    # Assert: two full weeks only
    assert len(weekly) == 2

    # Week 1: 1–7
    w1 = weekly[0]
    assert w1["week_start"][0] == 391
    assert w1["week_end"][0] == 397
    assert w1.filter(pl.col("player") == "A")["time_seconds"][0] == 60 * 4
    assert w1.filter(pl.col("player") == "B")["time_seconds"][0] == 120 * 3

    # Week 2: 8–14
    w2 = weekly[1]
    assert w2["week_start"][0] == 398
    assert w2["week_end"][0] == 404
    assert w2.filter(pl.col("player") == "A")["time_seconds"][0] == 60 * 3
    assert w2.filter(pl.col("player") == "B")["time_seconds"][0] == 120 * 4


def test_incomplete_week_is_dropped_pips():
    # 10 days → week 1 (1–7) complete, week 2 (8–14) incomplete
    df = pl.DataFrame({
        "player": ["A","B"] * 5,
        "pips_num": list(range(391, 401)),
        "time_seconds": [10, 20] * 5
    })

    weekly = compute_weekly_scores_pips(df)

    # Only week 1 should be returned
    assert len(weekly) == 1
    assert weekly[0]["week_start"][0] == 391
    assert weekly[0]["week_end"][0] == 397

def test_weekly_scores_respect_start_filter_wordle():
    df = pl.DataFrame({
        "player": ["A","B"] * 7,
        "wordle_num": list(range(1, 15)),
        "score": [3,4] * 7
    })

    weekly = compute_weekly_scores_wordle(
        df,
        game="wordle",
        wordle_start=8
    )

    # Only week 2 (8–14) should remain
    assert len(weekly) == 1
    assert weekly[0]["week_start"][0] == 8
    assert weekly[0]["week_end"][0] == 14
