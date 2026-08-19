import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from wordle_bot.models import ScoreRecord

# Regex pattern for matching Wordle score headers (e.g., "Wordle 1,234 3/6" or "wordle 500 X/6")
WORDLE_SCORE_PATTERN = re.compile(r"Wordle\s+([\d,\s]+)\s+([1-6X])/6", re.IGNORECASE)

# Regex pattern for WhatsApp message timestamps/headers (e.g., "1/25/26, 1:32 AM - ")
WHATSAPP_HEADER_PATTERN = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4},\s+")


class WordleParser:
    """Parses Wordle game results and sender metadata from raw chat text."""

    def __init__(self) -> None:
        self.wordle_tally: int = 0
        self.pattern = WORDLE_SCORE_PATTERN

    def parse(self, message: str) -> Optional[Dict[str, Any]]:
        """Parse a single text message and return wordle number and score string if found."""
        match = self.pattern.search(message)
        if match:
            self.wordle_tally += 1
            wordle_num = int(match.group(1).replace(",", "").strip())
            score_str = match.group(2).strip()
            return {
                "wordle": wordle_num,
                "score": score_str,
            }
        return None

    @staticmethod
    def find_sender(lines: Sequence[str], index: int) -> Optional[str]:
        """
        Walk backwards from the given index to locate the sender name from WhatsApp message headers.
        """
        for i in range(index, -1, -1):
            line = lines[i]
            if WHATSAPP_HEADER_PATTERN.match(line):
                # Expected format: "1/25/26, 1:32 AM - Sender Name: message"
                parts = line.split("-", 1)
                if len(parts) > 1:
                    sender_part = parts[1].split(":", 1)[0].strip()
                    return sender_part
        return None

    @classmethod
    def parse_messages(cls, lines: Sequence[str]) -> List[Tuple[str, int, str]]:
        """
        Parse a list of WhatsApp message lines, extracting (sender, wordle_num, score_str).
        """
        results: List[Tuple[str, int, str]] = []
        for i, line in enumerate(lines):
            match = WORDLE_SCORE_PATTERN.search(line)
            if not match:
                continue

            sender = cls.find_sender(lines, i) or "Unknown"
            wordle_num = int(match.group(1).replace(",", "").strip())
            score_str = match.group(2).strip()
            results.append((sender, wordle_num, score_str))

        return results

    @staticmethod
    def parser_wordle_score(msg: Sequence[str]) -> List[Tuple[str, int, str]]:
        """Backward-compatible alias for parse_messages."""
        return WordleParser.parse_messages(msg)


# Module-level convenience functions
parse_wordle_scores = WordleParser.parse_messages
parser_wordle_score = WordleParser.parser_wordle_score