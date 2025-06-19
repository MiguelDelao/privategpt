from __future__ import annotations

"""Dashboard page placeholder for PrivateGPT UI (v2)."""

import streamlit as st
from pages_utils import initialize_session_state, require_auth, display_navigation_sidebar, APP_TITLE

st.set_page_config(page_title=f"Dashboard – {APP_TITLE}", layout="wide", initial_sidebar_state="expanded")

initialize_session_state()
require_auth()

display_navigation_sidebar(current_page="Dashboard")

st.title("Dashboard")
st.write("This is a placeholder dashboard.  Functionality will be added once the backend endpoints are ready.") 