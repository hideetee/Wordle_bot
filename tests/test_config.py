import json
import tempfile
from pathlib import Path
import pytest

from game_bot.config import (
    DEFAULT_CONFIG_WORDLE,
    DEFAULT_CONFIG_PIPS,
    WordleConfig,
    PipsConfig,
    load_config,
    save_config,
)


def test_wordle_config_dataclass():
    cfg = WordleConfig(group_name="Group A", group_name_send="Group B", wordle_start=1870, game = "wordle")
    d = cfg.to_dict()
    print(d)
    assert d == {"GROUP_NAME": "Group A", "GROUP_NAME_SEND": "Group B", "WORDLE_START": 1870, "game": "wordle"}

    from_d = WordleConfig.from_dict(d)
    assert from_d.group_name == "Group A"
    assert from_d.group_name_send == "Group B"
    assert from_d.wordle_start == 1870
    assert from_d.game == "wordle"

    # Test default None
    cfg_default = WordleConfig(group_name="Group A", group_name_send="Group B", wordle_start=None, game = "wordle")
    assert cfg_default.wordle_start is None
    assert cfg_default.to_dict() == {"GROUP_NAME": "Group A", "GROUP_NAME_SEND": "Group B", "WORDLE_START": None, "game": "wordle"}


def test_pips_config_dataclass():
    cfg = PipsConfig(group_name="Group A", group_name_send="Group B", pips_start=391, game = "pips")
    d = cfg.to_dict()
    print(d)
    assert d == {"GROUP_NAME": "Group A", "GROUP_NAME_SEND": "Group B", "PIPS_START": 391, "game": "pips"}

    from_d = PipsConfig.from_dict(d)
    assert from_d.group_name == "Group A"
    assert from_d.group_name_send == "Group B"
    assert from_d.pips_start == 391
    assert from_d.game == "pips"

    # Test default None
    cfg_default = PipsConfig(group_name="Group A", group_name_send="Group B", pips_start=None, game = "pips")
    assert cfg_default.pips_start is None
    assert cfg_default.to_dict() == {"GROUP_NAME": "Group A", "GROUP_NAME_SEND": "Group B", "PIPS_START": None, "game": "pips"}



def test_load_and_save_config_wordle(monkeypatch, tmp_path):
    fake_config_file = tmp_path / "config_wordle.json"
    monkeypatch.setattr("game_bot.config.CONFIG_FILE_WORDLE", fake_config_file)
    monkeypatch.setattr("game_bot.config.BASE_DIR", tmp_path)

    # First load should create default config
    loaded = load_config("wordle")
    assert loaded == DEFAULT_CONFIG_WORDLE

    # Modify and save
    custom = {"GROUP_NAME": "Custom Group", "GROUP_NAME_SEND": "My Channel", "WORDLE_START": 1850, "game" : "wordle"}
    save_config(custom)

    loaded_custom = load_config("wordle")
    assert loaded_custom == custom

def test_load_and_save_config_pips(monkeypatch, tmp_path):
    fake_config_file = tmp_path / "config_pips.json"
    monkeypatch.setattr("game_bot.config.CONFIG_FILE_PIPS", fake_config_file)
    monkeypatch.setattr("game_bot.config.BASE_DIR", tmp_path)

    # First load should create default config
    loaded = load_config("pips")
    assert loaded == DEFAULT_CONFIG_PIPS

    # Modify and save
    custom = {"GROUP_NAME": "Custom Pips Group", "GROUP_NAME_SEND": "My Pips Channel", "PIPS_START": 400, "game": "pips"}
    save_config(custom)

    loaded_custom = load_config("pips")
    assert loaded_custom == custom



def test_load_config_corrupted_file_falls_back_to_default_wordle(monkeypatch, tmp_path):
    fake_config_file = tmp_path / "config_wordle.json"
    fake_config_file.write_text("invalid json content")
    monkeypatch.setattr("game_bot.config.CONFIG_FILE_WORDLE", fake_config_file)
    monkeypatch.setattr("game_bot.config.BASE_DIR", tmp_path)

    loaded = load_config("wordle")
    assert loaded == DEFAULT_CONFIG_WORDLE

def test_load_config_corrupted_file_falls_back_to_default_pips(monkeypatch, tmp_path):
    fake_config_file = tmp_path / "config_pips.json"
    fake_config_file.write_text("invalid json content")
    monkeypatch.setattr("game_bot.config.CONFIG_FILE_PIPS", fake_config_file)
    monkeypatch.setattr("game_bot.config.BASE_DIR", tmp_path)

    loaded = load_config("pips")
    assert loaded == DEFAULT_CONFIG_PIPS
