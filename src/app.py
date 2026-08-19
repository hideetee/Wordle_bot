import streamlit as st

from wordle_bot.config import WordleConfig, load_config, save_config
from wordle_bot.database import WordleRepository
from wordle_bot.main import get_current_leaderboard, main
from wordle_bot.service import WordleBotService
from wordle_bot.utils import get_player_colors, plot_wordle_progress

st.set_page_config(page_title="Wordle Bot Dashboard", page_icon="🏆", layout="wide")
st.title("🏆 Wordle Bot Dashboard")

if "config" not in st.session_state:
    st.session_state.config = load_config()

# -----------------------------------------
# Settings Section
# -----------------------------------------
st.header("⚙️ Settings")

group_name_val = st.session_state.config.get("GROUP_NAME", "Wordle Golf")
group_name_send_val = st.session_state.config.get("GROUP_NAME_SEND", "Haidee UK (You)")

group_name_input = st.text_input("WhatsApp Group Name (Read from)", value=group_name_val, key="input_group_name")
group_send_input = st.text_input("WhatsApp Send-To Name", value=group_name_send_val, key="input_group_send")

if st.button("Save Settings"):
    st.session_state.config["GROUP_NAME"] = group_send_input or group_name_input
    st.session_state.config["GROUP_NAME_SEND"] = group_send_input
    save_config(st.session_state.config)
    st.success("Settings updated successfully!")

# -----------------------------------------
# Run Bot Section
# -----------------------------------------
st.header("🚀 Run Wordle Bot")

if st.button("Run Bot & Sync Scores"):
    with st.spinner("Connecting to WhatsApp and syncing scores..."):
        try:
            whatsapp = main(send_message=True)
            if whatsapp is not None:
                whatsapp.close()

            st.session_state.last_leaderboard = get_current_leaderboard(last_leaderboard=True)
            st.session_state.full_leaderboard = get_current_leaderboard(last_leaderboard=False)
            st.success("Scores synced and leaderboard updated successfully!")
        except Exception as e:
            st.error(f"Error running Wordle Bot: {e}")

# -----------------------------------------
# Show Leaderboard Section
# -----------------------------------------
st.header("📊 Current Leaderboard")

if "last_leaderboard" not in st.session_state:
    st.session_state.last_leaderboard = get_current_leaderboard(last_leaderboard=True)
if "full_leaderboard" not in st.session_state:
    st.session_state.full_leaderboard = get_current_leaderboard(last_leaderboard=False)

if st.session_state.last_leaderboard is not None and st.session_state.last_leaderboard.height > 0:
    st.subheader("Latest Week Summary")
    st.dataframe(st.session_state.last_leaderboard.to_pandas(), use_container_width=True)

    if st.session_state.full_leaderboard is not None and st.session_state.full_leaderboard.height > 0:
        players = st.session_state.full_leaderboard["player"].unique().to_list()
        player_colours = get_player_colors(players)

        st.subheader("📈 Leaderboard Progress Trends")
        col1, col2 = st.columns(2)
        with col1:
            st.pyplot(plot_wordle_progress(st.session_state.full_leaderboard, mode="score", colours=player_colours))
        with col2:
            st.pyplot(plot_wordle_progress(st.session_state.full_leaderboard, mode="rank", colours=player_colours))
else:
    st.info("No leaderboard data recorded yet. Click 'Run Bot & Sync Scores' to load initial data.")
