from __future__ import annotations

"""Enhanced LLM Chat page for developer testing with MCP integration."""

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
    page_title=f"LLM Chat – {APP_TITLE}", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

initialize_session_state()
require_auth()

display_navigation_sidebar(current_page="LLM Chat")

# Custom CSS for developer interface
st.markdown("""
<style>
.dev-response {
    background-color: #f8f9fa;
    border-left: 4px solid #007bff;
    padding: 10px;
    margin: 10px 0;
}
.thinking-box {
    background-color: #fff3cd;
    border: 1px solid #ffeaa7;
    padding: 10px;
    border-radius: 5px;
    margin: 10px 0;
}
.tool-call-box {
    background-color: #d1ecf1;
    border: 1px solid #bee5eb;
    padding: 10px;
    border-radius: 5px;
    margin: 10px 0;
}
.json-viewer {
    background-color: #1e1e1e;
    color: #d4d4d4;
    padding: 10px;
    border-radius: 5px;
    font-family: 'Courier New', monospace;
    font-size: 12px;
}
</style>
""", unsafe_allow_html=True)

st.title("🤖 Enhanced LLM Chat")
st.caption("Developer testing interface with MCP integration, thinking display, and tool call tracking")

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

# Initialize chat state
if "dev_conversation_id" not in st.session_state:
    st.session_state.dev_conversation_id = None
if "dev_messages" not in st.session_state:
    st.session_state.dev_messages = []

# Sidebar for settings and debug options
with st.sidebar:
    st.markdown("### 🔧 Developer Settings")
    
    # Model selection
    selected_model = st.selectbox(
        "Model:",
        ["privategpt-mcp", "llama3.2:3b", "qwen2.5:3b", "tinydolphin:latest"],
        key="dev_selected_model"
    )
    
    st.markdown("### 🐛 Debug Options")
    
    # Debug toggles
    show_thinking = st.checkbox("Show Thinking", value=True, key="show_thinking")
    show_raw_response = st.checkbox("Show Raw Response", value=False, key="show_raw")
    show_tool_calls = st.checkbox("Show Tool Calls", value=True, key="show_tools")
    show_ui_tags = st.checkbox("Show UI Tags", value=False, key="show_ui_tags")
    show_json_debug = st.checkbox("JSON Debug View", value=False, key="show_json")
    
    st.markdown("### 🛠️ MCP Integration")
    
    # MCP status check
    if st.button("🔍 Check MCP Status", key="check_mcp"):
        with st.spinner("Checking MCP..."):
            response = make_api_request("/health/mcp")
            if response and response.status_code == 200:
                st.success("✅ MCP Service Healthy")
            else:
                st.error("❌ MCP Service Unavailable")
    
    # System prompt display
    if st.button("👁️ View System Prompt", key="view_prompt"):
        with st.spinner("Getting system prompt..."):
            response = make_api_request(f"/api/prompts/for-model/{selected_model}")
            if response and response.status_code == 200:
                prompt_data = response.json()
                with st.expander("📝 Current System Prompt"):
                    st.code(prompt_data.get("prompt", "No prompt available"), language="xml")
    
    st.markdown("---")
    
    # Chat controls
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.dev_conversation_id = None
        st.session_state.dev_messages = []
        st.rerun()
    
    if st.button("🔄 New Conversation", use_container_width=True):
        st.session_state.dev_conversation_id = None
        st.rerun()

# Main chat interface
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown("### 💬 Conversation")
    
    # Display chat messages with enhanced debugging
    for i, message in enumerate(st.session_state.dev_messages):
        with st.chat_message(message["role"]):
            # Main content
            st.markdown(message["content"])
            
            # Enhanced debug info for assistant messages
            if message["role"] == "assistant" and show_thinking and message.get("thinking"):
                st.markdown('<div class="thinking-box">', unsafe_allow_html=True)
                st.markdown("**🧠 Thinking:**")
                st.info(message["thinking"])
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Tool calls display
            if message["role"] == "assistant" and show_tool_calls and message.get("has_tool_calls"):
                st.markdown('<div class="tool-call-box">', unsafe_allow_html=True)
                st.markdown("**🛠️ Tool calls executed**")
                if message.get("tool_call_details"):
                    for tool in message["tool_call_details"]:
                        st.write(f"- {tool.get('tool_name', 'Unknown tool')}: {tool.get('status', 'Unknown status')}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            # UI tags display
            if message["role"] == "assistant" and show_ui_tags and message.get("ui_tags"):
                with st.expander("🏷️ UI Tags"):
                    st.json(message["ui_tags"])
            
            # Raw response display
            if message["role"] == "assistant" and show_raw_response and message.get("raw_response"):
                with st.expander("📋 Raw Response"):
                    st.code(message["raw_response"], language="json")
            
            # JSON debug view
            if show_json_debug:
                with st.expander("🔍 JSON Debug"):
                    st.json(message)
            
            # Timestamp and metadata
            timestamp = message.get("timestamp", "Unknown time")
            model = message.get("model", "")
            generation_time = message.get("generation_time", 0)
            
            if message["role"] == "assistant":
                st.caption(f"*{timestamp} • {model} • {generation_time:.1f}s*")
            else:
                st.caption(f"*{timestamp}*")

with col2:
    st.markdown("### 📊 Chat Info")
    
    # Current conversation info
    if st.session_state.dev_conversation_id:
        st.success(f"**Conversation:** {st.session_state.dev_conversation_id[:8]}...")
    else:
        st.info("**No active conversation**")
    
    st.metric("Model", selected_model)
    st.metric("Messages", len(st.session_state.dev_messages))
    
    # Show average response time
    assistant_messages = [m for m in st.session_state.dev_messages if m["role"] == "assistant"]
    if assistant_messages:
        avg_time = sum(m.get("generation_time", 0) for m in assistant_messages) / len(assistant_messages)
        st.metric("Avg Response", f"{avg_time:.1f}s")

# Chat input
if prompt := st.chat_input("Ask the AI anything (with MCP tools available)..."):
    # Create conversation if needed
    if not st.session_state.dev_conversation_id:
        conv_data = {
            "title": f"Dev Chat - {datetime.now().strftime('%H:%M:%S')}",
            "model_name": selected_model
        }
        
        with st.spinner("Creating conversation..."):
            response = make_api_request("/api/chat/conversations", "POST", conv_data)
            
            if response and response.status_code == 201:
                st.session_state.dev_conversation_id = response.json()["id"]
                st.success("✅ Conversation created")
            else:
                st.error("❌ Failed to create conversation")
                st.stop()
    
    # Add user message to display
    timestamp = datetime.now().strftime("%H:%M:%S")
    user_message = {
        "role": "user",
        "content": prompt,
        "timestamp": timestamp
    }
    st.session_state.dev_messages.append(user_message)
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
        st.caption(f"*{timestamp}*")
    
    # Send message via API
    with st.chat_message("assistant"):
        with st.spinner("Generating response..."):
            chat_data = {
                "message": prompt,
                "model_name": selected_model,
                "stream": False
            }
            
            response = make_api_request(
                f"/api/chat/conversations/{st.session_state.dev_conversation_id}/chat",
                "POST",
                chat_data
            )
            
            if response and response.status_code == 200:
                result = response.json()
                assistant_response = result.get("response", {})
                
                # Display main content
                content = assistant_response.get("content", "No response content")
                st.markdown(content)
                
                # Prepare message for storage
                timestamp = datetime.now().strftime("%H:%M:%S")
                assistant_message = {
                    "role": "assistant",
                    "content": content,
                    "timestamp": timestamp,
                    "model": selected_model,
                    "generation_time": result.get("generation_time", 0),
                    "thinking": assistant_response.get("data", {}).get("thinking"),
                    "has_tool_calls": assistant_response.get("data", {}).get("has_tool_calls", False),
                    "ui_tags": assistant_response.get("data", {}).get("ui_tags", {}),
                    "raw_response": json.dumps(result, indent=2) if show_raw_response else None
                }
                
                # Add tool call details if available
                if assistant_message["has_tool_calls"]:
                    assistant_message["tool_call_details"] = result.get("tool_calls", [])
                
                st.session_state.dev_messages.append(assistant_message)
                
                # Show thinking immediately if enabled
                if show_thinking and assistant_message["thinking"]:
                    st.markdown('<div class="thinking-box">', unsafe_allow_html=True)
                    st.markdown("**🧠 Thinking:**")
                    st.info(assistant_message["thinking"])
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Show tool calls immediately if enabled
                if show_tool_calls and assistant_message["has_tool_calls"]:
                    st.markdown('<div class="tool-call-box">', unsafe_allow_html=True)
                    st.markdown("**🛠️ Tool calls executed**")
                    for tool in assistant_message.get("tool_call_details", []):
                        st.write(f"- {tool.get('tool_name', 'Unknown')}: {tool.get('status', 'Unknown')}")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Show generation info
                gen_time = result.get("generation_time", 0)
                st.caption(f"*{timestamp} • {selected_model} • {gen_time:.1f}s*")
                
            else:
                st.error("❌ Failed to send message")
                if response:
                    st.write(f"Status: {response.status_code}")
                    st.write(f"Response: {response.text}")

# Developer instructions and tips
if not st.session_state.dev_messages:
    st.markdown("---")
    st.markdown("""
    ### 🔧 Enhanced LLM Chat - Developer Features
    
    **MCP Integration:**
    - Available models include `privategpt-mcp` with full tool access
    - Test document search, file operations, and system commands
    - Toggle tool call display in sidebar
    
    **Debug Features:**
    - **Thinking Display**: See AI's reasoning process (similar to DeepSeek R1)
    - **Raw Response**: View complete API response data
    - **UI Tags**: Check XML tag parsing results
    - **JSON Debug**: Full message object inspection
    
    **Testing Capabilities:**
    - Switch models mid-conversation
    - View system prompts for each model
    - Monitor MCP service health
    - Track response times and tool usage
    
    **Example Prompts:**
    - "Search my documents for information about machine learning"
    - "List the contents of my project directory"
    - "Create a new file called test.py with a hello world script"
    - "What tools do you have available?"
    
    💡 *Use the sidebar controls to customize your debugging experience*
    """)
else:
    # Chat statistics
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    total_messages = len(st.session_state.dev_messages)
    user_messages = len([m for m in st.session_state.dev_messages if m["role"] == "user"])
    assistant_messages = [m for m in st.session_state.dev_messages if m["role"] == "assistant"]
    tool_call_messages = len([m for m in assistant_messages if m.get("has_tool_calls")])
    
    # Calculate average generation time
    generation_times = [m.get("generation_time", 0) for m in assistant_messages]
    avg_generation_time = sum(generation_times) / len(generation_times) if generation_times else 0
    
    col1.metric("Total Messages", total_messages)
    col2.metric("User Messages", user_messages)  
    col3.metric("Tool Calls", tool_call_messages)
    col4.metric("Avg Response", f"{avg_generation_time:.1f}s")