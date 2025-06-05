"""
Admin Dashboard for PrivateGPT Legal AI
Modern admin interface with system overview and user management access.
"""

import streamlit as st
from streamlit.web.server.server import Server
import sys
import os
import requests
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from utils.auth_client import AuthClient
    from pages_utils import apply_page_styling, hide_streamlit_style, show_sidebar
except ImportError:
    from docker.streamlit.utils.auth_client import AuthClient
    from docker.streamlit.pages_utils import apply_page_styling, hide_streamlit_style, show_sidebar


def display_admin_dashboard():
    """Main function to display the admin dashboard page."""
    st.set_page_config(
        page_title="Admin Dashboard - PrivateGPT Legal AI",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # --- ChatGPT Style CSS ---
    st.markdown("""<style>
        /* General Styles */
        body {
            font-family: 'Söhne', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Ubuntu', 'Cantarell', 'Noto Sans', 'sans-serif', 'Helvetica Neue', 'Arial', 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji';
            color: #ECECF1;
        }
        .main .block-container {
            padding-top: 2rem; padding-bottom: 2rem; padding-left: 3rem; padding-right: 3rem;
            max-width: 100%;
        }
        /* Hide Streamlit default UI elements */
        footer {visibility: hidden;}
        button[data-testid="baseButton-headerNoPadding"] { visibility: hidden; }
        header[data-testid="stHeader"] { display: none !important; visibility: hidden !important; }
        #stDecoration { display:none; }
        div[data-testid="stToolbar"] { display:none; }
        div[data-testid="stStatusWidget"] { display:none; }
        div[data-testid="stDeployButton"] { display: none; }
        #MainMenu { visibility: hidden; }
        /* Page Background */
        [data-testid="stAppViewContainer"] { background-color: #0D1117; }
        [data-testid="stSidebar"] { background-color: #161B22; padding-top: 1rem; }
        
        /* Button Styling */
        .stButton>button {
            background-color: #21262D;
            color: #C9D1D9;
            border: 1px solid #30363D;
            border-radius: 6px;
            padding: 0.75rem 1.5rem;
            font-size: 1rem;
            font-weight: 500;
            transition: background-color 0.2s ease, border-color 0.2s ease;
        }
        .stButton>button:hover {
            background-color: #30363D;
            border-color: #8B949E;
            color: #ECECF1;
        }
        .stButton>button:focus {
            outline: none !important;
            box-shadow: none !important;
            border-color: #58A6FF;
        }
        .stButton>button p {
            text-transform: none;
            color: inherit;
            font-weight: inherit;
        }

        /* Page Title Style */
        .page-title {
            font-size: 2.5rem;
            font-weight: 600;
            color: #ECECF1;
            margin-bottom: 0.5rem;
        }
        
        .page-subtitle {
            font-size: 1rem;
            color: #7D8590;
            margin-bottom: 2rem;
        }

        /* Welcome Card */
        .welcome-card {
            background-color: #161B22;
            border: 1px solid #30363D;
            border-radius: 12px;
            padding: 2rem;
            text-align: center;
            margin: 2rem 0;
        }

        /* Quick Action Cards */
        .action-card {
            background-color: #161B22;
            border: 1px solid #30363D;
            border-radius: 8px;
            padding: 1.5rem;
            text-align: center;
            transition: border-color 0.2s ease, transform 0.2s ease;
            cursor: pointer;
        }
        .action-card:hover {
            border-color: #58A6FF;
            transform: translateY(-2px);
        }

        /* Sidebar Styles */
        [data-testid="stSidebarNav"] ul { padding-left: 0; }
        [data-testid="stSidebarNav"] li { list-style-type: none; margin-bottom: 0.5rem; }
        [data-testid="stSidebarNav"] li a {
            text-decoration: none; color: #C9D1D9; padding: 0.5rem 1rem;
            border-radius: 6px; display: block;
            transition: background-color 0.2s ease, color 0.2s ease;
            font-size: 0.95rem;
        }
        [data-testid="stSidebarNav"] li a:hover { background-color: #21262D; color: #ECECF1; }
        [data-testid="stSidebarNav"] li a.active {
            background-color: #0D1117; color: #58A6FF; font-weight: 600;
        }
        [data-testid="stSidebarUserContent"] { padding-top: 0rem; }
        div[data-testid="stVerticalBlock"] { gap: 0.5rem !important; }

        /* Info boxes */
        .stInfo {
            background-color: #161B22;
            border: 1px solid #30363D;
            color: #C9D1D9;
        }
        .stSuccess {
            background-color: #161B22;
            border: 1px solid #2D5A27;
            color: #4AC26B;
        }
        .stWarning {
            background-color: #161B22;
            border: 1px solid #D29922;
            color: #F1C232;
        }
        .stError {
            background-color: #161B22;
            border: 1px solid #DA3633;
            color: #F85149;
        }

    </style>
    """, unsafe_allow_html=True)

    show_sidebar()

    if not st.session_state.get("authenticated"):
        st.warning("Please log in to access this page.")
        st.stop()

    auth_client = st.session_state.get("auth_client")
    user_info = st.session_state.get("user_info")

    if not auth_client or not user_info:
        st.error("Session not properly initialized. Please log in again.")
        st.stop()

    if user_info.get("role") != "admin":
        st.error("Access Denied: You do not have permission to view this page.")
        st.image("https://http.cat/403", caption="Access Denied", use_column_width=True)
        st.stop()

    # Page header
    st.markdown('<h1 class="page-title">🔑 Admin Dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Welcome to the administrative control center</p>', unsafe_allow_html=True)
    
    # Welcome section
    st.markdown(f"""
        <div class="welcome-card">
            <h2>Welcome, Administrator!</h2>
            <p>You have full administrative access to the PrivateGPT Legal AI system.</p>
            <p><strong>Current User:</strong> {user_info.get('email', 'Unknown')}</p>
            <p><strong>Login Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    """, unsafe_allow_html=True)

    # Quick actions
    st.subheader("🚀 Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
            <div class="action-card">
                <h3>🛠️ Admin Panel</h3>
                <p>Manage users, view system status, and configure settings</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Open Admin Panel", key="admin_panel_btn", type="primary"):
            st.switch_page("pages/admin_panel.py")
    
    with col2:
        st.markdown("""
            <div class="action-card">
                <h3>📄 Document Management</h3>
                <p>Upload, organize, and manage legal documents</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Manage Documents", key="docs_btn"):
            st.switch_page("pages/document_management.py")
    
    with col3:
        st.markdown("""
            <div class="action-card">
                <h3>💬 RAG Chat</h3>
                <p>Test document-based AI chat functionality</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Test RAG Chat", key="rag_btn"):
            st.switch_page("pages/rag_chat.py")

    st.markdown("---")

    # System overview
    st.subheader("📊 System Overview")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**System Health**")
        try:
            # Quick health check
            response = requests.get("http://knowledge-service:8000/health", timeout=3)
            if response.status_code == 200:
                st.success("✅ All services operational")
            else:
                st.warning("⚠️ Some services may be unavailable")
        except:
            st.error("❌ Unable to check system status")
    
    with col2:
        st.markdown("**Recent Activity**")
        activities = [
            f"🔐 Admin login: {user_info.get('email', 'Unknown')}",
            f"📊 Dashboard accessed at {datetime.now().strftime('%H:%M')}",
            f"🔍 System health check performed",
        ]
        
        for activity in activities:
            st.markdown(f"• {activity}")

    # Admin user details
    with st.expander("👤 Your Admin Profile", expanded=False):
        st.json(user_info)
    
    # Logout section
    if st.sidebar.button("🚪 Logout", key="admin_logout"):
        st.session_state.authenticated = False
        st.session_state.user_info = None
        st.session_state.token = None
        st.session_state.auth_client = None
        st.toast("Logged out successfully!", icon="👋")
        
        if 'current_page' in st.session_state:
            st.session_state.current_page = 'login' 

        server = Server.instance_if_exists()
        if server:
            server._on_pages_changed.send()
        st.rerun()


if __name__ == "__main__":
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_info = None
        st.session_state.token = None
        st.session_state.auth_client = None
        
    display_admin_dashboard() 