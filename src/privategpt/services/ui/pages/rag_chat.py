from __future__ import annotations

"""Enhanced RAG Chat page for developer testing with document retrieval."""

import streamlit as st
import httpx
import json
from datetime import datetime
from pages_utils import (
    initialize_session_state, 
    require_auth, 
    display_navigation_sidebar, 
    APP_TITLE
)

st.set_page_config(
    page_title=f"RAG Chat – {APP_TITLE}", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

initialize_session_state()
require_auth()

display_navigation_sidebar(current_page="RAG Chat")

# Custom CSS for RAG interface
st.markdown("""
<style>
.rag-response {
    background-color: #f8f9fa;
    border-left: 4px solid #28a745;
    padding: 10px;
    margin: 10px 0;
}
.document-context {
    background-color: #e7f3ff;
    border: 1px solid #b8e0ff;
    padding: 10px;
    border-radius: 5px;
    margin: 10px 0;
}
.retrieval-info {
    background-color: #f0f4f8;
    border: 1px solid #d1e7dd;
    padding: 10px;
    border-radius: 5px;
    margin: 10px 0;
}
.thinking-box {
    background-color: #fff3cd;
    border: 1px solid #ffeaa7;
    padding: 10px;
    border-radius: 5px;
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)

st.title("📚 Enhanced RAG Chat")
st.caption("Document-aware conversation with retrieval debugging and MCP integration")

# Helper function for API requests
def make_api_request(endpoint, method="GET", data=None, headers=None):
    """Helper function to make API requests"""
    try:
        gateway_url = st.session_state.get("gateway_url", "http://localhost:8000")
        auth_headers = {"Authorization": f"Bearer {st.session_state.get('access_token', '')}"}
        if headers:
            auth_headers.update(headers)
        
        with httpx.Client(timeout=30.0) as client:
            if method == "GET":
                response = client.get(f"{gateway_url}{endpoint}", headers=auth_headers)
            elif method == "POST":
                response = client.post(f"{gateway_url}{endpoint}", json=data, headers=auth_headers)
            
            return response
    except Exception as e:
        st.error(f"API request failed: {e}")
        return None

# Initialize RAG chat state
if "rag_conversation_id" not in st.session_state:
    st.session_state.rag_conversation_id = None
if "rag_messages" not in st.session_state:
    st.session_state.rag_messages = []

# Sidebar for RAG settings and debug options
with st.sidebar:
    st.markdown("### 🔧 RAG Settings")
    
    # Model selection
    selected_model = st.selectbox(
        "Model:",
        ["privategpt-mcp", "llama3.2:3b", "qwen2.5:3b"],
        key="rag_selected_model"
    )
    
    # RAG specific settings
    st.markdown("### 📚 Retrieval Settings")
    
    retrieval_k = st.slider("Documents to Retrieve", 1, 20, 5, key="rag_k")
    similarity_threshold = st.slider("Similarity Threshold", 0.0, 1.0, 0.7, 0.1, key="rag_threshold")
    
    st.markdown("### 🐛 Debug Options")
    
    # Debug toggles
    show_retrieved_docs = st.checkbox("Show Retrieved Documents", value=True, key="show_docs")
    show_retrieval_scores = st.checkbox("Show Similarity Scores", value=True, key="show_scores")
    show_thinking = st.checkbox("Show Thinking", value=True, key="rag_show_thinking")
    show_raw_response = st.checkbox("Show Raw Response", value=False, key="rag_show_raw")
    show_context_used = st.checkbox("Show Context Used", value=True, key="show_context")
    
    st.markdown("### 🔍 RAG Health")
    
    # RAG status check
    if st.button("🔍 Check RAG Status", key="check_rag"):
        with st.spinner("Checking RAG service..."):
            response = make_api_request("/health/rag")
            if response and response.status_code == 200:
                st.success("✅ RAG Service Healthy")
            else:
                st.error("❌ RAG Service Unavailable")
    
    # Document count check
    if st.button("📄 Check Document Count", key="check_docs"):
        with st.spinner("Checking documents..."):
            # This would need to be implemented in the API
            st.info("🚧 Document count endpoint not implemented yet")
    
    st.markdown("---")
    
    # Chat controls
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.rag_conversation_id = None
        st.session_state.rag_messages = []
        st.rerun()
    
    if st.button("🔄 New Conversation", use_container_width=True):
        st.session_state.rag_conversation_id = None
        st.rerun()

# Main chat interface
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown("### 💬 Document-Aware Conversation")
    
    # Display chat messages with RAG debugging
    for i, message in enumerate(st.session_state.rag_messages):
        with st.chat_message(message["role"]):
            # Main content
            st.markdown(message["content"])
            
            # Retrieved documents display
            if message["role"] == "assistant" and show_retrieved_docs and message.get("retrieved_docs"):
                st.markdown('<div class="document-context">', unsafe_allow_html=True)
                st.markdown("**📚 Retrieved Documents:**")
                for j, doc in enumerate(message["retrieved_docs"]):
                    score = doc.get("score", 0)
                    filename = doc.get("filename", "Unknown")
                    content_preview = doc.get("content", "")[:200] + "..."
                    
                    if show_retrieval_scores:
                        st.write(f"**{j+1}. {filename}** (similarity: {score:.3f})")
                    else:
                        st.write(f"**{j+1}. {filename}**")
                    
                    with st.expander(f"Preview: {filename}"):
                        st.write(content_preview)
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Context used display
            if message["role"] == "assistant" and show_context_used and message.get("context_used"):
                st.markdown('<div class="retrieval-info">', unsafe_allow_html=True)
                st.markdown("**🎯 Context Used in Response:**")
                st.write(message["context_used"][:500] + "..." if len(message["context_used"]) > 500 else message["context_used"])
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Thinking display
            if message["role"] == "assistant" and show_thinking and message.get("thinking"):
                st.markdown('<div class="thinking-box">', unsafe_allow_html=True)
                st.markdown("**🧠 Thinking:**")
                st.info(message["thinking"])
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Raw response display
            if message["role"] == "assistant" and show_raw_response and message.get("raw_response"):
                with st.expander("📋 Raw Response"):
                    st.code(message["raw_response"], language="json")
            
            # Timestamp and metadata
            timestamp = message.get("timestamp", "Unknown time")
            model = message.get("model", "")
            generation_time = message.get("generation_time", 0)
            
            if message["role"] == "assistant":
                doc_count = len(message.get("retrieved_docs", []))
                st.caption(f"*{timestamp} • {model} • {generation_time:.1f}s • {doc_count} docs*")
            else:
                st.caption(f"*{timestamp}*")

with col2:
    st.markdown("### 📊 RAG Info")
    
    # Current conversation info
    if st.session_state.rag_conversation_id:
        st.success(f"**Conversation:** {st.session_state.rag_conversation_id[:8]}...")
    else:
        st.info("**No active conversation**")
    
    st.metric("Model", selected_model)
    st.metric("Messages", len(st.session_state.rag_messages))
    st.metric("Retrieval K", retrieval_k)
    
    # Show retrieval statistics
    assistant_messages = [m for m in st.session_state.rag_messages if m["role"] == "assistant"]
    if assistant_messages:
        total_docs = sum(len(m.get("retrieved_docs", [])) for m in assistant_messages)
        avg_docs = total_docs / len(assistant_messages) if assistant_messages else 0
        st.metric("Avg Docs/Response", f"{avg_docs:.1f}")

# Chat input
if prompt := st.chat_input("Ask questions about your documents..."):
    # For now, show that RAG is not fully implemented yet
    st.warning("🚧 **RAG Backend Not Fully Implemented**")
    st.info("""
    The RAG (Retrieval-Augmented Generation) service is not yet fully connected to the API gateway.
    
    **When implemented, this will:**
    - Search through uploaded documents
    - Retrieve relevant context for your questions
    - Generate responses using document context
    - Show which documents were used
    - Display similarity scores and context
    
    **For now, use the Enhanced LLM Chat** which has MCP tools that can:
    - Search existing documents using `search_documents` tool
    - Read specific files using `read_file` tool
    - List directories using `list_directory` tool
    """)

# Instructions for when RAG is implemented
if not st.session_state.rag_messages:
    st.markdown("---")
    st.markdown("""
    ### 📚 Enhanced RAG Chat - Developer Features
    
    **Document Retrieval:**
    - Semantic search through your document collection
    - Configurable similarity thresholds and document counts
    - Support for multiple document types (PDF, TXT, DOCX, etc.)
    
    **Debug Features:**
    - **Retrieved Documents**: See which documents were found relevant
    - **Similarity Scores**: Check how well documents match your query
    - **Context Used**: View the exact text used to generate responses
    - **Thinking Display**: AI's reasoning with document context
    
    **RAG Configuration:**
    - Adjust number of documents to retrieve (K parameter)
    - Set similarity thresholds for relevance filtering
    - Monitor retrieval performance and accuracy
    
    **Integration with MCP:**
    - Combines document retrieval with tool capabilities
    - Enhanced responses using both context and real-time tools
    - Debug tool calls alongside document usage
    
    💡 *Once the RAG service is connected, this will be a powerful document Q&A interface*
    """)
else:
    # RAG statistics (placeholder for when implemented)
    st.markdown("---")
    st.markdown("**RAG Statistics:** Coming soon when backend is connected") 