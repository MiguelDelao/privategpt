"""
PrivateGPT Legal AI - RAG Chat
Document-based Q&A with AI assistance
"""

import streamlit as st
import requests
import time
import sys
import os

# Add parent directory to path to import pages_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pages_utils import (
    APP_TITLE, initialize_session_state, require_auth, 
    display_navigation_sidebar, apply_page_styling,
    get_logger
)

# Page configuration
st.set_page_config(
    page_title=f"RAG Chat - {APP_TITLE}", 
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply styling and authentication
apply_page_styling()
initialize_session_state()
require_auth()

# Knowledge Service URL
KNOWLEDGE_SERVICE_URL = "http://knowledge-service:8000"

# Initialize RAG chat specific session state
if "rag_chat_history" not in st.session_state:
    st.session_state.rag_chat_history = [] # Stores tuples of (query, response_dict)
if "selected_rag_document_source" not in st.session_state:
    st.session_state.selected_rag_document_source = "All Documents"
if "current_rag_query" not in st.session_state:
    st.session_state.current_rag_query = ""

def call_knowledge_service_chat(query: str, max_tokens: int = 1000, temperature: float = 0.7):
    """Call the knowledge service chat API"""
    try:
        payload = {
            "messages": [
                {"role": "user", "content": query}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "search_limit": 5,
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
        response = requests.get(f"{KNOWLEDGE_SERVICE_URL}/documents/", timeout=10)
        if response.status_code == 200:
            result = response.json()
            return result.get("documents", [])
        else:
            return []
    except Exception:
        return []

def display_rag_chat():
    """Display the RAG chat interface"""
    st.markdown(f'<div class="main-header">💬 Document Q&A (RAG)</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">Ask questions about your uploaded documents. The AI will use document content to generate answers.</div>', unsafe_allow_html=True)

    logger = get_logger()
    user_email = st.session_state.user_email

    # Load available documents from API
    api_documents = load_documents_from_api()
    available_sources = ["All Documents"] + sorted(list(set(doc.get("filename", "Unknown") for doc in api_documents)))
    
    # Sidebar for context selection and controls
    with st.sidebar:
        st.markdown("### ⚙️ Chat Settings")
        st.session_state.selected_rag_document_source = st.selectbox(
            "Select Document Context:",
            options=available_sources,
            index=available_sources.index(st.session_state.selected_rag_document_source) if st.session_state.selected_rag_document_source in available_sources else 0,
            help="Focus the AI's attention on a specific document or all documents."
        )
        
        # Temperature setting
        temperature = st.slider(
            "Response Creativity",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.1,
            help="Lower values = more focused answers, Higher values = more creative answers"
        )
        
        if st.button("🗑️ Clear Chat History", use_container_width=True, key="clear_rag_chat"):
            st.session_state.rag_chat_history = []
            st.session_state.current_rag_query = ""
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 💡 Tips")
        st.info("For best results: Be specific in your questions. The AI will search through your uploaded documents to find relevant information.")
        
        if not api_documents:
            st.warning("No documents found in the knowledge base. Please upload documents via the 'Documents' page.")
            if st.button("📂 Go to Documents", use_container_width=True):
                st.switch_page("pages/document_management.py")
        else:
            st.success(f"📚 {len(api_documents)} documents available")

    # Main chat area
    chat_container = st.container(height=500, border=False)
    with chat_container:
        if not api_documents:
             st.info("💬 Please upload documents first to start chatting with them.")
        
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
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.spinner("🧠 Searching documents and generating response..."):
            # Call the knowledge service chat API
            response_data = call_knowledge_service_chat(
                query=prompt,
                temperature=temperature,
                max_tokens=1000
            )
            
            if response_data["success"]:
                answer = response_data["answer"]
                sources = response_data.get("sources", [])
                took_ms = response_data.get("took_ms", 0)
                
                logger.log_ai_query(
                    user_email=user_email, 
                    query=prompt, 
                    response_tokens=len(answer.split()) if answer else 0
                )
                
                final_response = {
                    "answer": answer,
                    "sources": sources,
                    "took_ms": took_ms,
                    "model_used": response_data.get("model_used", "ollama")
                }
            else:
                logger.log_error(user_email, f"RAG Chat Error: {response_data['error']}", "rag_chat_error")
                final_response = {
                    "answer": f"I apologize, but I encountered an error: {response_data['error']}",
                    "sources": [],
                    "error": response_data["error"]
                }

        st.session_state.rag_chat_history.append((prompt, final_response))
        with st.chat_message("assistant"):
            st.markdown(final_response["answer"])
            if final_response.get("sources") and len(final_response["sources"]) > 0:
                with st.expander(f"📚 Cited Sources ({len(final_response['sources'])})"):
                    for i, source in enumerate(final_response["sources"]):
                        st.caption(f"**{i+1}. {source.get('metadata', {}).get('filename', 'Unknown Document')}** (Score: {source.get('score', 0):.2f})")
                        st.markdown(f"<small>{source.get('content', '')[:300]}...</small>", unsafe_allow_html=True)
                        st.markdown("---")
            if final_response.get("error"):
                st.error(f"Error: {final_response['error']}")
            if final_response.get("took_ms"):
                st.caption(f"⏱️ Response time: {final_response['took_ms']}ms")
        
        st.session_state.current_rag_query = ""


if __name__ == "__main__":
    display_navigation_sidebar(current_page="RAG Chat")
    display_rag_chat() 