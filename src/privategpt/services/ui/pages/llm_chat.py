from __future__ import annotations

"""LLM Chat page – placeholder until backend endpoints are wired up."""

import streamlit as st
from pages_utils import initialize_session_state, require_auth, display_navigation_sidebar, APP_TITLE

st.set_page_config(page_title=f"LLM Chat – {APP_TITLE}", layout="wide", initial_sidebar_state="expanded")

initialize_session_state()
require_auth()

display_navigation_sidebar(current_page="LLM Chat")

st.title("LLM Chat")

st.info("The LLM backend is not yet connected. This page will allow direct model chat once the /llm service is ready.") 