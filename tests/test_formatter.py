import polars as pl
import pytest
from wordle_bot.whatsapp import WhatsAppClient


def test_df_to_whatsapp_score_rank():
    df = pl.DataFrame({
        "player": ["Alice", "Bob"],
        "week_start": [1870, 1870],
        "week_end": [1876, 1876],
        "score": [20, 24],
        "rank": [1.0, 2.0]
    })

    formatted = WhatsAppClient.df_to_whatsapp_score_rank(df)
    assert "Player     Week     Score   Rank" in formatted
    assert "Alice" in formatted
    assert "Bob" in formatted
    assert "1870 - 1876" in formatted


def test_df_to_whatsapp_overall_score_rank():
    df = pl.DataFrame({
        "player": ["Alice", "Bob"],
        "overall_score": [20.0, 24.0],
        "overall_rank": [1.0, 2.0]
    })

    formatted = WhatsAppClient.df_to_whatsapp_overall_score_rank(df)
    assert "Player  AT Score  AT Rank" in formatted
    assert "Alice" in formatted
    assert "20.0" in formatted
