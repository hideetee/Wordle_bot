import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict

# ==============================
# DOMAIN CONSTANTS
# ==============================
WORDLE_FAIL_PENALTY_SCORE = 7 # number of players + 1
WORDLE_ANCHOR_NUMBER = 1875
WORDLE_ANCHOR_WEEKDAY = 5  # Friday (0 = Sunday, 1 = Monday, ..., 5 = Friday, 6 = Saturday)
DAYS_PER_WEEK = 7
SIMILARITY_THRESHOLD = 0.9
DEFAULT_CHECK_INTERVAL = 30
PIPS_FAIL_PENALTY_SCORE = 5 # number of players + 1
PIPS_ANCHOR_NUMBER = 395
PIPS_ANCHOR_WEEKDAY = 4 

# Base directory for game_bot data and config
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE_WORDLE = BASE_DIR / "config_wordle.json"
CONFIG_FILE_PIPS = BASE_DIR / "config_pips.json"
WORDLE_DATABASE_PATH = BASE_DIR / "scores_wordle.db"
PIPS_DATABASE_PATH = BASE_DIR / "scores_pips.db"

# Check if the database files exist, if not create them




@dataclass
class WordleConfig:
    group_name: str = "Wordle Golf"
    group_name_send: str = "Haidee UK (You)"
    wordle_start: Optional[int] = None,
    game: str = "wordle"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WordleConfig":
        raw_start = data.get("WORDLE_START")
        wordle_start = None
        if raw_start is not None and raw_start != "":
            try:
                wordle_start = int(raw_start)
            except (ValueError, TypeError):
                wordle_start = None

        return cls(
            group_name=data.get("GROUP_NAME", "Wordle Golf"),
            group_name_send=data.get("GROUP_NAME_SEND", "Haidee UK (You)"),
            wordle_start=wordle_start,
            game=data.get("game", "wordle")
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "GROUP_NAME": self.group_name,
            "GROUP_NAME_SEND": self.group_name_send,
            "WORDLE_START": self.wordle_start,
            "game": self.game
        }


DEFAULT_CONFIG_WORDLE = {
    "GROUP_NAME": "Wordle Golf",
    "GROUP_NAME_SEND": "Haidee UK (You)",
    "WORDLE_START": None,
    "game": "wordle"
}

DEFAULT_CONFIG_PIPS = {
    "GROUP_NAME": "Pips",
    "GROUP_NAME_SEND": "Haidee UK (You)",
    "PIPS_START": 391,
    "game": "pips"
}

@dataclass
class PipsConfig:
    group_name: str = "Pips"
    group_name_send: str = "Haidee UK (You)"
    pips_start: Optional[int] = None
    game: str = "pips"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PipsConfig":
        raw_start = data.get("PIPS_START")
        pips_start = None
        if raw_start not in (None, ""):
            try:
                pips_start = int(raw_start)
            except (ValueError, TypeError):
                pips_start = None

        return cls(
            group_name=data.get("GROUP_NAME", "Pips"),
            group_name_send=data.get("GROUP_NAME_SEND", "Haidee UK (You)"),
            pips_start=pips_start,
            game=data.get("game", "pips")
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "GROUP_NAME": self.group_name,
            "GROUP_NAME_SEND": self.group_name_send,
            "PIPS_START": self.pips_start,
            "game": self.game
        }

def ensure_base_dir() -> Path:
    """Ensure that the application data directory exists."""
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    return BASE_DIR


def get_config_path(game:str) -> Path:
    """Return the resolved path to config_wordle.json."""
    ensure_base_dir()
    if game == "wordle":
        return CONFIG_FILE_WORDLE
    elif game == "pips":
        return CONFIG_FILE_PIPS
    else:
        raise ValueError("Invalid game type. Must be 'wordle' or 'pips'.")


def get_database_path(game: str) -> Path:
    """Return the resolved path to scores.db."""
    ensure_base_dir()
    if game == "wordle":
        return WORDLE_DATABASE_PATH
    elif game == "pips":
        return PIPS_DATABASE_PATH
    else:
        raise ValueError("Invalid game type. Must be 'wordle' or 'pips'.")



def load_config(game:str) -> Dict[str, str]:
    """
    Load configuration from the user's config.json.
    Falls back to default configuration if missing or invalid.
    Works for wordle or pips game.
    """
    if game == "wordle":
        config_path = get_config_path('wordle')
        if not config_path.exists():
            save_config(DEFAULT_CONFIG_WORDLE)
            return DEFAULT_CONFIG_WORDLE.copy()

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                return DEFAULT_CONFIG_WORDLE.copy()
        except (json.JSONDecodeError, OSError, ValueError):
            save_config(DEFAULT_CONFIG_WORDLE)
            return DEFAULT_CONFIG_WORDLE.copy()
    elif game == "pips":
        config_path = get_config_path('pips')
        if not config_path.exists():
            save_config(DEFAULT_CONFIG_PIPS)
            return DEFAULT_CONFIG_PIPS.copy()

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                return DEFAULT_CONFIG_PIPS.copy()
        except (json.JSONDecodeError, OSError, ValueError):
            save_config(DEFAULT_CONFIG_PIPS)
            return DEFAULT_CONFIG_PIPS.copy()
    else: 
        raise ValueError("Invalid game type. Must be 'wordle' or 'pips'.")
        



def save_config(config: Dict[str, str]) -> None:
    """Save configuration dictionary to config.json depending on the game."""
    game = config.get("game")
    if game not in ("wordle", "pips"):
        raise ValueError("Invalid game type. Must be 'wordle' or 'pips'.")
    config_path = get_config_path(game)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


