"""
PrivateGPT Legal AI - Direct LLM Chat Page
Direct chat interface with Ollama LLM for testing and general queries
"""

import streamlit as st
import requests
import json
import time
from datetime import datetime
import sys
import os

# Add parent directory to path to import pages_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pages_utils import (
    APP_TITLE, LLM_MODEL_NAME, OLLAMA_URL,
    initialize_session_state, require_auth, apply_page_styling,
    get_logger, display_navigation_sidebar, get_rag_engine
)

# Page configuration
st.set_page_config(
    page_title=f"LLM Chat - {APP_TITLE}", 
    page_icon="🤖",
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Initialize session state and check authentication
initialize_session_state()
require_auth(main_app_file="../app.py")

# Apply consistent styling
apply_page_styling()

# Initialize LLM chat specific session state
if "llm_chat_history" not in st.session_state:
    st.session_state.llm_chat_history = [] # Stores tuples of (query, response_dict)
if "current_llm_query" not in st.session_state:
    st.session_state.current_llm_query = ""

def call_ollama_direct(prompt: str, model: str = "llama3:8b") -> dict:
    """Direct call to Ollama API"""
    try:
        url = f"{OLLAMA_URL}/api/generate"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 2048
            }
        }
        
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        return {
            "answer": result.get("response", "No response generated"),
            "model": model,
            "tokens": len(result.get("response", "").split()),
            "success": True
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "answer": f"Error connecting to Ollama: {str(e)}",
            "model": model,
            "tokens": 0,
            "success": False
        }
    except Exception as e:
        return {
            "answer": f"Unexpected error: {str(e)}",
            "model": model,
            "tokens": 0,
            "success": False
        }

def get_available_models() -> list:
    """Get list of available models from Ollama"""
    try:
        url = f"{OLLAMA_URL}/api/tags"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        models = [model["name"] for model in result.get("models", [])]
        return models if models else ["llama3:8b"]  # Default fallback
        
    except Exception:
        return ["llama3:8b", "llama3:70b"]  # Default fallback

def display_llm_chat():
    """Display the direct LLM chat interface"""
    st.markdown(f'<div class="main-header">🤖 Direct LLM Chat</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">Interact directly with the Large Language Model. No document context is used here.</div>', unsafe_allow_html=True)

    rag_engine = get_rag_engine() # RAG engine usually wraps LLM calls
    logger = get_logger()
    user_email = st.session_state.user_email

    # Sidebar for LLM settings and controls (can be expanded later)
    with st.sidebar:
        st.markdown("### ⚙️ LLM Settings")
        # Example: temperature slider, model selection if multiple LLMs are available
        # temperature = st.slider("Temperature:", 0.0, 1.0, 0.7, 0.05, help="Controls randomness. Lower is more deterministic.")
        st.info("Settings like temperature or model choice can be added here if your LLM service supports them.")

        if st.button("🗑️ Clear Chat History", use_container_width=True, key="clear_llm_chat"):
            st.session_state.llm_chat_history = []
            st.session_state.current_llm_query = ""
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 💡 Note")
        st.caption("This chat bypasses document retrieval. For questions about specific documents, please use the 'Document Q&A (RAG)' page.")

    # Main chat area
    chat_container = st.container(height=600, border=False)
    with chat_container:
        for query, response_data in st.session_state.llm_chat_history:
            with st.chat_message("user"):
                st.markdown(query)
            with st.chat_message("assistant"):
                st.markdown(response_data["answer"])
                if response_data.get("error"):
                    st.error(f"Error: {response_data['error']}")

    # Chat input
    prompt = st.chat_input("Ask the LLM anything...", key="llm_prompt")

    if prompt:
        st.session_state.current_llm_query = prompt
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.spinner("🤖 LLM is thinking..."):
            try:
                # Use the RAG engine's direct LLM call method if it exists,
                # or implement a direct Ollama call here.
                # Assuming RAGEngine has a method like generate_direct_llm_response
                # For this example, we'll simulate it or call a simplified version of RAG's generate_response without context.
                
                # This would be a more direct call to the LLM, perhaps via rag_engine.generate_direct_llm_response
                # or a new method in RAGEngine that doesn't require context_documents.
                # For now, let's use the existing generate_response with empty context as a stand-in.
                ai_response = rag_engine.generate_response(query=prompt, context_documents=[]) 
                
                response_data = {
                    "answer": ai_response.get("answer", "No answer received."),
                    "model_used": ai_response.get("model_used"), # Ensure this is populated by generate_response
                    "error": ai_response.get("error")
                }
                
                logger.log_ai_query(
                    user_email=user_email, 
                    query=prompt, 
                    query_type="llm_direct",
                    response_preview=response_data["answer"][:100],
                    # response_tokens=ai_response.get("response_tokens") # If available
                )

            except Exception as e:
                logger.log_error(user_email, f"LLM Chat Error: {str(e)}", "llm_chat_error")
                response_data = {"answer": f"An error occurred: {str(e)}", "error": str(e)}

        st.session_state.llm_chat_history.append((prompt, response_data))
        with st.chat_message("assistant"):
            st.markdown(response_data["answer"])
            if response_data.get("error"):
                st.error(f"Error: {response_data['error']}")
        st.session_state.current_llm_query = "" # Clear after processing

# Display navigation sidebar
display_navigation_sidebar(current_page="LLM Chat")

# Main script logic
if __name__ == "__main__":
    display_llm_chat() 