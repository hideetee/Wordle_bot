from unittest.mock import MagicMock
import polars as pl
import pytest

from wordle_bot.config import WordleConfig
from wordle_bot.database import WordleRepository
from wordle_bot.service import WordleBotService


@pytest.fixture
def mock_repo(tmp_path):
    db_file = tmp_path / "test_service.db"
    return WordleRepository(str(db_file))


def test_service_scrape_and_sync_scores(mock_repo):
    service = WordleBotService(repository=mock_repo)

    mock_client = MagicMock()
    # Mock return from scroll_until_cutoff_and_store
    mock_client.scroll_until_cutoff_and_store.return_value = [
        ("Alice", 1870, "3"),
        ("Bob", 1870, "4"),
        ("Alice", 1871, "X"),
    ]

    scores_df = service.scrape_and_sync_scores(mock_client)
    assert scores_df.height == 4  # Alice & Bob across 1870 and 1871

    # Alice 1871 converted to 7
    alice_1871 = scores_df.filter((pl.col("player") == "Alice") & (pl.col("wordle_num") == 1871))
    assert alice_1871["score"][0] == 7


def test_service_run_workflow(mock_repo):
    config = WordleConfig(group_name="Test Group", group_name_send="Test Send")
    service = WordleBotService(repository=mock_repo, config=config)

    # Pre-populate 1 full complete week
    mock_client = MagicMock()
    complete_week_scores = []
    for day in range(1870, 1877):
        complete_week_scores.append(("Alice", day, "3"))
        complete_week_scores.append(("Bob", day, "4"))

    mock_client.scroll_until_cutoff_and_store.return_value = complete_week_scores
    mock_client.send_message.return_value = True

    result = service.run(client=mock_client, send_announcement=True)

    assert result["success"] is True
    assert result["sent"] is True
    assert "🏆 Wordle Leaderboard" in result["message"]
    mock_client.open_group.assert_called_with("Test Send")
    mock_client.send_message.assert_called_once()
