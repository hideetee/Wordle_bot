from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional
import matplotlib.pyplot as plt
import polars as pl

from wordle_bot.config import (
    BASE_DIR,
    DATABASE_PATH,
    DEFAULT_CONFIG,
    WordleConfig,
    get_database_path,
    load_config,
    save_config,
)

# For backward compatibility
DATABASE = str(get_database_path())


# ==============================
# PLOTTING UTILITIES
# ==============================


def get_player_colors(players: List[str]) -> Dict[str, tuple]:
    """Return a consistent color map for a list of players."""
    cmap = plt.get_cmap("tab20")
    return {
        player: cmap(i % cmap.N)
        for i, player in enumerate(players)
    }


def plot_wordle_progress(
    df: pl.DataFrame,
    mode: str = "score",
    colours: Optional[Dict[str, tuple]] = None,
):
    """
    Plot overall Wordle progress over time.
    mode = "score" → plot overall_score
    mode = "rank"  → plot overall_rank
    """
    if df is None or df.height == 0:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.set_title("No Data Available")
        return plt

    if colours is None:
        colours = get_player_colors(df["player"].unique().to_list())

    plt.figure(figsize=(10, 6))
    ax = plt.gca()

    summary_rows = []

    for player in df["player"].unique():
        player_scores = df.filter(pl.col("player") == player)

        if mode == "score":
            plt.plot(
                player_scores["week_start"],
                player_scores["overall_score"],
                marker="o",
                color=colours[player],
                label=player,
            )
        else:
            plt.plot(
                player_scores["week_start"],
                player_scores["overall_rank"],
                marker="o",
                color=colours[player],
                label=player,
            )

        latest = player_scores.sort("week_start", descending=True).head(1)

        summary_rows.append({
            "player": player,
            "week_start": latest["week_start"][0],
            "week_end": latest["week_end"][0],
            "score": latest["score"][0],
            "AT_score": latest["overall_score"][0],
            "rank": latest["rank"][0],
            "AT_rank": latest["overall_rank"][0],
        })

    summary_df = pl.DataFrame(summary_rows)

    if mode == "score":
        summary_df = summary_df.sort("AT_score", descending=False)
        summary_lines = [
            f"{row['player']} - Score: {row['score']}, AT_score: {row['AT_score']}"
            for row in summary_df.to_dicts()
        ]
        ylabel = "Overall Score"
        title = "Overall Score by Player"
    else:
        summary_df = summary_df.sort("AT_rank", descending=False)
        summary_lines = [
            f"{row['player']} - Rank: {row['rank']}, AT_rank: {row['AT_rank']}"
            for row in summary_df.to_dicts()
        ]
        ylabel = "Overall Rank"
        title = "Overall Rank by Player"

    summary_title = (
        f"Wordle week {summary_df['week_start'].max()} - "
        f"{summary_df['week_end'].max()}"
    )

    summary_text = summary_title + "\n" + "\n".join(summary_lines)
    props = dict(boxstyle="round", facecolor="wheat", alpha=0.5)

    ax.text(
        0.95,
        0.1,
        summary_text,
        transform=ax.transAxes,
        fontsize=10,
        ha="right",
        va="bottom",
        bbox=props,
    )

    plt.legend()
    plt.title(title)
    plt.xlabel("Wordle Week Start")
    plt.ylabel(ylabel)
    plt.tight_layout()
    return plt


# ==============================
# STRING & TEXT UTILITIES
# ==============================


def normalize(text: str) -> str:
    """Normalize multiline text by stripping whitespace and removing empty lines."""
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def similarity(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings using SequenceMatcher."""
    return SequenceMatcher(None, a, b).ratio()
