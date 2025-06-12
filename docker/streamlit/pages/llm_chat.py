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
    APP_TITLE, LLM_MODEL_NAME, OLLAMA_URL, KNOWLEDGE_SERVICE_URL,
    initialize_session_state, require_auth, apply_page_styling,
    get_logger, display_navigation_sidebar
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
require_auth(main_app_file="app.py")

# Apply consistent styling
apply_page_styling()

# Initialize LLM chat specific session state
if "llm_chat_history" not in st.session_state:
    st.session_state.llm_chat_history = [] # Stores tuples of (query, response_dict)
if "current_llm_query" not in st.session_state:
    st.session_state.current_llm_query = ""

def get_selected_model_from_settings() -> str:
    """Get the currently selected model from admin settings"""
    try:
        response = requests.get(f"{KNOWLEDGE_SERVICE_URL}/admin/settings", timeout=10)
        if response.status_code == 200:
            settings = response.json()
            return settings.get("SELECTED_MODEL", "llama3:8b")
        else:
            return "llama3:8b"  # Fallback
    except Exception:
        return "llama3:8b"  # Fallback

def call_ollama_direct_stream(prompt: str, model: str = None):
    """Direct call to Ollama API with streaming support - generator function"""
    if model is None:
        model = get_selected_model_from_settings()
    
    try:
        url = f"{OLLAMA_URL}/api/generate"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True  # Enable streaming
        }
        
        response = requests.post(url, json=payload, timeout=60, stream=True)
        response.raise_for_status()
        
        # Handle streaming response
        full_response = ""
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line.decode('utf-8'))
                    if 'response' in chunk:
                        full_response += chunk['response']
                        # Yield each chunk for real-time display
                        yield {
                            "partial_response": full_response,
                            "done": chunk.get('done', False),
                            "model": model,
                            "success": True
                        }
                    if chunk.get('done', False):
                        break
                except json.JSONDecodeError:
                    continue
        
    except requests.exceptions.RequestException as e:
        yield {
            "partial_response": f"Error connecting to Ollama: {str(e)}",
            "done": True,
            "model": model,
            "success": False
        }
    except Exception as e:
        yield {
            "partial_response": f"Unexpected error: {str(e)}",
            "done": True,
            "model": model,
            "success": False
        }

def call_ollama_direct(prompt: str, model: str = None) -> dict:
    """Direct call to Ollama API - non-streaming for compatibility"""
    if model is None:
        model = get_selected_model_from_settings()
    try:
        url = f"{OLLAMA_URL}/api/generate"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
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
    chat_container = st.container(border=False)
    
    # Check if there's a pending response to generate
    has_pending_response = (len(st.session_state.llm_chat_history) > 0 and 
                           st.session_state.llm_chat_history[-1][1]["answer"] == "")
    
    if has_pending_response:
        # Handle streaming response for the last message
        last_query = st.session_state.llm_chat_history[-1][0]
        
        with chat_container:
            # Display all previous completed messages
            for query, response_data in st.session_state.llm_chat_history[:-1]:
                with st.chat_message("user"):
                    st.markdown(query)
                with st.chat_message("assistant"):
                    st.markdown(response_data["answer"])
                    if response_data.get("error"):
                        st.error(f"Error: {response_data['error']}")
            
            # Display the current user message
            with st.chat_message("user"):
                st.markdown(last_query)
            
            # Stream the assistant response
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                
                try:
                    full_response = ""
                    response_generator = call_ollama_direct_stream(last_query)
                    
                    for chunk in response_generator:
                        if chunk.get("success") and "partial_response" in chunk:
                            full_response = chunk["partial_response"]
                            message_placeholder.markdown(full_response + "▌")
                            
                            if chunk.get("done"):
                                break
                    
                    # Final update without cursor
                    message_placeholder.markdown(full_response)
                    
                    # Update session state with final response
                    st.session_state.llm_chat_history[-1] = (last_query, {
                        "answer": full_response,
                        "model_used": get_selected_model_from_settings(),
                        "error": None
                    })
                    
                    logger.log_ai_query(
                        user_email=user_email, 
                        query=last_query, 
                        response_tokens=len(full_response.split())
                    )

                except Exception as e:
                    error_message = f"An error occurred: {str(e)}"
                    message_placeholder.markdown(error_message)
                    
                    # Update session state with error
                    st.session_state.llm_chat_history[-1] = (last_query, {
                        "answer": error_message,
                        "model_used": get_selected_model_from_settings(),
                        "error": str(e)
                    })
                    
                    logger.log_error(user_email, f"LLM Chat Error: {str(e)}", "llm_chat_error")
    
    else:
        # Display regular chat history
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
        # Add user message to chat history immediately
        st.session_state.llm_chat_history.append((prompt, {"answer": "", "model_used": get_selected_model_from_settings()}))
        
        # Force refresh to show user message in the container
        st.rerun()

# Display navigation sidebar
display_navigation_sidebar(current_page="LLM Chat")

# Main script logic
if __name__ == "__main__":
    display_llm_chat() 