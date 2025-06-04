"""
Admin Dashboard for PrivateGPT Legal AI
Provides user management and system overview for administrators.
"""

import streamlit as st
from streamlit.web.server.server import Server

# Assuming pages_utils.py and auth_client.py are in ../utils or accessible via path
# For robust imports, especially when pages are in a subdirectory:
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from utils.auth_client import AuthClient
    from pages_utils import apply_page_styling, hide_streamlit_style, show_sidebar
except ImportError: # Fallback for direct execution/testing if path isn't set up
    from docker.streamlit.utils.auth_client import AuthClient
    from docker.streamlit.pages_utils import apply_page_styling, hide_streamlit_style, show_sidebar


def display_admin_dashboard():
    """Main function to display the admin dashboard page."""
    st.set_page_config(
        page_title="Admin Dashboard - PrivateGPT Legal AI",
        page_icon="🔒",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    apply_page_styling()
    hide_streamlit_style()
    show_sidebar()

    if not st.session_state.get("authenticated"):
        st.warning("Please log in to access this page.")
        # Force a re-run, which should trigger redirect in main app.py if login is enforced there
        # For a direct redirect, if running as a standalone page (less common for multipage):
        # st.switch_page("app.py") # Or your main login page
        st.stop()

    auth_client: Optional[AuthClient] = st.session_state.get("auth_client")
    user_info = st.session_state.get("user_info")

    if not auth_client or not user_info:
        st.error("Session not properly initialized. Please log in again.")
        st.stop()

    if user_info.get("role") != "admin":
        st.error("Access Denied: You do not have permission to view this page.")
        st.image("https://http.cat/403", caption="Access Denied", use_column_width=True)
        st.stop()

    st.title("🔑 Admin Dashboard")
    st.markdown("---_---")
    st.subheader("Welcome, Administrator!")
    
    st.markdown("This dashboard provides tools for user management and system monitoring.")

    # Placeholder for future content
    st.info("User management features and system metrics will be displayed here soon.")

    # Example: Display User Info (already available for the admin)
    with st.expander("Your Admin User Details", expanded=False):
        st.write(user_info)
    
    # Logout button (standard for all pages)
    if st.sidebar.button("Logout", key="admin_logout"):
        st.session_state.authenticated = False
        st.session_state.user_info = None
        st.session_state.token = None
        st.session_state.auth_client = None # Clear auth_client
        st.toast("Logged out successfully!", icon="👋")
        # Trigger a re-run to navigate to the login page (handled by app.py)
        # For multipage apps, st.rerun() is often used if the main app handles redirection.
        # Or explicitly switch:
        if 'current_page' in st.session_state:
            st.session_state.current_page = 'login' 

        # Check if Server.instance() exists before trying to call _on_pages_changed
        # This is a workaround for potential issues with st.rerun() in multipage apps
        # or when st.switch_page is preferred for more direct control.
        server = Server.instance_if_exists()
        if server:
            server._on_pages_changed.send() # Force sidebar update for page switching
        st.rerun()


if __name__ == "__main__":
    # This block is for potential direct execution of the page for testing (less common in multipage apps)
    # For multipage apps, ensure session_state is initialized similarly to how app.py would do it.
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False # Default to not authenticated
        st.session_state.user_info = None
        st.session_state.token = None
        st.session_state.auth_client = None
        # For testing, you might mock these:
        # st.session_state.authenticated = True
        # st.session_state.user_info = {"email": "admin@example.com", "role": "admin"}
        # st.session_state.auth_client = AuthClient("http://localhost:8001") # Mock client
        
    display_admin_dashboard() 