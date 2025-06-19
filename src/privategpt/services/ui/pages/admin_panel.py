from __future__ import annotations

"""Admin Panel page – placeholder until backend endpoints are wired up."""

import streamlit as st
from pages_utils import initialize_session_state, require_auth, display_navigation_sidebar, APP_TITLE

st.set_page_config(page_title=f"Admin Panel – {APP_TITLE}", layout="wide", initial_sidebar_state="expanded")

initialize_session_state()
require_auth(admin_only=True)

display_navigation_sidebar(current_page="Admin Panel")

st.title("Admin Panel")

st.info("Admin settings and user management will appear here once implemented.") 