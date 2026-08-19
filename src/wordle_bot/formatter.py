from typing import Optional
import polars as pl


def format_weekly_score_table(df: pl.DataFrame) -> str:
    """
    Format the latest completed week's scores and ranks into an aligned WhatsApp ASCII table.
    """
    if df is None or df.height == 0:
        return "No weekly scores recorded."

    rows = df.to_dicts()
    lines = ["Player     Week     Score   Rank"]
    for r in rows:
        player = str(r["player"])[:8]
        week_start = r.get("week_start", "")
        week_end = r.get("week_end", "")
        score = r.get("score", "")
        rank = r.get("rank", "")
        lines.append(f"{player:8} {week_start:4} - {week_end:4} {score:5}  {rank:4}")

    return "\n".join(lines)


def format_overall_score_table(df: pl.DataFrame) -> str:
    """
    Format all-time cumulative scores and ranks into an aligned WhatsApp ASCII table.
    """
    if df is None or df.height == 0:
        return "No overall scores recorded."

    rows = df.to_dicts()
    lines = ["Player  AT Score  AT Rank"]
    for r in rows:
        player = str(r["player"])[:6]
        overall_score = f"{float(r.get('overall_score', 0.0)):.1f}"
        overall_rank = f"{float(r.get('overall_rank', 0.0)):.1f}"
        lines.append(f"{player:6} {overall_score:>10} {overall_rank:>8}")

    return "\n".join(lines)


def format_leaderboard_announcement(leaderboard_df: pl.DataFrame) -> str:
    """
    Construct the complete WhatsApp announcement message including weekly and overall tables.
    """
    weekly_table = format_weekly_score_table(leaderboard_df)
    overall_table = format_overall_score_table(leaderboard_df)

    return (
        "🏆 Wordle Leaderboard\n\n"
        "Weekly Scores\n"
        f"{weekly_table}\n\n"
        "Overall Scores\n"
        f"{overall_table}"
    )
