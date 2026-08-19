import streamlit as st
from wordle_bot.utils import get_player_colors, load_config, save_config, plot_wordle_progress
from wordle_bot.main import main, get_current_leaderboard 
from wordle_bot.whatsapp import WhatsAppClient
# import asyncio

st.title("Wordle Bot Dashboard")

if "config" not in st.session_state:
    st.session_state.config = load_config()

# -----------------------------------------
# Session State Setup
# -----------------------------------------

if "leaderboard" not in st.session_state:
    st.session_state.leaderboard = None

# -----------------------------------------
# Settings
# -----------------------------------------
st.header("Settings")

# DEFAULT_CONFIG = config.copy()


if "config" not in st.session_state:
    st.session_state.config = config.copy()

st.text_input(
    "WhatsApp Group Name",
    key="GROUP_NAME"
)

st.text_input(
    "Send-To Name",
    key="GROUP_NAME_SEND"
)


if st.button("Save Settings"):
    # Copy widget values into config
    st.session_state.config["GROUP_NAME"] = st.session_state.GROUP_NAME
    st.session_state.config["GROUP_NAME_SEND"] = st.session_state.GROUP_NAME_SEND
    save_config(st.session_state.config)
    st.success("Settings updated!")

# -----------------------------------------
# Run Bot
# -----------------------------------------
st.header("Run Wordle Bot")

if st.button("Run Bot"):
    st.write("Running bot…")

    whatsapp = main()

    # Load leaderboard into session state
    last_lb = get_current_leaderboard(last_leaderboard=True)
    st.session_state.last_leaderboard = last_lb

    full_lb = get_current_leaderboard(last_leaderboard=False)
    st.session_state.full_leaderboard = full_lb

    # Close browser safely
    if whatsapp is not None:
        whatsapp.close()

    st.success("Updated and loaded data!")

# -----------------------------------------
# Show Leaderboard
# -----------------------------------------
if "last_leaderboard" not in st.session_state:
    st.session_state.last_leaderboard = get_current_leaderboard(last_leaderboard=True)
if "full_leaderboard" not in st.session_state:
    st.session_state.full_leaderboard = get_current_leaderboard(last_leaderboard=False)


players = st.session_state.full_leaderboard["player"].unique()

if "player_colours" not in st.session_state:
    st.session_state.player_colours = get_player_colors(players)
                                                        
# Print ONLY the last leaderboard
st.header("Last Leaderboard")
st.dataframe(st.session_state.last_leaderboard)

# Plot using FULL leaderboard
st.header("Leaderboard Progress")

st.pyplot(plot_wordle_progress(st.session_state.full_leaderboard, mode="score", colours=st.session_state.player_colours))
st.pyplot(plot_wordle_progress(st.session_state.full_leaderboard, mode="rank", colours=st.session_state.player_colours))





