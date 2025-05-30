"""
Shared utilities for PrivateGPT Legal AI pages
Contains common functions, authentication, and session state management
"""

import os
import streamlit as st
from datetime import datetime
from utils.auth_client import AuthClient
from utils.rag_engine import RAGEngine
from utils.document_processor import DocumentProcessor
from utils.compliance_logger import ComplianceLogger

# --- Application Constants ---
APP_TITLE = "PrivateGPT Legal AI Professional"
APP_SUBTITLE = "Your Secure, Self-Hosted Legal AI Assistant"
LLM_MODEL_NAME = "LLaMA-3 70B (Quantized GGUF Q4_K_M)"
VECTOR_DB_NAME = "Weaviate with bge-base-en-v1.5 embeddings"
WORKFLOW_ENGINE = "n8n"
VERSION_INFO = "Enhanced UI v2.1 - Demo Structure Edition"

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
def get_rag_engine():
    return RAGEngine(OLLAMA_URL, WEAVIATE_URL)

@st.cache_resource
def get_document_processor():
    return DocumentProcessor()

@st.cache_resource
def get_compliance_logger():
    return ComplianceLogger()

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

def add_demo_documents():
    """Add some demo documents for testing"""
    if len(st.session_state.get("uploaded_documents", [])) == 0:
        demo_docs = [
            {
                "name": "Alpha Corp Contract.pdf",
                "status": "Processed",
                "ingested_at": datetime(2024, 1, 15, 10, 30),
                "size": "2.3MB",
                "type": "contract",
                "document_id": "demo-001",
                "client_matter": "Contract Review",
                "uploaded_by": "demo@lawfirm.com"
            },
            {
                "name": "Smith v Jones Case Law.pdf",
                "status": "Processed", 
                "ingested_at": datetime(2024, 1, 10, 14, 15),
                "size": "1.8MB",
                "type": "case_law",
                "document_id": "demo-002",
                "client_matter": "Case Analysis",
                "uploaded_by": "lawyer1@lawfirm.com"
            },
            {
                "name": "IP Filing Motion.docx",
                "status": "Processed",
                "ingested_at": datetime(2024, 1, 8, 9, 45),
                "size": "856KB",
                "type": "filing",
                "document_id": "demo-003",
                "client_matter": "General Research",
                "uploaded_by": "admin@lawfirm.com"
            },
            {
                "name": "Legal Research Memo.txt",
                "status": "Processed",
                "ingested_at": datetime(2024, 1, 5, 16, 20),
                "size": "432KB",
                "type": "memo",
                "document_id": "demo-004",
                "client_matter": "Contract Review",
                "uploaded_by": "lawyer1@lawfirm.com"
            }
        ]
        st.session_state.uploaded_documents = demo_docs

def require_auth(admin_only=False, main_app_file="../app.py"):
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
            compliance_logger = get_compliance_logger()
            if 'login_time' in st.session_state:
                session_duration = int((datetime.now() - st.session_state.login_time).total_seconds())
            else:
                session_duration = None
                
            compliance_logger.log_user_logout(
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
    hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

    # Custom CSS for clean, simple appearance
    st.markdown("""
    <style>
        .main-header {
            font-size: 2.2rem;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 0.5rem;
        }
        .sub-header {
            font-size: 1.1rem;
            color: #6b7280;
            margin-bottom: 2rem;
        }
        .metric-card {
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 0.5rem 0;
        }
        .chat-message {
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 1rem 0;
            border-left: 4px solid #3b82f6;
        }
        .user-message {
            background-color: #f3f4f6;
            border-left-color: #10b981;
        }
        .assistant-message {
            background-color: #fef3c7;
            border-left-color: #f59e0b;
        }
        .legal-disclaimer {
            background-color: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 1rem 0;
            color: #991b1b;
            font-size: 0.9rem;
        }
    </style>
    """, unsafe_allow_html=True) 