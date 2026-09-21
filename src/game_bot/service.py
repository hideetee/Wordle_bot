import logging
from typing import Any, Dict, Optional, Tuple, Union
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
    name: str

    @abstractmethod
    def clean_and_fill_scores(
        self, 
        df: pl.DataFrame, 
        game_start: Optional[int] = None,
        **kwargs: Any,
    ) -> pl.DataFrame:
        """Clean and fill scores for the specific game."""
        pass

    @abstractmethod
    def rank_weekly_scores(
        self,
        df: pl.DataFrame,
        game_start: Optional[int] = None,
        **kwargs: Any,
    ) -> list[pl.DataFrame]:
        """Rank weekly scores for the game."""
        pass

    @abstractmethod
    def format_leaderboard_announcement(
        self,
        leaderboard_df: pl.DataFrame,
    ) -> str:
        """Format the leaderboard announcement message."""
        pass


class WordleGame(Game):
    """Implementation of Game for Wordle."""
    name: str = "wordle"

    def clean_and_fill_scores(
        self, 
        df: pl.DataFrame, 
        game_start: Optional[int] = None,
        wordle_start: Optional[int] = None,
        **kwargs: Any,
    ) -> pl.DataFrame:
        effective_start = game_start if game_start is not None else wordle_start
        return clean_and_fill_scores(df, game="wordle", game_start=effective_start)

    def rank_weekly_scores(
        self,
        df: pl.DataFrame,
        game_start: Optional[int] = None,
        wordle_start: Optional[int] = None,
        **kwargs: Any,
    ) -> list[pl.DataFrame]:
        effective_start = game_start if game_start is not None else wordle_start
        return rank_weekly_scores(df, game="wordle", game_start=effective_start)

    def format_leaderboard_announcement(
        self,
        leaderboard_df: pl.DataFrame,
    ) -> str:
        return format_leaderboard_announcement(leaderboard_df)


class PipsGame(Game):
    """Implementation of Game for Pips."""
    name: str = "pips"

    def clean_and_fill_scores(
        self, 
        df: pl.DataFrame, 
        game_start: Optional[int] = None,
        pips_start: Optional[int] = None,
        **kwargs: Any,
    ) -> pl.DataFrame:
        effective_start = game_start if game_start is not None else pips_start
        return clean_and_fill_scores(df, game="pips", game_start=effective_start)

    def rank_weekly_scores(
        self,
        df: pl.DataFrame,
        game_start: Optional[int] = None,
        pips_start: Optional[int] = None,
        **kwargs: Any,
    ) -> list[pl.DataFrame]:
        effective_start = game_start if game_start is not None else pips_start
        return rank_weekly_scores(df, game="pips", game_start=effective_start)

    def format_leaderboard_announcement(
        self,
        leaderboard_df: pl.DataFrame,
    ) -> str:
        return format_leaderboard_announcement(leaderboard_df)



class GameBotService:
    """Orchestrates game score syncing, ranking calculations, persistence, and announcements."""

    def __init__(
        self,
        game: Optional[Union[Game, str]] = None,
        repository: Optional[GameRepository] = None,
        config: WordleConfig | PipsConfig | None = None,
    ) -> None:
        if game is None:
            if config is not None and hasattr(config, "game") and config.game == "pips":
                self.game: Game = PipsGame()
            else:
                self.game = WordleGame()
        elif isinstance(game, str):
            if game == "pips":
                self.game = PipsGame()
            elif game == "wordle":
                self.game = WordleGame()
            else:
                raise ValueError(f"Unsupported game type: {game}")
        else:
            self.game = game

        self.repository = repository or GameRepository(game=getattr(self.game, "name", "wordle"))
        self.config = config or (WordleConfig() if getattr(self.game, "name", "wordle") == "wordle" else PipsConfig())

    def _get_effective_start(
        self,
        game_start: Optional[int] = None,
        wordle_start: Optional[int] = None,
        pips_start: Optional[int] = None,
    ) -> Optional[int]:
        if game_start is not None:
            return game_start
        if wordle_start is not None:
            return wordle_start
        if pips_start is not None:
            return pips_start
        if self.config is not None:
            if hasattr(self.config, "wordle_start") and self.config.wordle_start is not None:
                return self.config.wordle_start
            if hasattr(self.config, "pips_start") and self.config.pips_start is not None:
                return self.config.pips_start
        return None

    def scrape_and_sync_scores(
        self,
        client: WhatsAppClient,
        wordle_start: Optional[int] = None,
        game_start: Optional[int] = None,
        pips_start: Optional[int] = None,
    ) -> pl.DataFrame:
        """
        Scrape new messages from WhatsApp, clean/fill penalty scores, and persist to database.
        """
        effective_start = self._get_effective_start(
            game_start=game_start, wordle_start=wordle_start, pips_start=pips_start
        )
        latest_wordle = self.repository.get_latest_wordle_num()
        cutoff = (latest_wordle - 1) if latest_wordle is not None else None

        if effective_start is not None:
            if cutoff is None or effective_start > cutoff:
                cutoff = effective_start - 1

        logger.info(f"Latest in DB: {latest_wordle}, cutoff: {cutoff}, start: {effective_start}")

        raw_messages = client.scroll_until_cutoff_and_store(cutoff)
        logger.info(f"Scraped {len(raw_messages)} messages from WhatsApp")

        if raw_messages:
            num_col = f"{self.game.name}_num" if hasattr(self.game, "name") else "wordle_num"
            raw_df = pl.DataFrame(
                raw_messages, schema=["player", num_col, "score"], orient="row"
            )
            cleaned_scores = self.game.clean_and_fill_scores(raw_df, game_start=effective_start)
            self.repository.save_score_if_missing_or_7(cleaned_scores)

        return self.repository.load_scores(wordle_min=effective_start)

    def process_and_update_leaderboards(
        self,
        wordle_start: Optional[int] = None,
        game_start: Optional[int] = None,
        pips_start: Optional[int] = None,
    ) -> pl.DataFrame:
        """
        Compute weekly rankings and cumulative standings across scores and save them.
        Returns the latest leaderboard DataFrame.
        """
        effective_start = self._get_effective_start(
            game_start=game_start, wordle_start=wordle_start, pips_start=pips_start
        )
        scores_df = self.repository.load_scores(wordle_min=effective_start)
        if scores_df.height == 0:
            return self.repository.load_leaderboard(last_leaderboard=True, wordle_start=effective_start)

        existing_leaderboard = self.repository.load_leaderboard(wordle_start=effective_start)

        if existing_leaderboard.height == 0:
            # First run or empty leaderboard: compute across all historical scores from effective_start
            weekly_ranks = self.game.rank_weekly_scores(scores_df, game_start=effective_start)
            full_leaderboard = calculate_running_leaderboard(
                weekly_ranks, interest="overall_score"
            )
            for table in full_leaderboard:
                self.repository.save_leaderboard(table)
            return full_leaderboard[-1] if full_leaderboard else pl.DataFrame()

        # Incremental update based on latest week ranges
        num_col = "wordle_num" if "wordle_num" in scores_df.columns else ("pips_num" if "pips_num" in scores_df.columns else "game_num")
        last_table_end = existing_leaderboard["week_end"].max()

        if last_table_end is not None:
            calc_limit = last_table_end + 1
        elif effective_start is not None:
            calc_limit = effective_start
        else:
            calc_limit = 0

        scores_recent = scores_df.filter(pl.col(num_col) >= calc_limit)

        if scores_recent.height > 0:
            recent_weeks = self.game.rank_weekly_scores(scores_recent, game_start=calc_limit)
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
        game_start: Optional[int] = None,
        pips_start: Optional[int] = None,
    ) -> pl.DataFrame:
        """Fetch current leaderboard records from repository."""
        effective_start = self._get_effective_start(
            game_start=game_start, wordle_start=wordle_start, pips_start=pips_start
        )
        return self.repository.load_leaderboard(last_leaderboard=last_only, wordle_start=effective_start)

    def generate_announcement_message(
        self,
        leaderboard_df: Optional[pl.DataFrame] = None,
        wordle_start: Optional[int] = None,
        game_start: Optional[int] = None,
        pips_start: Optional[int] = None,
    ) -> str:
        """Construct the WhatsApp announcement message string."""
        effective_start = self._get_effective_start(
            game_start=game_start, wordle_start=wordle_start, pips_start=pips_start
        )
        if leaderboard_df is None or leaderboard_df.height == 0:
            leaderboard_df = self.get_leaderboard(last_only=True, game_start=effective_start)
        return self.game.format_leaderboard_announcement(leaderboard_df)

    def run(
        self,
        client: Optional[WhatsAppClient] = None,
        send_announcement: bool = True,
        wordle_start: Optional[int] = None,
        game_start: Optional[int] = None,
        pips_start: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute the end-to-end Bot synchronization workflow.
        """
        effective_start = self._get_effective_start(
            game_start=game_start, wordle_start=wordle_start, pips_start=pips_start
        )
        should_close_client = False
        if client is None:
            client = WhatsAppClient(self.config.group_name)
            should_close_client = True

        try:
            # 1. Scrape & Sync
            self.scrape_and_sync_scores(client, game_start=effective_start)

            # 2. Process Rankings
            latest_leaderboard = self.process_and_update_leaderboards(game_start=effective_start)

            # 3. Format Announcement
            message = self.generate_announcement_message(latest_leaderboard, game_start=effective_start)

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
