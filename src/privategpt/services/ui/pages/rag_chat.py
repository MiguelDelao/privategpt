from __future__ import annotations

"""RAG Chat page – placeholder until backend endpoints are wired up."""

import streamlit as st
from pages_utils import initialize_session_state, require_auth, display_navigation_sidebar, APP_TITLE

st.set_page_config(page_title=f"RAG Chat – {APP_TITLE}", layout="wide", initial_sidebar_state="expanded")

initialize_session_state()
require_auth()

display_navigation_sidebar(current_page="RAG Chat")

st.title("RAG Chat")

st.info("The Retrieval-Augmented Generation backend is not yet connected. This page will become interactive once the /rag service is available.") 