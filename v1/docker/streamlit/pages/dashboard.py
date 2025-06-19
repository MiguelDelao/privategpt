"""
PrivateGPT Legal AI - Dashboard
Main dashboard with system overview and quick actions
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os
import requests
from datetime import datetime
from pages_utils import (
    APP_TITLE, LLM_MODEL_NAME, VECTOR_DB_NAME, WORKFLOW_ENGINE, VERSION_INFO,
    initialize_session_state, require_auth, apply_page_styling,
    display_navigation_sidebar, get_logger
)

# Page configuration
st.set_page_config(
    page_title=f"Dashboard - {APP_TITLE}", 
    page_icon="🏠",
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Initialize session state and check authentication
initialize_session_state()
require_auth(main_app_file="app.py")

# Add parent directory to path to import pages_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Helper Functions ---
def get_dummy_chat_history():
    """Generate dummy chat history data."""
    return [
        {"id": "chat1", "title": "Contract Analysis Q&A", "timestamp": "2024-07-28 10:30 AM", "preview": "Discussed key clauses in the NDA document..."},
        {"id": "chat2", "title": "Legal Research - GDPR", "timestamp": "2024-07-27 03:45 PM", "preview": "Explored GDPR compliance requirements for new product..."},
        {"id": "chat3", "title": "Case Law Summary", "timestamp": "2024-07-26 09:00 AM", "preview": "Summarized findings from recent intellectual property cases..."},
        {"id": "chat4", "title": "Regulatory Update Brief", "timestamp": "2024-07-25 01:15 PM", "preview": "Reviewed new SEC filings and their implications..."},
    ]

def get_document_statistics():
    """Get document statistics from Knowledge Service API"""
    try:
        # Try to get stats from the knowledge service API
        response = requests.get("http://knowledge-service:8000/documents/", timeout=10)
        if response.status_code == 200:
            result = response.json()
            documents = result.get("documents", [])
            
            # Calculate statistics
            total_documents = len(documents)
            type_counts = {}
            total_size = 0
            
            for doc in documents:
                # Count document types
                doc_type = doc.get("content_type", "unknown").replace("application/", "")
                type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
                
                # Calculate average size (if available)
                size_mb = doc.get("size_mb", 0)
                total_size += size_mb
            
            avg_doc_size_kb = (total_size * 1024 / total_documents) if total_documents > 0 else 0
            
            return {
                "total_documents": total_documents,
                "document_types": type_counts,
                "average_doc_size_kb": avg_doc_size_kb
            }
        else:
            # Fallback to session state if API fails
            raise Exception(f"API returned {response.status_code}")
            
    except Exception as e:
        # Fallback to session state if knowledge service fails
        get_logger().log_error(st.session_state.user_email, f"Dashboard API stats error: {e}", "dashboard_stats")
        total_docs = len(st.session_state.get("uploaded_documents", []))
        type_counts = {}
        for doc in st.session_state.get("uploaded_documents", []):
            doc_type = doc.get("Type", doc.get("type", "unknown"))
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
        return {"total_documents": total_docs, "document_types": type_counts, "average_doc_size_kb": 0}

def display_dashboard():
    """Display the clean, professional dashboard content"""
    
    # Apply ChatGPT-style professional dark theme
    st.markdown("""
    <style>
        /* General Styles */
        body {
            font-family: 'Söhne', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Ubuntu', 'Cantarell', 'Noto Sans', 'sans-serif', 'Helvetica Neue', 'Arial', 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji';
            color: #ECECF1; /* Lighter text for dark background */
        }
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            padding-left: 3rem;
            padding-right: 3rem;
            max-width: 100%; /* Ensure content can go full width if needed */
        }

        /* Hide Streamlit default UI elements */
        /* Hide "Made with Streamlit" footer */
        footer {visibility: hidden;}
        /* Hide Hamburger Menu */
        button[data-testid="baseButton-headerNoPadding"] {
            visibility: hidden;
        }
        /* Hide Header */
        header[data-testid="stHeader"] {
            display: none !important;
            visibility: hidden !important;
        }
        /* Hide decoration */
        #stDecoration {
            display:none;
        }
        /* Hide Streamlit toolbar */
        div[data-testid="stToolbar"] {
            display:none;
        }
        /* Hide status widget (top right) */
        div[data-testid="stStatusWidget"] {
            display:none;
        }
        /* Hide deploy button if it reappears */
        div[data-testid="stDeployButton"] {
            display: none;
        }
        #MainMenu {
            visibility: hidden;
        }

        /* Page Background */
        [data-testid="stAppViewContainer"] {
            background-color: #0D1117; /* Dark background */
        }
        [data-testid="stSidebar"] {
            background-color: #161B22; /* Slightly lighter dark for sidebar */
            padding-top: 1rem;
        }

        /* Custom Header */
        .custom-header h1 {
            font-size: 2.5rem;
            font-weight: 600;
            color: #ECECF1;
            margin-bottom: 0.25rem;
        }
        .custom-header p {
            font-size: 1.125rem;
            color: #8B949E; /* GitHub-like secondary text color */
            margin-bottom: 2rem;
        }

        /* Quick Action Buttons */
        .stButton>button {
            background-color: #21262D; /* GitHub dark button color */
            color: #C9D1D9; /* GitHub dark button text color */
            border: 1px solid #30363D; /* GitHub dark button border */
            border-radius: 6px;
            padding: 0.75rem 1.5rem;
            font-size: 1rem;
            font-weight: 500;
            width: 100%;
            transition: background-color 0.2s ease, border-color 0.2s ease;
        }
        .stButton>button:hover {
            background-color: #30363D; /* Darker on hover */
            border-color: #8B949E;
            color: #ECECF1;
        }
        .stButton>button:focus {
            outline: none !important;
            box-shadow: none !important;
            border-color: #58A6FF; /* Blue border on focus, similar to GitHub */
        }
        /* Ensure button text is not uppercase */
        .stButton>button p {
            text-transform: none;
            color: inherit; /* Inherit color from button */
            font-weight: inherit; /* Inherit font weight */
        }


        /* Chat History Section */
        .chat-history-header h2 {
            font-size: 1.75rem;
            font-weight: 600;
            color: #ECECF1;
            margin-top: 2.5rem;
            margin-bottom: 1rem;
            border-bottom: 1px solid #30363D; /* Separator line */
            padding-bottom: 0.5rem;
        }
        .activity-item {
            background-color: #161B22; /* Slightly lighter dark for items */
            border: 1px solid #30363D;
            border-radius: 6px;
            padding: 0.6rem 0.9rem; /* Further reduced padding */
            margin-bottom: 0.75rem; /* Increased space between items */
            cursor: pointer; /* Whole item clickable */
            transition: background-color 0.2s ease, border-color 0.2s ease;
            display: flex; /* Use flex for side-by-side content and button */
            justify-content: space-between;
            align-items: center;
        }
        .activity-item:hover {
            background-color: #21262D; /* Subtle background change */
        }
        .activity-content {
            flex-grow: 1; /* Allow content to take available space */
            cursor: pointer; /* Make content area clickable */
            margin-right: 0.75rem; /* Slightly reduced space before delete button */
            min-width: 0; /* Allow content to shrink if needed */
        }
        .activity-item h3 {
            font-size: 1.1rem; /* Slightly larger title */
            font-weight: 500;
            color: #C9D1D9;
            margin-top: 0; /* No top margin for the title itself */
            margin-bottom: 0.05rem; /* Reduced bottom margin for title */
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            line-height: 1.3; /* Adjust line height for new font size */
        }
        .activity-item .timestamp {
            font-size: 0.75rem; /* Slightly smaller timestamp */
            color: #8B949E;
            margin-bottom: 0.2rem; /* Further reduced margin */
            line-height: 1.2;
        }
        .activity-item .preview {
            font-size: 0.85rem; /* Further reduced preview font size */
            color: #C9D1D9;
            line-height: 1.3;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .activity-item .actions {
            flex-shrink: 0; /* Prevent button container from shrinking */
        }
        .delete-button {
            background-color: transparent; /* Make button background transparent */
            color: #8B949E; /* Icon color */
            border: none;
            padding: 0.2rem; /* Adjusted padding for icon */
            border-radius: 4px;
            cursor: pointer;
            transition: color 0.2s ease, background-color 0.2s ease;
            display: inline-flex; /* Align icon nicely */
            align-items: center;
            justify-content: center;
            line-height: 1;
        }
        .delete-button:hover {
            color: #E6EDF3; /* Lighter icon color on hover */
            background-color: #30363D; /* Slight background on hover for better visibility */
        }
        .delete-button svg {
            width: 15px; /* Slightly smaller icon */
            height: 15px;
            fill: currentColor; /* Use text color for SVG fill */
        }


        /* Styling for sidebar buttons and text */
        [data-testid="stSidebarNav"] ul {
            padding-left: 0;
        }
        [data-testid="stSidebarNav"] li {
            list-style-type: none;
            margin-bottom: 0.5rem;
        }
        [data-testid="stSidebarNav"] li a {
            text-decoration: none;
            color: #C9D1D9;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            display: block;
            transition: background-color 0.2s ease, color 0.2s ease;
            font-size: 0.95rem; /* Slightly smaller font for sidebar items */
        }
        [data-testid="stSidebarNav"] li a:hover {
            background-color: #21262D;
            color: #ECECF1;
        }
        [data-testid="stSidebarNav"] li a.active { /* Style for active page link */
            background-color: #0D1117; /* Match app background for "selected" effect */
            color: #58A6FF; /* Blue accent for active link */
            font-weight: 600;
        }
        /* Remove Streamlit's default top padding for sidebar content */
        [data-testid="stSidebarUserContent"] {
            padding-top: 0rem;
        }
        /* Reduce gap for stVerticalBlock */
        div[data-testid="stVerticalBlock"] {
            gap: 0.5rem !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # Custom Header
    st.markdown("""
        <div class="custom-header">
            <h1>PrivateGPT</h1>
            <p>Welcome back! Here's your workspace overview.</p>
        </div>
    """, unsafe_allow_html=True)

    # Quick Actions
    st.markdown("<h2 style='font-size: 1.75rem; font-weight: 600; color: #ECECF1; margin-bottom: 1rem;'>Quick Actions</h2>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💬 Start Chat", key="start_rag_chat_dashboard"): # Changed key to avoid conflict if used elsewhere
            st.switch_page("pages/chat.py")
    with col2:
        if st.button("📂 Upload Documents", key="upload_documents_dashboard", use_container_width=True):
            st.switch_page("pages/document_management.py")
            
    st.markdown("<br>", unsafe_allow_html=True) # Spacer

    # Chat History Section
    st.markdown("<div class='chat-history-header'><h2>Chat History</h2></div>", unsafe_allow_html=True)
    chat_history = get_dummy_chat_history()

    if not chat_history:
        st.markdown("<p style='color: #8B949E;'>No chat history yet.</p>", unsafe_allow_html=True)
    else:
        for item in chat_history:
            item_id = item['id']
            item_title = item['title']
            item_timestamp = item['timestamp']
            item_preview = item['preview']
            
            # Sanitize title for console.log, if necessary, though for this example it's direct.
            js_title = item_title.replace("'", "\\'") # Basic sanitization for JS string

            item_html = f"""
            <div class="activity-item">
                <div class="activity-content" onclick="console.log('Clicked chat: {js_title}');">
                    <h3>{item_title}</h3>
                    <div class="timestamp">{item_timestamp}</div>
                    <div class="preview">{item_preview}</div>
                </div>
                <div class="actions">
                    <button class="delete-button" title="Delete chat" onclick="console.log('Delete clicked for chat ID: {item_id}'); event.stopPropagation();">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
                    </button>
                </div>
            </div>
            """
            st.markdown(item_html, unsafe_allow_html=True)

# Display navigation sidebar
display_navigation_sidebar(current_page="Dashboard")

# Main script logic
if __name__ == "__main__":
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = True 
        st.session_state.user_role = "admin"
        st.session_state.username = "test_dashboard_user"
    
    display_dashboard() 