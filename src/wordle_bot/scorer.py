from typing import Any, List, Optional, Sequence, Union
import polars as pl

from wordle_bot.calendar_utils import get_unique_week_ranges, get_wordle_week
from wordle_bot.config import FAIL_PENALTY_SCORE
from wordle_bot.models import ScoreRecord


# ==============================
# PURE SCORING FUNCTIONS
# ==============================


def clean_and_fill_scores(
    data: Union[pl.DataFrame, Sequence[Any]],
    wordle_start: Optional[int] = None,
) -> pl.DataFrame:
    """
    Accept a Polars DataFrame or a sequence of score objects/tuples and return a cleaned, filled DataFrame.
    
    1. Converts 'X' to 7 (penalty score).
    2. Filters out any scores before wordle_start if provided.
    3. Fills missing intermediate days with 7.
    4. Keeps unplayed days in the latest/current Wordle as null.
    """
    if isinstance(data, pl.DataFrame):
        df = data
    elif data:
        # Check if list of ScoreRecord / ScoreCalculator or list of tuples
        rows = []
        for item in data:
            if hasattr(item, "player") and hasattr(item, "wordle_num") and hasattr(item, "score"):
                rows.append((str(item.player), int(item.wordle_num), item.score))
            elif isinstance(item, (list, tuple)) and len(item) >= 3:
                rows.append((str(item[0]), int(item[1]), item[2]))
            else:
                raise ValueError(f"Unsupported score item format: {item}")

        df = pl.DataFrame(rows, schema=["player", "wordle_num", "score"], orient="row")
    else:
        return pl.DataFrame(schema={"player": pl.String, "wordle_num": pl.Int64, "score": pl.Int64})

    if df.height == 0:
        return df

    # Convert 'X' to FAIL_PENALTY_SCORE and cast to Int64
    df = df.with_columns(
        pl.when(pl.col("score").cast(pl.String) == "X")
        .then(FAIL_PENALTY_SCORE)
        .otherwise(pl.col("score"))
        .alias("score")
        .cast(pl.Int64)
    )

    if wordle_start is not None:
        df = df.filter(pl.col("wordle_num") >= wordle_start)
        if df.height == 0:
            return pl.DataFrame(schema={"player": pl.String, "wordle_num": pl.Int64, "score": pl.Int64})

    players = df.select(pl.col("player")).unique()
    wordles_max = df.select(pl.col("wordle_num")).max().item()
    if wordle_start is not None:
        wordles_min = wordle_start
    else:
        wordles_min = df.select(pl.col("wordle_num")).min().item()

    if wordles_min > wordles_max:
        return pl.DataFrame(schema={"player": pl.String, "wordle_num": pl.Int64, "score": pl.Int64})

    # Generate full grid of all wordle numbers for all players
    wordles_fill = pl.DataFrame({"wordle_num": list(range(wordles_min, wordles_max + 1))})
    full_grid = players.join(wordles_fill, how="cross")

    df_filled = full_grid.join(df, on=["player", "wordle_num"], how="left")

    # Conditionally fill missing with 7 only for wordle_num < max
    df_filled = df_filled.with_columns(
        pl.when(pl.col("wordle_num") < wordles_max)
        .then(pl.col("score").fill_null(FAIL_PENALTY_SCORE))
        .otherwise(pl.col("score"))
        .alias("score")
    )

    return df_filled.sort(["wordle_num", "player"])


def compute_weekly_scores(
    df: pl.DataFrame,
    wordle_start: Optional[int] = None,
) -> List[pl.DataFrame]:
    """
    Calculate the total score for each player for all complete 7-day Wordle weeks.
    Incomplete trailing weeks are omitted.
    If wordle_start is provided, only scores and weeks starting from wordle_start are considered.
    """
    if df is None or df.height == 0:
        return []

    if wordle_start is not None:
        df = df.filter(pl.col("wordle_num") >= wordle_start)
        if df.height == 0:
            return []

    week_ranges = get_unique_week_ranges(df["wordle_num"].unique().to_list())
    weekly_dfs = []

    for week_start, week_end in week_ranges:
        if wordle_start is not None and week_start < wordle_start:
            continue
        df_week = df.filter(
            (pl.col("wordle_num") >= week_start) & (pl.col("wordle_num") <= week_end)
        )
        if df_week.height > 0:
            weekly_dfs.append((df_week, week_start, week_end))

    if not weekly_dfs:
        return []

    # Check if last week is complete (has wordle_num equal to week_end)
    last_df, _, last_week_end = weekly_dfs[-1]
    if last_df["wordle_num"].max() < last_week_end:
        weekly_dfs = weekly_dfs[:-1]

    weekly_scores = []
    for df_week, week_start, week_end in weekly_dfs:
        weekly_score = (
            df_week.group_by("player")
            .agg(pl.sum("score"))
            .sort("score")
            .with_columns(
                pl.lit(week_start).cast(pl.Int64).alias("week_start"),
                pl.lit(week_end).cast(pl.Int64).alias("week_end"),
            )
        )
        weekly_scores.append(weekly_score)

    return weekly_scores


def rank_weekly_scores(
    df: pl.DataFrame,
    wordle_start: Optional[int] = None,
) -> List[pl.DataFrame]:
    """
    Compute competition ranking for each complete week with mean ranks assigned to ties.
    """
    weekly_scores = compute_weekly_scores(df, wordle_start=wordle_start)
    ranked_weeks = []

    for weekly_score in weekly_scores:
        # Assign raw sequential rank
        df_ranked = weekly_score.with_columns(
            pl.arange(1, weekly_score.height + 1).alias("raw_rank")
        )

        # Compute mean rank for players with tied scores
        df_ranked_grouped = df_ranked.group_by("score").agg(
            pl.col("raw_rank").mean().alias("rank")
        )

        df_final = (
            df_ranked.join(df_ranked_grouped, on="score", how="left")
            .sort("rank")
            .drop("raw_rank")
        )
        ranked_weeks.append(df_final)

    return ranked_weeks


def calculate_running_leaderboard(
    weekly_scores: List[pl.DataFrame],
    interest: str = "overall_rank",
    leaderboard: Optional[pl.DataFrame] = None,
) -> List[pl.DataFrame]:
    """
    Calculate running cumulative ranks and scores across consecutive weeks.
    """
    cumulative_rank = {}
    cumulative_score = {}

    if leaderboard is not None and leaderboard.height > 0:
        player_num = len(leaderboard["player"].unique())
        current_leaderboard = leaderboard.tail(player_num)
        cumulative_rank = {
            row["player"]: row["overall_rank"]
            for row in current_leaderboard.iter_rows(named=True)
        }
        cumulative_score = {
            row["player"]: row["overall_score"]
            for row in current_leaderboard.iter_rows(named=True)
        }

    ranked_weeks = []

    for week in weekly_scores:
        # Rank contribution for this week
        week_rank = week.group_by("player").agg(pl.sum("rank").alias("week_rank"))
        for row in week_rank.iter_rows(named=True):
            player = row["player"]
            cumulative_rank[player] = cumulative_rank.get(player, 0.0) + row["week_rank"]

        # Score contribution for this week
        week_score = week.group_by("player").agg(pl.sum("score").alias("week_score"))
        for row in week_score.iter_rows(named=True):
            player = row["player"]
            cumulative_score[player] = cumulative_score.get(player, 0.0) + row["week_score"]

        cumulative_df = pl.DataFrame({
            "player": list(cumulative_rank.keys()),
            "overall_rank": list(cumulative_rank.values()),
        })

        cumulative_score_df = pl.DataFrame({
            "player": list(cumulative_score.keys()),
            "overall_score": list(cumulative_score.values()),
        })

        week_with_running = (
            week.join(cumulative_df, on="player", how="left")
            .join(cumulative_score_df, on="player", how="left")
            .with_columns([
                pl.col("overall_rank").cast(pl.Float64),
                pl.col("overall_score").cast(pl.Float64),
            ])
            .sort(interest)
        )

        ranked_weeks.append(week_with_running)

    return ranked_weeks


# ==============================
# BACKWARD-COMPATIBLE WRAPPER
# ==============================


class ScoreCalculator:
    """Class representing an individual score, with backward-compatible static methods."""

    def __init__(self, player: str, wordle_num: int, score: Any) -> None:
        self.player = str(player)
        self.wordle_num = int(wordle_num)
        self.score = score

    def __repr__(self) -> str:
        return f"(player={self.player}, wordle={self.wordle_num}, score={self.score})\n"

    def numeric_score(self) -> int:
        if self.score == "X":
            return FAIL_PENALTY_SCORE
        return int(self.score)

    @staticmethod
    def score_cleaner(data, wordle_start: Optional[int] = None) -> pl.DataFrame:
        return clean_and_fill_scores(data, wordle_start=wordle_start)

    @staticmethod
    def wordle_week(wordle_num: int):
        return get_wordle_week(wordle_num)

    @staticmethod
    def store_week_ranges(df: pl.DataFrame):
        return get_unique_week_ranges(df["wordle_num"].unique().to_list())

    @staticmethod
    def compute_weekly_score(df: pl.DataFrame, wordle_start: Optional[int] = None) -> List[pl.DataFrame]:
        return compute_weekly_scores(df, wordle_start=wordle_start)

    @staticmethod
    def week_ranking(df: pl.DataFrame, wordle_start: Optional[int] = None) -> List[pl.DataFrame]:
        return rank_weekly_scores(df, wordle_start=wordle_start)

    @staticmethod
    def running_ranking(
        weekly_scores: List[pl.DataFrame],
        interest: str = "overall_rank",
        leaderboard: Optional[pl.DataFrame] = None,
        database: Optional[Any] = None,
    ) -> List[pl.DataFrame]:
        if leaderboard is None and database is not None:
            leaderboard = database.load_leaderboard()
        return calculate_running_leaderboard(weekly_scores, interest=interest, leaderboard=leaderboard)

    @staticmethod
    def ranking(df: pl.DataFrame, wordle_start: Optional[int] = None) -> pl.DataFrame:
        if wordle_start is not None and df.height > 0:
            df = df.filter(pl.col("wordle_num") >= wordle_start)
        return (
            df.group_by("player")
            .agg(pl.sum("score").alias("total_score"))
            .sort("total_score")
        )
