from typing import Any, List, Optional, Sequence, Union
import polars as pl

from game_bot.calendar_utils import CalendarUtils
from game_bot.config import WORDLE_FAIL_PENALTY_SCORE, PIPS_FAIL_PENALTY_SCORE
from game_bot.models import ScoreRecord
from game_bot.parser import WordleParser


# ==============================
# PURE SCORING FUNCTIONS
# ==============================


def _get_game_col(df: pl.DataFrame, game: str = "wordle") -> str:
    candidates = [f"{game}_num", "wordle_num", "pips_num", "game_num"]
    for col in candidates:
        if col in df.columns:
            return col
    return f"{game}_num"


def clean_and_fill_scores(
    data: Union[pl.DataFrame, Sequence[Any]],
    game: str = "wordle",
    game_start: Optional[int] = None,
    wordle_start: Optional[int] = None,
    pips_start: Optional[int] = None,
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
        - 'X' → WORDLE_FAIL_PENALTY_SCORE (7)

    Pips:
        - score column
        - 'X' → PIPS_FAIL_PENALTY_SCORE (5)
    """
    effective_start = game_start if game_start is not None else (wordle_start if wordle_start is not None else pips_start)

    if isinstance(data, pl.DataFrame):
        df = data
        output_col = _get_game_col(df, game)
    elif data:
        output_col = "pips_num" if game == "pips" else "wordle_num"
        rows = []
        for item in data:
            if hasattr(item, "player") and (hasattr(item, "game_num") or hasattr(item, "wordle_num") or hasattr(item, "pips_num")) and hasattr(item, "score"):
                num = getattr(item, "game_num", None)
                if num is None:
                    num = getattr(item, "wordle_num", None)
                if num is None:
                    num = getattr(item, "pips_num", None)
                rows.append((str(item.player), int(num), item.score))
            elif isinstance(item, (list, tuple)) and len(item) >= 3:
                rows.append((str(item[0]), int(item[1]), item[2]))
            else:
                raise ValueError(f"Unsupported score item format: {item}")

        df = pl.DataFrame(rows, schema=["player", output_col, "score"], orient="row")
    else:
        output_col = "pips_num" if game == "pips" else "wordle_num"
        return pl.DataFrame(schema={"player": pl.String, output_col: pl.Int64, "score": pl.Int64})

    if df.height == 0:
        return pl.DataFrame(schema={"player": pl.String, output_col: pl.Int64, "score": pl.Int64})

    penalty = WORDLE_FAIL_PENALTY_SCORE if game == "wordle" else PIPS_FAIL_PENALTY_SCORE

    # Convert 'X' to penalty and cast to Int64
    df = df.with_columns(
        pl.when(pl.col("score").cast(pl.String) == "X")
        .then(penalty)
        .otherwise(pl.col("score"))
        .alias("score")
        .cast(pl.Int64)
    )

    player_list = df.select("player").unique()["player"].to_list()

    prefix_map = {}
    for name in player_list:
        others = [o for o in player_list if o != name]
        prefix_map[name] = WordleParser.shortest_unique_prefix(name, others)

    prefix_df = pl.DataFrame({
        "player": list(prefix_map.keys()),
        "prefix": list(prefix_map.values())
    })

    # Join and replace
    df = df.join(prefix_df, on="player", how="left")
    df = df.with_columns(pl.col("prefix").alias("player")).drop("prefix")

    if effective_start is not None:
        df = df.filter(pl.col(output_col) >= effective_start)
        if df.height == 0:
            return pl.DataFrame(schema={"player": pl.String, output_col: pl.Int64, "score": pl.Int64})

    players = pl.DataFrame(df.select(pl.col("player")).unique()['player'])
    # player_list = df.select(pl.col("player")).unique()['player'].to_list()

    # prefix_map = {}
    # for name in player_list:
    #     others = [o for o in player_list if o != name]
    #     prefix_map[name] = WordleParser.shortest_unique_prefix(name, others)

    # df = df.with_columns(
    #     pl.col('player').map_dict(prefix_map).alias("player")
    # )
    
    games_max = df.select(pl.col(output_col)).max().item()

    if effective_start is not None:
        games_min = effective_start
    else:
        games_min = df.select(pl.col(output_col)).min().item()

    if games_min > games_max:
        return pl.DataFrame(schema={"player": pl.String, output_col: pl.Int64, "score": pl.Int64})

    # Generate full grid of all game numbers for all players
    games_fill = pl.DataFrame({output_col: list(range(games_min, games_max + 1))})
    full_grid = players.join(games_fill, how="cross")

    df_filled = full_grid.join(df, on=["player", output_col], how="left")

    # Conditionally fill missing with penalty only for game_num < max
    df_filled = df_filled.with_columns(
        pl.when(pl.col(output_col) < games_max)
        .then(pl.col("score").fill_null(penalty))
        .otherwise(pl.col("score"))
        .alias("score")
        .cast(pl.Int64)
    )

    return df_filled.select(["player", output_col, "score"]).sort([output_col, "player"])


def compute_weekly_scores(
    df: pl.DataFrame,
    game: str = "wordle",
    game_start: Optional[int] = None,
    wordle_start: Optional[int] = None,
    pips_start: Optional[int] = None,
) -> List[pl.DataFrame]:
    """
    Calculate the total score for each player for all complete 7-day {game} weeks.
    Incomplete trailing weeks are omitted.
    If game_start is provided, only scores and weeks starting from game_start are considered.
    """
    if df is None or df.height == 0:
        return []

    df 
    
    effective_start = game_start if game_start is not None else (wordle_start if wordle_start is not None else pips_start)
    col_name = _get_game_col(df, game)

    if effective_start is not None:
        df = df.filter(pl.col(col_name) >= effective_start)
        if df.height == 0:
            return []

    get_unique_week_ranges = CalendarUtils(game).get_unique_week_ranges
    week_ranges = get_unique_week_ranges(df[col_name].unique().to_list())
    weekly_dfs = []

    for week_start, week_end in week_ranges:
        if effective_start is not None and week_start < effective_start:
            continue
        df_week = df.filter(
            (pl.col(col_name) >= week_start) & (pl.col(col_name) <= week_end)
        )
        if df_week.height > 0:
            weekly_dfs.append((df_week, week_start, week_end))

    if not weekly_dfs:
        return []

    # Check if last week is complete (has game_num equal to week_end)
    last_df, _, last_week_end = weekly_dfs[-1]
    if last_df[col_name].max() < last_week_end:
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
    game: str = "wordle",
    game_start: Optional[int] = None,
    wordle_start: Optional[int] = None,
    pips_start: Optional[int] = None,
) -> List[pl.DataFrame]:
    """
    Compute competition ranking for each complete week with mean ranks assigned to ties.
    """
    effective_start = game_start if game_start is not None else (wordle_start if wordle_start is not None else pips_start)
    weekly_scores = compute_weekly_scores(df, game=game, game_start=effective_start)
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
    game: str = "wordle",
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

    def __init__(self, player: str, game_num: int, score: Any, game: str = "wordle") -> None:
        self.player = str(player)
        self.game_num = int(game_num)
        self.wordle_num = int(game_num)
        self.pips_num = int(game_num)
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
    def score_cleaner(
        data,
        game: str = "wordle",
        game_start: Optional[int] = None,
        wordle_start: Optional[int] = None,
        pips_start: Optional[int] = None,
    ) -> pl.DataFrame:
        return clean_and_fill_scores(
            data,
            game=game,
            game_start=game_start,
            wordle_start=wordle_start,
            pips_start=pips_start,
        )

    @staticmethod
    def game_week(game: str, game_num: int):
        get_week_range = CalendarUtils(game).get_week_range
        return get_week_range(game_num)

    @staticmethod
    def wordle_week(wordle_num: int):
        return CalendarUtils("wordle").get_week_range(wordle_num)

    @staticmethod
    def store_week_ranges(df: pl.DataFrame, game: Optional[str] = None):
        if game is None:
            if "game" in df.columns and df.height > 0:
                game = df["game"].unique()[0]
            elif "pips_num" in df.columns:
                game = "pips"
            else:
                game = "wordle"
        col_name = _get_game_col(df, game)
        get_unique_week_ranges = CalendarUtils(game).get_unique_week_ranges
        return get_unique_week_ranges(df[col_name].unique().to_list())

    @staticmethod
    def compute_weekly_score(
        df: pl.DataFrame,
        game: str = "wordle",
        game_start: Optional[int] = None,
        wordle_start: Optional[int] = None,
        pips_start: Optional[int] = None,
    ) -> List[pl.DataFrame]:
        return compute_weekly_scores(
            df,
            game=game,
            game_start=game_start,
            wordle_start=wordle_start,
            pips_start=pips_start,
        )

    @staticmethod
    def week_ranking(
        df: pl.DataFrame,
        game: str = "wordle",
        game_start: Optional[int] = None,
        wordle_start: Optional[int] = None,
        pips_start: Optional[int] = None,
    ) -> List[pl.DataFrame]:
        return rank_weekly_scores(
            df,
            game=game,
            game_start=game_start,
            wordle_start=wordle_start,
            pips_start=pips_start,
        )

    @staticmethod
    def running_ranking(
        weekly_scores: List[pl.DataFrame],
        game: str = "wordle",
        interest: str = "overall_rank",
        leaderboard: Optional[pl.DataFrame] = None,
        database: Optional[Any] = None,
    ) -> List[pl.DataFrame]:
        if leaderboard is None and database is not None:
            leaderboard = database.load_leaderboard()
        return calculate_running_leaderboard(
            weekly_scores,
            game=game,
            interest=interest,
            leaderboard=leaderboard,
        )

    @staticmethod
    def ranking(
        df: pl.DataFrame,
        game: str = "wordle",
        game_start: Optional[int] = None,
        wordle_start: Optional[int] = None,
        pips_start: Optional[int] = None,
    ) -> pl.DataFrame:
        effective_start = game_start if game_start is not None else (wordle_start if wordle_start is not None else pips_start)
        col_name = _get_game_col(df, game)
        if effective_start is not None and df.height > 0:
            df = df.filter(pl.col(col_name) >= effective_start)
        return (
            df.group_by("player")
            .agg(pl.sum("score").alias("total_score"))
            .sort("total_score")
        )
