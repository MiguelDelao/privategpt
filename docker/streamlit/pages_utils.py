"""
Shared utilities for PrivateGPT Legal AI pages
Contains common functions, authentication, and session state management
"""

import os
import streamlit as st
from datetime import datetime
from utils.auth_client import AuthClient
from utils.logger import Logger
from utils.document_processor import DocumentProcessor

# --- Application Constants ---
APP_TITLE = "PrivateGPT Legal AI Suite"
APP_SUBTITLE = "Your Secure, Self-Hosted Legal AI Assistant"
LLM_MODEL_NAME = "LLaMA-3 70B (Quantized GGUF Q4_K_M)"
VECTOR_DB_NAME = "Weaviate with bge-base-en-v1.5 embeddings"
WORKFLOW_ENGINE = "n8n"
VERSION_INFO = "Version 2.5 - Polished Interface"

# Configuration
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://weaviate:8080")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Initialize services
@st.cache_resource
def get_auth_client():
    return AuthClient(AUTH_SERVICE_URL)

@st.cache_resource
def get_document_processor():
    return DocumentProcessor()

def get_logger():
    """Get logger instance"""
    return Logger()

def initialize_session_state():
    """Initialize essential session state variables"""
    # Authentication status
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "user_role" not in st.session_state:
        st.session_state.user_role = None
    if "access_token" not in st.session_state:
        st.session_state.access_token = None
    if "user_info" not in st.session_state:
        st.session_state.user_info = {"user": {"email": "unknown@example.com", "role": "user"}}
    
    # App-specific data
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "llm_chat_history" not in st.session_state:
        st.session_state.llm_chat_history = []
    if "uploaded_documents" not in st.session_state:
        st.session_state.uploaded_documents = []
    if "current_matter" not in st.session_state:
        st.session_state.current_matter = "General Research"
    
    # For passing messages between pages
    if "login_error_message" not in st.session_state:
        st.session_state.login_error_message = None

def require_auth(admin_only=False, main_app_file="app.py"):
    """
    Checks if a user is authenticated and authorized for the current page.
    If not, redirects to the login page.
    This should be called at the top of every authenticated page script.
    
    Args:
        admin_only (bool): If True, also checks if the user has an 'admin' role.
        main_app_file (str): The filename of the main application script (login page).
    """
    initialize_session_state()

    authenticated = st.session_state.get("authenticated", False)
    token = st.session_state.get("access_token")

    if not authenticated or not token:
        st.session_state.login_error_message = "Please log in to access this page."
        st.switch_page(main_app_file)

    # Verify token is still valid
    auth_client = get_auth_client()
    try:
        user_info = auth_client.verify_token(token)
        if not user_info:
            raise Exception("Invalid token")
        # Update session state with fresh user info
        st.session_state.user_info = user_info  # Set the complete user_info object
        st.session_state.user_email = user_info.get("user", {}).get("email", st.session_state.user_email)
        st.session_state.user_role = user_info.get("user", {}).get("role", st.session_state.user_role)
    except Exception:
        # Token is invalid, clear auth state and redirect
        st.session_state.authenticated = False
        st.session_state.user_email = None
        st.session_state.user_role = None
        st.session_state.access_token = None
        st.session_state.login_error_message = "Session expired or token invalid. Please log in again."
        st.switch_page(main_app_file)

    # Check for admin role if required
    if admin_only:
        if st.session_state.get("user_role") != "admin":
            st.error("Access Denied: You do not have admin privileges to view this page.")
            if st.button("Go to Dashboard"):
                st.switch_page("pages/dashboard.py")
            st.stop()
    
    return True

def display_navigation_sidebar(current_page="Dashboard"):
    """Display custom navigation sidebar with logout functionality"""
    with st.sidebar:
        st.markdown("### 🏢 PrivateGPT Legal AI")
        st.markdown("---")
        
        # User info
        st.caption(f"**{st.session_state.user_email}**")
        st.caption(f"Role: {st.session_state.user_role.title()}")
        
        st.markdown("---")
        st.markdown("### 📋 Navigation")
        
        # Dashboard
        if st.button("🏠 Dashboard", 
                    use_container_width=True, 
                    key="nav_dashboard",
                    type="primary" if current_page == "Dashboard" else "secondary"):
            st.switch_page("pages/dashboard.py")
            
        # RAG Chat
        if st.button("💬 RAG Chat", 
                    use_container_width=True, 
                    key="nav_rag_chat",
                    type="primary" if current_page == "RAG Chat" else "secondary"):
            st.switch_page("pages/rag_chat.py")
            
        # LLM Chat
        if st.button("🤖 LLM Chat", 
                    use_container_width=True, 
                    key="nav_llm_chat",
                    type="primary" if current_page == "LLM Chat" else "secondary"):
            st.switch_page("pages/llm_chat.py")
            
        # Document Management
        if st.button("📂 Documents", 
                    use_container_width=True, 
                    key="nav_documents",
                    type="primary" if current_page == "Documents" else "secondary"):
            st.switch_page("pages/document_management.py")
        
        # Admin Panel (only for admins)
        if st.session_state.user_role == "admin":
            if st.button("🛠️ Admin Panel", 
                        use_container_width=True, 
                        key="nav_admin",
                        type="primary" if current_page == "Admin Panel" else "secondary"):
                st.switch_page("pages/admin_panel.py")
        
        st.markdown("---")
        
        # Quick Stats
        st.markdown("### 📊 Quick Stats")
        docs_count = len(st.session_state.get("uploaded_documents", []))
        chat_count = len(st.session_state.get("chat_history", []))
        st.metric("Documents", docs_count)
        st.metric("Chat Messages", chat_count)
        
        st.markdown("---")
        
        # Logout
        if st.button("🚪 Logout", key="sidebar_logout", use_container_width=True, type="secondary"):
            # Log logout with session duration
            logger = get_logger()
            if 'login_time' in st.session_state:
                session_duration = int((datetime.now() - st.session_state.login_time).total_seconds())
            else:
                session_duration = None
                
            logger.log_user_logout(
                user_email=st.session_state.user_email,
                session_duration_seconds=session_duration
            )
            
            # Clear all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            # Go back to login
            st.switch_page("app.py")
        
        st.markdown("---")
        st.caption(VERSION_INFO)

def apply_page_styling():
    """Apply consistent styling across all pages"""
    
    # New friendly dark theme styling
    st.markdown(f"""
        <style>
            /* --- Base & Typography --- */
            body {{
                font-family: 'Inter', sans-serif;
                color: #EEEEEE; /* Main text color */
                background-color: #222831; /* Main background */
            }}

            .stApp {{
                background-color: #222831; /* Main background for Streamlit app container */
            }}

            h1, h2, h3, h4, h5, h6 {{
                color: #FFFFFF; /* Pure white for headers */
                font-weight: 600;
            }}

            h1 {{
                font-size: 2.2em;
                border-bottom: 2px solid #393E46; /* Secondary accent for border */
                padding-bottom: 0.3em;
                margin-bottom: 0.7em;
            }}

            h2 {{
                font-size: 1.8em;
                margin-top: 1.5em;
                margin-bottom: 0.6em;
            }}

            h3 {{
                font-size: 1.4em;
                margin-top: 1.2em;
                margin-bottom: 0.5em;
            }}

            p, .stMarkdown, .stText {{
                color: #EEEEEE; /* Main text color for paragraphs */
                line-height: 1.6;
            }}

            a {{
                color: #76ABAE; /* Softer teal for links */
            }}
            a:hover {{
                color: #00ADB5; /* Brighter teal on hover */
            }}

            /* --- Streamlit Specific Components --- */
            .stButton>button {{
                border: 2px solid #393E46; /* Secondary accent for border */
                background-color: #393E46; /* Secondary accent for button background */
                color: #EEEEEE; /* Main text color for button text */
                padding: 0.5em 1em;
                border-radius: 8px;
                font-weight: 500;
                transition: background-color 0.3s ease, border-color 0.3s ease;
            }}
            .stButton>button:hover {{
                background-color: #00ADB5; /* Primary accent on hover */
                border-color: #00ADB5; /* Primary accent border on hover */
                color: #FFFFFF;
            }}
            .stButton>button:focus {{
                outline: none;
                box-shadow: 0 0 0 3px rgba(0, 173, 181, 0.5); /* Primary accent focus ring */
            }}
            
            /* Primary button style */
            .stButton>button[kind="primary"] {{
                background-color: #00ADB5; /* Primary accent */
                border-color: #00ADB5; 
                color: #FFFFFF;
            }}
            .stButton>button[kind="primary"]:hover {{
                background-color: #007A7F; /* Darker shade of primary accent for hover */
                border-color: #007A7F;
            }}
            
            .stTextInput>div>div>input, .stTextArea textarea, .stSelectbox>div>div {{
                background-color: #3A4049; /* Custom input background */
                color: #EEEEEE; /* Main text color for input text */
                border-radius: 8px;
                border: 1px solid #393E46; /* Secondary accent border */
            }}
            
            .stTextInput>div>div>input:focus, .stTextArea textarea:focus {{
                 border: 1px solid #00ADB5; /* Primary accent border on focus */
                 box-shadow: 0 0 0 3px rgba(0, 173, 181, 0.3);
            }}

            .stSidebar {{
                background-color: #2A3038; /* Slightly different dark shade for sidebar */
                border-right: 1px solid #393E46; /* Secondary accent border */
            }}
            
            .stSidebar [data-testid="stMarkdownContainer"] h3 {{
                 color: #FFFFFF;
                 font-size: 1.2em;
                 margin-top: 0.8em;
                 margin-bottom: 0.4em;
            }}
            
            .stSidebar [data-testid="stMarkdownContainer"] p, .stSidebar .stCaption {{
                 color: #B0B0D0; /* Keeping a slightly muted color for sidebar secondary text */
            }}
            
            .stMetric {{
                background-color: #2A3038; /* Card background for metrics */
                border-radius: 8px;
                padding: 1em;
                border: 1px solid #393E46; /* Secondary accent border */
            }}
            .stMetric label {{
                color: #A0A0C0; /* Muted label color for metrics */
            }}
            .stMetric .stMetricValue {{
                color: #FFFFFF;
            }}

            /* Custom class for main headers in pages */
            .main-header {{
                font-size: 2.5em;
                color: #FFFFFF;
                font-weight: 700;
                padding-bottom: 0.2em;
                margin-bottom: 0.3em;
                text-align: left;
            }}
            .sub-header {{
                font-size: 1.1em;
                color: #B0B0D0; /* Muted sub-header color */
                margin-bottom: 2em;
                text-align: left;
            }}
            
            /* --- General Layout --- */
            [data-testid="stHorizontalBlock"] {{
                gap: 1rem; /* Add gap between columns */
            }}

            /* --- Dataframes --- */
            .stDataFrame {{
                border: 1px solid #393E46; /* Secondary accent border */
                border-radius: 8px;
            }}
            
            /* Remove default Streamlit footer */
            footer {{
                visibility: hidden;
            }}
            
            /* For containers to have a slight card look */
            [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] > [data-testid="stBlock"] > div:has(>[data-testid="stVerticalBlock"]), 
            [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] > [data-testid="stExpander"] {{
                background-color: #2A3038; /* Card background */
                padding: 1rem;
                border-radius: 8px;
                margin-bottom: 1rem;
                border: 1px solid #393E46; /* Secondary accent border */
            }}
            
        </style>
        <!-- Link to Google Fonts for 'Inter' -->
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">

    """, unsafe_allow_html=True)

    # You can add more specific page styling or adjustments here if needed
    pass 