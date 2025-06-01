"""
PrivateGPT Legal AI - Main Application Entry Point
Clean, extensible multi-page application with professional authentication
"""

import os
import time
import streamlit as st
import sys
from datetime import datetime
from utils.auth_client import AuthClient
from utils.logger import Logger
from pages_utils import (
    APP_TITLE, APP_SUBTITLE, VERSION_INFO,
    initialize_session_state,
    get_auth_client,
    get_logger,
    apply_page_styling
)

# Add parent directory to path to import pages_utils
sys.path.append(os.path.join(os.path.dirname(__file__), 'pages'))

# Page configuration for the login page
st.set_page_config(
    page_title=f"Login - {APP_TITLE}", 
    page_icon="🔑",
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# Apply global styling
apply_page_styling()

# Initialize session state
initialize_session_state()

# Hide Streamlit style elements
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stDeployButton {display: none;}
.css-1d391kg {padding-top: 0rem;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Custom CSS for professional appearance
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 1rem;
        text-align: center;
    }
    .legal-disclaimer {
        background-color: #fef2f2;
        border: 1px solid #fecaca;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
        color: #991b1b;
    }
</style>
""", unsafe_allow_html=True)

def display_login_page():
    """Display the login interface and handle authentication"""
    auth_client = get_auth_client()
    logger = get_logger()

    # Redirect if already authenticated
    if st.session_state.get("authenticated", False):
        st.switch_page("pages/dashboard.py")
        return

    st.markdown(f'<div style="text-align: center; margin-top: 2rem; margin-bottom: 1rem;">'
                f'<h1 style="font-size: 2.8em; color: #FFFFFF; border-bottom: none; margin-bottom: 0.2em;">🔒 {APP_TITLE}</h1>'
                f'<p style="font-size: 1.2em; color: #B0B0D0;">{APP_SUBTITLE}</p>'
                f'</div>', unsafe_allow_html=True)

    # Login Form
    # Using a more visually distinct container for the form
    with st.container(border=True):
        st.markdown("<h3 style='text-align: center; margin-bottom: 1.5rem; color: #FFFFFF;'>Admin Login</h3>", unsafe_allow_html=True)
        
        email = st.text_input(
            "Email Address", 
            placeholder="Enter your email", 
            key="login_email", 
            value=st.session_state.get("login_form_email", "admin@admin.com") # Pre-fill for convenience
        )
        password = st.text_input(
            "Password", 
            type="password", 
            placeholder="Enter your password", 
            key="login_password",
            value=st.session_state.get("login_form_password", "admin") # Pre-fill for convenience
        )

        st.session_state.login_form_email = email # Persist form value
        st.session_state.login_form_password = password

        if st.button("➡️ Login", use_container_width=True, type="primary"):
            if not email or not password:
                st.error("Email and password are required.")
            else:
                with st.spinner("Authenticating..."):
                    try:
                        response = auth_client.login(email, password)
                        if response and response.get("access_token"):
                            st.session_state.authenticated = True
                            st.session_state.access_token = response["access_token"]
                            st.session_state.user_email = response.get("user", {}).get("email", email)
                            st.session_state.user_role = response.get("user", {}).get("role", "user")
                            st.session_state.login_time = datetime.now() # For session duration tracking
                            
                            # Clear login form persisted values on success
                            if "login_form_email" in st.session_state: del st.session_state.login_form_email
                            if "login_form_password" in st.session_state: del st.session_state.login_form_password
                            if "login_error_message" in st.session_state: del st.session_state.login_error_message

                            logger.log_user_login(user_email=email, success=True)
                            st.success("Login successful! Redirecting...")
                            time.sleep(1)
                            st.switch_page("pages/dashboard.py")
                        else:
                            error_message = response.get("detail", "Invalid credentials or authentication failed.")
                            st.session_state.login_error_message = error_message # Store for display
                            logger.log_user_login(user_email=email, success=False, error_message=error_message)
                            st.error(error_message)
                    except Exception as e:
                        error_msg = f"Login request failed: {str(e)}"
                        st.session_state.login_error_message = error_msg
                        logger.log_user_login(user_email=email, success=False, error_message=error_msg)
                        st.error(error_msg)
        
        # Display persistent error message if any from previous attempts
        if "login_error_message" in st.session_state and st.session_state.login_error_message:
            if not (st.button("Dismiss error", key="dismiss_login_error", use_container_width=True)):
                 st.error(st.session_state.login_error_message)
            else:
                del st.session_state.login_error_message # Clear on dismiss
                st.rerun()

    st.markdown("<br><p style='text-align: center; color: #888;'>Ensure all services are running. Default: admin@example.com / admin</p>", unsafe_allow_html=True)

# --- Main script logic for app.py ---
if __name__ == "__main__":
    display_login_page()

    # Handle success message from other pages (like successful logout)
    if st.session_state.get("login_success_message"):
        st.success(st.session_state.login_success_message)
        st.session_state.login_success_message = None

    # Auto-redirect if already authenticated
    if st.session_state.get("authenticated"):
        st.switch_page("pages/dashboard.py") 