# GameBot End-to-End Execution Flow

This document details the end-to-end architecture and code execution workflow of the GameBot application (supporting both Wordle and Pips).

---

## 1. Execution Architecture Diagram

```mermaid
flowchart TD
    subgraph Entrypoints["Entry Points"]
        UI["app.py (Streamlit Dashboard)"]
        CLI["main.py (CLI / Cron Script)"]
    end

    subgraph Config["Configuration & Initialization"]
        CFG["config.py<br/>load_config('wordle' | 'pips')"]
        SVC_INIT["GameBotService Initialization<br/>(WordleGame | PipsGame)"]
        REPO_INIT["GameRepository Initialization<br/>(SQLite scores_*.db)"]
    end

    subgraph Step1["Step 1: Scrape & Sync"]
        WAC["WhatsAppClient (Playwright)<br/>open_group(group_name)"]
        SCROLL["scroll_until_cutoff_and_store()<br/>Scrolls chat panel upwards"]
        PARSER["parser.py<br/>WordleParser / PipsParser"]
        CLEAN["scorer.py<br/>clean_and_fill_scores()<br/>(X -> penalty, fills gaps)"]
        SAVE_SCORES["database.py<br/>GameRepository.save_score_if_missing_or_7()"]
    end

    subgraph Step2["Step 2: Ranking & Leaderboard"]
        LOAD_SCORES["database.py<br/>GameRepository.load_scores()"]
        CALENDAR["calendar_utils.py<br/>CalendarUtils.get_unique_week_ranges()<br/>(Sunday - Saturday 7-day bounds)"]
        WEEKLY_RANK["scorer.py<br/>rank_weekly_scores()<br/>(Aggregate score & mean ties)"]
        RUNNING_LB["scorer.py<br/>calculate_running_leaderboard()<br/>(Cumulative score & rank)"]
        SAVE_LB["database.py<br/>GameRepository.save_leaderboard()"]
    end

    subgraph Step3["Step 3: Formatting & Delivery"]
        FMT["formatter.py<br/>format_leaderboard_announcement()"]
        SEND["WhatsAppClient.send_message()<br/>Post text to target group"]
        CLOSE["WhatsAppClient.close()<br/>Close browser context"]
    end

    UI -->|"Run Bot Button"| CLI
    CLI --> CFG
    CFG --> SVC_INIT
    SVC_INIT --> REPO_INIT
    SVC_INIT --> Step1
    Step1 --> Step2
    Step2 --> Step3

    WAC --> SCROLL
    SCROLL --> PARSER
    PARSER --> CLEAN
    CLEAN --> SAVE_SCORES

    SAVE_SCORES --> LOAD_SCORES
    LOAD_SCORES --> CALENDAR
    CALENDAR --> WEEKLY_RANK
    WEEKLY_RANK --> RUNNING_LB
    RUNNING_LB --> SAVE_LB

    SAVE_LB --> FMT
    FMT --> SEND
    SEND --> CLOSE
```

---

## 2. End-to-End Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Runner as main.py / app.py
    participant Service as GameBotService
    participant Browser as WhatsAppClient (Playwright)
    participant Parser as WordleParser / PipsParser
    participant Scorer as Game / scorer.py
    participant Calendar as CalendarUtils
    participant DB as GameRepository (SQLite)
    participant Formatter as formatter.py

    User->>Runner: Trigger run (CLI or Streamlit button)
    Runner->>Runner: load_config(game)
    Runner->>Service: GameBotService(game, repository, config)
    Runner->>Service: run(client, send_announcement)

    rect rgb(240, 248, 255)
    note over Service,DB: 1. Scrape & Sync Scores
    Service->>DB: get_latest_wordle_num()
    DB-->>Service: latest_wordle
    Service->>Browser: scroll_until_cutoff_and_store(cutoff)
    loop Upward chat scroll
        Browser->>Parser: parse_messages(chat_lines)
        Parser-->>Browser: List of (player, game_num, score)
    end
    Browser-->>Service: raw_messages
    Service->>Scorer: clean_and_fill_scores(raw_df, effective_start)
    Scorer-->>Service: cleaned_scores
    Service->>DB: save_score_if_missing_or_7(cleaned_scores)
    end

    rect rgb(245, 255, 245)
    note over Service,DB: 2. Process Weekly Rankings & Standings
    Service->>DB: load_scores(wordle_min=effective_start)
    DB-->>Service: scores_df
    Service->>DB: load_leaderboard(wordle_start=effective_start)
    DB-->>Service: existing_leaderboard
    Service->>Scorer: rank_weekly_scores(scores_df)
    Scorer->>Calendar: get_unique_week_ranges(game_numbers)
    Calendar-->>Scorer: [(week_start, week_end), ...]
    Scorer-->>Service: weekly_ranks
    Service->>Scorer: calculate_running_leaderboard(weekly_ranks)
    Scorer-->>Service: updated_leaderboard
    Service->>DB: save_leaderboard(table)
    end

    rect rgb(255, 250, 240)
    note over Service,Browser: 3. Announcement & Delivery
    Service->>Formatter: format_leaderboard_announcement(leaderboard_df)
    Formatter-->>Service: formatted announcement string
    opt send_announcement is True and group_name_send configured
        Service->>Browser: open_group(group_name_send)
        Service->>Browser: send_message(announcement_text)
        Browser-->>Service: sent status (True / False)
    end
    Service->>Browser: close()
    end

    Service-->>Runner: {"success": True, "message": text, "leaderboard": df}
    Runner-->>User: Display result / print announcement
```

---

## 3. Step-by-Step Execution Breakdown

### Phase 1: Initialization & Configuration
- **Entry Points**:
  - `src/app.py`: Interactive Streamlit dashboard allowing users to customize settings, trigger bot runs, and visualize leaderboard trends.
  - `src/main.py`: Headless command-line entrypoint.
- **Config Management** (`src/game_bot/config.py`):
  - `load_config(game)` reads `config_wordle.json` or `config_pips.json` with domain fallback defaults.
  - Dataclasses `WordleConfig` and `PipsConfig` store target chat names and start number limits.
- **Service & Repository Setup**:
  - `GameBotService` is instantiated with the corresponding `Game` strategy (`WordleGame` or `PipsGame`) and `GameRepository` (pointing to `scores_wordle.db` or `scores_pips.db`).

### Phase 2: Scraping & Syncing Scores (`scrape_and_sync_scores`)
- **Browser Automation** (`src/game_bot/whatsapp.py`):
  - Uses Playwright to launch a persistent Chromium context at `https://web.whatsapp.com`.
  - Searches and opens the WhatsApp reading group via `open_group()`.
- **Chat Scrolling & Cutoff Check**:
  - Queries `GameRepository.get_latest_wordle_num()` to find the most recent puzzle number in the database.
  - Repeatedly scrolls upward until messages preceding the cutoff puzzle number are loaded.
- **Message Parsing** (`src/game_bot/parser.py`):
  - Uses regex patterns to identify game headers (`Wordle <num> <score>/6` or `Pips #<num> <difficulty> <emoji> <time>`) and walks backward to locate the sender from WhatsApp timestamps.
- **Cleaning & Penalty Filling** (`src/game_bot/scorer.py`):
  - `clean_and_fill_scores()` converts failure `"X"` entries to penalty values (`7` for Wordle, `5` for Pips).
  - Cross-joins active players with the sequence of game numbers to fill unplayed intermediate days with penalties, while leaving the latest in-progress day as `None`.
- **Database Persistence** (`src/game_bot/database.py`):
  - `GameRepository.save_score_if_missing_or_7()` inserts newly discovered scores and overwrites penalty placeholders without clobbering valid historical entries.

### Phase 3: Weekly Rankings & Cumulative Standings (`process_and_update_leaderboards`)
- **Score Loading**:
  - Pulls historical score records from SQLite starting at `effective_start`.
- **Calendar Boundaries** (`src/game_bot/calendar_utils.py`):
  - Computes 7-day Sunday-to-Saturday competition weeks based on the game's anchor number and anchor weekday.
- **Weekly Score Aggregation & Ranking** (`src/game_bot/scorer.py`):
  - `compute_weekly_scores()` aggregates total scores per player, omitting incomplete trailing weeks.
  - `rank_weekly_scores()` assigns sequential ranks and handles score ties using mean ranking.
- **Running Leaderboard Accumulation**:
  - `calculate_running_leaderboard()` computes cumulative overall scores and overall ranks across consecutive weeks.
  - `GameRepository.save_leaderboard()` persists weekly leaderboard snapshots.

### Phase 4: Announcement Formatting & WhatsApp Dispatch
- **Message Formatting** (`src/game_bot/formatter.py`):
  - `format_leaderboard_announcement()` formats the latest week's results and overall standings into WhatsApp monospace text tables with trophies and headers.
- **WhatsApp Message Sending**:
  - If `send_announcement` is enabled, navigates to the announcement recipient group (`group_name_send`).
  - Dispatches the announcement text and verifies delivery via `send_message()`.
- **Teardown**:
  - Closes the Playwright browser session and SQLite database connection safely.
