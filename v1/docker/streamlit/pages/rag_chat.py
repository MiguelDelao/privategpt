"""
PrivateGPT Legal AI - RAG Chat
Document-based Q&A with AI assistance
"""

import streamlit as st
import requests
import time
import sys
import os
import logging
import json

# Add parent directory to path to import pages_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pages_utils import (
    APP_TITLE, initialize_session_state, require_auth, 
    display_navigation_sidebar, # apply_page_styling, # Removed
    get_logger
)

# Page configuration
st.set_page_config(
    page_title=f"RAG Chat - {APP_TITLE}", 
    # page_icon="💬", # Removed icon for cleaner look
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply styling and authentication
# apply_page_styling() # Removed call
initialize_session_state()
require_auth()

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
        font-size: 2.25rem;
        font-weight: 600;
        color: #ECECF1;
        margin-bottom: 0.5rem;
    }
    
    .page-subtitle {
        font-size: 1rem;
        color: #7D8590;
        margin-bottom: 2rem;
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

    /* Chat Message Styling */
    .stChatMessage {
        background-color: transparent;
        border: none;
        padding: 1rem 0;
    }
    
    /* Selectbox and Slider Styling */
    .stSelectbox > div > div {
        background-color: #21262D;
        border: 1px solid #30363D;
        color: #C9D1D9;
    }
    .stSelectbox > div > div:hover {
        border-color: #8B949E;
    }
    
    .stSlider > div > div > div {
        background-color: #21262D;
    }
    .stSlider > div > div > div > div {
        color: #C9D1D9;
    }

    /* Info, Warning, Success boxes */
    .stInfo {
        background-color: #161B22;
        border: 1px solid #30363D;
        color: #C9D1D9;
    }
    .stWarning {
        background-color: #161B22;
        border: 1px solid #D29922;
        color: #F1C232;
    }
    .stSuccess {
        background-color: #161B22;
        border: 1px solid #2D5A27;
        color: #4AC26B;
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: #161B22;
        color: #C9D1D9;
        border: 1px solid #30363D;
    }
    .streamlit-expanderContent {
        background-color: #0D1117;
        border: 1px solid #30363D;
        border-top: none;
    }

</style>
""", unsafe_allow_html=True)

# Knowledge Service URL
KNOWLEDGE_SERVICE_URL = "http://knowledge-service:8000"

# Initialize RAG chat specific session state
if "rag_chat_history" not in st.session_state:
    st.session_state.rag_chat_history = [] # Stores tuples of (query, response_dict)
if "selected_rag_document_source" not in st.session_state:
    st.session_state.selected_rag_document_source = "All Documents"
if "current_rag_query" not in st.session_state:
    st.session_state.current_rag_query = ""

def call_knowledge_service_chat_stream(query: str, max_tokens: int = 1000, temperature: float = 0.7, search_limit: int = 10):
    """Call the knowledge service streaming chat API"""
    try:
        payload = {
            "messages": [
                {"role": "user", "content": query}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "search_limit": search_limit,
            "include_sources": True
        }
        
        response = requests.post(
            f"{KNOWLEDGE_SERVICE_URL}/chat/stream",
            json=payload,
            timeout=60,
            stream=True
        )
        
        if response.status_code == 200:
            full_response = ""
            sources = []
            took_ms = 0
            
            for line in response.iter_lines():
                if line:
                    try:
                        chunk_data = json.loads(line.decode('utf-8'))
                        
                        # Handle sources (sent first)
                        if "sources" in chunk_data:
                            sources = chunk_data["sources"]
                            continue
                        
                        # Handle partial responses
                        if "partial_response" in chunk_data:
                            full_response = chunk_data["partial_response"]
                            yield {
                                "success": True,
                                "partial_response": full_response,
                                "done": chunk_data.get("done", False),
                                "sources": sources
                            }
                            
                        # Handle final response
                        elif "message" in chunk_data and chunk_data.get("done"):
                            took_ms = chunk_data.get("took_ms", 0)
                            yield {
                                "success": True,
                                "answer": full_response,
                                "sources": sources,
                                "took_ms": took_ms,
                                "model_used": chunk_data.get("model_used", "ollama"),
                                "done": True
                            }
                            return
                            
                        # Handle errors
                        elif "error" in chunk_data:
                            yield {
                                "success": False,
                                "error": chunk_data["error"]
                            }
                            return
                            
                    except json.JSONDecodeError:
                        continue
            
            # Fallback final response if no explicit "done" was received
            if full_response:
                yield {
                    "success": True,
                    "answer": full_response,
                    "sources": sources,
                    "took_ms": took_ms,
                    "model_used": "ollama",
                    "done": True
                }
        else:
            yield {
                "success": False,
                "error": f"API error: {response.status_code} - {response.text}"
            }
            
    except requests.exceptions.Timeout:
        yield {
            "success": False,
            "error": "Request timeout - the query took too long to process"
        }
    except Exception as e:
        yield {
            "success": False,
            "error": str(e)
        }

def call_knowledge_service_chat(query: str, max_tokens: int = 1000, temperature: float = 0.7, search_limit: int = 10):
    """Call the knowledge service chat API"""
    try:
        payload = {
            "messages": [
                {"role": "user", "content": query}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "search_limit": search_limit,
            "include_sources": True
        }
        
        response = requests.post(
            f"{KNOWLEDGE_SERVICE_URL}/chat/",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "answer": result.get("message", {}).get("content", "No response generated"),
                "sources": result.get("sources", []),
                "took_ms": result.get("took_ms", 0),
                "model_used": result.get("model_used", "ollama")
            }
        else:
            return {
                "success": False,
                "error": f"API error: {response.status_code} - {response.text}"
            }
            
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timeout - the query took too long to process"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def load_documents_from_api():
    """Load available documents from the knowledge service"""
    try:
        headers = {}
        if "access_token" in st.session_state and st.session_state.access_token:
            headers["Authorization"] = f"Bearer {st.session_state.access_token}"
        
        response = requests.get(f"{KNOWLEDGE_SERVICE_URL}/documents/", timeout=10, headers=headers)
        if response.status_code == 200:
            result = response.json()
            return result.get("documents", [])
        else:
            return []
    except Exception as e:
        st.error(f"Error loading documents: {str(e)}")
        return []

def load_clients_from_api():
    """Load available clients from the auth service for filtering"""
    try:
        headers = {}
        if "access_token" in st.session_state and st.session_state.access_token:
            headers["Authorization"] = f"Bearer {st.session_state.access_token}"
        
        response = requests.get("http://auth-service:8000/admin/clients/", timeout=10, headers=headers)
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            return []
    except Exception:
        return []

def display_rag_chat():
    """Display the RAG chat interface"""
    # Modern page header
    st.markdown('<div class="page-title">💬 Document Q&A</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Ask questions about your uploaded documents. The AI will search through your knowledge base to provide accurate answers.</div>', unsafe_allow_html=True)

    logger = get_logger()
    user_email = st.session_state.user_email

    # Load available documents from API
    api_documents = load_documents_from_api()
    available_sources = ["All Documents"] + sorted(list(set(doc.get("filename", "Unknown") for doc in api_documents)))
    
    # Load available clients for filtering
    available_clients = load_clients_from_api()
    client_options = ["All Clients"] + [f"{client.get('name', 'Unknown')} ({client.get('id', 'No ID')[:8]}...)" for client in available_clients]
    
    # Sidebar for context selection and controls
    with st.sidebar:
        st.markdown("### ⚙️ Chat Settings")
        
        # Client selection dropdown
        if "selected_client_filter" not in st.session_state:
            st.session_state.selected_client_filter = "All Clients"
            
        selected_client = st.selectbox(
            "Client Filter:",
            options=client_options,
            index=client_options.index(st.session_state.selected_client_filter) if st.session_state.selected_client_filter in client_options else 0,
            help="Filter documents by client. Admins see all clients, users see only their authorized clients."
        )
        st.session_state.selected_client_filter = selected_client
        
        # Document selection dropdown 
        st.session_state.selected_rag_document_source = st.selectbox(
            "Document Context:",
            options=available_sources,
            index=available_sources.index(st.session_state.selected_rag_document_source) if st.session_state.selected_rag_document_source in available_sources else 0,
            help="Focus the AI's attention on a specific document or all documents."
        )
        
        # Sidebar for settings
        st.header("Chat Settings")
        
        # Clear chat button
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.rag_chat_history = []
            st.rerun()
        
        # Advanced RAG Configuration
        with st.expander("🔧 Advanced RAG Settings", expanded=False):
            st.markdown("**Search Configuration**")
            
            search_limit = st.slider(
                "Documents to Retrieve",
                min_value=1,
                max_value=50,
                value=10,
                help="Higher values = more context but slower responses. Based on OpenAI research: 10-15 is optimal for most cases."
            )
            
            st.markdown("**Response Configuration**")
            
            temperature = st.slider(
                "Creativity",
                min_value=0.0,
                max_value=2.0,
                value=0.7,
                step=0.1,
                help="Lower = more factual, Higher = more creative"
            )
            
            max_tokens = st.slider(
                "Response Length",
                min_value=100,
                max_value=4000,
                value=1000,
                step=100,
                help="Maximum tokens in response"
            )
            
            # Performance info
            st.info(
                f"**Performance Estimate:**\\n"
                f"• 1-10 docs: ~2-3 seconds\\n"
                f"• 11-25 docs: ~3-5 seconds\\n"
                f"• 26-50 docs: ~5-10 seconds"
            )
        
        st.markdown("---")
        st.markdown("### 💡 Tips")
        st.info("For best results: Be specific in your questions. The AI will search through your uploaded documents to find relevant information.")
        
        if not api_documents:
            st.warning("No documents found in the knowledge base. Please upload documents via the 'Documents' page.")
            if st.button("📂 Go to Documents", use_container_width=True):
                st.switch_page("pages/document_management.py")
        else:
            st.success(f"📚 {len(api_documents)} documents available")

    # Main chat area with proper scrolling container
    chat_container = st.container(border=False)
    
    # Check if there's a pending response to generate
    has_pending_response = (len(st.session_state.rag_chat_history) > 0 and 
                           st.session_state.rag_chat_history[-1][1].get("answer", "") == "")
    
    if has_pending_response:
        # Handle streaming response for the last message
        last_query = st.session_state.rag_chat_history[-1][0]
        
        with chat_container:
            # Display all previous completed messages
            for query, response_data in st.session_state.rag_chat_history[:-1]:
                with st.chat_message("user"):
                    st.markdown(query)
                with st.chat_message("assistant"):
                    st.markdown(response_data["answer"])
                    if response_data.get("sources") and len(response_data["sources"]) > 0:
                        with st.expander(f"📚 Cited Sources ({len(response_data['sources'])})"):
                            for i, source in enumerate(response_data["sources"]):
                                st.caption(f"**{i+1}. {source.get('metadata', {}).get('filename', 'Unknown Document')}** (Score: {source.get('score', 0):.2f})")
                                st.markdown(f"<small>{source.get('content', '')[:300]}...</small>", unsafe_allow_html=True)
                                st.markdown("---")
                    if response_data.get("error"):
                        st.error(f"Error: {response_data['error']}")
                    if response_data.get("took_ms"):
                        st.caption(f"⏱️ Response time: {response_data['took_ms']}ms")
            
            # Display the current user message
            with st.chat_message("user"):
                st.markdown(last_query)
            
            # Stream the assistant response
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                sources_placeholder = st.empty()
                error_placeholder = st.empty()
                time_placeholder = st.empty()
                
                try:
                    full_response = ""
                    sources = []
                    took_ms = 0
                    response_generator = call_knowledge_service_chat_stream(
                        query=last_query,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        search_limit=search_limit
                    )
                    
                    for chunk in response_generator:
                        if chunk.get("success"):
                            if "partial_response" in chunk:
                                full_response = chunk["partial_response"]
                                message_placeholder.markdown(full_response + "▌")
                                
                                # Update sources if available
                                if chunk.get("sources"):
                                    sources = chunk["sources"]
                            
                            elif chunk.get("done"):
                                full_response = chunk.get("answer", full_response)
                                sources = chunk.get("sources", sources)
                                took_ms = chunk.get("took_ms", 0)
                                break
                        else:
                            error_message = f"Error: {chunk.get('error', 'Unknown error')}"
                            error_placeholder.error(error_message)
                            
                            # Update session state with error
                            st.session_state.rag_chat_history[-1] = (last_query, {
                                "answer": error_message,
                                "sources": [],
                                "error": chunk.get('error', 'Unknown error'),
                                "model_used": "ollama"
                            })
                            
                            logger.log_error(user_email, f"RAG Chat Error: {chunk.get('error')}", "rag_chat_error")
                            return
                    
                    # Final update without cursor
                    message_placeholder.markdown(full_response)
                    
                    # Display sources
                    if sources and len(sources) > 0:
                        with sources_placeholder.expander(f"📚 Cited Sources ({len(sources)})"):
                            for i, source in enumerate(sources):
                                st.caption(f"**{i+1}. {source.get('metadata', {}).get('filename', 'Unknown Document')}** (Score: {source.get('score', 0):.2f})")
                                st.markdown(f"<small>{source.get('content', '')[:300]}...</small>", unsafe_allow_html=True)
                                st.markdown("---")
                    
                    # Display response time
                    if took_ms > 0:
                        time_placeholder.caption(f"⏱️ Response time: {took_ms}ms")
                    
                    # Update session state with final response
                    st.session_state.rag_chat_history[-1] = (last_query, {
                        "answer": full_response,
                        "sources": sources,
                        "took_ms": took_ms,
                        "model_used": "ollama"
                    })
                    
                    logger.log_ai_query(
                        user_email=user_email, 
                        query=last_query, 
                        response_tokens=len(full_response.split()) if full_response else 0
                    )

                except Exception as e:
                    error_message = f"An error occurred: {str(e)}"
                    error_placeholder.error(error_message)
                    
                    # Update session state with error
                    st.session_state.rag_chat_history[-1] = (last_query, {
                        "answer": error_message,
                        "sources": [],
                        "error": str(e),
                        "model_used": "ollama"
                    })
                    
                    logger.log_error(user_email, f"RAG Chat Error: {str(e)}", "rag_chat_error")
    
    else:
        # Display regular chat history
        with chat_container:
            if not api_documents:
                st.info("💬 Please upload documents first to start chatting with them.")
            
            # Display all chat history
            for query, response_data in st.session_state.rag_chat_history:
                with st.chat_message("user"):
                    st.markdown(query)
                with st.chat_message("assistant"):
                    st.markdown(response_data["answer"])
                    if response_data.get("sources") and len(response_data["sources"]) > 0:
                        with st.expander(f"📚 Cited Sources ({len(response_data['sources'])})"):
                            for i, source in enumerate(response_data["sources"]):
                                st.caption(f"**{i+1}. {source.get('metadata', {}).get('filename', 'Unknown Document')}** (Score: {source.get('score', 0):.2f})")
                                st.markdown(f"<small>{source.get('content', '')[:300]}...</small>", unsafe_allow_html=True)
                                st.markdown("---")
                    if response_data.get("error"):
                        st.error(f"Error: {response_data['error']}")
                    if response_data.get("took_ms"):
                        st.caption(f"⏱️ Response time: {response_data['took_ms']}ms")

    # Chat input
    prompt = st.chat_input("Ask a question about your documents...", key="rag_prompt")

    if prompt:
        st.session_state.current_rag_query = prompt
        
        # Add user message to chat history immediately with empty response
        st.session_state.rag_chat_history.append((prompt, {"answer": "", "sources": [], "model_used": "ollama"}))
        
        # Force refresh to show user message and start streaming
        st.rerun()


if __name__ == "__main__":
    display_navigation_sidebar(current_page="RAG Chat")
    display_rag_chat() 