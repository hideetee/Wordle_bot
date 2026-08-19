import os
import sqlite3
from pathlib import Path
from typing import Optional, Union

import polars as pl

from wordle_bot.config import get_database_path
from wordle_bot.models import ScoreRecord


class WordleRepository:
    """Repository interface for persisting player scores and leaderboard records to SQLite."""

    def __init__(self, database_path: Optional[Union[str, Path]] = None) -> None:
        if database_path is None:
            self.database_path = str(get_database_path())
        else:
            self.database_path = str(database_path)

        # Ensure parent directory exists
        parent_dir = os.path.dirname(self.database_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        self.conn = sqlite3.connect(self.database_path, check_same_thread=False)
        self.create_tables()

    def __enter__(self) -> "WordleRepository":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        """Close the database connection."""
        try:
            self.conn.close()
        except sqlite3.Error:
            pass

    def create_tables(self) -> None:
        """Initialize the database schema if tables do not exist."""
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scores (
                    player TEXT,
                    wordle INTEGER,
                    score INTEGER,
                    PRIMARY KEY(player, wordle)
                )
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS leaderboard (
                    player TEXT,
                    week_start INTEGER,
                    week_end INTEGER,
                    score INTEGER,
                    rank REAL,
                    overall_rank REAL,
                    overall_score REAL,
                    PRIMARY KEY(player, week_start, week_end)
                )
                """
            )

    def save_score(self, player: str, wordle: int, score: Optional[int]) -> None:
        """Insert or replace a score for a player and Wordle number."""
        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO scores (player, wordle, score)
                VALUES (?, ?, ?)
                """,
                (player, wordle, score),
            )

    def save_score_if_missing_or_7(self, df: pl.DataFrame) -> None:
        """
        Insert incoming scores if unrecorded, or update existing record if currently null.
        Preserves existing valid scores.
        """
        if df is None or df.height == 0:
            return

        df = df.with_columns(pl.col("score").cast(pl.Int64))
        cursor = self.conn.cursor()

        with self.conn:
            for row in df.to_dicts():
                player = row["player"]
                wordle = row["wordle_num"]
                score = row["score"]

                cursor.execute(
                    """
                    SELECT score FROM scores
                    WHERE player = ? AND wordle = ?
                    """,
                    (player, wordle),
                )
                existing = cursor.fetchone()

                if existing is None or existing[0] is None:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO scores (player, wordle, score)
                        VALUES (?, ?, ?)
                        """,
                        (player, wordle, score),
                    )

    def load_scores(
        self,
        wordle_num: Optional[int] = None,
        wordle_min: Optional[int] = None,
        wordle_max: Optional[int] = None,
    ) -> pl.DataFrame:
        """
        Load scores matching the specified filters, returned as a sorted Polars DataFrame.
        """
        cursor = self.conn.cursor()

        if wordle_min is not None and wordle_max is not None:
            cursor.execute(
                "SELECT player, wordle, score FROM scores WHERE wordle BETWEEN ? AND ?",
                (wordle_min, wordle_max),
            )
        elif wordle_min is not None:
            cursor.execute(
                "SELECT player, wordle, score FROM scores WHERE wordle >= ?",
                (wordle_min,),
            )
        elif wordle_max is not None:
            cursor.execute(
                "SELECT player, wordle, score FROM scores WHERE wordle <= ?",
                (wordle_max,),
            )
        elif wordle_num is not None:
            cursor.execute(
                "SELECT player, wordle, score FROM scores WHERE wordle = ?",
                (wordle_num,),
            )
        else:
            cursor.execute("SELECT player, wordle, score FROM scores")

        rows = cursor.fetchall()
        if not rows:
            return pl.DataFrame(
                schema={"player": pl.String, "wordle_num": pl.Int64, "score": pl.Int64}
            )

        data = [(row[0], row[1], row[2]) for row in rows]
        df = pl.DataFrame(
            data, schema=["player", "wordle_num", "score"], orient="row"
        ).sort(by=["wordle_num", "player"])

        return df

    def save_leaderboard(self, leaderboard_df: pl.DataFrame) -> None:
        """Persist a completed weekly leaderboard DataFrame to the database."""
        if leaderboard_df is None or leaderboard_df.height == 0:
            return

        with self.conn:
            for row in leaderboard_df.to_dicts():
                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO leaderboard
                    (player, week_start, week_end, score, rank, overall_rank, overall_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["player"],
                        row["week_start"],
                        row["week_end"],
                        row["score"],
                        row["rank"],
                        row["overall_rank"],
                        row["overall_score"],
                    ),
                )

    def load_leaderboard(
        self,
        wordle_num: Optional[int] = None,
        week_start: Optional[int] = None,
        week_end: Optional[int] = None,
        last_leaderboard: bool = False,
    ) -> pl.DataFrame:
        """
        Load leaderboard records matching filters, returned as a Polars DataFrame.
        """
        cursor = self.conn.cursor()

        if week_start is not None and week_end is not None:
            cursor.execute(
                """
                SELECT player, week_start, week_end, score, rank, overall_rank, overall_score
                FROM leaderboard
                WHERE week_start >= ? AND week_end <= ?
                """,
                (week_start, week_end),
            )
        elif week_start is not None:
            cursor.execute(
                """
                SELECT player, week_start, week_end, score, rank, overall_rank, overall_score
                FROM leaderboard
                WHERE week_start >= ?
                """,
                (week_start,),
            )
        elif week_end is not None:
            cursor.execute(
                """
                SELECT player, week_start, week_end, score, rank, overall_rank, overall_score
                FROM leaderboard
                WHERE week_end <= ?
                """,
                (week_end,),
            )
        elif wordle_num is not None:
            cursor.execute(
                """
                SELECT player, week_start, week_end, score, rank, overall_rank, overall_score
                FROM leaderboard
                WHERE week_start <= ? AND week_end >= ?
                """,
                (wordle_num, wordle_num),
            )
        elif last_leaderboard:
            cursor.execute(
                """
                SELECT player, week_start, week_end, score, rank, overall_rank, overall_score
                FROM leaderboard
                WHERE week_end = (SELECT MAX(week_end) FROM leaderboard)
                """
            )
        else:
            cursor.execute(
                """
                SELECT player, week_start, week_end, score, rank, overall_rank, overall_score
                FROM leaderboard
                """
            )

        rows = cursor.fetchall()
        schema = {
            "player": pl.String,
            "week_start": pl.Int64,
            "week_end": pl.Int64,
            "score": pl.Int64,
            "rank": pl.Float64,
            "overall_rank": pl.Float64,
            "overall_score": pl.Float64,
        }

        if not rows:
            return pl.DataFrame(schema=schema)

        data = [(row[0], row[1], row[2], row[3], row[4], row[5], row[6]) for row in rows]
        return pl.DataFrame(data, schema=schema, orient="row")

    def get_latest_wordle_num(self) -> Optional[int]:
        """Return the maximum Wordle number present in the scores table, or None if empty."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(wordle) FROM scores")
        result = cursor.fetchone()
        return result[0] if result and result[0] is not None else None


# Backward-compatible alias
Database_wordle = WordleRepository