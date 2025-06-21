from __future__ import annotations

"""Admin Panel page – Provider configuration and system management."""

import streamlit as st
import httpx
import json
import os
from pages_utils import initialize_session_state, require_auth, display_navigation_sidebar, APP_TITLE, GATEWAY_URL

st.set_page_config(page_title=f"Admin Panel – {APP_TITLE}", layout="wide", initial_sidebar_state="expanded")

initialize_session_state()
require_auth(admin_only=True)

display_navigation_sidebar(current_page="Admin Panel")

st.title("🔧 Admin Panel")
st.markdown("*System configuration and provider management*")

# Helper function for API requests
def make_admin_request(endpoint, method="GET", data=None):
    """Make API request with admin authentication"""
    try:
        auth_headers = {"Authorization": f"Bearer {st.session_state.get('access_token', '')}"}
        
        with httpx.Client(timeout=10.0) as client:
            if method == "GET":
                response = client.get(f"{GATEWAY_URL}{endpoint}", headers=auth_headers)
            elif method == "POST":
                response = client.post(f"{GATEWAY_URL}{endpoint}", json=data, headers=auth_headers)
            elif method == "PUT":
                response = client.put(f"{GATEWAY_URL}{endpoint}", json=data, headers=auth_headers)
            
            return response
    except Exception as e:
        st.error(f"Admin API request failed: {str(e)}")
        return None

# ═══════════════════════════════════════════════════════════════════════════════════════
# 🏭 PROVIDER CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════════════

st.header("🏭 LLM Provider Configuration")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Current Provider Status")
    
    if st.button("🔄 Refresh Provider Status", type="primary"):
        with st.spinner("Checking provider status..."):
            response = make_admin_request("/api/llm/models")
            if response and response.status_code == 200:
                models = response.json()
                providers = {}
                
                # Group by provider
                for model in models:
                    provider = model.get("provider", "unknown")
                    if provider not in providers:
                        providers[provider] = {"models": 0, "total_size": 0}
                    providers[provider]["models"] += 1
                    providers[provider]["total_size"] += model.get("size", 0)
                
                # Display provider status
                for provider, info in providers.items():
                    size_gb = info["total_size"] / (1024**3) if info["total_size"] > 0 else 0
                    
                    col_p1, col_p2, col_p3 = st.columns([2, 1, 1])
                    with col_p1:
                        st.write(f"**{provider.title()}**")
                    with col_p2:
                        st.metric("Models", info["models"])
                    with col_p3:
                        if size_gb > 0:
                            st.metric("Total Size", f"{size_gb:.1f} GB")
                        else:
                            st.metric("Type", "Cloud")
            else:
                st.error("❌ Unable to get provider status")

with col2:
    st.subheader("Quick Actions")
    
    if st.button("🔍 Test All Providers", use_container_width=True):
        st.info("Provider testing functionality coming soon")
    
    if st.button("📊 View Usage Stats", use_container_width=True):
        st.info("Usage statistics coming soon")
    
    if st.button("🔑 Manage API Keys", use_container_width=True):
        st.info("API key management coming soon")

# ═══════════════════════════════════════════════════════════════════════════════════════
# ⚙️ PROVIDER SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════════════

st.header("⚙️ Provider Settings")

# Current settings display
st.subheader("Current Configuration")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**🏭 Ollama**")
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    st.code(f"URL: {ollama_url}")
    st.write("Status: Local installation")

with col2:
    st.markdown("**🌐 OpenAI**")
    openai_key = os.getenv("OPENAI_API_KEY", "")
    if openai_key:
        st.code(f"API Key: {openai_key[:8]}...{openai_key[-4:]}")
        st.write("Status: ✅ Configured")
    else:
        st.code("API Key: Not configured")
        st.write("Status: ❌ Not configured")

with col3:
    st.markdown("**🧠 Anthropic**")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        st.code(f"API Key: {anthropic_key[:8]}...{anthropic_key[-4:]}")
        st.write("Status: ✅ Configured")
    else:
        st.code("API Key: Not configured")
        st.write("Status: ❌ Not configured")

# Configuration form
st.subheader("Update Provider Configuration")

with st.form("provider_config"):
    st.markdown("**Environment Variables Configuration**")
    st.info("ℹ️ Provider settings are managed via environment variables. Update your Docker Compose or environment configuration to change these values.")
    
    # Current values (read-only display)
    llm_provider = os.getenv("LLM_PROVIDER", "ollama")
    llm_base_url = os.getenv("LLM_BASE_URL", "http://llm-service:8000")
    llm_default_model = os.getenv("LLM_DEFAULT_MODEL", "")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_input("Default Provider", value=llm_provider, disabled=True, help="Set via LLM_PROVIDER env var")
        st.text_input("LLM Service URL", value=llm_base_url, disabled=True, help="Set via LLM_BASE_URL env var")
        
    with col2:
        st.text_input("Default Model", value=llm_default_model, disabled=True, help="Set via LLM_DEFAULT_MODEL env var")
        
        # Provider selection helper
        provider_options = ["ollama", "openai", "anthropic", "custom"]
        selected_provider = st.selectbox("Recommended Provider", provider_options, index=provider_options.index(llm_provider) if llm_provider in provider_options else 0, disabled=True)
    
    submitted = st.form_submit_button("💾 Configuration Info", type="secondary")
    
    if submitted:
        st.info("""
        **How to Update Configuration:**
        
        1. **Environment Variables**: Update your `.env` file or Docker Compose configuration
        2. **Restart Services**: Run `make restart` to apply changes
        3. **Verify**: Use the "Refresh Provider Status" button to confirm changes
        
        **Example .env entries:**
        ```
        LLM_PROVIDER=openai
        LLM_BASE_URL=http://llm-service:8000
        LLM_DEFAULT_MODEL=gpt-4
        OPENAI_API_KEY=sk-your-key-here
        ANTHROPIC_API_KEY=sk-ant-your-key-here
        ```
        """)

# ═══════════════════════════════════════════════════════════════════════════════════════
# 📊 SYSTEM INFORMATION
# ═══════════════════════════════════════════════════════════════════════════════════════

st.header("📊 System Information")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Service Status")
    
    if st.button("🏥 Check All Services"):
        with st.spinner("Checking services..."):
            # Check gateway status
            response = make_admin_request("/status")
            if response and response.status_code == 200:
                status_data = response.json()
                services = status_data.get("services", {})
                
                for service_name, service_info in services.items():
                    status = service_info.get("status", "unknown")
                    response_time = service_info.get("response_time_ms", 0)
                    
                    if status == "healthy":
                        st.success(f"✅ {service_name}: {status} ({response_time:.0f}ms)")
                    else:
                        st.error(f"❌ {service_name}: {status}")
            else:
                st.error("❌ Unable to get service status")

with col2:
    st.subheader("Configuration Summary")
    
    st.write(f"**Gateway URL:** `{GATEWAY_URL}`")
    st.write(f"**Current User:** `{st.session_state.get('user_email', 'Unknown')}`")
    st.write(f"**Admin Role:** ✅ Verified")
    
    # Environment info
    env = os.getenv("ENV", "local")
    st.write(f"**Environment:** `{env}`")
    
    # Database info
    db_url = os.getenv("DATABASE_URL", "Not configured")
    if "postgresql" in db_url.lower():
        st.write("**Database:** PostgreSQL")
    elif "sqlite" in db_url.lower():
        st.write("**Database:** SQLite")
    else:
        st.write("**Database:** Unknown")

# Footer
st.markdown("---")
st.caption("PrivateGPT v2 Admin Panel - Provider Configuration & System Management") 