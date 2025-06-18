from __future__ import annotations

"""Simple Streamlit UI for login via Auth service."""

import os
import requests
import streamlit as st

AUTH_BASE = os.getenv("AUTH_URL", "http://auth-service:8000/auth")

st.title("PrivateGPT – Login")

if "token" not in st.session_state:
    st.session_state.token = None

with st.form("login_form"):
    email = st.text_input("Email", value="", placeholder="user@example.com")
    password = st.text_input("Password", type="password")
    submitted = st.form_submit_button("Login")

    if submitted:
        try:
            resp = requests.post(
                f"{AUTH_BASE}/login",
                json={"email": email, "password": password},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                st.session_state.token = data["access_token"]
                st.success("Logged in!")
            else:
                st.error(f"Login failed: {resp.status_code} {resp.text}")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Error: {exc}")

if st.session_state.token:
    st.write("Current token:")
    st.code(st.session_state.token) 