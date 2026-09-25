from game_bot.scorer import ScoreCalculator as SC
import polars as pl
import polars.testing as pt
from game_bot.scorer import calculate_running_leaderboard


def test_running_leaderboard_wordle():
    # Week 1
    week1 = pl.DataFrame({
        "player": ["A", "B", "C"],
        "rank":   [1, 2, 3],
        "score":  [3, 4, 5],
    })

    # Week 2
    week2 = pl.DataFrame({
        "player": ["A", "B", "C"],
        "rank":   [2, 1, 3],
        "score":  [4, 3, 6],
    })

    weekly_scores = [week1, week2]

    ranked = calculate_running_leaderboard(
        weekly_scores,
        game="wordle",
        interest="overall_rank"
    )

    # Week 1 cumulative
    w1 = ranked[0]
    assert w1.filter(pl.col("player") == "A")["overall_rank"][0] == 1
    assert w1.filter(pl.col("player") == "B")["overall_rank"][0] == 2
    assert w1.filter(pl.col("player") == "C")["overall_rank"][0] == 3

    assert w1.filter(pl.col("player") == "A")["overall_score"][0] == 3
    assert w1.filter(pl.col("player") == "B")["overall_score"][0] == 4
    assert w1.filter(pl.col("player") == "C")["overall_score"][0] == 5

    # Week 2 cumulative
    w2 = ranked[1]
    assert w2.filter(pl.col("player") == "A")["overall_rank"][0] == 3  # 1 + 2
    assert w2.filter(pl.col("player") == "B")["overall_rank"][0] == 3  # 2 + 1
    assert w2.filter(pl.col("player") == "C")["overall_rank"][0] == 6  # 3 + 3

    assert w2.filter(pl.col("player") == "A")["overall_score"][0] == 7  # 3 + 4
    assert w2.filter(pl.col("player") == "B")["overall_score"][0] == 7  # 4 + 3
    assert w2.filter(pl.col("player") == "C")["overall_score"][0] == 11 # 5 + 6


def test_running_leaderboard_pips():
    # Week 1
    week1 = pl.DataFrame({
        "player": ["A", "B", "C"],
        "rank":   [1, 2, 3],
        "time_seconds": [60, 120, 180],   # 1m, 2m, 3m
    })

    # Week 2
    week2 = pl.DataFrame({
        "player": ["A", "B", "C"],
        "rank":   [2, 1, 3],
        "time_seconds": [70, 110, 200],
    })

    weekly_scores = [week1, week2]

    ranked = calculate_running_leaderboard(
        weekly_scores,
        game="pips",
        interest="overall_rank"
    )

    # Week 1 cumulative
    w1 = ranked[0]
    assert w1.filter(pl.col("player") == "A")["overall_rank"][0] == 1
    assert w1.filter(pl.col("player") == "B")["overall_rank"][0] == 2
    assert w1.filter(pl.col("player") == "C")["overall_rank"][0] == 3

    assert w1.filter(pl.col("player") == "A")["overall_time_seconds"][0] == 60
    assert w1.filter(pl.col("player") == "B")["overall_time_seconds"][0] == 120
    assert w1.filter(pl.col("player") == "C")["overall_time_seconds"][0] == 180

    # Week 2 cumulative
    w2 = ranked[1]
    assert w2.filter(pl.col("player") == "A")["overall_rank"][0] == 3  # 1 + 2
    assert w2.filter(pl.col("player") == "B")["overall_rank"][0] == 3  # 2 + 1
    assert w2.filter(pl.col("player") == "C")["overall_rank"][0] == 6  # 3 + 3

    assert w2.filter(pl.col("player") == "A")["overall_time_seconds"][0] == 130  # 60 + 70
    assert w2.filter(pl.col("player") == "B")["overall_time_seconds"][0] == 230  # 120 + 110
    assert w2.filter(pl.col("player") == "C")["overall_time_seconds"][0] == 380  # 180 + 200
