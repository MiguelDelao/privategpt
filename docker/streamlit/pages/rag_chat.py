"""
PrivateGPT Legal AI - RAG Chat
Document-based Q&A with AI assistance
"""

import streamlit as st
import time
import sys
import os

# Add parent directory to path to import pages_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pages_utils import (
    APP_TITLE, initialize_session_state, require_auth, 
    display_navigation_sidebar, apply_page_styling,
    get_logger, get_rag_engine, add_demo_documents
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
# add_demo_documents() # Only if you want demo docs to influence RAG context choices initially

# Initialize RAG chat specific session state
if "rag_chat_history" not in st.session_state:
    st.session_state.rag_chat_history = [] # Stores tuples of (query, response_dict)
if "selected_rag_document_source" not in st.session_state:
    st.session_state.selected_rag_document_source = "All Documents"
if "current_rag_query" not in st.session_state:
    st.session_state.current_rag_query = ""

def display_rag_chat():
    """Display the RAG chat interface"""
    st.markdown(f'<div class="main-header">💬 Document Q&A (RAG)</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">Ask questions about your uploaded documents. The AI will use document content to generate answers.</div>', unsafe_allow_html=True)

    rag_engine = get_rag_engine()
    logger = get_logger()
    user_email = st.session_state.user_email

    # Document Context / Client Matter Selection
    # In a real app, this might be a more sophisticated filter or based on user context
    # For now, using a simple selectbox or deriving from uploaded documents
    uploaded_documents = st.session_state.get("uploaded_documents", [])
    available_sources = ["All Documents"] + sorted(list(set(doc["name"] for doc in uploaded_documents)))
    
    # Sidebar for context selection and controls
    with st.sidebar:
        st.markdown("### ⚙️ Chat Settings")
        st.session_state.selected_rag_document_source = st.selectbox(
            "Select Document Context:",
            options=available_sources,
            index=available_sources.index(st.session_state.selected_rag_document_source) if st.session_state.selected_rag_document_source in available_sources else 0,
            help="Focus the AI's attention on a specific document or all documents."
        )
        
        if st.button("🗑️ Clear Chat History", use_container_width=True, key="clear_rag_chat"):
            st.session_state.rag_chat_history = []
            st.session_state.current_rag_query = ""
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 💡 Tips")
        st.info("For best results: Be specific in your questions. If asking about a particular document, select it from the context menu.")
        if not uploaded_documents:
            st.warning("No documents uploaded yet. Please upload documents via the 'Documents' page for the AI to answer questions about them.")
            if st.button("📂 Go to Documents", use_container_width=True):
                st.switch_page("pages/document_management.py")

    # Main chat area
    chat_container = st.container(height=500, border=False) # Use container for scrollable chat
    with chat_container:
        if not uploaded_documents and st.session_state.selected_rag_document_source == "All Documents":
             st.info("💬 Please upload documents first to start chatting with them.")
        
        for query, response_data in st.session_state.rag_chat_history:
            with st.chat_message("user"):
                st.markdown(query)
            with st.chat_message("assistant"):
                st.markdown(response_data["answer"])
                if response_data.get("sources"):
                    with st.expander("Cited Sources"):
                        for i, source in enumerate(response_data["sources"]):
                            st.caption(f"{i+1}. {source['source']} (Score: {source['score']:.2f})")
                            st.markdown(f"<small>{source['content'][:200]}...</small>", unsafe_allow_html=True)
                            st.markdown("---")
                if response_data.get("error"):
                    st.error(f"Error: {response_data['error']}")

    # Chat input
    prompt = st.chat_input("Ask a question about your documents...", key="rag_prompt")

    if prompt:
        st.session_state.current_rag_query = prompt
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.spinner("🧠 Thinking & searching documents..."):
            try:
                # Determine client_matter/source for filtering
                client_matter_filter = None # Or derive from selected_rag_document_source if it represents a client matter
                source_filter = None
                if st.session_state.selected_rag_document_source != "All Documents":
                    source_filter = st.session_state.selected_rag_document_source
                
                # 1. Search relevant documents (R part of RAG)
                # We will pass source_filter to search_documents if implemented there
                # For now, assuming search_documents handles a general query and we rely on LLM to focus if context is too broad.
                # A more robust implementation would filter documents in RAGEngine based on `source_filter`.
                
                # TEMP: Simplified search for now, RAGEngine should ideally allow filtering by source filename
                relevant_docs = rag_engine.search_documents(query=prompt, limit=3, client_matter=client_matter_filter)
                
                # Filter further if a specific document was selected and search_documents doesn't directly support it
                if source_filter and relevant_docs:
                    filtered_docs_for_llm = [doc for doc in relevant_docs if doc['source'] == source_filter]
                    if not filtered_docs_for_llm: # If specific doc search yields nothing, broaden slightly or notify
                         # This logic can be improved, e.g. pass source_filter to rag_engine.search_documents
                         pass # For now, just use what search_documents returned broadly
                    else:
                        relevant_docs = filtered_docs_for_llm

                # 2. Generate response using LLM with context (G part of RAG)
                ai_response = rag_engine.generate_response(query=prompt, context_documents=relevant_docs)
                
                response_data = {
                    "answer": ai_response.get("answer", "No answer found."),
                    "sources": relevant_docs, # Pass the searched documents as sources
                    "model_used": ai_response.get("model_used"),
                    "error": ai_response.get("error")
                }
                
                logger.log_ai_query(
                    user_email=user_email, 
                    query=prompt, 
                    response_tokens=ai_response.get("response_tokens") # If available
                )

            except Exception as e:
                logger.log_error(user_email, f"RAG Chat Error: {str(e)}", "rag_chat_error")
                response_data = {"answer": f"An error occurred: {str(e)}", "sources": [], "error": str(e)}

        st.session_state.rag_chat_history.append((prompt, response_data))
        with st.chat_message("assistant"):
            st.markdown(response_data["answer"])
            if response_data.get("sources"):
                with st.expander("Cited Sources"):
                    for i, source_doc in enumerate(response_data["sources"]):
                        st.caption(f"{i+1}. {source_doc['source']} (Score: {source_doc['score']:.2f})")
                        st.markdown(f"<small>{source_doc['content'][:200]}...</small>", unsafe_allow_html=True)
                        st.markdown("---") # Visual separator between sources
            if response_data.get("error"):
                st.error(f"Error: {response_data['error']}")
        st.session_state.current_rag_query = "" # Clear after processing
        # No st.rerun() here to keep the input field active and allow multiple queries


if __name__ == "__main__":
    display_navigation_sidebar(current_page="RAG Chat")
    display_rag_chat() 