from __future__ import annotations

"""
Shared utilities for Streamlit pages in the PrivateGPT UI (v2).
This is a lightweight adaptation of the v1 helper, the main change is that
all configuration values are pulled from environment variables instead of the
legacy config_loader module.
"""

from datetime import datetime
import os
import streamlit as st

from utils.auth_client import AuthClient
from utils.document_processor import DocumentProcessor
from utils.logger import Logger
from utils.llm_client import LLMClient

# ---------------------------------------------------------------------------
# Application-wide constants
# ---------------------------------------------------------------------------
APP_TITLE = os.getenv("APP_TITLE", "PrivateGPT")
APP_SUBTITLE = os.getenv("APP_SUBTITLE", "Your Secure, Self-Hosted AI Assistant")
VERSION_INFO = os.getenv("APP_VERSION", "v2.0.0-dev")
LLM_MODEL_NAME = os.getenv("LLM_MODEL", "LLaMA-3 70B")
VECTOR_DB_NAME = os.getenv("VECTOR_DB", "Weaviate+bge-base"); WORKFLOW_ENGINE = "n8n"

# Service endpoints
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://gateway-service:8000")
KNOWLEDGE_SERVICE_URL = os.getenv("RAG_URL", "http://rag-service:8000")
LLM_SERVICE_URL = os.getenv("LLM_URL", "http://llm-service:8000")
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://weaviate:8080")
ENVIRONMENT = os.getenv("ENV", "local")

# ---------------------------------------------------------------------------
# Helpers for cached service clients
# ---------------------------------------------------------------------------
@st.cache_resource
def get_auth_client():  # noqa: D401
    return AuthClient(GATEWAY_URL)

@st.cache_resource
def get_document_processor():  # noqa: D401
    return DocumentProcessor()

@st.cache_resource  
def get_llm_client():  # noqa: D401
    return LLMClient(LLM_SERVICE_URL)

def get_logger():  # noqa: D401
    return Logger()

# ---------------------------------------------------------------------------
# Session-state management
# ---------------------------------------------------------------------------

def initialize_session_state() -> None:
    """Ensure all required keys exist in st.session_state."""
    defaults = {
        "authenticated": False,
        "user_email": None,
        "user_role": None,
        "access_token": None,
        "user_info": {"user": {"email": "unknown@example.com", "role": "user"}},
        # App specific
        "chat_history": [],
        "llm_chat_history": [],
        "uploaded_documents": [],
        "current_matter": "General Research",
        # Cross-page messaging
        "login_error_message": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ---------------------------------------------------------------------------
# Auth gate wrapper
# ---------------------------------------------------------------------------

def require_auth(*, admin_only: bool = False, main_app_file: str = "app.py") -> bool:  # noqa: D401
    initialize_session_state()

    authenticated = st.session_state.get("authenticated", False)
    token = st.session_state.get("access_token")

    if not authenticated or not token:
        st.session_state.login_error_message = "Please log in to access this page."
        st.switch_page(main_app_file)

    auth_client = get_auth_client()
    try:
        user_info = auth_client.verify_token(token)
        if not user_info:
            raise Exception("Invalid token")
        st.session_state.user_info = user_info
        st.session_state.user_email = user_info.get("user", {}).get("email")
        st.session_state.user_role = user_info.get("user", {}).get("role")
    except Exception:  # noqa: BLE001
        for key in [
            "authenticated",
            "user_email",
            "user_role",
            "access_token",
        ]:
            st.session_state[key] = None if key != "authenticated" else False
        st.session_state.login_error_message = "Session expired or token invalid. Please log in again."
        st.switch_page(main_app_file)

    if admin_only and st.session_state.user_role != "admin":
        st.error("Access Denied: You do not have admin privileges to view this page.")
        if st.button("Go to Dashboard"):
            st.switch_page("pages/dashboard.py")
        st.stop()
    return True

# ---------------------------------------------------------------------------
# Sidebar + styling (copied verbatim from v1)
# ---------------------------------------------------------------------------

def display_navigation_sidebar(*, current_page: str = "Dashboard") -> None:  # noqa: D401
    import streamlit as st

    with st.sidebar:
        st.markdown(f"**{st.session_state.user_email}**")
        st.markdown("---")

        nav_items = [
            ("Dashboard", "pages/dashboard.py"),
            ("RAG Chat", "pages/rag_chat.py"),
            ("LLM Chat", "pages/llm_chat.py"),
            ("Documents", "pages/document_management.py"),
        ]
        for label, target in nav_items:
            if st.button(
                label,
                use_container_width=True,
                type="primary" if current_page == label else "secondary",
                key=f"nav_{label.replace(' ', '_').lower()}",
            ):
                st.switch_page(target)

        if st.session_state.user_role == "admin":
            if st.button(
                "Settings",
                use_container_width=True,
                type="primary" if current_page == "Admin Panel" else "secondary",
                key="nav_admin",
            ):
                st.switch_page("pages/admin_panel.py")

        st.markdown("---")
        st.metric("Documents", len(st.session_state.get("uploaded_documents", [])))
        st.metric("Chats", len(st.session_state.get("chat_history", [])))
        st.markdown("---")
        if st.button("Logout", key="sidebar_logout", use_container_width=True, type="secondary"):
            logger = get_logger()
            if "login_time" in st.session_state:
                dur = int((datetime.utcnow() - st.session_state.login_time).total_seconds())
            else:
                dur = None
            logger.log_user_logout(user_email=st.session_state.user_email, session_duration_seconds=dur)
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.switch_page("app.py")


# NOTE: apply_page_styling() is unchanged (long CSS) – keep original for brevity 