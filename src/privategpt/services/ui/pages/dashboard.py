from __future__ import annotations

"""Simple Single-Page Testing Dashboard for PrivateGPT v2."""

import streamlit as st
import httpx
import json
from datetime import datetime
from pages_utils import initialize_session_state, require_auth, display_navigation_sidebar, APP_TITLE, GATEWAY_URL

st.set_page_config(
    page_title=f"Developer Dashboard – {APP_TITLE}", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

initialize_session_state()
require_auth()

display_navigation_sidebar(current_page="Dashboard")

st.title("🔧 Developer Testing Dashboard")
st.markdown("*Simple testing interface for PrivateGPT v2*")

# Helper function for API requests
def make_api_request(endpoint, method="GET", data=None):
    """Simple API request helper"""
    try:
        auth_headers = {"Authorization": f"Bearer {st.session_state.get('access_token', '')}"}
        
        with httpx.Client(timeout=10.0) as client:
            if method == "GET":
                response = client.get(f"{GATEWAY_URL}{endpoint}", headers=auth_headers)
            elif method == "POST":
                response = client.post(f"{GATEWAY_URL}{endpoint}", json=data, headers=auth_headers)
            
            return response
    except Exception as e:
        st.error(f"Connection failed: {str(e)}")
        return None

# ═══════════════════════════════════════════════════════════════════════════════════════
# 🏥 SYSTEM STATUS
# ═══════════════════════════════════════════════════════════════════════════════════════

st.header("🏥 System Status")

col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    if st.button("🔄 Check All Services", type="primary", use_container_width=True):
        with st.spinner("Checking services..."):
            # Check gateway
            response = make_api_request("/status")
            if response and response.status_code == 200:
                st.success("✅ Gateway: Online")
                status_data = response.json()
                
                # Show service statuses
                services = status_data.get("services", {})
                for service_name, service_info in services.items():
                    status = service_info.get("status", "unknown")
                    response_time = service_info.get("response_time_ms", 0)
                    
                    if status == "healthy":
                        st.success(f"✅ {service_name}: {status} ({response_time:.0f}ms)")
                    else:
                        st.error(f"❌ {service_name}: {status}")
            else:
                st.error("❌ Gateway: Offline")

with col2:
    st.write("**Connection Info:**")
    st.write(f"Gateway: `{GATEWAY_URL}`")
    st.write(f"User: `{st.session_state.get('user_email', 'Unknown')}`")
    
    # Debug auth token
    token = st.session_state.get('access_token')
    if token:
        st.write(f"Auth: ✅ Active (Token: {token[:20]}...)")
    else:
        st.write("Auth: ❌ No Token")
        
    st.write(f"Authenticated: {st.session_state.get('authenticated', False)}")

with col3:
    st.metric("Current Time", datetime.now().strftime("%H:%M:%S"))

# ═══════════════════════════════════════════════════════════════════════════════════════
# 💬 QUICK CHAT TEST
# ═══════════════════════════════════════════════════════════════════════════════════════

st.header("💬 Quick Chat Test")

col1, col2 = st.columns([3, 1])

with col1:
    test_message = st.text_area(
        "Test Message:",
        value="Hello! What models do you have available?",
        height=80,
        help="Enter a message to test the AI chat functionality"
    )

with col2:
    model_choice = st.selectbox(
        "Model:",
        ["tinydolphin:latest", "llama3.2:1b", "privategpt-mcp"],
        help="Choose which model to test with"
    )
    
    st.write("**Model Info:**")
    model_info = {
        "tinydolphin:latest": "636 MB - Fast",
        "llama3.2:1b": "1.3 GB - Small", 
        "privategpt-mcp": "Tools enabled"
    }
    st.caption(model_info.get(model_choice, "Unknown"))

if st.button("🚀 Test LLM Service", type="primary", use_container_width=True):
    with st.spinner("Testing LLM service..."):
        # Test LLM service health directly
        try:
            response = make_api_request("/api/llm/models")
            if response and response.status_code == 200:
                st.success("✅ LLM Service is working!")
                models = response.json()
                st.write(f"**Available models:** {len(models)}")
                for model in models[:3]:  # Show first 3 models
                    name = model.get('name', 'Unknown')
                    size = model.get('size', 0)
                    size_gb = size / (1024**3) if size > 0 else 0
                    st.write(f"- {name} ({size_gb:.1f} GB)")
            else:
                st.error("❌ LLM Service not available")
                if response:
                    st.write(f"Status: {response.status_code}")
        except Exception as e:
            st.error(f"❌ Connection error: {e}")

st.info("💡 **Note:** Chat testing is temporarily disabled while fixing database issues. Use **Enhanced LLM Chat** page for full chat functionality.")

# ═══════════════════════════════════════════════════════════════════════════════════════
# 🛠️ AVAILABLE MODELS
# ═══════════════════════════════════════════════════════════════════════════════════════

st.header("🛠️ Available Models")

if st.button("📋 List Models", use_container_width=True):
    with st.spinner("Getting models..."):
        response = make_api_request("/api/llm/models")
        if response and response.status_code == 200:
            models = response.json()
            
            if models:
                for model in models:
                    name = model.get('name', 'Unknown')
                    size = model.get('size', 0)
                    size_gb = size / (1024**3) if size > 0 else 0
                    
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"**{name}**")
                    with col2:
                        st.write(f"{size_gb:.1f} GB" if size_gb > 0 else "Unknown size")
                    with col3:
                        if name in ["tinydolphin:latest", "llama3.2:1b"]:
                            st.success("✅ Ready")
                        else:
                            st.info("🔄 Available")
            else:
                st.warning("No models found")
        else:
            st.error("❌ Could not get models")

# ═══════════════════════════════════════════════════════════════════════════════════════
# 🔍 API TESTING
# ═══════════════════════════════════════════════════════════════════════════════════════

st.header("🔍 API Testing")

col1, col2 = st.columns([2, 2])

with col1:
    endpoint = st.selectbox(
        "Endpoint:",
        [
            "/status",
            "/api/chat/conversations",
            "/api/llm/models",
            "/health",
            "/api/prompts/"
        ]
    )
    
    method = st.selectbox("Method:", ["GET", "POST"])

with col2:
    if method == "POST":
        request_body = st.text_area(
            "Request Body (JSON):",
            value='{"title": "Test conversation"}',
            height=60
        )
    else:
        request_body = None

if st.button("🚀 Send API Request", use_container_width=True):
    with st.spinner("Sending request..."):
        try:
            data = None
            if request_body and method == "POST":
                data = json.loads(request_body)
        except json.JSONDecodeError:
            st.error("❌ Invalid JSON in request body")
            data = None

        if method != "POST" or data is not None or request_body is None:
            response = make_api_request(endpoint, method, data)
            
            if response:
                # Show status
                if response.status_code < 300:
                    st.success(f"✅ {response.status_code}")
                else:
                    st.error(f"❌ {response.status_code}")
                
                # Show response
                try:
                    content = response.json()
                    st.json(content)
                except:
                    st.text(response.text)

# ═══════════════════════════════════════════════════════════════════════════════════════
# 💡 QUICK HELP
# ═══════════════════════════════════════════════════════════════════════════════════════

st.header("💡 Quick Help")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **🚀 Getting Started:**
    1. Check services are online
    2. Test chat with tinydolphin model
    3. Go to LLM Chat for full features
    
    **🔧 Troubleshooting:**
    - If services offline → restart containers
    - If chat fails → try tinydolphin first
    - If connection errors → check Docker logs
    """)

with col2:
    st.markdown("""
    **📚 Available Features:**
    - **LLM Chat**: Full chat with debugging
    - **RAG Chat**: Document-aware chat (coming soon)
    - **Models**: tinydolphin (fast), llama3.2 (better)
    
    **🛠️ For Developers:**
    - API testing interface above
    - Full debugging in chat pages
    - Tool integration with MCP models
    """)

# Footer
st.markdown("---")
st.caption("PrivateGPT v2 Developer Dashboard - Simplified Interface")