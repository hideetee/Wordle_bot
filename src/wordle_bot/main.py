# Use env scoring_bot to run this script


import polars as pl
from wordle_bot.database import Database_wordle
from wordle_bot.parser import WordleParser
from wordle_bot.scorer import ScoreCalculator
from wordle_bot.whatsapp import WhatsAppClient
from wordle_bot.utils import DATABASE, load_config
import streamlit as st

def get_current_leaderboard(last_leaderboard=False):
 
    database = Database_wordle(DATABASE)

    current_leaderboard = database.load_leaderboard(last_leaderboard=last_leaderboard)

    return current_leaderboard



def main():

    # config = load_config()
    # GROUP_NAME = config["GROUP_NAME"]
    # GROUP_NAME_SEND = config["GROUP_NAME_SEND"]

    GROUP_NAME = st.session_state.config["GROUP_NAME"]
    GROUP_NAME_SEND = st.session_state.config["GROUP_NAME_SEND"]

    database = Database_wordle(DATABASE)
    whatsapp = WhatsAppClient(GROUP_NAME)

    print("=== START BOT RUN ===")

    # 1. SCRAPE NEW MESSAGES
    latest = database.get_latest_wordle_num()
    cutoff = latest - 1 if latest is not None else None
    print(f"Latest in DB before scrape: {latest}, cutoff={cutoff}")

    messages = whatsapp.scroll_until_cutoff_and_store(cutoff)
    print(f"Scraped {len(messages)} new messages")

    # 2. CLEAN + SAVE NEW SCORES
    df = pl.DataFrame(messages, schema=["player", "wordle_num", "score"], orient = "row")
    cleaned = ScoreCalculator.score_cleaner(df)
    database.save_score_if_missing_or_7(cleaned)

    # 3. RELOAD SCORES AFTER SAVING
    scores_df = database.load_scores()
    latest = database.get_latest_wordle_num()
    print(f"Latest in DB after saving: {latest}")

    # 4. COMPUTE WEEK RANGE LIMIT
    calc_limit = ScoreCalculator.store_week_ranges(pl.DataFrame({"wordle_num": [latest]}))[0][0]
    print(f"calc_limit={calc_limit}")

    # 5. SELECT SCORES FOR CURRENT WEEK 
    if latest >= calc_limit:
        scores_recent = scores_df.filter(pl.col('wordle_num') >= calc_limit)
    # else:
    #     scores_recent = scores_df.filter(pl.col('wordle_num') == pl.col('wordle_num').max())
    else:
        print(f"Latest wordle_num {latest} is less than calc_limit {calc_limit}. No scores for current week.")


    print(f"Scores in current week: {scores_recent.shape[0]}")

    # Check if leaderboard exists
    leaderboard = database.load_leaderboard()
    if len(leaderboard) == 0:
        # Create leaderboard using all scores if it doesn't exist
        print("Leaderboard does not exist. Creating leaderboard using all scores.")
        weekly_scores_all = ScoreCalculator.week_ranking(scores_df)
        leaderboard_all = ScoreCalculator.running_ranking(
            weekly_scores_all,
            interest="overall_score",
            database=database
        )
        print(leaderboard_all[-1])

        for table in leaderboard_all:
            print(f"Saving week {table['week_start'][0]}–{table['week_end'][0]}")
            database.save_leaderboard(table)

    else: 
        print("Leaderboard exists. Proceeding with current week scores.")
    # 6. WEEKLY + OVERALL RANKING
        week_scores = ScoreCalculator.week_ranking(scores_recent)
        leaderboard_recent = ScoreCalculator.running_ranking(
            week_scores,
            interest="overall_score",
            database=database
        )

    if leaderboard_recent == []:
        print("No complete leaderboard. Loading last saved leaderboard.")
        latest_leaderboard = database.load_leaderboard(last_leaderboard=True)
    else:
        latest_leaderboard = leaderboard_recent[-1]


    # 9. FORMAT MESSAGE
    weekly_scores = whatsapp.df_to_whatsapp_score_rank(latest_leaderboard)
    overall_scores = whatsapp.df_to_whatsapp_overall_score_rank(latest_leaderboard)

    message = (
        "🏆 Wordle Leaderboard\n\n"
        "Weekly Scores\n"
        f"{weekly_scores}\n\n"
        "Overall Scores\n"
        f"{overall_scores}"
    )

    print("=== MESSAGE TO SEND ===")
    print(message)

    # 10. SEND
    whatsapp.open_group(GROUP_NAME_SEND)
    whatsapp.send_message(message)

    print("=== END BOT RUN ===")

    return whatsapp


if __name__ == "__main__":
    main()
