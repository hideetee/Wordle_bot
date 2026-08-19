import logging
from typing import Optional
import polars as pl

from wordle_bot.config import WordleConfig, load_config
from wordle_bot.database import WordleRepository
from wordle_bot.service import WordleBotService
from wordle_bot.whatsapp import WhatsAppClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_current_leaderboard(last_leaderboard: bool = False) -> pl.DataFrame:
    """Fetch current leaderboard DataFrame from database."""
    repo = WordleRepository()
    return repo.load_leaderboard(last_leaderboard=last_leaderboard)


def main(send_message: bool = True) -> Optional[WhatsAppClient]:
    """
    Main entry point for running the Wordle Bot workflow.
    """
    logger.info("=== START WORDLE BOT RUN ===")
    config = WordleConfig.from_dict(load_config())
    service = WordleBotService(config=config)

    whatsapp_client = WhatsAppClient(group_name=config.group_name)

    try:
        result = service.run(client=whatsapp_client, send_announcement=send_message)
        logger.info("=== LEADERBOARD ANNOUNCEMENT ===")
        print(result["message"])
        logger.info("=== END WORDLE BOT RUN ===")
        return whatsapp_client
    except Exception as e:
        logger.error(f"Error during bot execution: {e}")
        whatsapp_client.close()
        raise


if __name__ == "__main__":
    client = main(send_message=False)
    if client is not None:
        client.close()
