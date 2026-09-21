"""GameBot - Automated tracking, scoring, and leaderboard management for Wordle and Pips."""

from game_bot.calendar_utils import CalendarUtils
from game_bot.config import (
    DAYS_PER_WEEK,
    WORDLE_FAIL_PENALTY_SCORE,
    PIPS_FAIL_PENALTY_SCORE,
    PIPS_ANCHOR_NUMBER,
    PIPS_ANCHOR_WEEKDAY,
    SIMILARITY_THRESHOLD,
    WORDLE_ANCHOR_NUMBER,
    WORDLE_ANCHOR_WEEKDAY,
    WordleConfig,
    PipsConfig,
    load_config,
    save_config,
)
from game_bot.database import Database_game, GameRepository
from game_bot.formatter import (
    format_leaderboard_announcement,
    format_overall_score_table,
    format_weekly_score_table,
)
from game_bot.models import (
    LeaderboardEntry,
    ScoreRecord,
    WeeklyScore,
    WeekRange,
)
from game_bot.parser import (
    WordleParser,
    PipsParser,
    parse_wordle_scores,
    parser_wordle_score,
    parse_pips_scores,
    parser_pips_score,
    parse_messages,
    parse_scores,
    parser_score,
)
from game_bot.scorer import (
    ScoreCalculator,
    calculate_running_leaderboard,
    clean_and_fill_scores,
    compute_weekly_scores,
    rank_weekly_scores,
)
from game_bot.service import Game, GameBotService, PipsGame, WordleGame
from game_bot.whatsapp import WhatsAppClient

game_week = ScoreCalculator.game_week

__all__ = [
    "GameRepository",
    "Database_game",
    "WordleParser",
    "PipsParser",
    "parse_wordle_scores",
    "parser_wordle_score",
    "parse_pips_scores",
    "parser_pips_score",
    "parse_messages",
    "parse_scores",
    "parser_score",
    "ScoreCalculator",
    "clean_and_fill_scores",
    "compute_weekly_scores",
    "rank_weekly_scores",
    "calculate_running_leaderboard",
    "CalendarUtils",
    "game_week",
    "WhatsAppClient",
    "Game",
    "WordleGame",
    "PipsGame",
    "GameBotService",
    "WordleConfig",
    "PipsConfig",
    "load_config",
    "save_config",
    "format_weekly_score_table",
    "format_overall_score_table",
    "format_leaderboard_announcement",
    "ScoreRecord",
    "WeekRange",
    "WeeklyScore",
    "LeaderboardEntry",
    "WORDLE_FAIL_PENALTY_SCORE",
    "WORDLE_ANCHOR_NUMBER",
    "WORDLE_ANCHOR_WEEKDAY",
    "PIPS_ANCHOR_NUMBER",
    "PIPS_FAIL_PENALTY_SCORE",
    "PIPS_ANCHOR_WEEKDAY",
    "DAYS_PER_WEEK",
    "SIMILARITY_THRESHOLD",
]
