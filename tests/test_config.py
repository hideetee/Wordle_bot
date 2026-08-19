import json
import tempfile
from pathlib import Path
import pytest

from wordle_bot.config import (
    DEFAULT_CONFIG,
    WordleConfig,
    load_config,
    save_config,
)


def test_wordle_config_dataclass():
    cfg = WordleConfig(group_name="Group A", group_name_send="Group B")
    d = cfg.to_dict()
    assert d == {"GROUP_NAME": "Group A", "GROUP_NAME_SEND": "Group B"}

    from_d = WordleConfig.from_dict(d)
    assert from_d.group_name == "Group A"
    assert from_d.group_name_send == "Group B"


def test_load_and_save_config(monkeypatch, tmp_path):
    fake_config_file = tmp_path / "config.json"
    monkeypatch.setattr("wordle_bot.config.CONFIG_FILE", fake_config_file)
    monkeypatch.setattr("wordle_bot.config.BASE_DIR", tmp_path)

    # First load should create default config
    loaded = load_config()
    assert loaded == DEFAULT_CONFIG

    # Modify and save
    custom = {"GROUP_NAME": "Custom Group", "GROUP_NAME_SEND": "My Channel"}
    save_config(custom)

    loaded_custom = load_config()
    assert loaded_custom == custom


def test_load_config_corrupted_file_falls_back(monkeypatch, tmp_path):
    fake_config_file = tmp_path / "config.json"
    fake_config_file.write_text("invalid json content")
    monkeypatch.setattr("wordle_bot.config.CONFIG_FILE", fake_config_file)
    monkeypatch.setattr("wordle_bot.config.BASE_DIR", tmp_path)

    loaded = load_config()
    assert loaded == DEFAULT_CONFIG
