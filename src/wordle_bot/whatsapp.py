# Use env scoring_bot to run this script

from email.mime import text
from itertools import count
from pyexpat.errors import messages
from re import search
import re
import sqlite3
from unicodedata import name
from datetime import datetime


from playwright.sync_api import sync_playwright

import wordle_bot.leaderboard as leaderboard



# ==============================
# CONFIGURATION
# ==============================

GROUP_NAME = "Wordle Golf"   # <-- CHANGE THIS
DATABASE = "scores.db"

CHECK_INTERVAL = 5



# class WhatsApp:

#     def __init__(self):

#         self.playwright = sync_playwright().start()

#         self.browser = self.playwright.chromium.launch_persistent_context(
#             user_data_dir="browser",
#             headless=False
#         )

#         self.page = self.browser.new_page()

#         self.page.goto("https://web.whatsapp.com")

#         search = self.page.locator("div[contenteditable='true']").first

#         search.click()

#         search.fill("Wordle Golf")

#         messages = self.page.locator("div.copyable-text")

#         count = messages.count()

#         print(count)

#         for i in range(count):

#             print(messages.nth(i).inner_text())

#         seen_messages = set()

#         messages.get_attribute("data-id")

#         search.press("Enter")



# ==============================
# WHATSAPP
# ==============================


class WhatsApp:


    def __init__(self):

        self.playwright = sync_playwright().start()


        # self.context = (
        #     self.playwright
        #     .chromium
        #     .launch_persistent_context(

        #         user_data_dir="browser",

        #         headless=False

        #     )
        # )

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
            10000
        )


        self.open_group(
            GROUP_NAME
        )



    def open_group(self, name):

        print(
            f"Opening {name}"
        )


        search = self.page.wait_for_selector("[aria-label='Search or start a new chat']")
        search.click()
        search.fill(name)


        self.page.wait_for_timeout(
            3000
        )

        
        search.press(
            "Enter"
        )

        # print("NOT pressing Enter")


        self.page.wait_for_timeout(
            5000
        )


    def get_messages(self):

        messages = []


        print("Searching for messages...")

        # elements = self.page.locator(
        #     "div.copyable-text"
        # )    
        # 

        elements = self.page.locator(
            'span[data-testid="selectable-text"]',
            has_text="Wordle"
            ).first  



        count = elements.count()

        print(f"Found {count} messages")


        for i in range(count):

            element = elements.nth(i)


            try:

                text = (
                    element
                    .text_content()
                )

                sender = (
                    element
                    .get_attribute(
                    "data-pre-plain-text"
                    )
                )

                # Comment out when done testing, this is just for debugging
                print("\nNEW MESSAGE")
                print("------------------------")
                print(f"Sender: {sender}")
                print(text)
                print("------------------------")

                if text and "Wordle" in text:
                    print(">>> WORDLE FOUND <<<")

                messages.append(
                {

                    "text": text.strip(),

                    "sender": sender

                })
                
                
            except:

                print(f"Error reading message {i}: {e}")

        print(f"\nReturning {len(messages)} Wordle messages")     


        return messages



    def send_message(self,message):

        box = (
            self.page
            .locator(
            "footer div[contenteditable='true']"
            )
        )


        box.fill(
            message
        )


        box.press(
            "Enter"
        )




# ==============================
# WORDLE PARSER
# ==============================


class WordleParser:


    pattern = re.compile(
        r"Wordle\s+([\d,\s]+)\s+([1-6X])/6",
        re.I
    )

    @staticmethod
    def parse(message):

        result = WordleParser.pattern.search(message)


        if result:

            return {

                "wordle":
                    int(result.group(1)),


                "score":
                    result.group(2)

            }


        return None


# ==============================
# HELPER FUNCTIONS
# ==============================


def extract_sender(header):

    if not header:

        return "Unknown"


    # Example:
    #
    # [12:30, 13/07/2026] Alice:


    result = re.search(
        r"\]\s*(.*?):",
        header
    )


    if result:

        return result.group(1)


    return "Unknown"



def create_leaderboard(rows):

    if not rows:

        return "No scores yet."


    text = (
        "🏆 Wordle Leaderboard\n\n"
    )


    medals = [
        "🥇",
        "🥈",
        "🥉"
    ]


    for i,row in enumerate(rows):

        player = row[0]

        average = row[1]


        if i < 3:

            prefix = medals[i]

        else:

            prefix = f"{i+1}."


        text += (
            f"{prefix} {player}: "
            f"{average:.2f}\n"
        )


    return text


# ==============================
# CONVERT TO WHATSAPP-FRIENDLY FORMAT
# ==============================

def df_to_whatsapp_score_rank(df):
    rows = df.to_dicts()
    lines = ["Player     Week     Score   Rank"]
    for r in rows:
        lines.append(
            f"{r['player']:6} {r['week_start']:4} - {r['week_end']:4} {r['score']:5}  {r['rank']:4}"
        )
    return "\n".join(lines)

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


    database = Database()


    whatsapp = WhatsApp()


    parser = WordleParser()


    processed = set()


    print(
        "Bot running..."
    )


    while True:


        messages = (
            whatsapp
            .get_messages()
        )


        for message in messages:


            key = (
                message["sender"],
                message["text"]
            )


            if key in processed:

                continue


            processed.add(key)



            result = (
                parser
                .parse(
                    message["text"]
                )
            )


            if result:


                player = extract_sender(
                    message["sender"]
                )

                # player = "Test_Player"


                print(
                    player,
                    result
                )


                database.save_score(

                    player,

                    result["wordle"],

                    result["score"]

                )

                # # For real use, send the leaderboard to WhatsApp. 
                # board = create_leaderboard(

                #     database.leaderboard()

                # )


                # whatsapp.send_message(
                #     board
                # )


                # for testing, just print in terminal
                leaderboard = create_leaderboard(database.leaderboard())

                print("\n============================")
                print("LEADERBOARD")
                print("============================")
                print(leaderboard)
                print("============================\n")


        time.sleep(
            CHECK_INTERVAL
        )


if __name__ == "__main__":

    main()