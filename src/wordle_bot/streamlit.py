import streamlit as st
from wordle_bot.utils import load_config, save_config

st.title("Wordle Bot Settings")

config = load_config()

group_name = st.text_input("WhatsApp Group Name", config["GROUP_NAME"])
group_name_send = st.text_input("Send-To Name", config["GROUP_NAME_SEND"])

if st.button("Save Settings"):
    config["GROUP_NAME"] = group_name
    config["GROUP_NAME_SEND"] = group_name_send
    save_config(config)
    st.success("Settings updated!")
