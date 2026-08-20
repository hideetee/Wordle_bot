import tempfile
import os
import sqlite3
import pytest
import polars as pl
from polars.testing import assert_frame_equal
from wordle_bot.database import Database_wordle


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_database_initialization_creates_tables(temp_db_path):
    db = Database_wordle(temp_db_path)
    cursor = db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scores'")
    assert cursor.fetchone() is not None


def test_save_and_load_score(temp_db_path):
    db = Database_wordle(temp_db_path)
    db.save_score("Alice", 1000, 4)
    db.save_score("Bob", 1000, 5)

    df = db.load_scores()
    assert df.shape == (2, 3)
    assert set(df["player"].to_list()) == {"Alice", "Bob"}


def test_save_score_if_missing_or_7(temp_db_path):
    db = Database_wordle(temp_db_path)
    db.save_score("Alice", 1000, 3)

    incoming_df = pl.DataFrame({
        "player": ["Alice", "Bob", "Alice"],
        "wordle_num": [1000, 1000, 1001],
        "score": [7, 4, 2]
    })

    db.save_score_if_missing_or_7(incoming_df)

    df = db.load_scores()
    # Alice at 1000 should keep 3 (not overwritten with 7)
    alice_1000 = df.filter((pl.col("player") == "Alice") & (pl.col("wordle_num") == 1000))
    assert alice_1000["score"][0] == 3

    # Bob at 1000 should be inserted as 4
    bob_1000 = df.filter((pl.col("player") == "Bob") & (pl.col("wordle_num") == 1000))
    assert bob_1000["score"][0] == 4

    # Alice at 1001 should be inserted as 2
    alice_1001 = df.filter((pl.col("player") == "Alice") & (pl.col("wordle_num") == 1001))
    assert alice_1001["score"][0] == 2


def test_load_scores_filters(temp_db_path):
    db = Database_wordle(temp_db_path)
    db.save_score("Alice", 100, 3)
    db.save_score("Alice", 101, 4)
    db.save_score("Alice", 102, 5)

    # Filter single wordle
    df_single = db.load_scores(wordle_num=101)
    assert df_single.shape[0] == 1
    assert df_single["wordle_num"][0] == 101

    # Filter range
    df_range = db.load_scores(wordle_min=101, wordle_max=102)
    assert df_range.shape[0] == 2
    assert set(df_range["wordle_num"].to_list()) == {101, 102}


def test_get_latest_wordle_num(temp_db_path):
    db = Database_wordle(temp_db_path)
    assert db.get_latest_wordle_num() is None

    db.save_score("Alice", 500, 3)
    db.save_score("Bob", 505, 4)
    assert db.get_latest_wordle_num() == 505


def test_save_and_load_leaderboard(temp_db_path):
    db = Database_wordle(temp_db_path)

    leaderboard_df = pl.DataFrame({
        "player": ["Alice", "Bob"],
        "week_start": [1870, 1870],
        "week_end": [1876, 1876],
        "score": [20, 22],
        "rank": [1.0, 2.0],
        "overall_rank": [1.0, 2.0],
        "overall_score": [20.0, 22.0]
    })

    db.save_leaderboard(leaderboard_df)

    loaded = db.load_leaderboard(week_start=1870, week_end=1876)
    assert loaded.shape[0] == 2
    assert "player" in loaded.columns
    assert "overall_rank" in loaded.columns


def test_load_scores_and_leaderboard_with_wordle_start(temp_db_path):
    db = Database_wordle(temp_db_path)
    db.save_score("Alice", 100, 3)
    db.save_score("Alice", 105, 4)
    db.save_score("Alice", 110, 5)

    # load_scores with wordle_start
    df = db.load_scores(wordle_start=105)
    assert df.shape[0] == 2
    assert set(df["wordle_num"].to_list()) == {105, 110}

    # save leaderboard across 2 weeks
    lb_df = pl.DataFrame({
        "player": ["Alice", "Alice"],
        "week_start": [1870, 1877],
        "week_end": [1876, 1883],
        "score": [20, 22],
        "rank": [1.0, 1.0],
        "overall_rank": [1.0, 2.0],
        "overall_score": [20.0, 42.0]
    })
    db.save_leaderboard(lb_df)

    loaded_all_from_1877 = db.load_leaderboard(wordle_start=1877)
    assert loaded_all_from_1877.shape[0] == 1
    assert loaded_all_from_1877["week_start"][0] == 1877

    loaded_last_from_1870 = db.load_leaderboard(last_leaderboard=True, wordle_start=1870)
    assert loaded_last_from_1870.shape[0] == 1
    assert loaded_last_from_1870["week_end"][0] == 1883


def test_default_database_path(monkeypatch, tmp_path):
    custom_db = tmp_path / "custom_scores.db"
    monkeypatch.setattr("wordle_bot.database.get_database_path", lambda: custom_db)
    repo = Database_wordle()
    assert repo.database_path == str(custom_db)
    repo.close()

