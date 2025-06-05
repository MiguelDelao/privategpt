"""
PrivateGPT Legal AI - Admin Panel
Modern admin interface for user management and system oversight
"""

import streamlit as st
import pandas as pd
import sys
import os
import requests
import time
from datetime import datetime, timedelta
from pages_utils import (
    APP_TITLE, LLM_MODEL_NAME, VECTOR_DB_NAME, WORKFLOW_ENGINE, VERSION_INFO,
    initialize_session_state, require_auth, display_navigation_sidebar,
    get_logger, get_auth_client
)

# Page configuration
st.set_page_config(
    page_title=f"Admin Panel - {APP_TITLE}", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Initialize session state and check authentication (admin only)
initialize_session_state()
require_auth(admin_only=True, main_app_file="app.py")

# --- ChatGPT Style CSS ---
st.markdown("""<style>
    /* General Styles */
    body {
        font-family: 'Söhne', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Ubuntu', 'Cantarell', 'Noto Sans', 'sans-serif', 'Helvetica Neue', 'Arial', 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji';
        color: #ECECF1;
    }
    .main .block-container {
        padding-top: 2rem; padding-bottom: 2rem; padding-left: 3rem; padding-right: 3rem;
        max-width: 100%;
    }
    /* Hide Streamlit default UI elements */
    footer {visibility: hidden;}
    button[data-testid="baseButton-headerNoPadding"] { visibility: hidden; }
    header[data-testid="stHeader"] { display: none !important; visibility: hidden !important; }
    #stDecoration { display:none; }
    div[data-testid="stToolbar"] { display:none; }
    div[data-testid="stStatusWidget"] { display:none; }
    div[data-testid="stDeployButton"] { display: none; }
    #MainMenu { visibility: hidden; }
    /* Page Background */
    [data-testid="stAppViewContainer"] { background-color: #0D1117; }
    [data-testid="stSidebar"] { background-color: #161B22; padding-top: 1rem; }
    
    /* Button Styling */
    .stButton>button {
        background-color: #21262D;
        color: #C9D1D9;
        border: 1px solid #30363D;
        border-radius: 6px;
        padding: 0.75rem 1.5rem;
        font-size: 1rem;
        font-weight: 500;
        transition: background-color 0.2s ease, border-color 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #30363D;
        border-color: #8B949E;
        color: #ECECF1;
    }
    .stButton>button:focus {
        outline: none !important;
        box-shadow: none !important;
        border-color: #58A6FF;
    }
    .stButton>button p {
        text-transform: none;
        color: inherit;
        font-weight: inherit;
    }

    /* Page Title Style */
    .page-title {
        font-size: 2.25rem;
        font-weight: 600;
        color: #ECECF1;
        margin-bottom: 0.5rem;
    }
    
    .page-subtitle {
        font-size: 1rem;
        color: #7D8590;
        margin-bottom: 2rem;
    }

    /* Sidebar Styles */
    [data-testid="stSidebarNav"] ul { padding-left: 0; }
    [data-testid="stSidebarNav"] li { list-style-type: none; margin-bottom: 0.5rem; }
    [data-testid="stSidebarNav"] li a {
        text-decoration: none; color: #C9D1D9; padding: 0.5rem 1rem;
        border-radius: 6px; display: block;
        transition: background-color 0.2s ease, color 0.2s ease;
        font-size: 0.95rem;
    }
    [data-testid="stSidebarNav"] li a:hover { background-color: #21262D; color: #ECECF1; }
    [data-testid="stSidebarNav"] li a.active {
        background-color: #0D1117; color: #58A6FF; font-weight: 600;
    }
    [data-testid="stSidebarUserContent"] { padding-top: 0rem; }
    div[data-testid="stVerticalBlock"] { gap: 0.5rem !important; }

    /* Form Styling */
    .stTextInput > div > div > input, 
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div {
        background-color: #21262D;
        border: 1px solid #30363D;
        color: #C9D1D9;
        border-radius: 6px;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stSelectbox > div > div:focus {
        border-color: #58A6FF;
        box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.1);
    }

    /* Table Styling */
    .stDataFrame {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 8px;
    }
    .stDataFrame table {
        color: #C9D1D9;
        background-color: transparent;
    }
    .stDataFrame th {
        background-color: #21262D;
        color: #ECECF1;
        font-weight: 600;
        border-bottom: 1px solid #30363D;
    }
    .stDataFrame td {
        border-bottom: 1px solid #30363D;
    }

    /* Info boxes */
    .stInfo {
        background-color: #161B22;
        border: 1px solid #30363D;
        color: #C9D1D9;
    }
    .stWarning {
        background-color: #161B22;
        border: 1px solid #D29922;
        color: #F1C232;
    }
    .stSuccess {
        background-color: #161B22;
        border: 1px solid #2D5A27;
        color: #4AC26B;
    }
    .stError {
        background-color: #161B22;
        border: 1px solid #DA3633;
        color: #F85149;
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: #161B22;
        color: #C9D1D9;
        border: 1px solid #30363D;
        border-radius: 6px;
    }
    .streamlit-expanderContent {
        background-color: #0D1117;
        border: 1px solid #30363D;
        border-top: none;
        border-radius: 0 0 6px 6px;
    }



</style>
""", unsafe_allow_html=True)

# Add parent directory to path to import pages_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Helper Functions ---
def get_user_accounts():
    """Get user accounts data from auth service."""
    try:
        auth_client = get_auth_client()
        user_token = st.session_state.access_token
        
        # Try to get real user data from auth service
        users_data = auth_client.list_users(user_token)
        
        if users_data and users_data.get("users"):
            users = users_data["users"]
            return pd.DataFrame([
                {
                    "email": user.get("email", "Unknown"),
                    "role": user.get("role", "user"),
                    "status": "Active" if user.get("is_active", True) else "Inactive",
                    "created_at": user.get("created_at", "Unknown")[:10] if user.get("created_at") else "Unknown"
                }
                for user in users
            ])
        else:
            # Return empty DataFrame if no users or auth service unavailable
            return pd.DataFrame()
    
    except Exception as e:
        # Log error but return empty DataFrame instead of crashing
        get_logger().log_error("admin", f"Failed to get user accounts: {e}", "admin_user_list")
        return pd.DataFrame()

@st.dialog("🗑️ Delete All Vector Data", width="large")
def delete_confirmation_modal():
    """Modal dialog for confirming deletion of all Weaviate data"""
    st.warning("⚠️ **This action cannot be undone!**")
    st.markdown("You are about to permanently delete:")
    st.markdown("• All documents from the vector database")
    st.markdown("• All embeddings and vector data")
    st.markdown("• All indexed content")
    
    st.markdown("---")
    st.markdown("**Are you absolutely sure you want to continue?**")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("✅ Yes, Delete All", type="primary", use_container_width=True):
            with st.spinner("Deleting all data..."):
                success, message = perform_delete_all_weaviate_data()
                if success:
                    st.success(message)
                    # Clear cached data
                    for key in list(st.session_state.keys()):
                        if key.startswith("documents-") or key.startswith("uploaded_"):
                            del st.session_state[key]
                    time.sleep(2)  # Brief pause to show success message
                else:
                    st.error(message)
                    time.sleep(2)  # Brief pause to show error message
                st.rerun()  # Close modal and refresh main app
    
    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            st.rerun()  # Close modal without action

def perform_delete_all_weaviate_data():
    """Delete all data from Weaviate database."""
    try:
        # Try multiple endpoint variations to ensure connectivity
        endpoints = [
            "http://knowledge-service:8000",
            "http://localhost:8000", 
            "http://127.0.0.1:8000"
        ]
        
        working_endpoint = None
        for endpoint in endpoints:
            try:
                test_response = requests.get(f"{endpoint}/health", timeout=5)
                if test_response.status_code == 200:
                    working_endpoint = endpoint
                    break
            except:
                continue
        
        if not working_endpoint:
            return False, "Unable to connect to knowledge service on any endpoint"
        
        all_documents = []
        current_page = 1
        page_size = 100  # Max allowed by the API
        
        # Loop to fetch all documents using pagination
        while True:
            try:
                response = requests.get(
                    f"{working_endpoint}/documents/?page={current_page}&page_size={page_size}", 
                    timeout=10
                )
                response.raise_for_status() # Will raise HTTPError for bad responses (4xx or 5xx)
                data = response.json()
                documents_on_page = data.get("documents", [])
                all_documents.extend(documents_on_page)
                
                # Check if this was the last page
                # (Assuming API might indicate this, or if fewer docs than page_size are returned)
                if not documents_on_page or len(documents_on_page) < page_size:
                    break 
                
                current_page += 1
                
            except requests.exceptions.HTTPError as http_err:
                error_detail = f"HTTP error fetching page {current_page}: {http_err}, status_code={http_err.response.status_code}"
                try:
                    error_json = http_err.response.json()
                    error_detail += f", response={error_json}"
                except ValueError:
                    error_detail += f", response_text='{http_err.response.text[:200]}'"
                get_logger().log_error("admin", error_detail, "weaviate_get_docs")
                return False, f"Error fetching documents: {error_detail}"
            except requests.exceptions.RequestException as req_err:
                error_detail = f"Request error fetching page {current_page}: {req_err}"
                get_logger().log_error("admin", error_detail, "weaviate_get_docs")
                return False, f"Error fetching documents: {error_detail}"
            except ValueError as json_err: # Includes JSONDecodeError
                error_detail = f"JSON decode error fetching page {current_page}: {json_err}"
                get_logger().log_error("admin", error_detail, "weaviate_get_docs")
                return False, f"Error parsing document data: {error_detail}"

        if not all_documents:
            return True, "No documents found in Weaviate (database already empty)"
        
        # Delete each document individually
        deleted_count = 0
        failed_count = 0
        
        for doc in all_documents:
            doc_id = doc.get("id")
            if doc_id:
                try:
                    delete_response = requests.delete(f"{working_endpoint}/documents/{doc_id}", timeout=10)
                    if delete_response.status_code == 200:
                        deleted_count += 1
                    else:
                        failed_count += 1
                        # Attempt to get more detailed error information
                        error_detail = f"status_code={delete_response.status_code}"
                        try:
                            error_json = delete_response.json()
                            error_detail += f", response={error_json}"
                        except ValueError: # Not a JSON response
                            error_detail += f", response_text='{delete_response.text[:200]}'" # Show first 200 chars
                        get_logger().log_error("admin", f"Failed to delete doc_id {doc_id}: {error_detail}", "weaviate_delete")
                        # The function will return a generic error message later, but this logs specifics
                except requests.exceptions.RequestException as e_req:
                    failed_count += 1
                    get_logger().log_error("admin", f"Request failed for doc_id {doc_id}: {str(e_req)}", "weaviate_delete")
        
        if failed_count == 0:
            return True, f"Successfully deleted all {deleted_count} documents from Weaviate"
        else:
            # Make the returned message more informative about the failure
            return False, f"Attempted to delete {deleted_count + failed_count} documents. Successfully deleted: {deleted_count}. Failed: {failed_count}. Check logs for details on failed deletions."
    except Exception as e:
        return False, f"Error deleting Weaviate data: {str(e)}"

def delete_user_account(user_email):
    """Delete a user account."""
    try:
        auth_client = get_auth_client()
        user_token = st.session_state.access_token
        
        # Call auth service to delete user
        result = auth_client.delete_user(user_token, user_email)
        return True, f"User {user_email} deleted successfully"
    
    except Exception as e:
        return False, f"Failed to delete user {user_email}: {str(e)}"

def display_admin_panel():
    """Display the modern admin panel content"""
    # Page header
    st.markdown('<h1 class="page-title">🛠️ Admin Panel</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">User management and data administration</p>', unsafe_allow_html=True)
    
    # User Management Section
    st.subheader("👥 User Management")
    
    # Create new user
    with st.expander("➕ Create New User", expanded=False):
        display_create_user_form()
    
    st.markdown("") # Add spacing
    
    # User list with delete functionality
    display_user_list()
    
    st.markdown("---")
    
    # Database Management
    st.subheader("🗄️ Database Management")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("**Delete All Vector Data**")
        st.caption("Permanently remove all documents and embeddings from the Weaviate database")
    with col2:
        if st.button("🗑 Delete All Data", key="delete_all_data", type="secondary"):
            delete_confirmation_modal()

def display_create_user_form():
    """Display the create user form with modern styling"""
    auth_client = get_auth_client()
    user_token = st.session_state.access_token
    
    with st.form("create_user_form"):
        st.markdown("**User Information**")
        
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
            if new_email and new_password:
                try:
                    # Parse client matters
                    client_matters = [matter.strip() for matter in client_matters_text.split('\n') if matter.strip()]
                    
                    # Create user using AuthClient
                    result = auth_client.create_user(
                        token=user_token,
                        email=new_email,
                        password=new_password,
                        role=new_role,
                        client_matters=client_matters
                    )
                    
                    st.success(f"✅ User '{new_email}' created successfully!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Failed to create user: {str(e)}")
            else:
                st.error("Please fill in all required fields (marked with *)")

def display_user_list():
    """Display user list with delete functionality only"""
    st.markdown("**Current Users**")
    
    try:
        users_df = get_user_accounts()
        
        if not users_df.empty:
            # Display users table
            st.dataframe(users_df, use_container_width=True, hide_index=True)
            
            # User delete action
            st.markdown("**Delete User**")
            
            # Create user selection dropdown
            user_options = {
                f"{row.get('email', 'Unknown')} ({row.get('role', 'user')})": row.get('email')
                for index, row in users_df.iterrows()
            }
            
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_user_display = st.selectbox(
                    "Select user to delete:",
                    options=list(user_options.keys()),
                    key="user_delete_selector"
                )
                selected_user_email = user_options.get(selected_user_display)
            
            with col2:
                if st.button("❌ Delete User", key="delete_user_btn", type="secondary"):
                    if selected_user_email and selected_user_email != st.session_state.user_email:
                        with st.spinner(f"Deleting user {selected_user_email}..."):
                            success, message = delete_user_account(selected_user_email)
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                    elif selected_user_email == st.session_state.user_email:
                        st.warning("You cannot delete your own account!")
                    else:
                        st.warning("Please select a user to delete.")
        else:
            st.info("No users found in the system.")
    
    except Exception as e:
        st.error(f"Failed to load user data: {e}")

# Display navigation sidebar
display_navigation_sidebar(current_page="Admin Panel")

# Main script logic
if __name__ == "__main__":
    display_admin_panel() 