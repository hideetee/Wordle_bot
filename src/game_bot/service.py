import logging
from typing import Any, Dict, Optional, Tuple
import polars as pl
from abc import ABC, abstractmethod

# from game_bot.calendar_utils import CalendarUtils
from game_bot.config import WordleConfig, load_config, PipsConfig
from game_bot.database import GameRepository
from game_bot.formatter import format_leaderboard_announcement
from game_bot.models import ScoreRecord
from game_bot.scorer import (
    calculate_running_leaderboard,
    clean_and_fill_scores,
    rank_weekly_scores,
)
from game_bot.whatsapp import WhatsAppClient

logger = logging.getLogger(__name__)

class Game(ABC):
    """Base class for different game types."""

    @abstractmethod
    def clean_and_fill_scores(
        self, 
        df: pl.DataFrame, 
        game_start: Optional[int] = None) -> pl.DataFrame:
        """Clean and fill scores for the specific game."""
        pass

    @abstractmethod
    def rank_weekly_scores(
        self,
        df: pl.DataFrame,
        wordle_start: Optional[int] = None
    ) -> list[pl.DataFrame]:
        """Rank weekly scores for Wordle."""
        pass

    @abstractmethod
    def format_leaderboard_announcement(
        self,
        leaderboard_df: pl.DataFrame
    ) -> str:
        """Format the leaderboard announcement message."""
        pass

class WordleGame(Game):
    """Implementation of Game for Wordle."""

    def clean_and_fill_scores(
        self, 
        df: pl.DataFrame, 
        wordle_start: Optional[int] = None
    ) -> pl.DataFrame:
        return clean_and_fill_scores(df, wordle_start=wordle_start)

    def rank_weekly_scores(
        self,
        df: pl.DataFrame,
        wordle_start: Optional[int] = None
    ) -> list[pl.DataFrame]:
        return rank_weekly_scores(df, wordle_start=wordle_start)

    def format_leaderboard_announcement(
        self,
        leaderboard_df: pl.DataFrame
    ) -> str:
        return format_leaderboard_announcement(leaderboard_df)

class PipsGame(Game):
    """Implementation of Game for Pips."""

    def clean_and_fill_scores(
        self, 
        df: pl.DataFrame, 
        pips_start: Optional[int] = None
    ) -> pl.DataFrame:
        return pips_clean_and_fill_scores(df, pips_start=pips_start)

    def rank_weekly_scores(
        self,
        df: pl.DataFrame,
        pips_start: Optional[int] = None
    ) -> list[pl.DataFrame]:
        return rank_weekly_scores(df, pips_start=pips_start)

    def format_leaderboard_announcement(
        self,
        leaderboard_df: pl.DataFrame
    ) -> str:
        return format_leaderboard_announcement(leaderboard_df)



class GameBotService:
    """Orchestrates Wordle score syncing, ranking calculations, persistence, and announcements."""

    def __init__(
        self,
        game: Game,
        repository: Optional[GameRepository] = None,
        config: WordleConfig | PipsConfig | None = None,
    ) -> None:
        self.game = game
        self.repository = repository or GameRepository()
        self.config = config


    def scrape_and_sync_scores(
        self,
        client: WhatsAppClient,
        wordle_start: Optional[int] = None,
    ) -> pl.DataFrame:
        """
        Scrape new messages from WhatsApp, clean/fill penalty scores, and persist to database.
        """
        effective_start = wordle_start if wordle_start is not None else self.config.wordle_start
        latest_wordle = self.repository.get_latest_wordle_num()
        cutoff = (latest_wordle - 1) if latest_wordle is not None else None

        if effective_start is not None:
            if cutoff is None or effective_start > cutoff:
                cutoff = effective_start - 1

        logger.info(f"Latest in DB: {latest_wordle}, cutoff: {cutoff}, wordle_start: {effective_start}")

        raw_messages = client.scroll_until_cutoff_and_store(cutoff)
        logger.info(f"Scraped {len(raw_messages)} messages from WhatsApp")

        if raw_messages:
            raw_df = pl.DataFrame(
                raw_messages, schema=["player", "wordle_num", "score"], orient="row"
            )
            if game == "wordle":
                cleaned_scores = clean_and_fill_scores(raw_df, wordle_start=effective_start)
            elif game == "pips":
                cleaned_scores = pips_clean_and_fill_scores(raw_df, wordle_start=effective_start)
            # cleaned_scores = clean_and_fill_scores(raw_df, wordle_start=effective_start)
            self.repository.save_score_if_missing_or_7(cleaned_scores)

        return self.repository.load_scores(wordle_min=effective_start)

    def process_and_update_leaderboards(
        self,
        wordle_start: Optional[int] = None,
    ) -> pl.DataFrame:
        """
        Compute weekly rankings and cumulative standings across scores and save them.
        Returns the latest leaderboard DataFrame.
        """
        effective_start = wordle_start if wordle_start is not None else self.config.wordle_start
        scores_df = self.repository.load_scores(wordle_min=effective_start)
        if scores_df.height == 0:
            return self.repository.load_leaderboard(last_leaderboard=True, wordle_start=effective_start)

        existing_leaderboard = self.repository.load_leaderboard(wordle_start=effective_start)

        if existing_leaderboard.height == 0:
            # First run or empty leaderboard: compute across all historical scores from effective_start
            weekly_ranks = rank_weekly_scores(scores_df, wordle_start=effective_start)
            full_leaderboard = calculate_running_leaderboard(
                weekly_ranks, interest="overall_score"
            )
            for table in full_leaderboard:
                self.repository.save_leaderboard(table)
            return full_leaderboard[-1] if full_leaderboard else pl.DataFrame()

        # Incremental update based on latest week ranges
        latest_wordle = scores_df["wordle_num"].max()
        last_table_end = existing_leaderboard["week_end"].max()

        if last_table_end is not None:
            calc_limit = last_table_end + 1
        elif effective_start is not None:
            calc_limit = effective_start
        else:
            calc_limit = 0

        scores_recent = scores_df.filter(pl.col("wordle_num") >= calc_limit)

        if scores_recent.height > 0:
            recent_weeks = rank_weekly_scores(scores_recent, wordle_start=calc_limit)
            updated_leaderboard = calculate_running_leaderboard(
                recent_weeks, interest="overall_score", leaderboard=existing_leaderboard
            )
            for table in updated_leaderboard:
                self.repository.save_leaderboard(table)

        return self.repository.load_leaderboard(last_leaderboard=True, wordle_start=effective_start)

    def get_leaderboard(
        self,
        last_only: bool = False,
        wordle_start: Optional[int] = None,
    ) -> pl.DataFrame:
        """Fetch current leaderboard records from repository."""
        effective_start = wordle_start if wordle_start is not None else self.config.wordle_start
        return self.repository.load_leaderboard(last_leaderboard=last_only, wordle_start=effective_start)

    def generate_announcement_message(
        self,
        leaderboard_df: Optional[pl.DataFrame] = None,
        wordle_start: Optional[int] = None,
    ) -> str:
        """Construct the WhatsApp announcement message string."""
        if leaderboard_df is None or leaderboard_df.height == 0:
            leaderboard_df = self.get_leaderboard(last_only=True, wordle_start=wordle_start)
        return format_leaderboard_announcement(leaderboard_df)

    def run(
        self,
        client: Optional[WhatsAppClient] = None,
        send_announcement: bool = True,
        wordle_start: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute the end-to-end Wordle Bot synchronization workflow.
        """
        effective_start = wordle_start if wordle_start is not None else self.config.wordle_start
        should_close_client = False
        if client is None:
            client = WhatsAppClient(self.config.group_name)
            should_close_client = True

        try:
            # 1. Scrape & Sync
            self.scrape_and_sync_scores(client, wordle_start=effective_start)

            # 2. Process Rankings
            latest_leaderboard = self.process_and_update_leaderboards(wordle_start=effective_start)

            # 3. Format Announcement
            message = self.generate_announcement_message(latest_leaderboard, wordle_start=effective_start)

            # 4. Send Message if configured
            sent = False
            if send_announcement and self.config.group_name_send:
                client.open_group(self.config.group_name_send)
                sent = client.send_message(message)

            return {
                "success": True,
                "message": message,
                "sent": sent,
                "leaderboard": latest_leaderboard,
            }
        finally:
            if should_close_client and client is not None:
                client.close()
