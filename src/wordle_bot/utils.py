import matplotlib.pyplot as plt
import polars as pl


def plot_wordle_progress(df, mode="score"):
    """
    mode = "score" → plot overall_score
    mode = "rank"  → plot overall_rank
    """

    plt.figure(figsize=(10, 6))
    ax = plt.gca()

    summary_rows = []

    for player in df['player'].unique():
        player_scores = df.filter(pl.col("player") == player)

        # Plot depending on mode
        if mode == "score":
            plt.plot(
                player_scores['week_start'],
                player_scores['overall_score'],
                marker='o',
                label=player
            )
        else:  # mode == "rank"
            plt.plot(
                player_scores['week_start'],
                player_scores['overall_rank'],
                marker='o',
                label=player
            )

        # Get the latest row (max week_start)
        latest = player_scores.sort("week_start", descending=True).head(1)

        summary_rows.append({
            "player": player,
            "week_start": latest["week_start"][0],
            "week_end": latest["week_end"][0],
            "score": latest["score"][0],
            "AT_score": latest["overall_score"][0],
            "rank": latest["rank"][0],
            "AT_rank": latest["overall_rank"][0]
        })

    # Convert summary rows to a DataFrame
    summary_df = pl.DataFrame(summary_rows)

    # Sort depending on mode
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

    # Title for the annotation box
    summary_title = (
        f"Wordle week {summary_df['week_start'].max()} - "
        f"{summary_df['week_end'].max()}"
    )

    summary_text = summary_title + "\n" + "\n".join(summary_lines)

    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)

    # Bottom-right, nudged slightly left/up
    ax.text(
        0.95, 0.1,
        summary_text,
        transform=ax.transAxes,
        fontsize=10,
        ha='right',
        va='bottom',
        bbox=props
    )

    plt.legend()
    plt.title(title)
    plt.xlabel("Wordle Week Start")
    plt.ylabel(ylabel)
    plt.tight_layout()
    plt.show()
