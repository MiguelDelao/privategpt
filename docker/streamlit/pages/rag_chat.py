"""
PrivateGPT Legal AI - RAG Chat
Document-based Q&A with AI assistance
"""

import streamlit as st
import time
from datetime import datetime
from pages_utils import (
    APP_TITLE, initialize_session_state, require_auth, apply_page_styling,
    get_rag_engine, get_compliance_logger, add_demo_documents, display_navigation_sidebar
)

# Page configuration
st.set_page_config(
    page_title=f"RAG Chat - {APP_TITLE}",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state and check authentication
initialize_session_state()
require_auth(main_app_file="../app.py")

# Apply consistent styling
apply_page_styling()

# Add demo documents
add_demo_documents()

def display_rag_chat():
    """Display the RAG chat interface"""
    st.header("💬 RAG Chat - Document Q&A")
    st.markdown("Ask questions about your uploaded documents. The AI will provide answers with source citations.")
    
    # Current matter selection
    st.subheader("📁 Current Matter")
    current_matter = st.selectbox(
        "Select client matter",
        ["General Research", "Contract Review", "Case Analysis", "IP Filing"],
        index=0,
        key="rag_matter_select"
    )
    st.session_state.current_matter = current_matter
    
    st.markdown("---")
    
    # Chat interface
    st.subheader("💬 Chat Interface")
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        if st.session_state.chat_history:
            for message in st.session_state.chat_history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
                    if "sources" in message and message["sources"]:
                        with st.expander("📚 Sources"):
                            for source in message["sources"]:
                                st.markdown(f"- **{source['document']}** (Page {source.get('page', 'N/A')})")
        else:
            st.info("Start a conversation by typing a question below.")
    
    # Chat input
    if prompt := st.chat_input("Ask a question about your documents..."):
        # Add user message
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate AI response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing documents and generating response..."):
                try:
                    rag_engine = get_rag_engine()
                    response = rag_engine.query_documents(
                        query=prompt,
                        client_matter=current_matter,
                        user_email=st.session_state.user_email
                    )
                    
                    # Display response
                    st.markdown(response["answer"])
                    
                    # Show sources if available
                    if response.get("sources"):
                        with st.expander("📚 Sources"):
                            for source in response["sources"]:
                                st.markdown(f"- **{source['document']}** (Relevance: {source.get('score', 'N/A')})")
                    
                    # Add to chat history
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": response["answer"],
                        "sources": response.get("sources", [])
                    })
                    
                    # Log the interaction
                    compliance_logger = get_compliance_logger()
                    compliance_logger.log_ai_query(
                        user_email=st.session_state.user_email,
                        query=prompt,
                        response_tokens=len(response["answer"].split()) if response.get("answer") else 0
                    )
                    
                except Exception as e:
                    st.error(f"Error generating response: {str(e)}")
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": f"I apologize, but I encountered an error: {str(e)}"
                    })
    
    st.markdown("---")
    
    # Chat controls
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Clear Chat History", key="clear_rag_chat"):
            st.session_state.chat_history = []
            st.rerun()
    
    with col2:
        if st.button("📂 Go to Documents", key="goto_docs"):
            st.switch_page("pages/document_management.py")

    # Upload documents hint
    if not st.session_state.uploaded_documents:
        with st.container():
            st.info("💡 **Tip:** Upload documents first to get the best answers!")
            if st.button("📂 Go to Document Management", key="rag_upload_hint"):
                st.switch_page("pages/document_management.py")

# Display navigation sidebar
display_navigation_sidebar(current_page="RAG Chat")

# Main script logic
if __name__ == "__main__":
    display_rag_chat() 