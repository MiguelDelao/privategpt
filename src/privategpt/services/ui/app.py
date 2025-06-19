from __future__ import annotations

"""
PrivateGPT – Streamlit UI login page (v2).
Adapted from the v1 implementation but without the legacy config_loader
dependency.  Only Auth endpoints are currently functional; navigation after
login goes to the new dashboard page placeholder.
"""

import os
import time
from datetime import datetime

import streamlit as st

from utils.auth_client import AuthClient
from utils.logger import Logger
from pages_utils import (
    APP_TITLE,
    initialize_session_state,
    get_auth_client,
    get_logger,
)

# ---------------------------------------------------------------------------
# Streamlit page config & styling
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title=f"{APP_TITLE} - Login",
    page_icon="🔐",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Big block of CSS/JS for styling removed for brevity – keep original design

# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

initialize_session_state()

auth_client = get_auth_client()
logger = get_logger()

if st.session_state.get("authenticated", False):
    st.switch_page("pages/dashboard.py")
    st.stop()

st.title(APP_TITLE)

with st.form(key="login_form", clear_on_submit=False):
    email = st.text_input("Email", value=st.session_state.get("login_form_email", "admin@admin.com"))
    password = st.text_input("Password", type="password", value=st.session_state.get("login_form_password", "admin"))
    submitted = st.form_submit_button("Sign In", type="primary")

    if submitted:
        if not email or not password:
            st.error("Please enter both email and password.")
        else:
            with st.spinner("Signing in..."):
                try:
                    resp = auth_client.login(email, password)
                    if resp and resp.get("access_token"):
                        st.session_state.authenticated = True
                        st.session_state.access_token = resp["access_token"]
                        user_data = resp.get("user", {})
                        st.session_state.user_email = user_data.get("email", email)
                        st.session_state.user_role = user_data.get("role", "user")
                        st.session_state.login_time = datetime.utcnow()
                        # Clear temp form values
                        for k in ["login_form_email", "login_form_password", "login_error_message"]:
                            st.session_state.pop(k, None)
                        logger.log_user_login(user_email=email, success=True)
                        st.switch_page("pages/dashboard.py")
                    else:
                        err = resp.get("detail", "Invalid credentials.")
                        st.session_state.login_error_message = err
                        logger.log_user_login(user_email=email, success=False, error_message=err)
                except Exception as exc:  # noqa: BLE001
                    err = str(exc)
                    st.session_state.login_error_message = err
                    logger.log_user_login(user_email=email, success=False, error_message=err)

if err_msg := st.session_state.get("login_error_message"):
    st.error(err_msg)
    if st.button("Dismiss", key="dismiss_login_error"):
        st.session_state.pop("login_error_message", None)
        st.rerun() 