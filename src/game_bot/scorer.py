from typing import Any, List, Optional, Sequence, Union
import polars as pl

from game_bot.calendar_utils import CalendarUtils
from game_bot.config import WORDLE_FAIL_PENALTY_SCORE, PIPS_FAIL_PENALTY_SCORE
from game_bot.models import ScoreRecord


# ==============================
# PURE SCORING FUNCTIONS
# ==============================


def clean_and_fill_scores(
    data: Union[pl.DataFrame, Sequence[Any]],
    game: str,
    game_start: Optional[int] = None,
) -> pl.DataFrame:
    """
    Clean and fill scores for a given game (Wordle or Pips).
    Accept a Polars DataFrame or a sequence of score objects/tuples and return a cleaned, filled DataFrame.
    
    1. Converts 'X' to penalty score.
    2. Filters out any scores before game_start if provided.
    3. Fills missing intermediate days with penalty score.
    4. Keeps unplayed days in the latest/current game as null.

    Wordle:
        - score column (int)
        - 'X' → WORDLE_FAIL_PENALTY_SCORE

    Pips:
        - time column (string "m:ss")
        - 'X' → PIPS_FAIL_PENALTY_SCORE 

    """
    if isinstance(data, pl.DataFrame):
        df = data
    elif data:
        # Check if list of ScoreRecord / ScoreCalculator or list of tuples
        rows = []
        for item in data:
            if hasattr(item, "player") and hasattr(item, "game_num") and hasattr(item, "score"):
                rows.append((str(item.player), int(item.game_num), item.score))
            elif isinstance(item, (list, tuple)) and len(item) >= 3:
                rows.append((str(item[0]), int(item[1]), item[2]))
            else:
                raise ValueError(f"Unsupported score item format: {item}")

        df = pl.DataFrame(rows, schema=["player", "game_num", "score"], orient="row")
    else:
        return pl.DataFrame(schema={"player": pl.String, "game_num": pl.Int64, "score": pl.Int64})

    if df.height == 0:
        return df

    # Convert 'X' to FAIL_PENALTY_SCORE and cast to Int64
    if game == "wordle":
        df = df.with_columns(
            pl.when(pl.col("score").cast(pl.String) == "X")
            .then(WORDLE_FAIL_PENALTY_SCORE)
            .otherwise(pl.col("score"))
            .alias("score")
            .cast(pl.Int64)
        )
    elif game == "pips":
        df = df.with_columns(
            pl.when(pl.col("score").cast(pl.String) == "X")
            .then(PIPS_FAIL_PENALTY_SCORE)
            .otherwise(pl.col("score"))
            .alias("score")
            .cast(pl.Int64)
        )

    if game_start is not None:
        df = df.filter(pl.col("game_num") >= game_start)
        if df.height == 0:
            return pl.DataFrame(schema={"player": pl.String, "game_num": pl.Int64, "score": pl.Int64})

    players = df.select(pl.col("player")).unique()
    games_max = df.select(pl.col("game_num")).max().item()

    if game_start is not None:
        games_min = game_start
    else:
        games_min = df.select(pl.col("game_num")).min().item()

    if games_min > games_max:
        return pl.DataFrame(schema={"player": pl.String, "game_num": pl.Int64, "score": pl.Int64})

    # Generate full grid of all wordle numbers for all players
    games_fill = pl.DataFrame({"game_num": list(range(games_min, games_max + 1))})
    full_grid = players.join(games_fill, how="cross")

    df_filled = full_grid.join(df, on=["player", "game_num"], how="left")

    # Conditionally fill missing with 7 only for game_num < max
    if game == "wordle":
        df_filled = df_filled.with_columns(
            pl.when(pl.col("game_num") < games_max)
            .then(pl.col("score").fill_null(WORDLE_FAIL_PENALTY_SCORE))
            .otherwise(pl.col("score"))
            .alias("score")
        )
    elif game == "pips":
        df_filled = df_filled.with_columns(
            pl.when(pl.col("game_num") < games_max)
            .then(pl.col("score").fill_null(PIPS_FAIL_PENALTY_SCORE))
            .otherwise(pl.col("score"))
            .alias("score")
        )
    else: 
        raise ValueError(f"Unsupported game type: {game}")

    return df_filled.sort(["game_num", "player"])


def compute_weekly_scores(
    df: pl.DataFrame,
    game: str,
    game_start: Optional[int] = None,
) -> List[pl.DataFrame]:
    """
    Calculate the total score for each player for all complete 7-day {game} weeks.
    Incomplete trailing weeks are omitted.
    If game_start is provided, only scores and weeks starting from game_start are considered.
    """
    if df is None or df.height == 0:
        return []

    if game_start is not None:
        df = df.filter(pl.col("game_num") >= game_start)
        if df.height == 0:
            return []
        
    get_unique_week_ranges = CalendarUtils(game).get_unique_week_ranges
    week_ranges = get_unique_week_ranges(df["game_num"].unique().to_list())
    weekly_dfs = []

    for week_start, week_end in week_ranges:
        if game_start is not None and week_start < game_start:
            continue
        df_week = df.filter(
            (pl.col("game_num") >= week_start) & (pl.col("game_num") <= week_end)
        )
        if df_week.height > 0:
            weekly_dfs.append((df_week, week_start, week_end))

    if not weekly_dfs:
        return []

    # Check if last week is complete (has game_num equal to week_end)
    last_df, _, last_week_end = weekly_dfs[-1]
    if last_df["game_num"].max() < last_week_end:
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
    game: str,
    game_start: Optional[int] = None,
) -> List[pl.DataFrame]:
    """
    Compute competition ranking for each complete week with mean ranks assigned to ties.
    """
    weekly_scores = compute_weekly_scores(df, game=game, game_start=game_start)
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
    game: str,
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

    def __init__(self, player: str, game_num: int, score: Any, game: str) -> None:
        self.player = str(player)
        self.game_num = int(game_num)
        self.score = score
        self.game = str(game)

    def __repr__(self) -> str:
        return f"(player={self.player}, game={self.game_num}, score={self.score}), game={self.game}\n"

    def numeric_score(self) -> int:
        if self.game == "wordle" and self.score == "X":
            return WORDLE_FAIL_PENALTY_SCORE
        elif self.game == "pips" and self.score == "X":
            return PIPS_FAIL_PENALTY_SCORE
        return int(self.score)

    @staticmethod
    def score_cleaner(data, game_start: Optional[int] = None) -> pl.DataFrame:
        return clean_and_fill_scores(data, game_start=game_start)

    @staticmethod
    def game_week(game, game_num: int):
        get_week_range = CalendarUtils(game).get_week_range
        return get_week_range(game, game_num)

    @staticmethod
    def store_week_ranges(df: pl.DataFrame):
        get_unique_week_ranges = CalendarUtils(df["game"].unique()[0]).get_unique_week_ranges
        return get_unique_week_ranges(df["game_num"].unique().to_list())

    # def compute_weekly_score(self, df: pl.DataFrame, game_start: Optional[int] = None) -> List[pl.DataFrame]:
    #     return compute_weekly_scores(df, game_start=game_start, game=self.game)

    @staticmethod
    def compute_weekly_score(df, game, game_start=None):
        return compute_weekly_scores(df, game_start=game_start, game=game)

    

    @staticmethod
    def week_ranking(df: pl.DataFrame, game_start: Optional[int] = None) -> List[pl.DataFrame]:
        return rank_weekly_scores(df, game_start=game_start)

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
    def ranking(df: pl.DataFrame, game_start: Optional[int] = None) -> pl.DataFrame:
        if game_start is not None and df.height > 0:
            df = df.filter(pl.col("game_num") >= game_start)
        return (
            df.group_by("player")
            .agg(pl.sum("score").alias("total_score"))
            .sort("total_score")
        )
