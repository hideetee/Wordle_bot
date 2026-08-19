import polars as pl
import pytest
from wordle_bot.formatter import (
    format_leaderboard_announcement,
    format_overall_score_table,
    format_weekly_score_table,
)
from wordle_bot.whatsapp import WhatsAppClient


def test_format_weekly_score_table():
    df = pl.DataFrame({
        "player": ["Alice", "Bob"],
        "week_start": [1870, 1870],
        "week_end": [1876, 1876],
        "score": [20, 24],
        "rank": [1.0, 2.0],
    })

    formatted = format_weekly_score_table(df)
    assert "Player     Week     Score   Rank" in formatted
    assert "Alice" in formatted
    assert "Bob" in formatted
    assert "1870 - 1876" in formatted


def test_format_overall_score_table():
    df = pl.DataFrame({
        "player": ["Alice", "Bob"],
        "overall_score": [20.0, 24.0],
        "overall_rank": [1.0, 2.0],
    })

    formatted = format_overall_score_table(df)
    assert "Player  AT Score  AT Rank" in formatted
    assert "Alice" in formatted
    assert "20.0" in formatted


def test_format_leaderboard_announcement():
    df = pl.DataFrame({
        "player": ["Alice", "Bob"],
        "week_start": [1870, 1870],
        "week_end": [1876, 1876],
        "score": [20, 24],
        "rank": [1.0, 2.0],
        "overall_score": [20.0, 24.0],
        "overall_rank": [1.0, 2.0],
    })

    msg = format_leaderboard_announcement(df)
    assert "🏆 Wordle Leaderboard" in msg
    assert "Weekly Scores" in msg
    assert "Overall Scores" in msg


def test_whatsapp_client_static_methods_backward_compatible():
    df = pl.DataFrame({
        "player": ["Alice", "Bob"],
        "week_start": [1870, 1870],
        "week_end": [1876, 1876],
        "score": [20, 24],
        "rank": [1.0, 2.0],
        "overall_score": [20.0, 24.0],
        "overall_rank": [1.0, 2.0],
    })

    w_formatted = WhatsAppClient.df_to_whatsapp_score_rank(df)
    assert "Alice" in w_formatted

    o_formatted = WhatsAppClient.df_to_whatsapp_overall_score_rank(df)
    assert "Alice" in o_formatted
