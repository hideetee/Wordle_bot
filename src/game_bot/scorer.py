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




def clean_and_fill_scores_wordle(
    data: Union[pl.DataFrame, Sequence[Any]],
    wordle_start: Optional[int] = None,
) -> pl.DataFrame:
    """
    Clean and fill scores for a given game (Wordle).
    Accept a Polars DataFrame or a sequence of score objects/tuples and return a cleaned, filled DataFrame.
    
    1. Converts 'X' to penalty score.
    2. Filters out any scores before game_start if provided.
    3. Fills missing intermediate days with penalty score.
    4. Keeps unplayed days in the latest/current game as null.

    Wordle:
        - score column (int)
        - 'X' → WORDLE_FAIL_PENALTY_SCORE (7)
    """
    effective_start = wordle_start if wordle_start is not None else None

    if isinstance(data, pl.DataFrame):
        df = data
    else:
        rows = []
        for item in data:
            # ScoreRecord dataclass
            if isinstance(item, ScoreRecord):
                rows.append((item.player, int(item.wordle_num), item.score))
    
            # ScoreCalculator with as_tuple()
            elif hasattr(item, "as_tuple"):
                p, num, score = item.as_tuple()[:3]
                rows.append((str(p), int(num), score))
    
            # Raw tuple/list: (player, num, score)
            elif isinstance(item, (list, tuple)) and len(item) >= 3:
                rows.append((str(item[0]), int(item[1]), item[2]))
    
            else:
                raise ValueError(f"Unsupported score item format: {item}")

        df = pl.DataFrame(rows, schema=["player", "wordle_num", "score"], orient="row")

    if df.height == 0:
        return pl.DataFrame(schema={"player": pl.String, "wordle_num": pl.Int64, "score": pl.Int64})

    player_list = df.select("player").unique()["player"].to_list()
    
    prefix_map = {}
    for name in player_list:
        others = [o for o in player_list if o != name]
        prefix_map[name] = WordleParser.shortest_unique_prefix(name, others)
        
    
    penalty = WORDLE_FAIL_PENALTY_SCORE

    # Convert 'X' to WORDLE_FAIL_PENALTY_SCORE and cast to Int64
    df = df.with_columns(
        pl.when(pl.col("score").cast(pl.String) == "X")
        .then(penalty)
        .otherwise(pl.col("score"))
        .alias("score")
        .cast(pl.Int64)
    )

    prefix_df = pl.DataFrame({
        "player": list(prefix_map.keys()),
        "prefix": list(prefix_map.values())
    })

    # Join and replace
    df = df.join(prefix_df, on="player", how="left")
    df = df.with_columns(pl.col("prefix").alias("player")).drop("prefix")

    if effective_start is not None:
        df = df.filter(pl.col("wordle_num") >= effective_start)
        if df.height == 0:
            return pl.DataFrame(schema={"player": pl.String, "wordle_num": pl.Int64, "score": pl.Int64})

    players = pl.DataFrame(df.select(pl.col("player")).unique()['player'])
    games_max = df.select(pl.col("wordle_num")).max().item()

    if effective_start is not None:
        games_min = effective_start
    else:
        games_min = df.select(pl.col("wordle_num")).min().item()

    if games_min > games_max:
        return pl.DataFrame(schema={"player": pl.String, "wordle_num": pl.Int64, "score": pl.Int64})

    # Generate full grid of all game numbers for all players
    games_fill = pl.DataFrame({ "wordle_num": list(range(games_min, games_max + 1))})
    full_grid = players.join(games_fill, how="cross")

    df_filled = full_grid.join(df, on=["player", "wordle_num"], how="left")

    # Conditionally fill missing with penalty only for game_num < max
    df_filled = df_filled.with_columns(
        pl.when(pl.col("wordle_num") < games_max)
        .then(pl.col("score").fill_null(penalty))
        .otherwise(pl.col("score"))
        .alias("score")
        .cast(pl.Int64)
    )

    return df_filled.select(["player", "wordle_num", "score"]).sort(["wordle_num", "player"])


def clean_and_fill_scores_pips(
        data: Union[pl.DataFrame, Sequence[Any]],
        game: str = "pips",
        pips_start: Optional[int] = None,
) -> pl.DataFrame:
    """
    Clean and fill scores for a given game (Pips).
    Accept a Polars DataFrame or a sequence of score objects/tuples and return a cleaned, filled DataFrame.
    
    1. Filters out any scores before game_start if provided.
    2. Fills missing intermediate days with null.
    3. Keeps unplayed days in the latest/current game as null.

    Pips:
        - time_str column (int)
    """
    effective_start = pips_start if pips_start is not None else None

    if isinstance(data, pl.DataFrame):
        df = data
    else:
        rows = []
        for item in data:
        
            if isinstance(item, ScoreRecord):
                if game == "wordle":
                    rows.append((item.player, int(item.wordle_num), item.score))
                else:  # pips
                    rows.append((item.player, int(item.pips_num), item.time_str))

            elif hasattr(item, "as_tuple"):
                p, num, val = item.as_tuple()[:3]
                rows.append((str(p), int(num), val))

            elif isinstance(item, (list, tuple)) and len(item) >= 3:
                rows.append((str(item[0]), int(item[1]), item[2]))

            else:
                raise ValueError(f"Unsupported score item format: {item}")

        
        df = pl.DataFrame(rows, schema=["player", "pips_num", "time_str"], orient="row")

    if df.height == 0:
        return pl.DataFrame(schema={"player": pl.String, "pips_num": pl.Int64, "time_str": pl.String})


    # Convert time_str to time_seconds
    df = df.with_columns(
        pl.when(pl.col("time_str").cast(pl.String).str.contains(":"))
                    .then(
                        pl.col("time_str")
                        .cast(pl.String)
                        .str.split(":")
                        .list.get(0)
                        .cast(pl.Int64) * 60
                        + pl.col("time_str")
                        .cast(pl.String)
                        .str.split(":")
                        .list.get(1)
                        .cast(pl.Int64)
                    )
                    .alias("time_seconds")
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
    df = df.join(prefix_df, on="player", how="left")
    df = df.with_columns(
        pl.col("prefix").alias("player")
    ).drop("prefix")

    # if "time_str" in df.columns:
    #     df = df.drop("time_str")
    
     # Filter start
    if pips_start is not None:
        df = df.filter(pl.col("pips_num") >= pips_start)
        if df.height == 0:
            return pl.DataFrame(
                schema={"player": pl.String, "pips_num": pl.Int64, "time_seconds": pl.Int64}
            )

    # Fill missing days
    players_df = df.select("player").unique()
    max_day = df.select(pl.col("pips_num")).max().item()
    min_day = pips_start if pips_start is not None else df.select(pl.col("pips_num")).min().item()

    days = pl.DataFrame({"pips_num": list(range(min_day, max_day + 1))})
    full_grid = players_df.join(days, how="cross")

    df_filled = full_grid.join(df, on=["player", "pips_num"], how="left")
    # if "time_str" in df_filled.columns:
    #     df_filled = df_filled.drop("time_str")


    return df_filled.select(["player", "pips_num", "time_str", "time_seconds"]).sort(["pips_num", "player"])

# helper for compute_weekly_scores
def _split_into_complete_weeks(
    df: pl.DataFrame,
    game: str,
    start_num: Optional[int] = None,
) -> List[tuple[pl.DataFrame, int, int]]:

    if df is None or df.height == 0:
        return []

    col_name = _get_game_col(df, game)

    if start_num is not None:
        df = df.filter(pl.col(col_name) >= start_num)

    if df.height == 0:
        return []

    calendar = CalendarUtils(game)

    week_ranges = calendar.get_unique_week_ranges(
        df[col_name].unique().to_list()
    )

    weekly_dfs = []

    for week_start, week_end in week_ranges:

        if start_num is not None and week_start < start_num:
            continue

        df_week = df.filter(
            (pl.col(col_name) >= week_start)
            & (pl.col(col_name) <= week_end)
        )

        if df_week.height > 0:
            weekly_dfs.append(
                (df_week, week_start, week_end)
            )

    # Remove incomplete trailing week
    if weekly_dfs:
        last_df, _, last_week_end = weekly_dfs[-1]

        if last_df[col_name].max() < last_week_end:
            weekly_dfs.pop()

    return weekly_dfs      

def compute_weekly_scores_wordle(
    df: pl.DataFrame,
    game: str = "wordle",
    wordle_start: Optional[int] = None,
) -> List[pl.DataFrame]:
    """
    Calculate the total score for each player for all complete 7-day {game} weeks.
    Incomplete trailing weeks are omitted.
    If wordle_start is provided, only scores and weeks starting from wordle_start are considered.
    """
    if df is None or df.height == 0:
        return []

    effective_start = wordle_start if wordle_start is not None else None
    col_name = _get_game_col(df, game)

    if effective_start is not None:
        df = df.filter(pl.col(col_name) >= effective_start)
        if df.height == 0:
            return []

    get_unique_week_ranges = CalendarUtils(game).get_unique_week_ranges
    week_ranges = get_unique_week_ranges(df[col_name].unique().to_list())
    weekly_dfs = _split_into_complete_weeks(df, game=game, start_num=effective_start)

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



def compute_weekly_scores_pips(
    df: pl.DataFrame,
    game: str = "pips",
    pips_start: Optional[int] = None,
) -> List[pl.DataFrame]:
    """
    Calculate the total score for each player for all complete 7-day {game} weeks.
    Incomplete trailing weeks are omitted.
    If pips_start is provided, only scores and weeks starting from pips_start are considered.
    """
    if df is None or df.height == 0:
        return []

    # Convert time_str to time_seconds if not already present
    if "time_str" in df.columns and "time_seconds" not in df.columns:
        df = df.with_columns(
            pl.when(pl.col("time_str").cast(pl.String).str.contains(":"))
            .then(
                pl.col("time_str")
                .cast(pl.String)
                .str.split(":")
                .list.get(0)
                .cast(pl.Int64) * 60
                + pl.col("time_str")
                .cast(pl.String)
                .str.split(":")
                .list.get(1)
                .cast(pl.Int64)
            )
            .alias("time_seconds")
        )

    effective_start = pips_start if pips_start is not None else None
    col_name = _get_game_col(df, game)

    if effective_start is not None:
        df = df.filter(pl.col(col_name) >= effective_start)
        if df.height == 0:
            return []

    get_unique_week_ranges = CalendarUtils(game).get_unique_week_ranges
    week_ranges = get_unique_week_ranges(df[col_name].unique().to_list())
    weekly_dfs = _split_into_complete_weeks(df, game=game, start_num=effective_start)

    weekly_scores = []
    for df_week, week_start, week_end in weekly_dfs:
        weekly_score = (
            df_week.group_by("player")
            .agg(pl.sum("time_seconds"))
            .sort("time_seconds")
            .with_columns(
                pl.lit(week_start).cast(pl.Int64).alias("week_start"),
                pl.lit(week_end).cast(pl.Int64).alias("week_end"),
            )
        )
        weekly_scores.append(weekly_score)

    return weekly_scores


def rank_weekly_scores_wordle(
    df: pl.DataFrame,
    game: str = "wordle",
    wordle_start: Optional[int] = None,
) -> List[pl.DataFrame]:
    """
    Compute competition ranking for each complete week with mean ranks assigned to ties.
    """
    effective_start = wordle_start if wordle_start is not None else None
    weekly_scores = compute_weekly_scores_wordle(df, game=game, wordle_start=effective_start)
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

def rank_weekly_scores_pips(
    df: pl.DataFrame,
    game: str = "pips",
    pips_start: Optional[int] = None,
) -> List[pl.DataFrame]:
    """
    Compute weekly Pips rankings with:
       - mean competition rank
       - total_seconds
       - avg_seconds
       - week_start / week_end
    """
    effective_start = pips_start if pips_start is not None else None
    weekly_scores = compute_weekly_scores_pips(df, game=game, pips_start=effective_start) #player, pips_num, time_seconds, week_start, week_end
    ranked_weeks = []

    for weekly_score in weekly_scores:
        # Assign raw sequential rank
        df_ranked = weekly_score.with_columns(
            pl.arange(1, weekly_score.height + 1).alias("raw_rank")
        )

        # Compute mean rank for players with tied scores
        df_ranked_grouped = df_ranked.group_by("time_seconds").agg(
            pl.col("raw_rank").mean().alias("rank")
        )

        df_final = (
            df_ranked.join(df_ranked_grouped, on="time_seconds", how="left")
            .sort("rank")
            .drop("raw_rank")
        )

        # sum total sec and convert to 'mm:ss' format
        df_total_sec = (
            df_final.group_by("player")
            .agg(
                pl.sum("time_seconds").alias("total_seconds")
        )
        .with_columns(
            (
                (pl.col("total_seconds") // 60).cast(pl.String)
                + ":"
                + (pl.col("total_seconds") % 60).cast(pl.String).str.zfill(2)
                ).alias("time_str")
            )
        )

        if "time_str" in df.columns and "time_seconds" not in df.columns:
               df = df.with_columns(
                   pl.when(pl.col("time_str").cast(pl.String).str.contains(":"))
                   .then(
                       pl.col("time_str")
                       .cast(pl.String)
                       .str.split(":")
                       .list.get(0)
                       .cast(pl.Int64) * 60
                       + pl.col("time_str")
                       .cast(pl.String)
                       .str.split(":")
                       .list.get(1)
                       .cast(pl.Int64)
                   )
                   .alias("time_seconds")
               )
               
        df_avg_sec = df.group_by("player").agg(
                   pl.mean("time_seconds").round(2).alias("avg_seconds"))



        # week_start = int(df_final["week_start"].min())
        # week_end = int(df_final["week_end"].max())

        week_table = (
            df_final
            .join(df_total_sec, on="player")
            .join(df_avg_sec, on="player")
            .select([
                "player",
                "week_start",
                "week_end",
                "rank",
                "total_seconds",
                "time_str",
                "avg_seconds",
                ])
            .sort("rank")
        )

        ranked_weeks.append(week_table)

    return ranked_weeks

    #    "player": pl.String,
    #         "week_start": pl.Int64,
    #         "week_end": pl.Int64,
    #         "total_seconds": pl.Int64,
    #         "rank": pl.Float64,
    #         "overall_rank": pl.Float64,
    #         "avg_seconds": pl.Float64,
    #         "overall_seconds": pl.Float64,

            

def calculate_running_leaderboard(
    weekly_scores: List[pl.DataFrame],
    game: str = Optional[str],
    interest: str = "overall_rank",
    leaderboard: Optional[pl.DataFrame] = None,
) -> List[pl.DataFrame]:
    """
    Calculate running cumulative ranks and scores across consecutive weeks.
    """
    cumulative_rank = {}
    cumulative_score = {}

    if game not in ('wordle', 'pips'):
        raise ValueError(f"Unsupported game type: {game}. Must be 'wordle' or 'pips'.")

    # Game-specific metrics
    score_metric = "score" if game == "wordle" else "time_seconds"

    if leaderboard is not None and leaderboard.height > 0:
        player_num = len(leaderboard["player"].unique())
        current_leaderboard = leaderboard.tail(player_num)
        cumulative_rank = {
            row["player"]: row["overall_rank"]
            for row in current_leaderboard.iter_rows(named=True)
        }
        cumulative_score = {
            row["player"]: row[f"overall_{score_metric}"]
            for row in current_leaderboard.iter_rows(named=True)
        }

    ranked_weeks = []

    for week in weekly_scores:
        # Rank contribution for this week
        rank = week.group_by("player").agg(pl.sum("rank").alias("rank"))
        for row in rank.iter_rows(named=True):
            player = row["player"]
            cumulative_rank[player] = cumulative_rank.get(player, 0.0) + row["rank"]

        # Score contribution for this week
        week_score = week.group_by("player").agg(pl.sum(f"{score_metric}").alias(f"week_{score_metric}"))
        for row in week_score.iter_rows(named=True):
            player = row["player"]
            cumulative_score[player] = cumulative_score.get(player, 0.0) + row[f"week_{score_metric}"]

        cumulative_df = pl.DataFrame({
            "player": list(cumulative_rank.keys()),
            "overall_rank": list(cumulative_rank.values()),
        })

        cumulative_score_df = pl.DataFrame({
            "player": list(cumulative_score.keys()),
            f"overall_{score_metric}": list(cumulative_score.values()),
        })

        week_with_running = (
            week.join(cumulative_df, on="player", how="left")
            .join(cumulative_score_df, on="player", how="left")
            .with_columns([
                pl.col("overall_rank").cast(pl.Float64),
                pl.col(f"overall_{score_metric}").cast(pl.Float64),
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
        self.wordle_num = int(game_num)
        self.pips_num = int(game_num)
        self.score = score
        self.game = str(game)

    def __repr__(self) -> str:
        if self.game == "wordle":
            return f"(player={self.player}, wordle_num={self.wordle_num}, score={self.score}), game={self.game}\n"
        elif self.game == "pips":
            return f"(player={self.player}, pips_num={self.pips_num}, score={self.score}), game={self.game}\n"

    # def numeric_score(self) -> int:
    #     if self.game == "wordle" and self.score == "X":
    #         return WORDLE_FAIL_PENALTY_SCORE
    #     elif self.game == "pips" and self.score == "X":
    #         return PIPS_FAIL_PENALTY_SCORE
    #     return int(self.score)

    def as_tuple(self):
        if self.game == "wordle":
            return (self.player, self.wordle_num, self.score, self.game)
        else:
            return (self.player, self.pips_num, self.score, self.game)

    @staticmethod
    def score_cleaner(
        data,
        game: str = Optional[str],
        wordle_start: Optional[int] = None,
        pips_start: Optional[int] = None,
    ) -> pl.DataFrame:
        if game == "wordle":
            return clean_and_fill_scores_wordle(
                data,
                wordle_start=wordle_start,
            )
        elif game == "pips":
            return clean_and_fill_scores_pips(
                data,
                pips_start=pips_start,
            )
        else:
            raise ValueError(f"Unsupported game type: {game}. Must be 'wordle' or 'pips'.")


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
        game: str = Optional[str],
        wordle_start: Optional[int] = None,
        pips_start: Optional[int] = None,
    ) -> List[pl.DataFrame]:
        if game == "wordle":
            return compute_weekly_scores_wordle(
                df,
                game=game,
                wordle_start=wordle_start,
            )
        elif game == "pips":
            return compute_weekly_scores_pips(
                df,
                game=game,
                pips_start=pips_start,
            )
        else:
            raise ValueError(f"Unsupported game type: {game}. Must be 'wordle' or 'pips'.")
        


    @staticmethod
    def week_ranking(
        df: pl.DataFrame,
        game: str = Optional[str],
        # game_start: Optional[int] = None,
        wordle_start: Optional[int] = None,
        pips_start: Optional[int] = None,
    ) -> List[pl.DataFrame]:

        dispatch = {
            "wordle": rank_weekly_scores_wordle,
            "pips": rank_weekly_scores_pips,
        }

        if game not in dispatch:
            raise ValueError(f"Unsupported game type: {game}. Must be 'wordle' or 'pips'.")

        if game == 'wordle':
            return dispatch[game](
                df,
                game=game,
                # game_start=game_start,
                wordle_start=wordle_start,
            )
        elif game == 'pips':
            return dispatch[game](
                df,
                game=game,
                # game_start=game_start,
                pips_start=pips_start,
            )
        else:
            raise ValueError(f"Unsupported game type: {game}. Must be 'wordle' or 'pips'. in week_ranking()")
    

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
