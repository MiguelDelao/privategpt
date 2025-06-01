"""
PrivateGPT Legal AI - Direct LLM Chat Page
Direct chat interface with Ollama LLM for testing and general queries
"""

import streamlit as st
import requests
import json
import time
from datetime import datetime
from pages_utils import (
    APP_TITLE, LLM_MODEL_NAME, OLLAMA_URL,
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
require_auth(main_app_file="../app.py")

# Apply consistent styling
apply_page_styling()

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
    st.header("🤖 LLM Chat - Direct Model Access")
    st.markdown("Chat directly with the language model without document context. Perfect for testing and general queries.")
    
    # Simple model selection
    col1, col2 = st.columns([2, 1])
    with col1:
        available_models = get_available_models()
        selected_model = st.selectbox("Select Model", available_models, key="llm_model_select")
    with col2:
        if st.button("🗑️ Clear Chat"):
            st.session_state.llm_chat_history = []
            st.rerun()

    # Display existing chat messages
    if not st.session_state.llm_chat_history:
        st.info("💡 Start a conversation by asking any question. This is direct LLM chat without document context.")

    # Display chat history
    for message in st.session_state.llm_chat_history:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.markdown(message["content"])
                st.caption(f"🕒 {message['timestamp'].strftime('%H:%M:%S')}")
        else:
            with st.chat_message("assistant"):
                st.markdown(message["content"])
                
                # Show model info
                model_used = message.get("model", "Unknown")
                tokens = message.get("tokens", 0)
                success = message.get("success", True)
                
                status_emoji = "✅" if success else "❌"
                st.caption(f"🕒 {message['timestamp'].strftime('%H:%M:%S')} | Model: {model_used} | Tokens: {tokens} {status_emoji}")

    # Chat input
    if prompt := st.chat_input("Ask the LLM anything...", key="llm_chat_input"):
        # Add user message to history
        st.session_state.llm_chat_history.append({
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now()
        })
        
        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)
            st.caption(f"🕒 {datetime.now().strftime('%H:%M:%S')}")

        # Generate LLM response
        with st.chat_message("assistant"):
            # Prepare full prompt with system context
            system_prompt = "You are a helpful AI assistant."
            full_prompt = f"{system_prompt}\n\nUser: {prompt}\nAssistant:"
            
            # Show processing status
            with st.status(f"🤖 Generating response with {selected_model}...", expanded=True) as status:
                start_time = time.time()
                
                # Call Ollama
                response = call_ollama_direct(full_prompt, selected_model)
                
                end_time = time.time()
                generation_time = end_time - start_time
                
                status.update(
                    label=f"✅ Response generated in {generation_time:.1f}s", 
                    state="complete", 
                    expanded=False
                )
            
            # Display response with streaming effect
            message_placeholder = st.empty()
            full_response = response["answer"]
            
            if response["success"] and st.session_state.get("enable_streaming", True):
                # Simulate streaming
                displayed_text = ""
                words = full_response.split()
                for i, word in enumerate(words):
                    displayed_text += word + " "
                    message_placeholder.markdown(displayed_text + "▌")
                    time.sleep(0.03)  # Streaming speed
                message_placeholder.markdown(full_response)
            else:
                message_placeholder.markdown(full_response)
            
            # Show model info
            status_emoji = "✅" if response["success"] else "❌"
            st.caption(f"🕒 {datetime.now().strftime('%H:%M:%S')} | Model: {response['model']} | Tokens: {response['tokens']} {status_emoji}")
        
        # Log AI interaction
        logger = get_logger()
        
        logger.log_ai_query(
            user_email=st.session_state.user_email,
            query=prompt,
            response_tokens=response["tokens"]
        )
        
        # Add assistant response to history
        st.session_state.llm_chat_history.append({
            "role": "assistant",
            "content": response["answer"],
            "model": response["model"],
            "tokens": response["tokens"],
            "success": response["success"],
            "timestamp": datetime.now()
        })

    # Warning notice
    st.markdown("---")
    st.markdown("""
    <div class="legal-disclaimer">
        <strong>Note:</strong> This is direct LLM chat without access to your uploaded documents. 
        For document-based queries, use the RAG Chat feature.
    </div>
    """, unsafe_allow_html=True)

# Display navigation sidebar
display_navigation_sidebar(current_page="LLM Chat")

# Main script logic
if __name__ == "__main__":
    display_llm_chat() 