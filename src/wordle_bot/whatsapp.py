import logging
import re
import time
from typing import List, Optional, Sequence, Tuple
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright
import polars as pl

from wordle_bot.config import SIMILARITY_THRESHOLD
from wordle_bot.formatter import format_overall_score_table, format_weekly_score_table
from wordle_bot.parser import WordleParser
from wordle_bot.utils import normalize, similarity

logger = logging.getLogger(__name__)


class WhatsAppClient:
    """Automates WhatsApp Web interaction via Playwright to scrape scores and send messages."""

    def __init__(
        self,
        group_name: Optional[str] = None,
        user_data_dir: str = "browser",
        executable_path: str = "/usr/bin/google-chrome",
        headless: bool = False,
    ) -> None:
        self.group_name = group_name
        self.user_data_dir = user_data_dir
        self.executable_path = executable_path
        self.headless = headless

        self._playwright = sync_playwright().start()
        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            executable_path=self.executable_path,
            headless=self.headless,
        )
        self.page = self._context.pages[0] if self._context.pages else self._context.new_page()
        self.page.goto("https://web.whatsapp.com")
        self.page.wait_for_timeout(5000)

        if self.group_name:
            self.open_group(self.group_name)

    def __enter__(self) -> "WhatsAppClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        """Close browser context and stop Playwright process."""
        try:
            self._context.close()
        except Exception as e:
            logger.debug(f"Error closing browser context: {e}")
        try:
            self._playwright.stop()
        except Exception as e:
            logger.debug(f"Error stopping Playwright: {e}")

    def open_group(self, name: str) -> None:
        """Search for and open a WhatsApp chat/group by name."""
        search = self.page.locator("input[type='text'][data-tab='3']")
        search.click()
        search.fill(name)
        self.page.wait_for_timeout(2000)
        search.press("Enter")
        self.page.wait_for_timeout(3000)

    def scroll_until_cutoff_and_store(
        self, cutoff_wordle_num: Optional[int] = None
    ) -> List[Tuple[str, int, str]]:
        """
        Scroll through chat history until a Wordle score <= cutoff_wordle_num is found.
        Returns a list of parsed (sender, wordle_num, score_str) tuples.
        """
        parsed_wordles: List[Tuple[str, int, str]] = []
        seen = set()
        wordle_pattern = re.compile(r"Wordle\s+([\d,]+)", re.IGNORECASE)

        while True:
            elements = self.page.locator("div.copyable-text")
            count = elements.count()
            found_cutoff = False

            for i in range(count):
                element = elements.nth(i)
                raw = element.get_attribute("data-pre-plain-text")
                if raw is None:
                    continue

                # Extract sender name
                parts = raw.split("]")[-1].split(":")
                sender = parts[0].strip() if parts else "Unknown"
                inner_text = element.inner_text()

                match = wordle_pattern.search(inner_text)
                if not match:
                    continue

                wordle_num = int(match.group(1).replace(",", ""))
                key = (sender, wordle_num)
                if key in seen:
                    continue
                seen.add(key)

                parsed_msg = WordleParser.parse_messages([inner_text])
                if parsed_msg:
                    parsed_wordles.append((sender, parsed_msg[0][1], parsed_msg[0][2]))

                if cutoff_wordle_num is not None and wordle_num <= cutoff_wordle_num:
                    found_cutoff = True

            if found_cutoff:
                break

            # Scroll up in message panel to load older messages
            self.page.locator('div[data-testid="conversation-panel-messages"]').evaluate(
                "el => el.scrollBy(0, -2000)"
            )
            time.sleep(1)

        return parsed_wordles

    def message_sent(self, message: str) -> bool:
        """Check if the latest chat message matches the expected sent message content."""
        last_message = self.page.locator("[data-testid='msg-container']").last

        try:
            last_message.wait_for(timeout=1000)
        except PlaywrightTimeoutError:
            return False

        fail_count = last_message.locator("[data-testid='fail-container']").count()

        try:
            expected = normalize(message)
            actual = last_message.locator("span[data-testid='selectable-text']").inner_text()
            actual = normalize(actual)
        except Exception:
            return False

        score = similarity(expected, actual)
        return score >= SIMILARITY_THRESHOLD and fail_count == 0

    def send_message(self, message: str, max_retries: int = 5, timeout: float = 10.0) -> bool:
        """Send a text message in the currently open chat with automatic retries."""
        input_box = self.page.locator("[data-testid='conversation-compose-box-input']")
        time.sleep(1)

        for attempt in range(max_retries):
            if attempt == 0:
                input_box.wait_for(state="visible")
                input_box.click()
                input_box.fill("")
                input_box.fill(message)
                input_box.press("Enter")
            else:
                last_message = self.page.locator("[data-testid='msg-container']").last
                fail_button = last_message.locator("[data-testid='fail-container']")
                if fail_button.count() == 0 and self.message_sent(message):
                    return True
                if fail_button.count() > 0:
                    fail_button.click()

            deadline = time.time() + timeout
            while time.time() < deadline:
                if self.message_sent(message):
                    return True

                last_message = self.page.locator("[data-testid='msg-container']").last
                if last_message.locator("[data-testid='fail-container']").count() > 0:
                    break

                time.sleep(0.2)

        return False

    # Backward-compatible static presentation methods
    @staticmethod
    def df_to_whatsapp_score_rank(df: pl.DataFrame) -> str:
        return format_weekly_score_table(df)

    @staticmethod
    def df_to_whatsapp_overall_score_rank(df: pl.DataFrame) -> str:
        return format_overall_score_table(df)