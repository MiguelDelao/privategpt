"""
PrivateGPT Legal AI - Main Application Entry Point
Clean, extensible multi-page application with professional authentication
"""

import os
import time
import streamlit as st
from datetime import datetime
from utils.auth_client import AuthClient
from utils.compliance_logger import ComplianceLogger
from pages_utils import (
    APP_TITLE, APP_SUBTITLE, VERSION_INFO,
    initialize_session_state,
    get_auth_client,
    get_compliance_logger
)

# Page configuration for the login page
st.set_page_config(
    page_title=f"Login - {APP_TITLE}", 
    page_icon="⚖️",
    layout="centered", 
    initial_sidebar_state="collapsed"
)

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

def display_login_form():
    """Display the login form and handle login logic"""
    st.markdown('<div class="main-header">⚖️ PrivateGPT Legal AI</div>', unsafe_allow_html=True)
    st.subheader(APP_SUBTITLE)
    st.markdown("---")

    # Legal disclaimer
    st.markdown("""
    <div class="legal-disclaimer">
        <strong>Legal Disclaimer:</strong> This AI assistant is designed to assist legal professionals 
        with research and document analysis. All AI-generated content should be reviewed by qualified 
        attorneys. This tool does not constitute legal advice and should not be relied upon as such.
    </div>
    """, unsafe_allow_html=True)

    st.header("🔐 Authentication Required")

    # Display any login error messages
    if st.session_state.login_error_message:
        st.error(st.session_state.login_error_message)
        st.session_state.login_error_message = None

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="admin@lawfirm.com or lawyer1@lawfirm.com", key="login_email")
        password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
        submitted = st.form_submit_button("Login", type="primary", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Email and password are required.")
            else:
                auth_client = get_auth_client()
                compliance_logger = get_compliance_logger()
                
                try:
                    with st.spinner("Authenticating..."):
                        token_response = auth_client.login(email, password)
                    
                    # Login successful, update session state
                    st.session_state.authenticated = True
                    st.session_state.access_token = token_response["access_token"]
                    st.session_state.user_email = email
                    st.session_state.user_role = token_response.get("user_role", "user")
                    st.session_state.login_time = datetime.now()
                    
                    # Log successful login
                    compliance_logger.log_user_login(
                        user_email=email,
                        success=True,
                        ip_address="localhost"  # In production, get real IP
                    )
                    
                    st.success("✅ Login successful! Redirecting to dashboard...")
                    time.sleep(1)  # Brief pause for user feedback
                    st.switch_page("pages/dashboard.py")
                    
                except Exception as e:
                    # Log failed login attempt
                    compliance_logger.log_user_login(
                        user_email=email,
                        success=False,
                        ip_address="localhost"
                    )
                    # Also log the specific error
                    compliance_logger.log_error(
                        user_email=email,
                        error_message=str(e),
                        error_type="authentication"
                    )
                    st.error(f"❌ Login failed: {str(e)}")

    st.info("Demo credentials: admin@lawfirm.com / lawyer1@lawfirm.com")
    st.caption(VERSION_INFO)

# --- Main script logic for app.py ---
if __name__ == "__main__":
    # Check if user is already authenticated
    if st.session_state.get("authenticated", False) and st.session_state.get("access_token"):
        auth_client = get_auth_client()
        try:
            user_info = auth_client.verify_token(st.session_state.access_token)
            if user_info:
                # Already logged in and token is valid, redirect to dashboard
                st.switch_page("pages/dashboard.py")
            else:
                # Token is invalid, clear auth state and show login with error
                st.session_state.authenticated = False
                st.session_state.access_token = None
                st.session_state.user_email = None
                st.session_state.user_role = None
                st.session_state.login_error_message = "Your session has expired. Please log in again."
                display_login_form()
        except Exception:
            # Token verification failed, clear auth state
            st.session_state.authenticated = False
            st.session_state.access_token = None
            st.session_state.user_email = None
            st.session_state.user_role = None
            st.session_state.login_error_message = "Session expired. Please log in again."
            display_login_form()
    else:
        # Not authenticated, show login form
        display_login_form()

    # Handle success message from other pages (like successful logout)
    if st.session_state.get("login_success_message"):
        st.success(st.session_state.login_success_message)
        st.session_state.login_success_message = None

    # Auto-redirect if already authenticated
    if st.session_state.get("authenticated"):
        st.switch_page("pages/dashboard.py") 