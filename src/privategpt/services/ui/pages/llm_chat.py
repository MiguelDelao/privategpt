from __future__ import annotations

"""LLM Chat page with streaming support for direct model interaction."""

import streamlit as st
import time
from datetime import datetime
from pages_utils import (
    initialize_session_state, 
    require_auth, 
    display_navigation_sidebar, 
    APP_TITLE,
    get_llm_client,
    get_logger
)

st.set_page_config(
    page_title=f"LLM Chat – {APP_TITLE}", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

initialize_session_state()
require_auth()

display_navigation_sidebar(current_page="LLM Chat")

llm_client = get_llm_client()
logger = get_logger()

st.title("🤖 LLM Chat")
st.caption("Direct conversation with the language model")

# Initialize chat history if not exists
if "llm_messages" not in st.session_state:
    st.session_state.llm_messages = []

# Model selection and settings in sidebar
with st.sidebar:
    st.markdown("### Model Settings")
    
    # Get available models
    try:
        with st.spinner("Loading models..."):
            available_models = llm_client.get_models()
        
        model_names = [model["name"] for model in available_models]
        selected_model = st.selectbox(
            "Model", 
            model_names, 
            index=0 if model_names else None,
            key="selected_model"
        )
        
        # Model info
        if available_models and selected_model:
            model_info = next((m for m in available_models if m["name"] == selected_model), None)
            if model_info:
                st.caption(f"Size: {model_info.get('size', 0) / 1024 / 1024 / 1024:.1f} GB")
        
    except Exception as e:
        st.error(f"Failed to load models: {str(e)}")
        selected_model = "tinydolphin:latest"  # fallback
        st.info("Using fallback model: tinydolphin:latest")
    
    # Generation settings
    temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1, key="temperature")
    max_tokens = st.slider("Max Tokens", 50, 1000, 300, 50, key="max_tokens")
    
    # Streaming toggle
    use_streaming = st.toggle("Enable Streaming", value=True, key="use_streaming")
    
    st.markdown("---")
    
    # Chat controls
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.llm_messages = []
        st.rerun()
    
    # Health check
    try:
        health_status = llm_client.health_check()
        if health_status:
            st.success("🟢 LLM Service Online")
        else:
            st.error("🔴 LLM Service Offline")
    except:
        st.warning("🟡 LLM Service Status Unknown")

# Main chat interface
st.markdown("### Chat")

# Display chat messages
for i, message in enumerate(st.session_state.llm_messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # Show timestamp for messages
        if "timestamp" in message:
            st.caption(f"*{message['timestamp']}*")

# Chat input
if prompt := st.chat_input("Ask the AI anything..."):
    # Add user message to chat history
    timestamp = datetime.now().strftime("%H:%M:%S")
    user_message = {
        "role": "user", 
        "content": prompt,
        "timestamp": timestamp
    }
    st.session_state.llm_messages.append(user_message)
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
        st.caption(f"*{timestamp}*")
    
    # Generate AI response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        
        try:
            if use_streaming:
                # Streaming response
                full_response = ""
                start_time = time.time()
                
                with st.spinner("Thinking..."):
                    for chunk in llm_client.generate_stream(
                        prompt=prompt,
                        model=selected_model,
                        max_tokens=max_tokens,
                        temperature=temperature
                    ):
                        full_response += chunk
                        response_placeholder.markdown(full_response + "▌")
                        time.sleep(0.01)  # Small delay for visual effect
                
                # Final response without cursor
                response_placeholder.markdown(full_response)
                generation_time = time.time() - start_time
                
            else:
                # Non-streaming response
                with st.spinner("Generating response..."):
                    start_time = time.time()
                    full_response = llm_client.generate(
                        prompt=prompt,
                        model=selected_model,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                    generation_time = time.time() - start_time
                    response_placeholder.markdown(full_response)
            
            # Add response time caption
            response_timestamp = datetime.now().strftime("%H:%M:%S")
            st.caption(f"*{response_timestamp} • Generated in {generation_time:.1f}s • {len(full_response.split())} words*")
            
            # Add AI message to chat history
            assistant_message = {
                "role": "assistant",
                "content": full_response,
                "timestamp": response_timestamp,
                "generation_time": generation_time,
                "model": selected_model
            }
            st.session_state.llm_messages.append(assistant_message)
            
            # Log the interaction
            logger.log(
                level="info",
                message="LLM chat interaction",
                extra={
                    "user_email": st.session_state.user_email,
                    "model": selected_model,
                    "prompt_length": len(prompt),
                    "response_length": len(full_response),
                    "generation_time": generation_time,
                    "streaming": use_streaming
                }
            )
            
        except Exception as e:
            st.error(f"Failed to generate response: {str(e)}")
            st.info("Please check that the LLM service is running and accessible.")

# Chat statistics
if st.session_state.llm_messages:
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    total_messages = len(st.session_state.llm_messages)
    user_messages = len([m for m in st.session_state.llm_messages if m["role"] == "user"])
    assistant_messages = len([m for m in st.session_state.llm_messages if m["role"] == "assistant"])
    
    # Calculate average generation time
    generation_times = [m.get("generation_time", 0) for m in st.session_state.llm_messages if m["role"] == "assistant"]
    avg_generation_time = sum(generation_times) / len(generation_times) if generation_times else 0
    
    col1.metric("Total Messages", total_messages)
    col2.metric("Your Messages", user_messages)  
    col3.metric("AI Responses", assistant_messages)
    col4.metric("Avg Response Time", f"{avg_generation_time:.1f}s")

# Instructions
if not st.session_state.llm_messages:
    st.markdown("""
    ### 💡 How to use LLM Chat
    
    1. **Select a model** from the sidebar (tinydolphin:latest is recommended for faster responses)
    2. **Adjust settings** like temperature and max tokens as needed
    3. **Enable streaming** for real-time response generation
    4. **Type your message** in the chat input below
    5. **View responses** with generation time and word count
    
    This is a direct connection to the language model - no document context is included.
    For document-based Q&A, use the **RAG Chat** instead.
    """)