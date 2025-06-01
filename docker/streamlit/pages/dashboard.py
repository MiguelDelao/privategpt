"""
PrivateGPT Legal AI - Dashboard
Main dashboard with system overview and quick actions
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os
from datetime import datetime
from pages_utils import (
    APP_TITLE, LLM_MODEL_NAME, VECTOR_DB_NAME, WORKFLOW_ENGINE, VERSION_INFO,
    initialize_session_state, require_auth, apply_page_styling, add_demo_documents,
    display_navigation_sidebar, get_logger, get_rag_engine
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

# Add parent directory to path to import pages_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Helper Functions ---
def get_recent_activities(limit=5):
    """Mockup for recent activities - replace with actual data source if available"""
    # Placeholder: In a real app, this would come from a database or logs
    demo_activities = [
        {"timestamp": datetime(2024, 7, 20, 10, 30), "user": st.session_state.user_email, "action": "Uploaded 'Alpha Corp MSA.pdf'", "type": "document"},
        {"timestamp": datetime(2024, 7, 20, 9, 15), "user": st.session_state.user_email, "action": "Started RAG chat on 'Contract Review'", "type": "chat"},
        {"timestamp": datetime(2024, 7, 19, 16, 45), "user": "legal.team@example.com", "action": "Searched for 'indemnity clauses'", "type": "search"},
        {"timestamp": datetime(2024, 7, 19, 14, 20), "user": st.session_state.user_email, "action": "Used LLM Chat for quick query", "type": "llm"},
        {"timestamp": datetime(2024, 7, 18, 11, 0), "user": "paralegal@example.com", "action": "Uploaded 'Case Brief XYZ.docx'", "type": "document"},
    ]
    # Add some dynamic elements for realism
    if "uploaded_documents" in st.session_state and st.session_state.uploaded_documents:
        last_doc = st.session_state.uploaded_documents[0]
        demo_activities.insert(0, {
            "timestamp": last_doc.get("ingested_at", datetime.now()), 
            "user": last_doc.get("uploaded_by", st.session_state.user_email), 
            "action": f"Processed '{last_doc['name']}'",
            "type": "document"
        })
    return sorted(demo_activities, key=lambda x: x["timestamp"], reverse=True)[:limit]

def get_document_statistics():
    """Get document statistics from RAG Engine or session state"""
    try:
        rag_engine = get_rag_engine()
        stats = rag_engine.get_document_stats()
        # Augment with session data if needed for a more complete picture during demo
        if not stats["total_documents"] and "uploaded_documents" in st.session_state:
            stats["total_documents"] = len(st.session_state.uploaded_documents)
            type_counts = {}
            for doc in st.session_state.uploaded_documents:
                doc_type = doc.get("type", "unknown")
                type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
            stats["document_types"] = type_counts
        return stats
    except Exception as e:
        # Fallback to session state if RAG engine fails (e.g. not fully started)
        # get_logger().log_error(st.session_state.user_email, f"Dashboard RAG stats error: {e}", "dashboard_stats")
        total_docs = len(st.session_state.get("uploaded_documents", []))
        type_counts = {}
        for doc in st.session_state.get("uploaded_documents", []):
            doc_type = doc.get("type", "unknown")
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
        return {"total_documents": total_docs, "document_types": type_counts, "average_doc_size_kb": 0}

def display_dashboard():
    """Display the main dashboard content"""
    
    st.markdown(f'<div class="main-header">🏠 {APP_TITLE} Dashboard</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">Welcome, {st.session_state.user_email}! Get an overview of your legal AI workspace.</div>', unsafe_allow_html=True)

    # Key Metrics Section
    st.markdown("### 📊 Key Metrics")
    doc_stats = get_document_statistics()
    total_documents = doc_stats.get("total_documents", 0)
    document_types_data = doc_stats.get("document_types", {})
    
    num_doc_types = len(document_types_data)
    avg_doc_size = doc_stats.get("average_doc_size_kb", 0)

    kpi_cols = st.columns(3)
    with kpi_cols[0]:
        st.metric(label="Total Documents Indexed", value=total_documents)
    with kpi_cols[1]:
        st.metric(label="Document Types Managed", value=num_doc_types)
    with kpi_cols[2]:
        st.metric(label="Avg. Document Size", value=f"{avg_doc_size:.1f} KB" if avg_doc_size else "N/A")

    st.markdown("<br>", unsafe_allow_html=True) # Spacer

    # Charts Section
    row2_cols = st.columns([2, 3]) # Adjusted column proportions

    with row2_cols[0]:
        st.markdown("#### 📁 Document Types Distribution")
        if document_types_data:
            doc_type_df = pd.DataFrame(list(document_types_data.items()), columns=['Document Type', 'Count']).sort_values("Count", ascending=False)
            fig_doc_types = px.bar(
                doc_type_df, 
                x='Document Type', 
                y='Count', 
                color='Document Type',
                labels={'Count': 'Number of Documents'},
                height=350,
                template="plotly_dark" # Using a dark theme for plotly
            )
            fig_doc_types.update_layout(
                margin=dict(l=20, r=20, t=30, b=20),
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)',
                legend_title_text='',
                xaxis_tickangle=-45
            )
            st.plotly_chart(fig_doc_types, use_container_width=True)
        else:
            st.info("No document type data available to display chart.")

    with row2_cols[1]:
        st.markdown("#### 📜 Recent Activity Feed")
        recent_activities = get_recent_activities()
        if recent_activities:
            for activity in recent_activities:
                col1, col2 = st.columns([1,4])
                with col1:
                    st.caption(activity["timestamp"].strftime("%b %d, %H:%M"))
                with col2:
                    icon = "📄" if activity["type"] == "document" else "💬" if activity["type"] == "chat" else "🔍" if activity["type"] == "search" else "🤖"
                    st.markdown(f"**{icon} {activity['action']}** <span style='color: #888'>by {activity['user']}</span>", unsafe_allow_html=True)
                st.markdown("<hr style='margin: 0.3rem 0; border-color: #4A4A7F;'>", unsafe_allow_html=True) # Subtle separator
        else:
            st.info("No recent activities to display.")

    st.markdown("<br>", unsafe_allow_html=True)

    # Quick Actions / Links Section
    st.markdown("### ⚡ Quick Actions")
    action_cols = st.columns(3)
    with action_cols[0]:
        if st.button("💬 Start New RAG Chat", use_container_width=True, type="primary"):
            st.switch_page("pages/rag_chat.py")
    with action_cols[1]:
        if st.button("📂 Upload Documents", use_container_width=True):
            st.switch_page("pages/document_management.py")
    with action_cols[2]:
        if st.button("🤖 Quick LLM Query", use_container_width=True):
            st.switch_page("pages/llm_chat.py")

# Display navigation sidebar
display_navigation_sidebar(current_page="Dashboard")

# Main script logic
if __name__ == "__main__":
    display_dashboard() 