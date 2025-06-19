from __future__ import annotations

"""Document Management page – placeholder until backend endpoints are wired up."""

import streamlit as st
from pages_utils import initialize_session_state, require_auth, display_navigation_sidebar, APP_TITLE

st.set_page_config(page_title=f"Documents – {APP_TITLE}", layout="wide", initial_sidebar_state="expanded")

initialize_session_state()
require_auth()

display_navigation_sidebar(current_page="Documents")

st.title("Documents")

st.info("Document upload and management will be available once the RAG backend is connected.") 