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
    
    # Get provider status from LLM service
    if st.button("🔄 Refresh Provider Status", type="primary"):
        with st.spinner("Loading provider information..."):
            # Get models and provider info
            response = make_admin_request("/api/llm/models")
            health_response = make_admin_request("/api/llm/health")
            
            if response and response.status_code == 200:
                models_data = response.json()
                
                # Group models by provider
                provider_summary = {}
                for model in models_data:
                    provider = model.get("provider", "unknown")
                    if provider not in provider_summary:
                        provider_summary[provider] = {
                            "models": [],
                            "total_size": 0,
                            "capabilities": set()
                        }
                    
                    provider_summary[provider]["models"].append(model)
                    if model.get("size"):
                        provider_summary[provider]["total_size"] += model.get("size", 0)
                    
                    caps = model.get("capabilities", [])
                    if caps:
                        provider_summary[provider]["capabilities"].update(caps)
                
                # Display provider information
                for provider, info in provider_summary.items():
                    model_count = len(info["models"])
                    total_size_gb = info["total_size"] / (1024**3) if info["total_size"] > 0 else 0
                    capabilities = ", ".join(sorted(info["capabilities"]))
                    
                    # Provider status indicator
                    if health_response and health_response.status_code == 200:
                        health_data = health_response.json()
                        provider_health = health_data.get("providers", {}).get(provider, {})
                        status = provider_health.get("status", "unknown")
                        
                        if status == "healthy":
                            st.success(f"✅ **{provider.title()}**: {model_count} models available")
                        else:
                            st.warning(f"⚠️ **{provider.title()}**: {status}")
                    else:
                        st.info(f"🏭 **{provider.title()}**: {model_count} models")
                    
                    # Model details
                    with st.expander(f"View {provider} models"):
                        for model in info["models"][:5]:  # Show first 5 models
                            name = model.get("name", "unknown")
                            size = model.get("size", 0)
                            size_text = f" ({size / (1024**3):.1f}GB)" if size > 0 else ""
                            description = model.get("description", "")
                            st.write(f"• **{name}**{size_text}")
                            if description:
                                st.write(f"  _{description}_")
                        
                        if len(info["models"]) > 5:
                            st.write(f"... and {len(info['models']) - 5} more models")
                    
                    if total_size_gb > 0:
                        st.caption(f"Total storage: {total_size_gb:.1f}GB")
                    if capabilities:
                        st.caption(f"Capabilities: {capabilities}")
                    
                    st.markdown("---")
            else:
                st.error("❌ Failed to load provider information")
    
    # Current environment configuration
    st.subheader("Environment Configuration")
    
    # Get configuration from settings (config.json + env vars)
    try:
        with httpx.Client(timeout=5.0) as client:
            headers = {}
            token = st.session_state.get("access_token")
            if token:
                headers["Authorization"] = f"Bearer {token}"
            
            # Try to get config from a potential settings endpoint, or use fallback
            config_status = {
                "Ollama": {
                    "enabled": True,  # Default from config.json
                    "base_url": "http://ollama:11434",
                    "model": "llama3.2", 
                    "type": "Local"
                },
                "OpenAI": {
                    "enabled": False,  # Default from config.json
                    "api_key_configured": bool(os.getenv("OPENAI_API_KEY", "")),
                    "base_url": "https://api.openai.com/v1",
                    "model": "gpt-4",
                    "type": "Cloud API"
                },
                "Anthropic": {
                    "enabled": False,  # Default from config.json
                    "api_key_configured": bool(os.getenv("ANTHROPIC_API_KEY", "")),
                    "base_url": "https://api.anthropic.com", 
                    "model": "claude-3-5-sonnet-20241022",
                    "type": "Cloud API"
                }
            }
            
            # Override with environment variables if present
            if os.getenv("OLLAMA_ENABLED"):
                config_status["Ollama"]["enabled"] = os.getenv("OLLAMA_ENABLED", "true").lower() == "true"
            if os.getenv("OPENAI_ENABLED"):
                config_status["OpenAI"]["enabled"] = os.getenv("OPENAI_ENABLED", "false").lower() == "true"
            if os.getenv("ANTHROPIC_ENABLED"):
                config_status["Anthropic"]["enabled"] = os.getenv("ANTHROPIC_ENABLED", "false").lower() == "true"
                
    except Exception as e:
        st.error(f"Failed to load configuration: {e}")
        config_status = {}
    
    # Display configuration table
    for provider, config in config_status.items():
        enabled = config["enabled"]
        provider_type = config["type"]
        
        if enabled:
            if provider == "Ollama":
                st.success(f"✅ **{provider}** ({provider_type}): Enabled")
                st.write(f"   Base URL: `{config['base_url']}`")
                st.write(f"   Default Model: `{config['model']}`")
            else:
                api_key_status = "✅ Configured" if config.get("api_key_configured") else "❌ Not configured"
                if config.get("api_key_configured"):
                    st.success(f"✅ **{provider}** ({provider_type}): Enabled")
                else:
                    st.warning(f"⚠️ **{provider}** ({provider_type}): Enabled but API key missing")
                st.write(f"   API Key: {api_key_status}")
                st.write(f"   Default Model: `{config['model']}`")
        else:
            st.info(f"ℹ️ **{provider}** ({provider_type}): Disabled")
        
        st.markdown("---")

with col2:
    st.subheader("Configuration Guide")
    
    st.markdown("""
    **🔧 Provider Configuration:**
    
    **Method 1: config.json (Persistent)**
    ```json
    {
      "openai_enabled": true,
      "openai_api_key": "sk-your-key-here",
      "anthropic_enabled": true,
      "anthropic_api_key": "sk-ant-your-key-here"
    }
    ```
    
    **Method 2: Environment Variables (Override)**
    ```bash
    export OPENAI_ENABLED=true
    export OPENAI_API_KEY=sk-...
    export ANTHROPIC_ENABLED=true
    export ANTHROPIC_API_KEY=sk-ant-...
    ```
    """)
    
    st.info("💡 Edit config.json for persistent settings, use env vars for temporary overrides")
    st.warning("🔄 Restart services after changing configuration")

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