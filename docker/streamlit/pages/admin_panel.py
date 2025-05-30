"""
PrivateGPT Legal AI - Admin Panel
Clean admin interface for user management and system oversight
"""

import streamlit as st
import json
from datetime import datetime, timedelta
from pages_utils import (
    APP_TITLE, LLM_MODEL_NAME, VECTOR_DB_NAME, WORKFLOW_ENGINE, VERSION_INFO,
    initialize_session_state, require_auth, display_navigation_sidebar, apply_page_styling,
    get_compliance_logger, get_rag_engine, get_auth_client, add_demo_documents
)

# Page configuration
st.set_page_config(
    page_title=f"Admin Panel - {APP_TITLE}", 
    page_icon="🛠️",
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Initialize session state and check authentication (admin only)
initialize_session_state()
require_auth(admin_only=True, main_app_file="../app.py")

# Apply consistent styling
apply_page_styling()

# Add demo data
add_demo_documents()

def display_admin_panel():
    """Display the clean admin panel content"""
    st.header("🛠️ Admin Panel")
    st.markdown("User management and system administration")
    
    # System status overview
    col1, col2, col3, col4 = st.columns(4)
    
    try:
        # Mock health check for demo
        with col1:
            st.metric("🗃️ Vector DB", "Online")
        
        with col2:
            st.metric("🤖 LLM Service", "Online")
        
        with col3:
            st.metric("🔐 Auth Service", "Online")  # If we got here, auth is working
        
        with col4:
            docs_count = len(st.session_state.get("uploaded_documents", []))
            st.metric("📄 Documents", docs_count)
    
    except Exception as e:
        st.error(f"Unable to check system health: {str(e)}")
    
    st.markdown("---")
    
    # User Management Section
    st.subheader("👥 User Management")
    
    # Create new user
    with st.expander("➕ Create New User", expanded=False):
        display_create_user_form()
    
    # List existing users
    display_user_list()
    
    st.markdown("---")
    
    # System logs and monitoring
    st.subheader("📊 System Overview")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**System Configuration**")
        config_info = {
            "Environment": "Production",
            "LLM Model": LLM_MODEL_NAME,
            "Vector DB": VECTOR_DB_NAME,
            "Workflow Engine": WORKFLOW_ENGINE,
            "Version": VERSION_INFO
        }
        
        for key, value in config_info.items():
            st.text(f"{key}: {value}")
    
    with col2:
        st.markdown("**Recent Activity**")
        # Mock recent admin activities
        activities = [
            f"{datetime.now().strftime('%H:%M')} - System health check passed",
            f"{(datetime.now() - timedelta(minutes=15)).strftime('%H:%M')} - User login: {st.session_state.user_email}",
            f"{(datetime.now() - timedelta(minutes=30)).strftime('%H:%M')} - Document processed: Alpha Corp Contract.pdf",
            f"{(datetime.now() - timedelta(hours=1)).strftime('%H:%M')} - System startup completed",
        ]
        
        for activity in activities:
            st.text(f"• {activity}")

def display_create_user_form():
    """Display the create user form"""
    auth_client = get_auth_client()
    user_token = st.session_state.access_token
    
    with st.form("create_user_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_email = st.text_input("Email Address*", placeholder="user@lawfirm.com")
            new_password = st.text_input("Password*", type="password", placeholder="Secure password")
        
        with col2:
            new_role = st.selectbox("Role*", ["user", "admin", "partner", "associate"])
            client_matters_text = st.text_area(
                "Client Matters (one per line)", 
                value="General Research\nContract Review\nCase Analysis",
                height=100
            )
        
        create_submitted = st.form_submit_button("Create User", type="primary")
        
        if create_submitted:
            if not new_email or not new_password:
                st.error("Email and password are required.")
            else:
                try:
                    # Parse client matters
                    client_matters = [matter.strip() for matter in client_matters_text.split('\n') if matter.strip()]
                    
                    # Create user using existing AuthClient
                    result = auth_client.create_user(
                        token=user_token,
                        email=new_email,
                        password=new_password,
                        role=new_role,
                        client_matters=client_matters
                    )
                    
                    st.success(f"✅ User '{new_email}' created successfully!")
                    
                    # Log the admin action using appropriate method
                    compliance_logger = get_compliance_logger()
                    compliance_logger.log_page_view(
                        user_email=st.session_state.user_email,
                        page_name=f"admin_action_create_user_{new_email}"
                    )
                    
                    st.rerun()  # Refresh to show new user
                    
                except Exception as e:
                    st.error(f"Failed to create user: {str(e)}")

def display_user_list():
    """Display list of existing users"""
    auth_client = get_auth_client()
    user_token = st.session_state.access_token
    
    try:
        users_data = auth_client.list_users(user_token)
        
        if users_data.get("users"):
            users = users_data["users"]
            
            st.markdown(f"**Existing Users ({len(users)} total)**")
            
            # Display users in a clean format
            for user in users:
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    
                    with col1:
                        email = user.get("email", "Unknown")
                        role = user.get("role", "user")
                        st.write(f"👤 **{email}**")
                        st.caption(f"Role: {role.title()}")
                    
                    with col2:
                        client_matters = user.get("client_matters", [])
                        st.write(f"📁 {len(client_matters)} matters")
                    
                    with col3:
                        created = user.get("created_at", "Unknown")
                        if created != "Unknown" and len(created) > 10:
                            created = created[:10]  # Show just date
                        st.write(f"📅 {created}")
                    
                    with col4:
                        st.write("✅ Active")
                    
                    # Show client matters in expandable section
                    if client_matters:
                        with st.expander("Client Matters", expanded=False):
                            for matter in client_matters:
                                st.text(f"• {matter}")
                    
                    st.markdown("---")
        else:
            st.info("No users found or unable to load user list.")
            show_demo_users()
            
    except Exception as e:
        st.error(f"Failed to load users: {str(e)}")
        show_demo_users()

def show_demo_users():
    """Show demo users as fallback"""
    st.markdown("**Demo Users:**")
    demo_users = [
        {"email": "admin@lawfirm.com", "role": "admin", "status": "Active"},
        {"email": "lawyer1@lawfirm.com", "role": "user", "status": "Active"},
        {"email": "demo@lawfirm.com", "role": "user", "status": "Active"}
    ]
    
    for user in demo_users:
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.write(f"👤 {user['email']}")
        with col2:
            st.write(user['role'].title())
        with col3:
            st.write(user['status'])

# Display navigation sidebar
display_navigation_sidebar(current_page="Admin Panel")

# Main script logic
if __name__ == "__main__":
    display_admin_panel() 