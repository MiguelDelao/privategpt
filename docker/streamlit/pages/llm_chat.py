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

# Add project root to path for config loader
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config_loader import get_config_loader

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

def get_selected_model() -> str:
    """Get the currently selected model from centralized Redis-backed config"""
    config_loader = get_config_loader()
    return config_loader.get("model.name", "llama3.2:1b")

def get_llm_settings() -> dict:
    """Get LLM settings from centralized Redis-backed config"""
    config_loader = get_config_loader()
    return {
        "max_tokens": config_loader.get("models.llm.default_max_tokens", 1000),
        "temperature": config_loader.get("models.llm.default_temperature", 0.7),
        "timeout_seconds": config_loader.get("models.llm.timeout_seconds", 120)
    }

def send_llm_query(prompt: str, system_prompt: str = None) -> dict:
    """Send query directly to Ollama LLM service"""
    try:
        model = get_selected_model()
        settings = get_llm_settings()
        
        # Default system prompt for LLM chat
        if not system_prompt:
            system_prompt = "You are a helpful AI assistant. Provide clear, accurate, and helpful responses."
        
        # Prepare request
        request_data = {
            "model": model,
            "prompt": f"System: {system_prompt}\n\nUser: {prompt}\n\nAssistant:",
            "stream": False,
            "options": {
                "temperature": settings["temperature"],
                "num_predict": settings["max_tokens"]
            }
        }
        
        # Send request to Ollama
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=request_data,
            timeout=settings["timeout_seconds"]
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "answer": result.get("response", "No response generated"),
                "model_used": model,
                "settings_used": settings,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}",
                "model_used": model,
                "timestamp": datetime.now().isoformat()
            }
            
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timed out. The model may be taking too long to respond.",
            "model_used": model,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error: {str(e)}",
            "model_used": get_selected_model(),
            "timestamp": datetime.now().isoformat()
        }

def send_llm_query_stream(prompt: str, system_prompt: str = None):
    """Send streaming query to Ollama LLM service"""
    try:
        model = get_selected_model()
        settings = get_llm_settings()
        
        # Default system prompt for LLM chat
        if not system_prompt:
            system_prompt = "You are a helpful AI assistant. Provide clear, accurate, and helpful responses."
        
        # Prepare request
        request_data = {
            "model": model,
            "prompt": f"System: {system_prompt}\n\nUser: {prompt}\n\nAssistant:",
            "stream": True,
            "options": {
                "temperature": settings["temperature"],
                "num_predict": settings["max_tokens"]
            }
        }
        
        # Send streaming request to Ollama
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=request_data,
            timeout=settings["timeout_seconds"],
            stream=True
        )
        
        if response.status_code == 200:
            full_response = ""
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line.decode('utf-8'))
                        if 'response' in chunk:
                            token = chunk['response']
                            full_response += token
                            yield token
                        if chunk.get('done', False):
                            break
                    except json.JSONDecodeError:
                        continue
            
            # Return final response info
            yield {
                "done": True,
                "full_response": full_response,
                "model_used": model,
                "settings_used": settings,
                "timestamp": datetime.now().isoformat()
            }
        else:
            yield {
                "error": f"HTTP {response.status_code}: {response.text}",
                "model_used": model,
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        yield {
            "error": f"Error: {str(e)}",
            "model_used": get_selected_model(),
            "timestamp": datetime.now().isoformat()
        }

def get_available_models() -> list:
    """Get list of available models from Ollama"""
    try:
        url = f"{OLLAMA_URL}/api/tags"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        models = [model["name"] for model in result.get("models", [])]
        return models if models else ["llama3.2:1b"]  # Default fallback
        
    except Exception:
        return ["llama3.2:1b", "llama3:8b"]  # Default fallback

# --- Main Page Layout ---

# Header
st.title("🤖 Direct LLM Chat")
st.markdown("Chat directly with the language model without document context")

# Display navigation sidebar
display_navigation_sidebar("LLM Chat")

# Current model info
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    current_model = get_selected_model()
    settings = get_llm_settings()
    st.info(f"**Current Model:** {current_model} | **Max Tokens:** {settings['max_tokens']} | **Temperature:** {settings['temperature']}")

with col2:
    if st.button("🔄 Refresh Models", help="Check for newly available models"):
        st.rerun()

with col3:
    # Model selection (for quick switching)
    available_models = get_available_models()
    if len(available_models) > 1:
        selected_model = st.selectbox(
            "Quick Switch Model",
            available_models,
            index=available_models.index(current_model) if current_model in available_models else 0,
            key="model_selector",
            help="Note: This is temporary. Use Admin Panel for permanent changes."
        )
        if selected_model != current_model:
            st.warning(f"⚠️ Model switched to {selected_model} for this session only. Use Admin Panel to make permanent changes.")

# Chat interface
st.markdown("---")

# Chat history display
if st.session_state.llm_chat_history:
    st.markdown("### Chat History")
    
    for i, (query, response_dict) in enumerate(reversed(st.session_state.llm_chat_history[-10:])):  # Show last 10
        with st.container():
            # User message
            st.markdown(f"**You:** {query}")
            
            # Assistant response
            if response_dict.get("success", True):
                st.markdown(f"**Assistant:** {response_dict.get('answer', 'No response')}")
                
                # Show metadata in expander
                with st.expander("Response Details", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.text(f"Model: {response_dict.get('model_used', 'Unknown')}")
                        st.text(f"Timestamp: {response_dict.get('timestamp', 'Unknown')}")
                    with col2:
                        if 'settings_used' in response_dict:
                            settings_used = response_dict['settings_used']
                            st.text(f"Max Tokens: {settings_used.get('max_tokens', 'Unknown')}")
                            st.text(f"Temperature: {settings_used.get('temperature', 'Unknown')}")
            else:
                st.error(f"**Error:** {response_dict.get('error', 'Unknown error')}")
            
            st.markdown("---")

# New query input
st.markdown("### Ask a Question")

# System prompt customization
with st.expander("🎛️ Advanced Options", expanded=False):
    custom_system_prompt = st.text_area(
        "Custom System Prompt (Optional)",
        placeholder="You are a helpful AI assistant specialized in...",
        help="Override the default system prompt to customize the AI's behavior"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        use_streaming = st.checkbox("Enable Streaming Response", value=True, help="Show response as it's generated")
    with col2:
        if st.button("🗑️ Clear Chat History"):
            st.session_state.llm_chat_history = []
            st.rerun()

# Query input
query = st.text_area(
    "Your Question:",
    value=st.session_state.current_llm_query,
    height=100,
    placeholder="Ask me anything! I can help with general questions, explanations, analysis, and more...",
    key="llm_query_input"
)

# Send button
col1, col2 = st.columns([1, 4])
with col1:
    send_button = st.button("🚀 Send", type="primary", disabled=not query.strip())

if send_button and query.strip():
    # Use selected model if different from current
    temp_model = None
    if 'model_selector' in st.session_state and st.session_state.model_selector != current_model:
        temp_model = st.session_state.model_selector
    
    # Add query to history immediately
    st.session_state.llm_chat_history.append((query, {"answer": "", "model_used": temp_model or current_model}))
    
    # Clear input
    st.session_state.current_llm_query = ""
    
    if use_streaming:
        # Streaming response
        with st.container():
            st.markdown(f"**You:** {query}")
            response_placeholder = st.empty()
            
            full_response = ""
            response_info = {}
            
            # Temporarily override model if selected
            if temp_model:
                original_model = get_config_loader().get("model.name")
                get_config_loader().set_setting("model.name", temp_model)
            
            try:
                for chunk in send_llm_query_stream(query, custom_system_prompt):
                    if isinstance(chunk, dict):
                        if "error" in chunk:
                            response_placeholder.error(f"**Error:** {chunk['error']}")
                            response_info = chunk
                            break
                        elif chunk.get("done"):
                            response_info = chunk
                            break
                    else:
                        full_response += chunk
                        response_placeholder.markdown(f"**Assistant:** {full_response}▌")
                
                # Final response without cursor
                if full_response and not response_info.get("error"):
                    response_placeholder.markdown(f"**Assistant:** {full_response}")
                    
                    # Update history with complete response
                    st.session_state.llm_chat_history[-1] = (query, {
                        "success": True,
                        "answer": full_response,
                        "model_used": response_info.get("model_used", temp_model or current_model),
                        "settings_used": response_info.get("settings_used", {}),
                        "timestamp": response_info.get("timestamp", datetime.now().isoformat())
                    })
                else:
                    # Update history with error
                    st.session_state.llm_chat_history[-1] = (query, response_info)
                    
            finally:
                # Restore original model if temporarily changed
                if temp_model:
                    get_config_loader().set_setting("model.name", original_model)
            
    else:
        # Non-streaming response
        with st.spinner("Generating response..."):
            # Temporarily override model if selected
            if temp_model:
                original_model = get_config_loader().get("model.name")
                get_config_loader().set_setting("model.name", temp_model)
            
            try:
                response_dict = send_llm_query(query, custom_system_prompt)
                
                # Update history with response
                st.session_state.llm_chat_history[-1] = (query, response_dict)
                
            finally:
                # Restore original model if temporarily changed
                if temp_model:
                    get_config_loader().set_setting("model.name", original_model)
    
    # Rerun to show updated history
    st.rerun()

# Footer
st.markdown("---")
st.markdown(f"**PrivateGPT Legal AI** - Direct LLM Chat | Model: {current_model}") 