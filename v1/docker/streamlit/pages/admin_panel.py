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
import json
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

# --- Client Data Management ---
DATA_DIR = "data" # Relative to project root where streamlit runs
CLIENTS_FILE = os.path.join(DATA_DIR, "clients.json")

def _ensure_data_dir_and_clients_file():
    """Ensures the data directory and clients.json file exist."""
    if not os.path.exists(DATA_DIR):
        try:
            os.makedirs(DATA_DIR)
        except OSError as e:
            st.error(f"Failed to create data directory {DATA_DIR}: {e}")
            return False # Critical error
    if not os.path.isfile(CLIENTS_FILE):
        try:
            with open(CLIENTS_FILE, 'w') as f:
                json.dump([], f)
        except IOError as e:
            st.error(f"Failed to create clients file {CLIENTS_FILE}: {e}")
            return False # Critical error
    return True

def load_clients() -> list[str]:
    """Loads client names from the JSON file."""
    if not _ensure_data_dir_and_clients_file():
        return [] # Return empty if directory/file creation failed
    try:
        with open(CLIENTS_FILE, 'r') as f:
            clients = json.load(f)
            if isinstance(clients, list) and all(isinstance(c, str) for c in clients):
                return sorted(list(set(clients))) # Ensure unique and sorted
            st.warning(f"Clients file {CLIENTS_FILE} is corrupted or has an unexpected format. Resetting.")
            return [] 
    except (IOError, json.JSONDecodeError) as e:
        st.warning(f"Error reading clients file {CLIENTS_FILE}: {e}. Resetting.")
        return []

def save_clients(clients_list: list[str]) -> bool:
    """Saves client names to the JSON file."""
    if not _ensure_data_dir_and_clients_file():
        return False # Bail if directory/file setup failed
    try:
        # Ensure unique and sorted before saving, remove empty strings
        unique_sorted_clients = sorted(list(set(client.strip() for client in clients_list if client.strip())))
        with open(CLIENTS_FILE, 'w') as f:
            json.dump(unique_sorted_clients, f, indent=4)
        return True
    except IOError as e:
        st.error(f"Failed to save clients to {CLIENTS_FILE}: {e}")
        return False

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

# --- LLM Settings Display ---
def display_llm_settings():
    """Display LLM configuration settings"""
    st.markdown("**Configure Large Language Model Parameters**")
    st.caption("These settings control how the AI responds to questions and processes documents.")
    
    # Get current environment-based defaults
    knowledge_service_url = os.getenv("KNOWLEDGE_SERVICE_URL", "http://knowledge-service:8000")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Context Settings
        st.markdown("**Context & Token Limits**")
        
        max_context_tokens = st.number_input(
            "Maximum Context Tokens",
            min_value=1000,
            max_value=8000,
            value=3000,
            step=500,
            help="Maximum number of tokens from documents to include in prompts. Lower values = faster responses but less context."
        )
        
        default_search_limit = st.number_input(
            "Default Search Results",
            min_value=1,
            max_value=20,
            value=5,
            step=1,
            help="Number of document chunks to retrieve for each question. Lower values = faster responses."
        )
        
        timeout_seconds = st.number_input(
            "LLM Timeout (seconds)",
            min_value=30,
            max_value=300,
            value=120,
            step=30,
            help="How long to wait for the AI to respond before timing out."
        )
    
    with col2:
        # Response Settings
        st.markdown("**Response Parameters**")
        
        default_max_tokens = st.number_input(
            "Max Response Tokens",
            min_value=100,
            max_value=4000,
            value=1000,
            step=100,
            help="Maximum length of AI responses. Higher values allow longer responses."
        )
        
        default_temperature = st.slider(
            "Response Creativity",
            min_value=0.0,
            max_value=2.0,
            value=0.7,
            step=0.1,
            help="0.0 = Very focused and consistent, 2.0 = Very creative and varied"
        )
        
        st.markdown("")  # Spacing
        st.markdown("**Model Selection**")
        
        # Fetch available models
        try:
            user_token = st.session_state.get("access_token")
            headers = {"Authorization": f"Bearer {user_token}"} if user_token else {}
            
            models_response = requests.get(
                f"{knowledge_service_url}/admin/models/available",
                headers=headers,
                timeout=10
            )
            
            if models_response.status_code == 200:
                models_data = models_response.json()
                available_models = models_data.get("models", [])
                current_selected = models_data.get("selected_model", "llama3:8b")
                
                if available_models:
                    model_names = [model["name"] for model in available_models]
                    
                    # Find current selection index
                    try:
                        current_index = model_names.index(current_selected)
                    except ValueError:
                        current_index = 0
                    
                    selected_model = st.selectbox(
                        "Available Models",
                        options=model_names,
                        index=current_index,
                        help="Select the AI model to use for responses"
                    )
                    
                    # Show model info
                    selected_model_info = next((m for m in available_models if m["name"] == selected_model), None)
                    if selected_model_info:
                        size_gb = selected_model_info.get("size", 0) / (1024**3)
                        st.caption(f"Size: {size_gb:.1f} GB")
                else:
                    st.warning("No models available in Ollama")
                    selected_model = current_selected
                    
            else:
                st.warning("Could not fetch available models")
                selected_model = "llama3:8b"
                
        except Exception as e:
            st.error(f"Error fetching models: {str(e)}")
            selected_model = "llama3:8b"
        
        # Refresh models button
        col_refresh1, col_refresh2 = st.columns([1, 1])
        with col_refresh2:
            if st.button("🔄 Refresh Models", key="refresh_models_btn", help="Check for newly installed models"):
                st.rerun()
    
    # Apply Settings Button
    if st.button("💾 Apply Settings", type="primary", key="apply_llm_settings"):
        settings_data = {
            "MAX_CONTEXT_TOKENS": str(max_context_tokens),
            "DEFAULT_SEARCH_LIMIT": str(default_search_limit),
            "LLM_TIMEOUT_SECONDS": str(timeout_seconds),
            "DEFAULT_MAX_TOKENS": str(default_max_tokens),
            "DEFAULT_TEMPERATURE": str(default_temperature),
            "SELECTED_MODEL": selected_model
        }
        
        try:
            # Update settings via knowledge service API
            user_token = st.session_state.get("access_token")
            headers = {"Authorization": f"Bearer {user_token}"} if user_token else {}
            
            response = requests.post(
                f"{knowledge_service_url}/admin/settings",
                json=settings_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                st.success("✅ LLM settings updated successfully! Changes will take effect for new conversations.")
            else:
                st.error(f"❌ Failed to update settings: {response.text}")
                
        except Exception as e:
            st.error(f"❌ Error updating settings: {str(e)}")
    
    # Display current effective settings
    with st.expander("📊 Current Settings", expanded=False):
        try:
            user_token = st.session_state.get("access_token")
            headers = {"Authorization": f"Bearer {user_token}"} if user_token else {}
            
            response = requests.get(
                f"{knowledge_service_url}/admin/settings",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                current_settings = response.json()
                st.json(current_settings)
            else:
                st.warning("Could not fetch current settings")
                
        except Exception as e:
            st.info("Settings API not available")


# --- Admin Panel Display ---
def display_admin_panel():
    """Display the modern admin panel content"""
    auth_client = get_auth_client() # Get AuthClient instance
    user_token = st.session_state.get("access_token")

    if not user_token:
        st.error("User token not found. Please log in again.")
        return
    if not auth_client:
        st.error("AuthClient not available.")
        return

    # Page header
    st.markdown('<h1 class="page-title">🛠️ Admin Panel</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">User management, data administration, and client configuration</p>', unsafe_allow_html=True)
    
    # Global Client Selection Dropdown (Top Level)
    st.markdown("---")
    st.subheader("🔍 Client Context Filter")
    
    try:
        # Load available clients for global filtering
        clients_data = auth_client.list_clients(user_token)
        client_options = ["All Clients"] + [f"{client.get('name', 'Unknown')} ({client.get('id', 'No ID')[:8]}...)" 
                                           for client in clients_data]
        
        # Initialize session state for client filter if not exists
        if "admin_selected_client_filter" not in st.session_state:
            st.session_state.admin_selected_client_filter = "All Clients"
            
        # Global client filter dropdown
        col1, col2 = st.columns([3, 1])
        with col1:
            selected_global_client = st.selectbox(
                "Select Client Context:",
                options=client_options,
                index=client_options.index(st.session_state.admin_selected_client_filter) 
                      if st.session_state.admin_selected_client_filter in client_options else 0,
                help="Filter all admin operations by client. 'All Clients' shows everything. Specific clients show only data for that client.",
                key="global_client_filter"
            )
            st.session_state.admin_selected_client_filter = selected_global_client
            
        with col2:
            if st.button("🔄 Refresh Clients", key="refresh_clients_filter", help="Reload client list"):
                st.rerun()
                
        # Show current context
        if selected_global_client == "All Clients":
            st.info("🌐 **Current Context:** All Clients - Viewing system-wide data")
        else:
            # Extract client name from display format
            client_name = selected_global_client.split(" (")[0] if "(" in selected_global_client else selected_global_client
            st.info(f"🎯 **Current Context:** {client_name} - Viewing client-specific data")
            
    except Exception as e:
        st.error(f"Failed to load clients for filtering: {e}")
        st.session_state.admin_selected_client_filter = "All Clients"
        
    st.markdown("---")
    
    # User Management Section
    st.subheader("👥 User Management")
    
    # Create new user
    with st.expander("➕ Create New User", expanded=False):
        display_create_user_form()
    
    st.markdown("") # Add spacing
    
    # User list with delete functionality
    display_user_list()
    
    st.markdown("---")
    
    # LLM Settings
    st.subheader("🤖 LLM Settings")
    display_llm_settings()
    
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

    st.markdown("---")

    # Client Management Section
    st.subheader("🗂️ Client Configuration")
    
    try:
        clients_data = auth_client.list_clients(user_token)
        # clients_data is expected to be a list of dicts, e.g., [{"id": "uuid", "name": "Client A"}, ...]
    except Exception as e:
        st.error(f"Failed to load clients: {e}")
        clients_data = [] # Default to empty list on error

    # Input for new client
    new_client_name_input = st.text_input("New Client Name", key="new_client_name_admin_input")
    if st.button("Add Client", key="add_client_button_admin"):
        if new_client_name_input and new_client_name_input.strip():
            cleaned_name = new_client_name_input.strip()
            # Check for duplicates client-side before API call to save a request
            if any(client['name'] == cleaned_name for client in clients_data):
                st.warning(f"Client '{cleaned_name}' already exists.")
            else:
                try:
                    auth_client.create_client(user_token, cleaned_name)
                    st.success(f"Client '{cleaned_name}' added successfully.")
                    st.rerun() 
                except Exception as e:
                    st.error(f"Failed to add client '{cleaned_name}': {e}")
        else:
            st.warning("Client name cannot be empty.")

    # Display current clients with delete option
    if clients_data:
        st.markdown("**Current Clients:**")
        for client in clients_data: # client is a dict like {"id": "...". "name": "..."}
            client_id = client.get("id")
            client_name = client.get("name", "Unnamed Client")
            col_client1, col_client2 = st.columns([0.85, 0.15])
            with col_client1:
                st.markdown(f"• {client_name} (ID: {client_id})")
            with col_client2:
                delete_button_key = f"delete_client_{client_id}" # Ensure key is unique
                if st.button(f"Delete", key=delete_button_key, help=f"Delete client {client_name}", type="secondary"):
                    try:
                        auth_client.delete_client(user_token, client_id)
                        st.success(f"Client '{client_name}' deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete client '{client_name}': {e}")
                    # No need to break here as rerun will handle loop re-evaluation
        st.caption(f"Total clients: {len(clients_data)}")
    else:
        st.info("No clients configured yet. Add one above.")
    
    st.markdown("---")

    # --- User-Client Authorization Section ---
    st.subheader("👤 User Client Authorizations")

    try:
        # Fetch all users for the selection dropdown
        # Ensure get_user_accounts() or auth_client.list_users() returns data in a usable format
        # Assuming list_users returns a list of dicts with at least 'email' and 'role'
        all_users_data = auth_client.list_users(user_token) 
        # Filter out system users or roles if necessary, e.g., if there are service accounts
        # For now, assume all users returned are relevant for client authorization management.
        user_email_options = sorted([user['email'] for user in all_users_data if user.get('email')])
        
        if not user_email_options:
            st.info("No users found to manage client authorizations.")
            return # Stop if no users to manage

    except Exception as e:
        st.error(f"Failed to load users for authorization management: {e}")
        user_email_options = []
        all_users_data = [] # Ensure it's defined for later use if needed

    if not user_email_options:
        # This check is after the try-except to handle cases where loading users failed
        # and st.info was not sufficient or if we want to halt further rendering for this section.
        st.warning("User list is empty. Cannot manage client authorizations.")
    else:
        # User selection dropdown
        selected_user_email_for_auth = st.selectbox(
            "Select User to Manage Client Authorizations:",
            options=user_email_options,
            key="selected_user_for_client_auth",
            index=0 # Default to the first user or handle no selection if preferred
        )

        if selected_user_email_for_auth:
            try:
                # Fetch currently authorized clients for the selected user
                user_current_clients_data = auth_client.get_user_authorized_clients(user_token, selected_user_email_for_auth)
                user_current_client_ids = {client['id'] for client in user_current_clients_data}

                # Fetch all available global clients for the multiselect options
                # clients_data should already be loaded from the Client Configuration section above.
                # If not, or if there's a chance of staleness, refetch:
                # all_global_clients_data = auth_client.list_clients(user_token)
                # For now, assume clients_data from above is sufficient and current.
                if not clients_data: # clients_data is from the Client Configuration section
                    st.warning("Client list not available. Please configure clients first or refresh.")
                else:
                    client_options_for_multiselect = {client['name']: client['id'] for client in clients_data}
                    client_names_for_multiselect = sorted(client_options_for_multiselect.keys())
                    
                    # Pre-select clients that the user is already authorized for
                    pre_selected_client_names = [
                        name for name, cid in client_options_for_multiselect.items() if cid in user_current_client_ids
                    ]

                    st.markdown(f"**Manage Client Access for:** `{selected_user_email_for_auth}`")
                    if user_current_clients_data:
                        st.markdown("Currently Authorized Clients: " + ", ".join(f"`{c['name']}`" for c in user_current_clients_data))
                    else:
                        st.info("This user is currently not authorized for any specific clients.")

                    selected_client_names_for_update = st.multiselect(
                        "Authorize for Clients:",
                        options=client_names_for_multiselect,
                        default=pre_selected_client_names,
                        key=f"multiselect_clients_for_{selected_user_email_for_auth.replace('.', '_')}" # Ensure unique key
                    )

                    if st.button("Update Client Authorizations", key=f"update_auth_btn_{selected_user_email_for_auth.replace('.', '_')}"):
                        selected_client_ids_for_update = [
                            client_options_for_multiselect[name] for name in selected_client_names_for_update
                        ]
                        try:
                            auth_client.update_user_authorized_clients(user_token, selected_user_email_for_auth, selected_client_ids_for_update)
                            st.success(f"Client authorizations updated for {selected_user_email_for_auth}.")
                            # Consider a targeted rerun or partial refresh if possible, for now, full rerun.
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to update client authorizations: {e}")
            
            except Exception as e:
                st.error(f"Error loading client authorization details for {selected_user_email_for_auth}: {e}")

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

# Main script logic
if __name__ == "__main__":
    # Ensure navigation and auth check are done before displaying panel
    # This might be handled by require_auth() if called at the top of the script
    display_navigation_sidebar(current_page="Admin Panel") 
    if st.session_state.get("authenticated") and st.session_state.get("user_role") == "admin":
        display_admin_panel()
    elif not st.session_state.get("authenticated"):
        st.warning("Please log in to access the admin panel.")
        # Optionally redirect to login or show login form
    else:
        st.error("You do not have permission to access this page.") 