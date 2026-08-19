"""Wordle Bot - Automated tracking, scoring, and leaderboard management for Wordle Golf."""

from wordle_bot.calendar_utils import get_unique_week_ranges, get_wordle_week, wordle_week
from wordle_bot.config import (
    DAYS_PER_WEEK,
    FAIL_PENALTY_SCORE,
    SIMILARITY_THRESHOLD,
    WORDLE_ANCHOR_NUMBER,
    WORDLE_ANCHOR_WEEKDAY,
    WordleConfig,
    load_config,
    save_config,
)
from wordle_bot.database import Database_wordle, WordleRepository
from wordle_bot.formatter import (
    format_leaderboard_announcement,
    format_overall_score_table,
    format_weekly_score_table,
)
from wordle_bot.models import (
    LeaderboardEntry,
    ScoreRecord,
    WeeklyScore,
    WeekRange,
)
from wordle_bot.parser import (
    WordleParser,
    parse_wordle_scores,
    parser_wordle_score,
)
from wordle_bot.scorer import (
    ScoreCalculator,
    calculate_running_leaderboard,
    clean_and_fill_scores,
    compute_weekly_scores,
    rank_weekly_scores,
)
from wordle_bot.service import WordleBotService
from wordle_bot.whatsapp import WhatsAppClient

__all__ = [
    "WordleRepository",
    "Database_wordle",
    "WordleParser",
    "parse_wordle_scores",
    "parser_wordle_score",
    "ScoreCalculator",
    "clean_and_fill_scores",
    "compute_weekly_scores",
    "rank_weekly_scores",
    "calculate_running_leaderboard",
    "get_wordle_week",
    "get_unique_week_ranges",
    "wordle_week",
    "WhatsAppClient",
    "WordleBotService",
    "WordleConfig",
    "load_config",
    "save_config",
    "format_weekly_score_table",
    "format_overall_score_table",
    "format_leaderboard_announcement",
    "ScoreRecord",
    "WeekRange",
    "WeeklyScore",
    "LeaderboardEntry",
    "FAIL_PENALTY_SCORE",
    "WORDLE_ANCHOR_NUMBER",
    "WORDLE_ANCHOR_WEEKDAY",
    "DAYS_PER_WEEK",
    "SIMILARITY_THRESHOLD",
]
