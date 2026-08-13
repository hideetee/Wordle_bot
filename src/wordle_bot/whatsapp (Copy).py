# Use env scoring_bot to run this script

from itertools import count
from pyexpat.errors import messages
from re import search
import re
import sqlite3
from unicodedata import name
from datetime import datetime
from wordle_bot.database import Database_wordle as DW
from wordle_bot.parser import WordleParser as WP
import time
from wordle_bot.scorer import ScoreCalculator as SC
import polars as pl
from playwright.sync_api import TimeoutError
from difflib import SequenceMatcher
from wordle_bot.utils import GROUP_NAME, DATABASE, CHECK_INTERVAL




from playwright.sync_api import sync_playwright

import wordle_bot.leaderboard as leaderboard









# ==============================
# WHATSAPP
# ==============================


class WhatsApp:


    def __init__(self, group_name):

        
        self.playwright = sync_playwright().start()

        # Use installed browser
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir="browser",
            # executable_path="/usr/bin/chromium",
            executable_path="/usr/bin/google-chrome",
            headless=False
        )


        self.page = self.context.pages[0]


        self.page.goto(
            "https://web.whatsapp.com"
        )


        print(
        """
        Waiting for WhatsApp login...

        Scan QR code if required.
        """
        )


        self.page.wait_for_timeout(
            5000
        )


        self.open_group(
            group_name
        )



    def open_group(self, name):

        print(
            f"Opening {name}"
        )


        # search = self.page.wait_for_selector("[aria-label='Search or start a new chat']")
        search = self.page.locator("input[type='text'][data-tab='3']")
        search.click()
        search.fill(name)

        print('Connected to WhatsApp. Waiting for group to load...')


        self.page.wait_for_timeout(
            3000
        )

        
        search.press(
            "Enter"
        )
        print(f"Opened group: {name}")


        self.page.wait_for_timeout(
            5000
        )



    def scroll_until_cutoff_and_store(self, cutoff_wordle_num):
            
        """
        Scroll through the chat and store parsed until a message with a Wordle number less than or equal to cutoff_wordle_num is found.
        """

        parsed_wordles = []
        seen = set()

        print(f"Scrolling until Wordle number {cutoff_wordle_num} is found...")

        WORDLE_NUM = re.compile(r"Wordle\s+([\d,]+)", re.I)

        # extra_scrape_done = False

        while True:
    
            elements = self.page.locator("div.copyable-text")                  

            count = elements.count()
            found_cutoff = False

            for i in range(count):
                element = elements.nth(i)
                raw = element.get_attribute("data-pre-plain-text")

                if raw is None:
                    continue

                sender = raw.split(']')[-1].split(': ')[0].strip()[0]
                print(f'this is the sender: {sender}')
                inner_text = elements.nth(i).inner_text()
                print(f'this is the inner element: {inner_text}')
                
                m = WORDLE_NUM.search(inner_text)
                if not m:
                    continue
                    
                # Normalize commas
                wordle_num = int(m.group(1).replace(",", ""))

                # Skip duplicates
                key = (sender, wordle_num)
                if key in seen:
                    continue
                seen.add(key)

                # Print every detected Wordle number
                print(f"Detected Wordle number: {wordle_num}")

                parsed_msg = WP.parser_wordle_score([inner_text])

                new_tuple = [(sender, parsed_msg[0][1], parsed_msg[0][2])]

                parsed_wordles.extend(new_tuple)

                if wordle_num <= cutoff_wordle_num:
                    print(f'Reached cutoff Wordle number {wordle_num}. Stopping scroll.')
                    found_cutoff = True
                    
    
            if found_cutoff:
                break

            self.page.locator('div[data-testid="conversation-panel-messages"]').evaluate("el => el.scrollBy(0, -2000)"
)
 
            time.sleep(1)
        return parsed_wordles


    @staticmethod
    def normalize(text):
        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if line]  # remove empty lines
        return "\n".join(lines)

    @staticmethod
    def similarity(a, b):
        """
        Function to calculate similarity between two strings using SequenceMatcher. 
        Returns a float between 0 and 1, where 1 means the strings are identical.
        This is so we can check if the message sent was recieved but with a less strict form.
        """
        return SequenceMatcher(None, a, b).ratio()
        
    def message_sent(self, message):

        first_line = message.splitlines()[0]

        last_message = self.page.locator("[data-testid='msg-container']").last

        print("=" * 40)
        print("Checking latest message...")

        try:
            last_message.wait_for(timeout=1000)
        except TimeoutError:
            print("No latest message")
            return False

        print("Message text:")
        print(repr(last_message.inner_text()))

        fail = last_message.locator("[data-testid='fail-container']").count()
        print("Fail containers:", fail)

        try:
            expected = self.normalize(message)
            actual = last_message.locator(
                "span[data-testid='selectable-text']"
            ).inner_text()
            actual = self.normalize(actual)
        except Exception as e:
            print(e)
            return False

        print("Expected:", repr(expected))
        print("Actual:", repr(actual))

        score = self.similarity(expected, actual)

        return score >= 0.9 and fail == 0


    def send_message(self,message, max_retries = 5, timeout= 10):

        input_box = self.page.locator(
        "[data-testid='conversation-compose-box-input']"
        )

        time.sleep(1) # Wait for the input box to be ready

        last = self.page.locator("[data-testid='msg-container']").last

        print("Lastest message:")
        print(last.inner_text())

        print("Has fail:",
              last.locator("[data-testid='fail-container']").count())
        


        for attempt in range(max_retries):

            print(f"Sending message (attempt {attempt+1}/{max_retries})")

            # First attempt types the message
            if attempt == 0:
                input_box.wait_for(state="visible")
                input_box.click()
                input_box.fill("")
                input_box.fill(message)
                input_box.press("Enter")


            # Later attempts click the failed message
            else:
                last_message = self.page.locator("[data-testid='msg-container']").last
                fail_button = last_message.locator("[data-testid='fail-container']")

                if fail_button.count() == 0:
                    if self.message_sent(message):
                        print("Message delivered.")
                        return True
                                
                print("Retrying...")
                fail_button.click()

            deadline = time.time() + timeout

            while time.time() < deadline:

                # Successfully sent?
                if self.message_sent(message):
                    print("Message delivered.")
                    return True

                # # Failed?
                last_message = self.page.locator("[data-testid='msg-container']").last
                if last_message.locator("[data-testid='fail-container']").count():
                    print("Message failed")
                    break
                print("Waiting for send confirmation, retrying...")
                print(repr(last_message.inner_text()))

                time.sleep(0.2)

            print("Giving up after retries.")
            return False

        # sleep(30000)

        
     


    # ==============================
    # CONVERT TO WHATSAPP-FRIENDLY FORMAT
    # ==============================

    @staticmethod
    def df_to_whatsapp_score_rank(df):
        rows = df.to_dicts()
        lines = ["Player     Week     Score   Rank"]
        for r in rows:
            lines.append(
                f"{r['player']:6} {r['week_start']:4} - {r['week_end']:4} {r['score']:5}  {r['rank']:4}"
            )
        return "\n".join(lines)

    @staticmethod
    def df_to_whatsapp_overall_score_rank(df):
        rows = df.to_dicts()
        lines = ["Player  AT Score  AT Rank"]
        for r in rows:
            lines.append(
                f"{r['player']:6} {r['overall_score']:10} {r['overall_rank']:8}"
            )
        return "\n".join(lines)



# ==============================
# MAIN BOT
# ==============================


def main():


    database = DW(DATABASE)


    latest = database.get_latest_wordle_num()
    cutoff = latest - 1 if latest is not None else None  # 1 less than the latest because it immediately stops once it sees the first Wordle_num = latest.    
    if latest is not None:
        print(f"Latest Wordle number in database: {latest}")
            # self.get_messages()  # Initial fetch to clear old messages
    else:
        print("No Wordle numbers found in database, scrape all messages.")
            # self.get_messages()  # Initial fetch to clear old messages

    whatsapp = WhatsApp(GROUP_NAME)

    parser = WP()
    
    # processed = set()

    print(
        "Bot running..."
    )

    
    
    while True:

        # Scroll until cutoff Wordle number is found and scrape detected messages
        messages = whatsapp.scroll_until_cutoff_and_store(cutoff_wordle_num=cutoff)


        new_scores_df = pl.DataFrame(messages, schema=["player", "wordle_num", "score"], orient="row")
        cleaned_scores = SC.score_cleaner(new_scores_df)
        database.save_score_if_missing_or_7(cleaned_scores)

        scores_df = database.load_scores()

        # #limit the number of calculations to the store week range inclusive of the latest wordle number in the database
        calc_limit = SC.store_week_ranges(pl.DataFrame({"wordle_num": [latest]}))[0][0]
        # print(f'calc_limit: {calc_limit}')

        if latest >= calc_limit:
            scores_recent = scores_df.filter(pl.col('wordle_num') >= calc_limit)
        else:
            scores_recent = scores_df.tail(8)

        week_scores = SC.week_ranking(scores_recent)

        leaderboard_recent = SC.running_ranking(week_scores, interest="overall_score", database=database)

        most_recent_wordle_num = scores_recent.select(pl.col("wordle_num")).max().item()

        # Remove incomplete leaderboards from the list of leaderboards to save
        leaderboard_recent = [table 
                              for table in leaderboard_recent
                              if most_recent_wordle_num >= table['week_end'][0]]
        if not leaderboard_recent:
            leaderboard_recent = [database.load_leaderboard(last_leaderboard=True)]
        else:
            for table in leaderboard_recent:
            #     week_ending = table['week_end'][0]
                # if most_recent_wordle_num >= week_ending:

                database.save_leaderboard(table)

    
        break
        # time.sleep(CHECK_INTERVAL)

    
    weekly_scores = WhatsApp.df_to_whatsapp_score_rank(leaderboard_recent[-1])
    # print(f'{weekly_score} \n')

    overall_scores = WhatsApp.df_to_whatsapp_overall_score_rank(leaderboard_recent[-1])
    # # print(f'{weekly_rank} \n')

    message = (
        f"🏆 Wordle Leaderboard\n\n"  +
        f'Weekly Scores\n' +
        f"{weekly_scores}\n\n" +
        f'Overall Scores\n' +
        f"{overall_scores}"
    )
    # message = 'test'

    print(message)

    whatsapp.open_group('Haidee UK (You)')

    whatsapp.send_message(message)




    #     time.sleep(
    #         CHECK_INTERVAL
    #     )


if __name__ == "__main__":

    main()