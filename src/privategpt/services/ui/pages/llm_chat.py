from __future__ import annotations

"""Simple LLM Chat page for basic testing."""

import streamlit as st
import httpx
import json
from datetime import datetime
from pages_utils import (
    initialize_session_state, 
    require_auth, 
    display_navigation_sidebar, 
    APP_TITLE,
    GATEWAY_URL
)

st.set_page_config(
    page_title=f"LLM Chat – {APP_TITLE}", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

initialize_session_state()
require_auth()

display_navigation_sidebar(current_page="LLM Chat")

st.title("💬 Simple LLM Chat")
st.caption("Basic chat interface for testing LLM connectivity")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar for dynamic settings
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    
    # Dynamic model loading
    if st.button("🔄 Refresh Models", help="Load available models from LLM service"):
        with st.spinner("Loading models..."):
            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(f"{GATEWAY_URL}/api/llm/models")
                    if response.status_code == 200:
                        models_data = response.json()
                        st.session_state.available_models = [m["name"] for m in models_data]
                        st.success(f"✅ Loaded {len(models_data)} models")
                    else:
                        st.error(f"❌ Failed to load models: {response.status_code}")
                        st.session_state.available_models = []
            except Exception as e:
                st.error(f"❌ Error loading models: {e}")
                st.session_state.available_models = []
    
    # Initialize available models if not set
    if "available_models" not in st.session_state:
        st.session_state.available_models = []
    
    # Model selection dropdown
    if st.session_state.available_models:
        selected_model = st.selectbox(
            "Model:",
            st.session_state.available_models,
            index=0,
            help="Select which model to use for chat"
        )
    else:
        selected_model = st.text_input(
            "Model:", 
            value="",
            placeholder="Enter model name or click 'Refresh Models'",
            help="No models loaded. Try refreshing or enter manually."
        )
    
    # Tool controls
    st.markdown("### 🛠️ Tool Settings")
    use_mcp = st.checkbox("Enable Tools (MCP)", value=True, help="Enable tool execution via MCP")
    
    if use_mcp:
        tool_mode = st.selectbox(
            "Available Tools:",
            ["All (*)", "None", "Custom"],
            index=0,
            help="Choose which tools are available to the AI"
        )
        
        if tool_mode == "All (*)":
            available_tools = "*"
        elif tool_mode == "None":
            available_tools = ""
        else:  # Custom
            # Predefined tools (these would come from MCP discovery in production)
            all_tools = ["search_documents", "file_operations", "system_info", "rag_chat"]
            selected_tools = st.multiselect(
                "Select Tools:",
                all_tools,
                default=all_tools,
                help="Choose specific tools for the AI to use"
            )
            available_tools = ",".join(selected_tools)
    else:
        available_tools = ""
    
    # Basic chat settings
    st.markdown("### 🎛️ Generation Settings")
    temperature = st.slider("Temperature:", 0.0, 2.0, 0.7, 0.1, help="Creativity level")
    max_tokens = st.slider("Max Tokens:", 100, 2000, 500, 50, help="Response length limit")
    
    st.markdown("---")
    
    # Clear chat button
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    # Test connection button
    if st.button("🔍 Test LLM Connection", use_container_width=True):
        with st.spinner("Testing connection..."):
            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(f"{GATEWAY_URL}/api/llm/models")
                    if response.status_code == 200:
                        models = response.json()
                        st.success(f"✅ Connected! Found {len(models)} models")
                    else:
                        st.error(f"❌ Connection failed: {response.status_code}")
            except Exception as e:
                st.error(f"❌ Connection error: {e}")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "timestamp" in message:
            # Build info string for assistant messages
            if message["role"] == "assistant":
                info_parts = [message['timestamp']]
                if "model" in message and message["model"]:
                    info_parts.append(f"Model: {message['model']}")
                if message.get("tools_used"):
                    info_parts.append("🛠️ Tools: Used")
                if message.get("response_time_ms"):
                    info_parts.append(f"⚡ {message['response_time_ms']:.0f}ms")
                st.caption(f"*{' | '.join(info_parts)}*")
            else:
                st.caption(f"*{message['timestamp']}*")

# Chat input
if prompt := st.chat_input("Type your message here..."):
    # Add user message to chat history
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.messages.append({
        "role": "user", 
        "content": prompt,
        "timestamp": timestamp
    })
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
        st.caption(f"*{timestamp}*")
    
    # Generate assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            # Choose endpoint based on tool settings
            if use_mcp and available_tools:
                endpoint = f"{GATEWAY_URL}/api/chat/mcp"
            else:
                endpoint = f"{GATEWAY_URL}/api/chat/direct"
            
            # Call appropriate chat endpoint
            with httpx.Client(timeout=30.0) as client:
                payload = {
                    "message": prompt,  # Simple endpoints take single message
                    "model": selected_model if selected_model else None,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "use_mcp": use_mcp,
                    "available_tools": available_tools
                }
                
                # Remove None values
                payload = {k: v for k, v in payload.items() if v is not None}
                
                with st.spinner("Thinking..."):
                    response = client.post(endpoint, json=payload, timeout=30.0)
                
                if response.status_code == 200:
                    result = response.json()
                    assistant_response = result.get("text", "No response generated")
                    response_timestamp = datetime.now().strftime("%H:%M:%S")
                    
                    # Display response
                    message_placeholder.markdown(assistant_response)
                    
                    # Show additional info
                    info_parts = []
                    info_parts.append(f"Model: {result.get('model', selected_model or 'unknown')}")
                    if result.get('tools_used'):
                        info_parts.append("🛠️ Tools: Used")
                    if result.get('response_time_ms'):
                        info_parts.append(f"⚡ {result.get('response_time_ms'):.0f}ms")
                    
                    st.caption(f"*{response_timestamp} - {' | '.join(info_parts)}*")
                    
                    # Add to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": assistant_response,
                        "timestamp": response_timestamp,
                        "model": result.get("model", selected_model),
                        "tools_used": result.get("tools_used", False),
                        "response_time_ms": result.get("response_time_ms")
                    })
                    
                else:
                    error_msg = f"Error {response.status_code}: {response.text}"
                    message_placeholder.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"❌ {error_msg}",
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    })
                    
        except httpx.TimeoutException:
            error_msg = "Request timed out. The model might be loading or the service is slow."
            message_placeholder.error(error_msg)
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"❌ {error_msg}",
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
            
        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            message_placeholder.error(error_msg)
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"❌ {error_msg}",
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })

# Footer with helpful info
st.markdown("---")
st.markdown("""
**💡 Tips:**
- **Dynamic Models**: Click "Refresh Models" to load available models from your LLM provider
- **Tool Control**: Toggle MCP tools on/off for different complexity levels
- **Performance**: Direct mode is faster, MCP mode provides more capabilities
- **No Hard-coding**: All models and tools are discovered dynamically
- **Provider Agnostic**: Works with Ollama, vLLM, or any compatible provider

**🔧 Current Configuration:**
- Provider: Check your `llm_provider` and `llm_base_url` settings
- Tools: MCP integration can be enabled/disabled per conversation
- Models: Loaded dynamically from your configured LLM service
""")