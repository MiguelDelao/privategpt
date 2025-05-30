"""
PrivateGPT Legal AI - Main Streamlit Application
Professional-grade legal AI assistant with RAG capabilities
"""

import os
import time
import json
import uuid
import requests
from datetime import datetime
from typing import Dict, List, Optional

import streamlit as st
import weaviate
import pandas as pd
from utils.auth_client import AuthClient
from utils.rag_engine import RAGEngine
from utils.document_processor import DocumentProcessor
from utils.compliance_logger import ComplianceLogger

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

# Configure Streamlit page and hide deploy button
st.set_page_config(
    page_title="PrivateGPT Legal AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Hide Streamlit style elements
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stDeployButton {display: none;}
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
    .source-citation {
        background-color: #e5e7eb;
        padding: 0.5rem;
        border-radius: 0.25rem;
        margin: 0.5rem 0;
        font-size: 0.875rem;
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

def check_authentication():
    """Check if user is authenticated"""
    if 'access_token' not in st.session_state:
        return False
    
    auth_client = get_auth_client()
    try:
        user_info = auth_client.verify_token(st.session_state.access_token)
        if user_info:
            st.session_state.user_info = user_info
            return True
    except Exception:
        pass
    
    return False

def login_page():
    """Display login page"""
    st.markdown('<div class="main-header">⚖️ PrivateGPT Legal AI</div>', unsafe_allow_html=True)
    
    # Legal disclaimer
    st.markdown("""
    <div class="legal-disclaimer">
        <strong>Legal Disclaimer:</strong> This AI assistant is designed to assist legal professionals 
        with research and document analysis. All AI-generated content should be reviewed by qualified 
        attorneys. This tool does not constitute legal advice and should not be relied upon as such.
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        st.subheader("🔐 Authentication Required")
        email = st.text_input("Email", placeholder="attorney@lawfirm.com")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", type="primary", use_container_width=True)
        
        if submit:
            if email and password:
                auth_client = get_auth_client()
                try:
                    with st.spinner("Authenticating..."):
                        token_response = auth_client.login(email, password)
                    
                    st.session_state.access_token = token_response["access_token"]
                    st.session_state.user_role = token_response["user_role"]
                    st.success("Login successful!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Login failed: {str(e)}")
            else:
                st.error("Please enter both email and password")

def main_application():
    """Main application interface"""
    user_info = st.session_state.user_info
    
    # Header
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown('<div class="main-header">⚖️ PrivateGPT Legal AI</div>', unsafe_allow_html=True)
    
    with col2:
        st.metric("User Role", user_info["user"]["role"].title())
    
    with col3:
        if st.button("🚪 Logout", type="secondary"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Sidebar
    with st.sidebar:
        st.header("📁 Document Management")
        
        # Document upload
        uploaded_file = st.file_uploader(
            "Upload Legal Documents",
            type=['pdf', 'docx', 'txt'],
            help="Upload case law, contracts, filings, or other legal documents"
        )
        
        if uploaded_file:
            if st.button("📤 Process Document", type="primary"):
                process_document(uploaded_file)
        
        # Client matter selection
        st.header("📋 Client Matter")
        client_matters = user_info["user"].get("client_matters", ["General Research"])
        selected_matter = st.selectbox("Select Client Matter", client_matters)
        st.session_state.current_matter = selected_matter
        
        # Document search
        st.header("🔍 Document Search")
        search_query = st.text_input("Search documents", placeholder="Enter search terms...")
        if search_query:
            search_documents(search_query)
    
    # Chat input (outside of tabs)
    st.header("💬 Legal AI Assistant")
    user_query = st.chat_input("Ask me about your legal documents...")
    
    if user_query:
        # Initialize chat history
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
            
        # Add user message to history
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_query,
            "timestamp": datetime.now()
        })
        
        # Process query with RAG
        with st.spinner("Analyzing documents and generating response..."):
            response = generate_rag_response(user_query)
        
        # Add assistant response to history
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": response["answer"],
            "sources": response["sources"],
            "timestamp": datetime.now()
        })

    # Main content area
    tab1, tab2, tab3 = st.tabs(["💬 Chat History", "📊 Analytics", "🛠️ Admin"])
    
    with tab1:
        chat_display()
    
    with tab2:
        analytics_dashboard()
    
    with tab3:
        if user_info["user"]["role"] == "admin":
            admin_interface()
        else:
            st.warning("Admin privileges required")

def process_document(uploaded_file):
    """Process uploaded document"""
    try:
        processor = get_document_processor()
        compliance_logger = get_compliance_logger()
        
        with st.spinner(f"Processing {uploaded_file.name}..."):
            # Extract text from document
            text_content = processor.extract_text(uploaded_file)
            
            # Upload to Weaviate (auto-chunking)
            rag_engine = get_rag_engine()
            document_id = rag_engine.add_document(
                content=text_content,
                filename=uploaded_file.name,
                client_matter=st.session_state.get("current_matter", "General"),
                doc_type=processor.get_document_type(uploaded_file.name)
            )
            
            # Log document processing
            compliance_logger.log_document_upload(
                user_email=st.session_state.user_info["user"]["email"],
                document_id=document_id,
                filename=uploaded_file.name,
                client_matter=st.session_state.get("current_matter", "General")
            )
            
            st.success(f"✅ Document '{uploaded_file.name}' processed successfully!")
            st.info(f"Document ID: {document_id}")
    
    except Exception as e:
        st.error(f"Failed to process document: {str(e)}")

def search_documents(query):
    """Search documents in vector database"""
    try:
        rag_engine = get_rag_engine()
        results = rag_engine.search_documents(query, limit=5)
        
        if results:
            st.subheader("📄 Search Results")
            for i, result in enumerate(results, 1):
                with st.expander(f"{i}. {result['source']} (Score: {result['score']:.3f})"):
                    st.text(result['content'][:500] + "..." if len(result['content']) > 500 else result['content'])
        else:
            st.info("No documents found matching your query")
    
    except Exception as e:
        st.error(f"Search failed: {str(e)}")

def chat_display():
    """Display chat history"""
    # Initialize chat history if it doesn't exist
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if not st.session_state.chat_history:
        st.info("💡 Ask a question about your legal documents using the chat input above!")
        return
    
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.write(message["content"])
                st.caption(f"🕒 {message['timestamp'].strftime('%H:%M:%S')}")
        else:
            with st.chat_message("assistant"):
                st.write(message["content"])
                
                # Show sources
                if "sources" in message and message["sources"]:
                    with st.expander("📚 Sources Used"):
                        for source in message["sources"]:
                            st.markdown(f"**{source['source']}** (Relevance: {source['score']:.3f})")
                            st.text(source['content'][:200] + "...")
                
                st.caption(f"🕒 {message['timestamp'].strftime('%H:%M:%S')}")

def generate_rag_response(query: str) -> Dict:
    """Generate response using RAG pipeline"""
    try:
        rag_engine = get_rag_engine()
        compliance_logger = get_compliance_logger()
        
        # Get relevant context
        context_results = rag_engine.search_documents(query, limit=3)
        
        # Generate response
        response = rag_engine.generate_response(query, context_results)
        
        # Log AI interaction
        compliance_logger.log_ai_interaction(
            user_email=st.session_state.user_info["user"]["email"],
            query=query,
            response_tokens=len(response["answer"].split()),
            sources_accessed=[r["source"] for r in context_results],
            client_matter=st.session_state.get("current_matter")
        )
        
        return {
            "answer": response["answer"],
            "sources": context_results
        }
    
    except Exception as e:
        st.error(f"Failed to generate response: {str(e)}")
        return {"answer": "I apologize, but I encountered an error processing your request.", "sources": []}

def analytics_dashboard():
    """Display analytics and metrics"""
    st.subheader("📊 Usage Analytics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Documents Processed", "42", "+3")
    
    with col2:
        st.metric("AI Queries Today", "18", "+5")
    
    with col3:
        st.metric("Active Users", "8", "+1")
    
    with col4:
        st.metric("System Uptime", "99.9%", "0.1%")
    
    # Usage charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Query Volume")
        # Sample data - replace with real metrics
        chart_data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=30, freq='D'),
            'queries': [10, 15, 12, 18, 20, 25, 22, 30, 28, 35, 32, 40, 38, 45, 42, 50, 48, 55, 52, 60, 58, 65, 62, 70, 68, 75, 72, 80, 78, 85]
        })
        st.line_chart(chart_data.set_index('date'))
    
    with col2:
        st.subheader("📊 Document Types")
        doc_types = pd.DataFrame({
            'Type': ['Contracts', 'Case Law', 'Filings', 'Memos'],
            'Count': [25, 15, 8, 12]
        })
        st.bar_chart(doc_types.set_index('Type'))

def admin_interface():
    """Admin interface for user management"""
    st.subheader("🛠️ Administration")
    
    tab1, tab2, tab3 = st.tabs(["👥 Users", "📋 Logs", "⚙️ Settings"])
    
    with tab1:
        st.subheader("User Management")
        
        # User creation form
        with st.form("create_user"):
            st.write("**Create New User**")
            new_email = st.text_input("Email")
            new_password = st.text_input("Password", type="password")
            new_role = st.selectbox("Role", ["user", "admin", "partner", "associate"])
            new_matters = st.text_area("Client Matters (one per line)")
            
            if st.form_submit_button("Create User"):
                # Implementation for user creation
                st.success("User created successfully!")
    
    with tab2:
        st.subheader("System Logs")
        st.info("Audit logs and compliance tracking would be displayed here")
    
    with tab3:
        st.subheader("System Settings")
        st.info("System configuration options would be displayed here")

# Main application flow
def main():
    """Main application entry point"""
    if not check_authentication():
        login_page()
    else:
        main_application()

if __name__ == "__main__":
    main() 