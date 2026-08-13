
import time
import re
from difflib import SequenceMatcher
from playwright.sync_api import sync_playwright, TimeoutError
# from playwright.async_api import async_playwright
from wordle_bot.utils import normalize, similarity
import tempfile

tmp_profile = tempfile.mkdtemp(prefix="chrome-profile") 

class WhatsAppClient:

    def __init__(self, group_name):
        self.playwright = sync_playwright().start()
        # self.user_data_dir = tmp_profile

        # self.context = self.playwright.chromium.launch_persistent_context(
        #     user_data_dir=self.user_data_dir,
        #     executable_path="/usr/bin/google-chrome",
        #     headless=False,
        #     args =[
        #         "--no-sandbox",
        #         "--disable-gpu",
        #         "--disable-dev-shm-usage",
        #         "--disable-infobars",
        #         "--disable-extensions",
        #     ]
        # )


        # ### 
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir="browser",
            executable_path="/usr/bin/google-chrome",
            headless=False
        )
        self.page = self.context.pages[0]
        self.page.goto("https://web.whatsapp.com")
        self.page.wait_for_timeout(5000)
        self.open_group(group_name)

        ### Async

        # self.context = await self.playwright.chromium.launch_persistent_context(
        #     user_data_dir=self.user_data_dir,
        #     executable_path="/usr/bin/google-chrome",
        #     headless=False
        # )

        # self.page = await self.context.new_page()
        # await self.page.goto("https://web.whatsapp.com")
        # await self.page.wait_for_timeout(5000)
        # await self.open_group(group_name)

    

    def close(self):
        try:
            self.context.close()
            self.playwright.stop()
        except Exception:
            pass


    # async def close(self):
    #     await self.context.close()
    #     await self.playwright.stop()

    def open_group(self, name):
        search = self.page.locator("input[type='text'][data-tab='3']")
        search.click()
        search.fill(name)
        self.page.wait_for_timeout(2000)
        search.press("Enter")
        self.page.wait_for_timeout(3000)

    def scroll_until_cutoff_and_store(self, cutoff_wordle_num):
        parsed_wordles = []
        seen = set()
        WORDLE_NUM = re.compile(r"Wordle\s+([\d,]+)", re.I)

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
                inner_text = element.inner_text()

                m = WORDLE_NUM.search(inner_text)
                if not m:
                    continue

                wordle_num = int(m.group(1).replace(",", ""))
                key = (sender, wordle_num)
                if key in seen:
                    continue
                seen.add(key)

                from wordle_bot.parser import WordleParser
                parsed_msg = WordleParser.parser_wordle_score([inner_text])
                parsed_wordles.append((sender, parsed_msg[0][1], parsed_msg[0][2]))

                if wordle_num <= cutoff_wordle_num:
                    found_cutoff = True

            if found_cutoff:
                break

            self.page.locator('div[data-testid="conversation-panel-messages"]').evaluate(
                "el => el.scrollBy(0, -2000)"
            )
            time.sleep(1)

        return parsed_wordles

    def message_sent(self, message):
        last_message = self.page.locator("[data-testid='msg-container']").last

        try:
            last_message.wait_for(timeout=1000)
        except TimeoutError:
            return False

        fail = last_message.locator("[data-testid='fail-container']").count()

        try:
            expected = normalize(message)
            actual = last_message.locator("span[data-testid='selectable-text']").inner_text()
            actual = normalize(actual)
        except Exception:
            return False

        score = similarity(expected, actual)
        return score >= 0.9 and fail == 0

    def send_message(self, message, max_retries=5, timeout=10):
        input_box = self.page.locator("[data-testid='conversation-compose-box-input']")
        time.sleep(1)

        for attempt in range(max_retries):
            if attempt == 0:
                input_box.wait_for(state="visible")
                input_box.click()
                input_box.fill("")
                input_box.fill(message)
                input_box.press("Enter")
            else:
                last_message = self.page.locator("[data-testid='msg-container']").last
                fail_button = last_message.locator("[data-testid='fail-container']")
                if fail_button.count() == 0:
                    if self.message_sent(message):
                        return True
                fail_button.click()

            deadline = time.time() + timeout
            while time.time() < deadline:
                if self.message_sent(message):
                    return True

                last_message = self.page.locator("[data-testid='msg-container']").last
                if last_message.locator("[data-testid='fail-container']").count():
                    break

                time.sleep(0.2)

        return False

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