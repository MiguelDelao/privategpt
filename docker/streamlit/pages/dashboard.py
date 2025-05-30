"""
PrivateGPT Legal AI - Dashboard
Main dashboard with system overview and quick actions
"""

import streamlit as st
import random
from datetime import datetime
from pages_utils import (
    APP_TITLE, LLM_MODEL_NAME, VECTOR_DB_NAME, WORKFLOW_ENGINE, VERSION_INFO,
    initialize_session_state, require_auth, apply_page_styling, add_demo_documents,
    display_navigation_sidebar
)

# Page configuration
st.set_page_config(
    page_title=f"Dashboard - {APP_TITLE}", 
    page_icon="🏠",
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Initialize session state and check authentication
initialize_session_state()
require_auth(main_app_file="../app.py")

# Apply consistent styling
apply_page_styling()

# Add demo documents
add_demo_documents()

def display_dashboard():
    """Display the dashboard content"""
    st.header(f"👋 Welcome to your Dashboard, {st.session_state.user_email}!")
    st.markdown(f"Leverage the power of **{LLM_MODEL_NAME}** for your legal analysis needs, securely within your private environment.")

    # System metrics
    cols = st.columns(3)
    with cols[0]:
        processed_docs_count = len([d for d in st.session_state.uploaded_documents if d["status"] == "Processed"])
        st.metric(label="Processed Documents", value=processed_docs_count)
    with cols[1]:
        # Mock value for demo purposes
        queries_today = random.randint(50, 200)
        query_delta = f"{random.randint(5,20)}% vs yesterday"
        st.metric(label="Queries Answered (Today)", value=queries_today, delta=query_delta)
    with cols[2]:
        st.metric(label="System Status", value="Operational ✅")
    
    st.markdown("---")

    # Quick actions
    st.subheader("Quick Actions")
    action_cols = st.columns(4)
    
    with action_cols[0]:
        if st.button("💬 RAG Chat", use_container_width=True, key="dash_rag_chat"):
            st.switch_page("pages/rag_chat.py")
    
    with action_cols[1]:
        if st.button("🤖 LLM Chat", use_container_width=True, key="dash_llm_chat"):
            st.switch_page("pages/llm_chat.py")
    
    with action_cols[2]:
        if st.button("📂 Documents", use_container_width=True, key="dash_documents"):
            st.switch_page("pages/document_management.py")
    
    with action_cols[3]:
        if st.session_state.user_role == "admin":
            if st.button("🛠️ Admin Panel", use_container_width=True, key="dash_admin"):
                st.switch_page("pages/admin_panel.py")
        else:
            st.button("💡 System Insights", use_container_width=True, disabled=True, key="dash_insights")

    st.markdown("---")

    # System overview
    st.subheader("System Overview")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        **Core AI Engine:**
        - **LLM:** {LLM_MODEL_NAME}
        - **Serving:** vLLM (OpenAI-compatible API)
        - **RAG & Vector Store:** {VECTOR_DB_NAME}
        - **Workflow Automation:** {WORKFLOW_ENGINE} for ingestion
        """)
        st.caption("Performance Target: P95 first-token latency ≤ 1s (400-token completion)")
    
    with col2:
        st.markdown("""
        **Key Features:**
        - **Privacy & Control:** Fully self-hosted, zero third-party data egress.
        - **Functionality:** Ingest documents, Q&A, Summarization.
        - **Security:** JWT Authentication, HTTPS, Encrypted Storage (LUKS).
        """)
        st.caption("UI built with Streamlit. Observability via Grafana Cloud.")
        
    st.markdown("---")

    # Recent activity
    st.subheader("Recent Activity")
    recent_activities = [
        {"activity": f"New Document '{st.session_state.uploaded_documents[0]['name']}' available for queries.", "time": "2 hours ago"},
        {"activity": "Chat session 'Contract Review Q&A' completed.", "time": "5 hours ago"},
        {"activity": f"User {st.session_state.user_email} logged in.", "time": "Just now"},
    ]
    
    for activity in recent_activities:
        st.text(f"- {activity['activity']} ({activity['time']})")

# Display navigation sidebar
display_navigation_sidebar(current_page="Dashboard")

# Main script logic
if __name__ == "__main__":
    display_dashboard() 