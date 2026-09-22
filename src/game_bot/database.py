import os
import sqlite3
from pathlib import Path
from typing import Optional, Union

import polars as pl

from game_bot.config import get_database_path
from game_bot.models import ScoreRecord


class GameRepository:
    """Repository interface for persisting player scores and leaderboard records to SQLite."""

    def __init__(
    self,
    database_path: Optional[Union[str, Path]] = None,
    game: Optional[str] = None
):
        if game not in ["wordle", "pips"]:
            raise ValueError("Game must be either 'wordle' or 'pips'.")
        
        self.game = game
        self.game_col = game
        self.game_num_col = f"{self.game_col}_num"

        print(game, self.game_col, self.game_num_col)
        
        if database_path is None:
            try:
                self.database_path = str(get_database_path(game))
            except TypeError:
                self.database_path = str(get_database_path())
        else:
            self.database_path = str(database_path)

        # Ensure parent directory exists
        parent_dir = os.path.dirname(self.database_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        self.conn = sqlite3.connect(self.database_path, check_same_thread=False)
        self.create_tables()

    def __enter__(self) -> "GameRepository":
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
            if self.game == "wordle":
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
                
            elif self.game == "pips":
                self.conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS pips_scores (
                        player TEXT,
                        pips_num INTEGER,
                        time_str TEXT,
                        PRIMARY KEY(player, pips_num)
                    )
                    """
                )

                self.conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS pips_leaderboard (
                        player TEXT,
                        week_start INTEGER,
                        week_end INTEGER,
                        total_seconds INTEGER,
                        avg_seconds REAL,
                        rank REAL,
                        overall_rank REAL,
                        overall_seconds REAL,
                        PRIMARY KEY(player, week_start, week_end)
                    )
                    """
                )
            else: 
                raise ValueError(f"Unsupported game type: {self.game}")

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

    
    def save_pips_score(self, player: str, pips_num: int, time_str: str):
        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO pips_scores (player, pips_num, time_str)
                VALUES (?, ?, ?)
                """,
                (player, pips_num, time_str),
            )

    def save_score_if_missing_or_7_wordle(self, df: pl.DataFrame) -> None:
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

    def save_score_if_null_pips(self, df: pl.DataFrame) -> None:
            """
            Insert incoming scores if unrecorded, or update existing record if currently null.
            Preserves existing valid scores.
            Function checks if the score is null (None) and only updates if it is null, otherwise it preserves the existing score.
            """
            if df is None or df.height == 0:
                return
    
            df = df.with_columns(pl.col("time_str").cast(pl.Utf8))
            cursor = self.conn.cursor()
    
            with self.conn:
                for row in df.to_dicts():
                    player = row["player"]
                    pips_num = row["pips_num"]
                    time_str = row["time_str"]
    
                    cursor.execute(
                        """
                        SELECT time_str FROM pips_scores
                        WHERE player = ? AND pips_num = ?
                        """,
                        (player, pips_num),
                    )
                    existing = cursor.fetchone()
    
                    if existing is None or existing[0] is None:
                        cursor.execute(
                            """
                            INSERT OR REPLACE INTO pips_scores (player, pips_num, time_str)
                            VALUES (?, ?, ?)
                            """,
                            (player, pips_num, time_str),
                        )

    
    def load_scores(
        self,
        wordle_num: Optional[int] = None,
        wordle_min: Optional[int] = None,
        wordle_max: Optional[int] = None,
        wordle_start: Optional[int] = None,
    ) -> pl.DataFrame:
        """
        Load scores matching the specified filters, returned as a sorted Polars DataFrame.
        """
        if wordle_start is not None and wordle_min is None:
            wordle_min = wordle_start

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

    def load_pips_scores(
        self,
        pips_num: Optional[int] = None,
        pips_min: Optional[int] = None,
        pips_max: Optional[int] = None,
    ) -> pl.DataFrame:
        """
        Load pips scores matching the specified filters, returned as a sorted Polars DataFrame.
        Mirrors the logic of load_scores() for Wordle.
        """

        cursor = self.conn.cursor()

        # Range: min + max
        if pips_min is not None and pips_max is not None:
            cursor.execute(
                "SELECT player, pips_num, time_str FROM pips_scores WHERE pips_num BETWEEN ? AND ?",
                (pips_min, pips_max),
            )

        # Min only
        elif pips_min is not None:
            cursor.execute(
                "SELECT player, pips_num, time_str FROM pips_scores WHERE pips_num >= ?",
                (pips_min,),
            )

        # Max only
        elif pips_max is not None:
            cursor.execute(
                "SELECT player, pips_num, time_str FROM pips_scores WHERE pips_num <= ?",
                (pips_max,),
            )

        # Exact match
        elif pips_num is not None:
            cursor.execute(
                "SELECT player, pips_num, time_str FROM pips_scores WHERE pips_num = ?",
                (pips_num,),
            )

        # No filters → full table
        else:
            cursor.execute(
                "SELECT player, pips_num, time_str FROM pips_scores"
            )

        rows = cursor.fetchall()

        # Empty result → return empty schema
        if not rows:
            return pl.DataFrame(
                schema={"player": pl.String, "pips_num": pl.Int64, "time_str": pl.String}
            )

        df = pl.DataFrame(
            rows,
            schema=["player", "pips_num", "time_str"],
            orient="row",
        ).sort(by=["pips_num", "player"])

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

    def save_pips_leaderboard(self, df):
        with self.conn:
            for row in df.to_dicts():
                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO pips_leaderboard
                    (player, week_start, week_end, rank, overall_rank, avg_seconds, overall_seconds)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["player"],
                        row["week_start"],
                        row["week_end"],
                        row["rank"],
                        row["overall_rank"],
                        row["avg_seconds"],
                        row["overall_seconds"],
                    ),
                )

    def load_leaderboard(
        self,
        wordle_num: Optional[int] = None,
        week_start: Optional[int] = None,
        week_end: Optional[int] = None,
        last_leaderboard: bool = False,
        wordle_start: Optional[int] = None,
    ) -> pl.DataFrame:
        """
        Load leaderboard records matching filters, returned as a Polars DataFrame.
        """
        if wordle_start is not None and week_start is None:
            week_start = wordle_start

        cursor = self.conn.cursor()

        if last_leaderboard:
            if week_start is not None:
                cursor.execute(
                    """
                    SELECT player, week_start, week_end, score, rank, overall_rank, overall_score
                    FROM leaderboard
                    WHERE week_start >= ? AND week_end = (SELECT MAX(week_end) FROM leaderboard WHERE week_start >= ?)
                    """,
                    (week_start, week_start),
                )
            else:
                cursor.execute(
                    """
                    SELECT player, week_start, week_end, score, rank, overall_rank, overall_score
                    FROM leaderboard
                    WHERE week_end = (SELECT MAX(week_end) FROM leaderboard)
                    """
                )
        elif week_start is not None and week_end is not None:
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

    def load_pips_leaderboard(
        self,
        pips_num: Optional[int] = None,
        week_start: Optional[int] = None,
        week_end: Optional[int] = None,
        last_leaderboard: bool = False,
        pips_start: Optional[int] = None,
    ) -> pl.DataFrame:

        if pips_start is not None and week_start is None:
            week_start = pips_start
    
        cursor = self.conn.cursor()
    
        if last_leaderboard:
            if week_start is not None:
                cursor.execute(
                    """
                    SELECT player, week_start, week_end, total_seconds, rank, overall_rank, avg_seconds, overall_seconds
                    FROM pips_leaderboard
                    WHERE week_start >= ?
                    AND week_end = (SELECT MAX(week_end) FROM pips_leaderboard WHERE week_start >= ?)
                    """,
                    (week_start, week_start),
                )
            else:
                cursor.execute(
                    """
                    SELECT player, week_start, week_end, total_seconds, rank, overall_rank, avg_seconds, overall_seconds
                    FROM pips_leaderboard
                    WHERE week_end = (SELECT MAX(week_end) FROM pips_leaderboard)
                    """
                )
        elif week_start is not None and week_end is not None:
            cursor.execute(
                """
                SELECT player, week_start, week_end, total_seconds, rank,
                       overall_rank, avg_seconds, overall_seconds
                FROM pips_leaderboard
                WHERE week_start >= ? AND week_end <= ?
                """,
                (week_start, week_end),
            )
        elif week_start is not None:
            cursor.execute(
                """
                SELECT player, week_start, week_end, total_seconds, rank,
                       overall_rank, avg_seconds, overall_seconds
                FROM pips_leaderboard
                WHERE week_start >= ?
                """,
                (week_start,),
            )
        elif week_end is not None:
            cursor.execute(
                """
                SELECT player, week_start, week_end, total_seconds, rank,
                       overall_rank, avg_seconds, overall_seconds
                FROM pips_leaderboard
                WHERE week_end <= ?
                """,
                (week_end,),
            )
        elif pips_num is not None:
            cursor.execute(
                """
                SELECT player, week_start, week_end, total_seconds, rank,
                       overall_rank, avg_seconds, overall_seconds
                FROM pips_leaderboard
                WHERE week_start <= ? AND week_end >= ?
                """,
                (pips_num, pips_num),
            )
        else:
            cursor.execute(
                """
                SELECT player, week_start, week_end, total_seconds, rank,
                       overall_rank, avg_seconds, overall_seconds
                FROM pips_leaderboard
                """
            )

        rows = cursor.fetchall()

        schema = {
            "player": pl.String,
            "week_start": pl.Int64,
            "week_end": pl.Int64,
            "total_seconds": pl.Int64,
            "rank": pl.Float64,
            "overall_rank": pl.Float64,
            "avg_seconds": pl.Float64,
            "overall_seconds": pl.Float64,
        }

        if not rows:
            return pl.DataFrame(schema=schema)

        data = [tuple(row) for row in rows]
        return pl.DataFrame(data, schema=schema, orient="row")


    def get_latest_wordle_num(self) -> Optional[int]:
        """Return the maximum Wordle number present in the scores table, or None if empty."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(wordle) FROM scores")
        result = cursor.fetchone()
        return result[0] if result and result[0] is not None else None

    def get_latest_pips_num(self) -> Optional[int]:
        """Return the maximum Pips number present in the pips_scores table, or None if empty."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(pips_num) FROM pips_scores") 
        result = cursor.fetchone()
        return result[0] if result and result[0] is not None else None



# Backward-compatible alias
Database_game = GameRepository