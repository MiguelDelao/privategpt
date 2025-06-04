"""
PrivateGPT Legal AI - Main Application Entry Point
Clean, extensible multi-page application with professional authentication
"""

import os
import time
import streamlit as st
import sys
from datetime import datetime
from utils.auth_client import AuthClient # Ensure this path is correct
from utils.logger import Logger # Ensure this path is correct
from pages_utils import (
    APP_TITLE, APP_SUBTITLE, VERSION_INFO,
    initialize_session_state,
    get_auth_client,
    get_logger,
    apply_page_styling
)

# Add parent directory to path to import pages_utils if pages_utils.py is in the root of pages/
# For a flat structure where pages_utils is in the same dir as app.py, this might not be needed
# Or if utils/ and pages_utils.py are directly under streamlit_app_directory/
# Assuming pages_utils.py and utils/ are in the same directory as app.py or correctly pathed.
# If pages_utils is in a subdirectory, the sys.path.append might be needed as it was before:
# sys.path.append(os.path.join(os.path.dirname(__file__), 'pages')) # If pages_utils is in 'pages' subdir

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

# Hide Streamlit style elements (optional, can be enabled if desired)
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden !important;}
footer {visibility: hidden !important;}
header {visibility: hidden !important;}
/* .stDeployButton {display: none !important;} */
/* .stAppDeployButton {display: none !important;} */
#stDecoration {display: none !important;}
/* .stDeployButtonContainer {display: none !important;} */
[data-testid="stToolbar"] {display: none !important;}
[data-testid="stDecoration"] {display: none !important;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

def display_login_page():
    """Display the login interface and handle authentication"""
    auth_client = get_auth_client()
    logger = get_logger()

    # Redirect if already authenticated
    if st.session_state.get("authenticated", False):
        st.switch_page("pages/dashboard.py") # Ensure this page exists
        return

    # --- Modernized Header ---
    st.markdown(
        f"""
        <div style="text-align: center; margin-top: 1rem; margin-bottom: 2rem;">
            <h1 style="font-size: 2.8em; color: #FFFFFF; border-bottom: none; margin-bottom: 0.2em;">
                🔑 {APP_TITLE}
            </h1>
            <p style="font-size: 1.2em; color: #B0B0D0;">{APP_SUBTITLE}</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

    # --- Login Form using st.form ---
    with st.form(key="login_form", border=False):
        st.markdown("<h3 style='text-align: center; margin-bottom: 1.5rem; color: #FFFFFF;'>Admin Login</h3>", unsafe_allow_html=True)
        
        email = st.text_input(
            label="Email Address",
            placeholder="Enter your email", 
            key="login_email_input",
            value=st.session_state.get("login_form_email", "admin@admin.com"),
            help="Use your registered email address."
        )
        password = st.text_input(
            label="Password",
            type="password", 
            placeholder="Enter your password", 
            key="login_password_input",
            value=st.session_state.get("login_form_password", "admin"),
            help="Enter the password associated with your email."
        )

        st.session_state.login_form_email = email
        st.session_state.login_form_password = password

        submitted = st.form_submit_button("➡️ Login", use_container_width=True, type="primary")

        if submitted:
            if not email or not password:
                st.error("📧 Email and 🔒 Password are required.")
            else:
                with st.spinner("Authenticating... ✨"):
                    try:
                        response = auth_client.login(email, password)
                        if response and response.get("access_token"):
                            st.session_state.authenticated = True
                            st.session_state.access_token = response["access_token"]
                            user_data = response.get("user", {})
                            st.session_state.user_email = user_data.get("email", email)
                            st.session_state.user_role = user_data.get("role", "user")
                            st.session_state.login_time = datetime.now()
                            
                            if "login_form_email" in st.session_state: del st.session_state.login_form_email
                            if "login_form_password" in st.session_state: del st.session_state.login_form_password
                            if "login_error_message" in st.session_state: del st.session_state.login_error_message

                            logger.log_user_login(user_email=email, success=True)
                            st.success("Login successful! Redirecting... 🚀")
                            time.sleep(1)
                            st.switch_page("pages/dashboard.py") # Ensure this page exists
                        else:
                            error_message = response.get("detail", "Invalid credentials or authentication failed.")
                            st.session_state.login_error_message = error_message
                            logger.log_user_login(user_email=email, success=False, error_message=error_message)
                    except Exception as e:
                        error_msg = f"Login request failed: {str(e)}"
                        st.session_state.login_error_message = error_msg
                        logger.log_user_login(user_email=email, success=False, error_message=error_msg)
    
    if "login_error_message" in st.session_state and st.session_state.login_error_message:
        st.error(st.session_state.login_error_message)
        if st.button("Dismiss error", key="dismiss_login_error", use_container_width=True):
            del st.session_state.login_error_message
            st.rerun()

    st.markdown(
        """
        <div style='text-align: center; margin-top: 2rem; color: #888; font-size: 0.9em;'>
            <p>Ensure all services are running. Contact support if you face issues.</p>
            <p style='font-size: 0.8em;'>Default credentials for demo: admin@admin.com / admin</p>
        </div>
        """, 
        unsafe_allow_html=True
    )
    st.caption(f"Version: {VERSION_INFO} | Environment: {os.getenv('ENVIRONMENT', 'development')}", unsafe_allow_html=False)

if __name__ == "__main__":
    display_login_page()

    if st.session_state.get("login_success_message"):
        st.success(st.session_state.login_success_message)
        del st.session_state.login_success_message 

    if st.session_state.get("authenticated"):
        st.switch_page("pages/dashboard.py") # Ensure this page exists 