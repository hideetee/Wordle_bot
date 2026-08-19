import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict

# ==============================
# DOMAIN CONSTANTS
# ==============================
FAIL_PENALTY_SCORE = 7
WORDLE_ANCHOR_NUMBER = 1875
WORDLE_ANCHOR_WEEKDAY = 5  # Friday (0 = Sunday, 1 = Monday, ..., 5 = Friday, 6 = Saturday)
DAYS_PER_WEEK = 7
SIMILARITY_THRESHOLD = 0.9
DEFAULT_CHECK_INTERVAL = 30

# Base directory for user data
BASE_DIR = Path(os.path.expanduser("~/.wordlebot"))
CONFIG_FILE = BASE_DIR / "config.json"
DATABASE_PATH = BASE_DIR / "scores.db"


@dataclass
class WordleConfig:
    group_name: str = "Wordle Golf"
    group_name_send: str = "Haidee UK (You)"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WordleConfig":
        return cls(
            group_name=data.get("GROUP_NAME", "Wordle Golf"),
            group_name_send=data.get("GROUP_NAME_SEND", "Haidee UK (You)"),
        )

    def to_dict(self) -> Dict[str, str]:
        return {
            "GROUP_NAME": self.group_name,
            "GROUP_NAME_SEND": self.group_name_send,
        }


DEFAULT_CONFIG = {
    "GROUP_NAME": "Wordle Golf",
    "GROUP_NAME_SEND": "Haidee UK (You)",
}


def ensure_base_dir() -> Path:
    """Ensure that the application data directory exists."""
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    return BASE_DIR


def get_config_path() -> Path:
    """Return the resolved path to config.json."""
    ensure_base_dir()
    return CONFIG_FILE


def get_database_path() -> Path:
    """Return the resolved path to scores.db."""
    ensure_base_dir()
    return DATABASE_PATH


def load_config() -> Dict[str, str]:
    """
    Load configuration from the user's config.json.
    Falls back to default configuration if missing or invalid.
    """
    config_path = get_config_path()
    if not config_path.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            return DEFAULT_CONFIG.copy()
    except (json.JSONDecodeError, OSError, ValueError):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, str]) -> None:
    """Save configuration dictionary to config.json."""
    config_path = get_config_path()
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
