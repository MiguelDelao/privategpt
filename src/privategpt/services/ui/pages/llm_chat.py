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
    
    # Provider and model loading
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🔄 Refresh", help="Load available providers and models"):
            with st.spinner("Loading providers and models..."):
                try:
                    with httpx.Client(timeout=10.0) as client:
                        headers = {}
                        token = st.session_state.get("access_token")
                        if token:
                            headers["Authorization"] = f"Bearer {token}"
                        
                        # Get models (now includes provider info)
                        response = client.get(f"{GATEWAY_URL}/api/llm/models", headers=headers)
                        if response.status_code == 200:
                            models_data = response.json()
                            st.session_state.models_data = models_data
                            
                            # Extract providers and models
                            providers = set()
                            provider_models = {}
                            for model in models_data:
                                provider = model.get("provider", "unknown")
                                providers.add(provider)
                                if provider not in provider_models:
                                    provider_models[provider] = []
                                provider_models[provider].append(model)
                            
                            st.session_state.available_providers = sorted(list(providers))
                            st.session_state.provider_models = provider_models
                            st.success(f"✅ Loaded {len(providers)} providers, {len(models_data)} models")
                        else:
                            st.error(f"❌ Failed to load models: {response.status_code}")
                            st.session_state.models_data = []
                            st.session_state.available_providers = []
                            st.session_state.provider_models = {}
                except Exception as e:
                    st.error(f"❌ Error loading models: {e}")
                    st.session_state.models_data = []
                    st.session_state.available_providers = []
                    st.session_state.provider_models = {}
    
    with col2:
        # Provider status indicator
        if hasattr(st.session_state, 'available_providers') and st.session_state.available_providers:
            provider_count = len(st.session_state.available_providers)
            model_count = len(st.session_state.get('models_data', []))
            st.metric("Providers", provider_count, help="Number of available LLM providers")
            st.metric("Models", model_count, help="Total available models across all providers")
    
    # Initial provider and model fetch on first load
    if "models_data" not in st.session_state:
        with st.spinner("Loading providers and models..."):
            try:
                with httpx.Client(timeout=10.0) as client:
                    headers = {}
                    token = st.session_state.get("access_token")
                    if token:
                        headers["Authorization"] = f"Bearer {token}"
                    resp = client.get(f"{GATEWAY_URL}/api/llm/models", headers=headers)
                    if resp.status_code == 200:
                        models_data = resp.json()
                        st.session_state.models_data = models_data
                        
                        # Extract providers and models
                        providers = set()
                        provider_models = {}
                        for model in models_data:
                            provider = model.get("provider", "unknown")
                            providers.add(provider)
                            if provider not in provider_models:
                                provider_models[provider] = []
                            provider_models[provider].append(model)
                        
                        st.session_state.available_providers = sorted(list(providers))
                        st.session_state.provider_models = provider_models
                    else:
                        st.session_state.models_data = []
                        st.session_state.available_providers = []
                        st.session_state.provider_models = {}
            except Exception:
                st.session_state.models_data = []
                st.session_state.available_providers = []
                st.session_state.provider_models = {}
    
    # Provider selection
    available_providers = st.session_state.get("available_providers", [])
    if available_providers:
        selected_provider = st.selectbox(
            "🏭 Provider:",
            ["All"] + available_providers,
            index=0,
            help="Filter models by provider"
        )
        
        # Get models for selected provider
        if selected_provider == "All":
            available_models = st.session_state.get("models_data", [])
        else:
            available_models = st.session_state.get("provider_models", {}).get(selected_provider, [])
        
        # Model selection dropdown with provider info
        if available_models:
            # Format model options with provider info
            model_options = []
            model_details = {}
            
            for model in available_models:
                name = model.get("name", "unknown")
                provider = model.get("provider", "unknown")
                size = model.get("size", 0)
                
                # Format display name
                if selected_provider == "All":
                    display_name = f"{provider}: {name}"
                else:
                    display_name = name
                
                # Add size info if available
                if size > 0:
                    size_gb = size / (1024**3)
                    display_name += f" ({size_gb:.1f}GB)"
                
                model_options.append(display_name)
                model_details[display_name] = model
            
            selected_model_display = st.selectbox(
                "🤖 Model:",
                model_options,
                index=0,
                help="Select which model to use for chat"
            )
            
            # Get the actual model data
            selected_model_data = model_details.get(selected_model_display, {})
            selected_model = selected_model_data.get("name", "")
            
            # Show model details
            if selected_model_data:
                provider = selected_model_data.get("provider", "unknown")
                capabilities = selected_model_data.get("capabilities", [])
                if capabilities:
                    caps_text = ", ".join(capabilities)
                    st.caption(f"📋 **Capabilities:** {caps_text}")
                st.caption(f"🏭 **Provider:** {provider}")
        else:
            st.warning(f"⚠️  No models found for provider '{selected_provider}'")
            selected_model = ""
    else:
        st.warning("⚠️  No providers found. Check your LLM service configuration.")
        selected_model = ""
    
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
                    headers = {}
                    token = st.session_state.get("access_token")
                    if token:
                        headers["Authorization"] = f"Bearer {token}"
                    response = client.get(f"{GATEWAY_URL}/api/llm/models", headers=headers)
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
            # Choose endpoint based on tool settings - USE STREAMING
            if use_mcp and available_tools:
                endpoint = f"{GATEWAY_URL}/api/chat/mcp/stream"
            else:
                endpoint = f"{GATEWAY_URL}/api/chat/direct/stream"
            
            # Call streaming chat endpoint
            with httpx.Client(timeout=180.0) as client:  # Longer timeout for streaming
                payload = {
                    "message": prompt,
                    "model": selected_model if selected_model else None,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "use_mcp": use_mcp,
                    "available_tools": available_tools
                }
                
                # Remove None values
                payload = {k: v for k, v in payload.items() if v is not None}
                
                # Start streaming
                assistant_response = ""
                response_timestamp = datetime.now().strftime("%H:%M:%S")
                
                with client.stream('POST', endpoint, json=payload, 
                                 headers={'Accept': 'text/event-stream'}) as response:
                    
                    if response.status_code == 200:
                        # Process streaming response
                        for line in response.iter_lines():
                            if line.startswith('data: '):
                                try:
                                    import json
                                    data = json.loads(line[6:])  # Remove 'data: ' prefix
                                    
                                    if data.get('type') == 'content_delta':
                                        # Add streaming content
                                        content = data.get('content', '')
                                        assistant_response += content
                                        # Update display in real-time
                                        message_placeholder.markdown(assistant_response + "▋")
                                        
                                    elif data.get('type') == 'message_complete':
                                        # Final message with metadata
                                        final_text = data.get('text', assistant_response)
                                        message_placeholder.markdown(final_text)
                                        
                                        # Show additional info
                                        info_parts = []
                                        info_parts.append(f"Model: {data.get('model', selected_model or 'unknown')}")
                                        if data.get('tools_used'):
                                            info_parts.append("🛠️ Tools: Used")
                                        if data.get('response_time_ms'):
                                            info_parts.append(f"⚡ {data.get('response_time_ms'):.0f}ms")
                                        
                                        st.caption(f"*{response_timestamp} - {' | '.join(info_parts)}*")
                                        
                                        # Add to chat history
                                        st.session_state.messages.append({
                                            "role": "assistant",
                                            "content": final_text,
                                            "timestamp": response_timestamp,
                                            "model": data.get("model", selected_model),
                                            "tools_used": data.get("tools_used", False),
                                            "response_time_ms": data.get("response_time_ms")
                                        })
                                        break
                                        
                                    elif data.get('type') == 'error':
                                        error_msg = data.get('message', 'Unknown streaming error')
                                        message_placeholder.error(f"❌ {error_msg}")
                                        st.session_state.messages.append({
                                            "role": "assistant",
                                            "content": f"❌ {error_msg}",
                                            "timestamp": response_timestamp
                                        })
                                        break
                                        
                                except json.JSONDecodeError:
                                    continue  # Skip invalid JSON lines
                                    
                    else:
                        error_msg = f"Error {response.status_code}: {response.text}"
                        message_placeholder.error(error_msg)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"❌ {error_msg}",
                            "timestamp": response_timestamp
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
- **Multi-Provider Support**: Switch between Ollama, OpenAI, Anthropic, and other providers
- **Dynamic Models**: Click "Refresh" to load available models from all configured providers
- **Provider Filtering**: Use the provider dropdown to focus on specific LLM providers
- **Tool Control**: Toggle MCP tools on/off for different complexity levels
- **Performance**: Direct mode is faster, MCP mode provides more capabilities

**🔧 Current Configuration:**
- **Providers**: Multiple LLM providers supported (Ollama, OpenAI, Anthropic)
- **Models**: Loaded dynamically with provider information and capabilities
- **Tools**: MCP integration can be enabled/disabled per conversation
- **Authentication**: All provider API keys managed securely through backend

**🏭 Provider Information:**
- **Ollama**: Local models (tinydolphin, llama3.2, etc.)
- **OpenAI**: Cloud models (GPT-4, GPT-3.5-turbo, etc.)
- **Anthropic**: Claude models (claude-3-5-sonnet, claude-3-haiku, etc.)
""")