# Wordle Bot 🏆

A Python application and automated bot designed to track, score, and manage **Wordle Golf** competitions within WhatsApp group chats. 

The bot uses **Playwright** to scrape Wordle results shared in WhatsApp, parses and cleans scores using **Polars**, maintains a persistent **SQLite** database, computes weekly and running overall leaderboards, and provides an interactive **Streamlit** dashboard with progress visualizations.

---

## 🌟 Features

* **Automated WhatsApp Scraping**: Log in to WhatsApp Web and dynamically scrape Wordle results directly from your target group chat.
* **Smart Wordle Parsing**: Extract Wordle numbers and scores (e.g., `Wordle 1,234 3/6` or `X/6` for fails) and map sent scores to specific players.
* **Wordle Golf Scoring Engine**:
  * Groups daily Wordle scores into 7-day Wordle weeks (Sunday–Saturday).
  * Automatically fills missing/failed days with penalty scores (`7`).
  * Computes weekly ranks and tracks cumulative running scores (`AT_score`) and overall ranks (`AT_rank`).
* **Persistent SQLite Database**: Stores raw player scores and finalized weekly leaderboard records in `scores.db`.
* **WhatsApp Reporting**: Automatically formats clean ASCII text leaderboards and posts them back into the specified WhatsApp group.
* **Streamlit Dashboard**:
  * Manage WhatsApp group settings dynamically.
  * Trigger bot updates with a single click.
  * View current leaderboard tables.
  * Visualize player progression over time with Matplotlib progress charts (Rank & Score trends).

---

## 📁 Repository Structure

```text
Wordle_bot/
├── pyproject.toml              # Package configuration & metadata
├── src/
│   ├── app.py                  # Streamlit Web UI Dashboard
│   └── wordle_bot/
│       ├── __init__.py         # Package public exports
│       ├── calendar_utils.py   # Wordle week calculation & date-anchor logic
│       ├── config.json         # WhatsApp group name configuration
│       ├── config.py           # Configuration helpers & domain constants
│       ├── database.py         # Database repository (WordleRepository)
│       ├── formatter.py        # WhatsApp ASCII tables & announcement formatter
│       ├── main.py             # Main CLI entry point & execution flow
│       ├── models.py           # Typed domain dataclasses
│       ├── parser.py           # Wordle score regex parser (WordleParser)
│       ├── scorer.py           # Scoring logic & ranking calculations
│       ├── service.py          # WordleBotService orchestration workflow
│       ├── utils.py            # Plotting, text normalization & helper functions
│       └── whatsapp.py         # WhatsApp Web automation via Playwright (WhatsAppClient)
└── tests/                      # Pytest unit test suite
    ├── test_calendar.py
    ├── test_compute_weekly_score.py
    ├── test_config.py
    ├── test_database.py
    ├── test_formatter.py
    ├── test_parser_wordle_score.py
    ├── test_score_cleaner.py
    ├── test_scorer.py
    ├── test_service.py
    ├── test_week_ranking.py
    └── test_wordle_week.py
```

---

## 🚀 Prerequisites & Installation

### 1. Requirements
* Python 3.9+
* Google Chrome or Chromium (managed by Playwright)

### 2. Dependencies
Install the required Python libraries:

```bash
pip install polars playwright streamlit matplotlib pytest
```

Install Playwright Chromium browser binaries:

```bash
playwright install chromium
```

Alternatively, install `wordle_bot` in editable mode:

```bash
pip install -e .
```

---

## ⚙️ Configuration

Update `src/wordle_bot/config.json` with the exact names of your WhatsApp target group:

```json
{
    "GROUP_NAME": "Your Wordle WhatsApp Group",
    "GROUP_NAME_SEND": "Your Wordle WhatsApp Group"
}
```

* **`GROUP_NAME`**: The WhatsApp group to scrape Wordle results from.
* **`GROUP_NAME_SEND`**: The WhatsApp group to send leaderboard updates to.

---

## 🖥️ Usage

### 1. Running the Streamlit Dashboard (Recommended)

To launch the web interface:

```bash
streamlit run src/app.py
```

From the dashboard you can:
* Edit and save WhatsApp group configurations.
* Click **Run Bot** to scrape new messages and update the leaderboard.
* View the latest leaderboard tables and visual progress plots.

### 2. Running via Command Line / Main Script

To run the bot directly:

```bash
python -m wordle_bot.main
```

> **Note**: On the first run, Playwright will open a Chromium window loading WhatsApp Web. You will need to scan the QR code with your phone to authenticate your WhatsApp session.

---

## 🧪 Running Unit Tests

Execute `pytest` to run the test suite:

```bash
pytest
```

---

## 👤 Author

* **Haidee Tang** ([Haidee.Tang95@gmail.com](mailto:Haidee.Tang95@gmail.com))
