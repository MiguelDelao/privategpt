"""
PrivateGPT Legal AI - Document Management Page
Modern table-style document management interface
"""

import streamlit as st
import time
import logging  # Added for standard logging
from datetime import datetime
import sys
import os
import pandas as pd
import requests
import json
from typing import Optional

# Add parent directory to path to import pages_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pages_utils import (
    APP_TITLE, initialize_session_state, require_auth, 
    display_navigation_sidebar, # apply_page_styling, # Removed
    get_logger,
    get_auth_client # Ensure get_auth_client is imported
)

# Page configuration
st.set_page_config(
    page_title=f"Documents - {APP_TITLE}", 
    # page_icon="📂", # Removed icon for cleaner look
    layout="wide", 
    initial_sidebar_state="expanded"
)

# apply_page_styling() # Removed call
initialize_session_state()
require_auth()

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
    
    /* Button Styling (consistent with dashboard) */
    .stButton>button {
        background-color: #21262D;
        color: #C9D1D9;
        border: 1px solid #30363D;
        border-radius: 6px;
        padding: 0.75rem 1.5rem;
        font-size: 1rem;
        font-weight: 500;
        /* width: 100%; */ /* Let buttons size naturally or control with columns */
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
        font-size: 2.25rem; /* Slightly smaller than dashboard main title */
        font-weight: 600;
        color: #ECECF1;
        margin-bottom: 1.5rem;
    }

    /* Table Styling - Placeholder, can be refined with st.dataframe or custom HTML */
    .stDataFrame table {
        color: #C9D1D9;
        background-color: #161B22;
        border: 1px solid #30363D;
    }
    .stDataFrame th {
        background-color: #21262D;
        color: #ECECF1;
        font-weight: 600;
    }
    .stDataFrame td, .stDataFrame th {
        border-color: #30363D;
    }

    /* Input/File Uploader Styling */
    div[data-testid="stFileUploader"] label {
        color: #C9D1D9;
        font-size: 1rem;
    }
    div[data-testid="stFileUploader"] section {
        background-color: #161B22;
        border-color: #30363D;
    }
    div[data-testid="stFileUploader"] section:hover {
        border-color: #58A6FF;
    }
    div[data-testid="stFileUploader"] button {
        background-color: #21262D;
        color: #C9D1D9;
        border: 1px solid #30363D;
    }
    div[data-testid="stFileUploader"] button:hover {
        background-color: #30363D;
        border-color: #8B949E;
    }

    /* Sidebar Styles (Copied from dashboard for consistency) */
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

</style>
""", unsafe_allow_html=True)

# Knowledge Service Configuration
KNOWLEDGE_SERVICE_URL = os.getenv("KNOWLEDGE_SERVICE_URL", "http://knowledge-service:8000")
ALL_DOCUMENTS_ID = "ALL_DOCUMENTS_VIEW" # Special ID for "All" view

# --- Placeholder functions for Client/Matter data ---
# REMOVED: Old placeholder functions for client/matter handling.
# The new system uses AuthClient and user's authorized clients.

# --- Placeholder functions for Client/Matter data ---
def get_formatted_client_matters_for_user(include_all_option=True):
    """Placeholder: Fetches and formats client/matter list for the current user."""
    # In a real app, this would call an API or service
    # It should return a list of tuples: (formatted_string, internal_id_or_object)
    # For now, using dummy data. The ID could be a composite like "client_id|matter_id"
    # Base list of actual client/matters
    client_matters = [
        ("Client Alpha - Project Titan", "C001|M101"),
        ("Client Alpha - Project Phoenix", "C001|M102"),
        ("Client Beta - Case Jupiter", "C002|M201"),
    ]
    if include_all_option:
        return [("All My Documents", ALL_DOCUMENTS_ID)] + client_matters
    return client_matters

def parse_client_matter_id(internal_id):
    """Placeholder: Parses client and matter IDs from the formatted string ID."""
    if internal_id == ALL_DOCUMENTS_ID or not internal_id:
        return None, None
    if "|" in internal_id:
        parts = internal_id.split("|")
        return parts[0], parts[1] # client_id, matter_id
    return None, None

def fetch_documents_from_api(token=None, client_id=None, matter_id=None):
    """Fetch documents from the knowledge service API with authorization."""
    logger = get_logger()
    params = {}
    headers = {}
    
    # Add authorization header if token is provided
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    endpoint = f"{KNOWLEDGE_SERVICE_URL}/documents/"
    logging.info(f"Fetching documents from {endpoint} with params: {params}")
    try:
        response = requests.get(endpoint, params=params, headers=headers, timeout=60)
        response.raise_for_status() 
        data = response.json()
        documents = data.get("documents", [])
        logging.info(f"Successfully fetched {len(documents)} documents.")

        # Attempt to fetch progress for any tasks marked as 'PROCESSING'
        # This assumes the 'status' and 'task_id' are part of the main document record
        # or we have a list of active task_ids in session_state
        
        updated_documents = []
        for doc in documents:
            doc_id = doc.get("id") # Assuming doc has an 'id'
            task_id_to_check = None

            if 'processing_tasks' in st.session_state and doc_id and doc_id in st.session_state.processing_tasks:
                 task_id_to_check = st.session_state.processing_tasks[doc_id]['task_id']
            elif doc.get("status") == "PROCESSING" and doc.get("task_id"): # If API returns task_id for processing docs
                 task_id_to_check = doc.get("task_id")
            
            if task_id_to_check:
                progress_info = fetch_task_progress(task_id_to_check)
                if progress_info:
                    doc["status"] = progress_info.get("status", doc.get("status"))
                    doc["chunk_progress"] = f"{progress_info.get('progress', 0.0)*100:.0f}% ({progress_info.get('chunks_processed','-')}/{progress_info.get('chunks_total','-')})"
                    doc["current_chunk"] = progress_info.get("stage", "N/A")
                    
                    # If task is completed (SUCCESS/FAILURE), remove from active processing list
                    if progress_info.get("status") in ["SUCCESS", "FAILURE"]:
                        if 'processing_tasks' in st.session_state and doc_id in st.session_state.processing_tasks:
                            del st.session_state.processing_tasks[doc_id]
                        # Potentially update the main doc record in backend if status changed from PROCESSING to SUCCESS/FAILURE
                        # For now, frontend will just reflect this until next full fetch
                else: # Failed to get progress, keep existing fields
                    doc["chunk_progress"] = "Error fetching progress"
                    doc["current_chunk"] = "N/A"

            else: # Not processing or no task_id, set defaults
                 doc["chunk_progress"] = ""
                 doc["current_chunk"] = ""
            updated_documents.append(doc)
        return updated_documents
    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error fetching documents: {http_err} - {response.text}"
        user_email = st.session_state.get("user_email", "system")
        get_logger().log_error(user_email, error_message, "api_fetch_documents_http")
        st.error(f"Failed to fetch documents. Server responded: {response.status_code}")
        return []
    except requests.exceptions.RequestException as e:
        error_message = f"Network error fetching documents: {str(e)}"
        user_email = st.session_state.get("user_email", "system")
        get_logger().log_error(user_email, error_message, "api_fetch_documents_network")
        st.error("Network error while fetching documents.")
        return []
    except Exception as e:
        error_message = f"Unexpected error fetching documents: {str(e)}"
        user_email = st.session_state.get("user_email", "system")
        get_logger().log_error(user_email, error_message, "api_fetch_documents_unexpected")
        st.error("An unexpected error occurred while fetching documents.")
        return []

def fetch_task_progress(task_id: str):
    logger = get_logger()
    if not task_id:
        return None
    try:
        response = requests.get(f"{KNOWLEDGE_SERVICE_URL}/documents/task_progress/{task_id}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        user_email = st.session_state.get("user_email", "system")
        get_logger().log_error(user_email, f"HTTP error fetching task progress for {task_id}: {http_err} - {http_err.response.text}", "api_fetch_task_progress_http")
        return None
    except requests.exceptions.RequestException as e:
        user_email = st.session_state.get("user_email", "system")
        get_logger().log_error(user_email, f"Network error fetching task progress for {task_id}: {str(e)}", "api_fetch_task_progress_network")
        return None
    except Exception as e:
        user_email = st.session_state.get("user_email", "system")
        get_logger().log_error(user_email, f"Unexpected error fetching task progress for {task_id}: {str(e)}", "api_fetch_task_progress_unexpected")
        return None

def delete_document_from_api(document_id: str, token=None):
    """Delete a document using the knowledge service API."""
    logger = get_logger()
    headers = {}
    
    # Add authorization header if token is provided
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        response = requests.delete(f"{KNOWLEDGE_SERVICE_URL}/documents/{document_id}", headers=headers, timeout=30)
        response.raise_for_status()
        logging.info(f"Document ID {document_id} deleted successfully.")
        return True, "Document deleted successfully."
    except requests.exceptions.HTTPError as http_err:
        error_detail = http_err.response.text
        if http_err.response.status_code == 404:
            msg = "Document not found."
            logging.warning(f"Attempted to delete non-existent document ID {document_id}")
            return False, msg
        user_email = st.session_state.get("user_email", "system")
        get_logger().log_error(user_email, f"HTTP error deleting doc {document_id}: {http_err} - {error_detail}", "api_delete_http")
        return False, f"Failed to delete: {error_detail[:200]}"
    except requests.exceptions.RequestException as e:
        user_email = st.session_state.get("user_email", "system")
        get_logger().log_error(user_email, f"Network error deleting doc {document_id}: {str(e)}", "api_delete_network")
        return False, f"Network error: {str(e)}"
    except Exception as e:
        user_email = st.session_state.get("user_email", "system")
        get_logger().log_error(user_email, f"Unexpected error deleting doc {document_id}: {str(e)}", "api_delete_unexpected")
        return False, f"Unexpected error: {str(e)}"

def upload_to_knowledge_service(uploaded_file, metadata_to_send=None, progress_callback=None, token=None):
    """Uploads a file to the knowledge service with optional metadata."""
    logger = get_logger()
    user_email = st.session_state.get("user_email", "system")
    files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
    data = {}
    headers = {}
    
    # Add authorization header if token is provided
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    if metadata_to_send: # metadata_to_send can be e.g. {"client_id": "actual_id"}
        try:
            data["metadata"] = json.dumps(metadata_to_send) 
        except TypeError as e:
            logger.log_error(user_email, f"Metadata serialization error: {str(e)}. Metadata: {metadata_to_send}", "api_upload_metadata_serialize")
            st.error(f"Could not prepare metadata for {uploaded_file.name}. Error: {e}")
            return None
    api_endpoint = f"{KNOWLEDGE_SERVICE_URL}/documents/upload"
    logger.log_document_upload(user_email, uploaded_file.name, uploaded_file.size)
    try:
        response = requests.post(api_endpoint, files=files, data=data, headers=headers, stream=True, timeout=300)
        response.raise_for_status()
        if progress_callback: progress_callback("Uploading...", 0.1)
        timeout = max(120, len(uploaded_file.getvalue()) / 1024 / 1024 * 10) 
        upload_accepted_data = response.json()
        logging.info(f"Upload accepted for '{uploaded_file.name}', task ID: {upload_accepted_data.get('task_id')}")
        return upload_accepted_data
    except requests.exceptions.HTTPError as http_err:
        error_detail = http_err.response.text
        user_email = st.session_state.get("user_email", "system")
        get_logger().log_error(user_email, f"HTTP error uploading: {http_err} - {error_detail}", "api_upload_http")
        st.error(f"Failed to upload '{uploaded_file.name}'. Server error: {http_err.response.status_code} - {http_err.response.text[:200]}")
        return None
    except requests.exceptions.RequestException as e:
        user_email = st.session_state.get("user_email", "system")
        get_logger().log_error(user_email, f"Network error uploading: {str(e)}", "api_upload_network")
        st.error(f"Network error while uploading '{uploaded_file.name}'.")
        return None
    except Exception as e:
        user_email = st.session_state.get("user_email", "system")
        get_logger().log_error(user_email, f"An unexpected error occurred during upload of '{uploaded_file.name}': {str(e)}", "api_upload_unexpected")
        st.error(f"An unexpected error occurred during upload of '{uploaded_file.name}': {str(e)}")
        return None

def process_document_wrapper(uploaded_file, selected_client_id: Optional[str], show_success=True):
    """Wrapper for upload process, using selected_client_id for metadata."""
    max_size = 200 * 1024 * 1024 
    if uploaded_file.size > max_size:
        st.error(f"File exceeds maximum size of 200MB.")
        return None

    with st.spinner(f"Submitting {uploaded_file.name} for processing..."):
        # Only include client_id in metadata if a specific client is selected
        # If None, let the backend default to "all"
        doc_metadata = {}
        if selected_client_id:  # Only add if a client_id is actually selected and not None
            doc_metadata["client_id"] = selected_client_id 
        
        upload_response_data = upload_to_knowledge_service(uploaded_file, metadata_to_send=doc_metadata, token=st.session_state.get("access_token"))
        
        if upload_response_data and upload_response_data.get("task_id"):
            task_id = upload_response_data["task_id"]
            filename = upload_response_data.get("filename", uploaded_file.name)
            
            if 'processing_tasks' not in st.session_state:
                st.session_state.processing_tasks = {}
            
            st.session_state.processing_tasks[task_id] = {
                "task_id": task_id,
                "filename": filename,
                "associated_client_id": selected_client_id, # Store selected client_id (can be None)
                "upload_time": datetime.now().isoformat(),
                "status": "PROCESSING",
                "stage": "Submitted",
                "progress_percent": 0.0
            }
            logging.info(f"Stored task {task_id} for {filename} (Client ID: {selected_client_id}) in session_state.processing_tasks")
            
            # Cache clearing - adjust later for new filtering
            current_view_id = st.session_state.get('selected_client_filter_key', ALL_DOCUMENTS_ID) # Key name change
            cache_key_current_view = 'documents-' + str(current_view_id) # Ensure key is string
            if cache_key_current_view in st.session_state:
                del st.session_state[cache_key_current_view]
            if ALL_DOCUMENTS_ID != current_view_id and ('documents-' + ALL_DOCUMENTS_ID) in st.session_state:
                 del st.session_state['documents-' + ALL_DOCUMENTS_ID]

            if show_success:
                client_display_name = selected_client_id if selected_client_id else "General"
                st.success(f"'{filename}' submitted (Task ID: {task_id}). Associated Client ID: {client_display_name}")
                st.rerun() 
            return {"task_id": task_id, "filename": filename} 
        else:
            logging.error(f"Upload of {uploaded_file.name} did not return task_id or failed.")
            st.error(f"Failed to submit '{uploaded_file.name}' for processing. Check logs.")
        return None

def display_document_management():
    """Main function to display the document management page."""
    display_navigation_sidebar()
    auth_client = get_auth_client()
    user_token = st.session_state.get("access_token")

    if not user_token or not auth_client:
        st.error("User not authenticated or auth client not available. Please log in.")
        return

    if 'processing_tasks' not in st.session_state: st.session_state.processing_tasks = {}
    # Initialize a common key for the document library filter selection
    if 'selected_library_filter_key' not in st.session_state: 
        st.session_state.selected_library_filter_key = "ALL_VIEWABLE" # Default filter

    st.markdown('<div class="page-title">Document Management</div>', unsafe_allow_html=True)
    st.caption("Upload, process, and manage your documents. Associate them with authorized clients.")

    # --- Document Library View Filter (NEW LOGIC) ---
    st.markdown("---")
    st.subheader("📄 Document Library")

    try:
        user_authorized_clients_for_view = auth_client.get_my_authorized_clients(user_token)
    except Exception as e:
        st.error(f"Error fetching your authorized clients for filtering: {e}")
        user_authorized_clients_for_view = []

    # Prepare filter options: (Display Name, Filter Key/ID)
    # Filter Key/ID: "ALL_VIEWABLE", "GENERAL_NO_CLIENT", or actual client_id
    library_filter_options = [
        ("All My Viewable Documents", "ALL_VIEWABLE"),
        ("General (No Client Association)", "GENERAL_NO_CLIENT")
    ]
    for client_info in user_authorized_clients_for_view:
        library_filter_options.append((client_info.get('name', 'Unnamed Client'), client_info.get('id')))
    
    # Get current index for the selectbox
    current_filter_key = st.session_state.selected_library_filter_key
    current_filter_index = 0
    for i, (_, key) in enumerate(library_filter_options):
        if key == current_filter_key:
            current_filter_index = i
            break
            
    selected_filter_tuple = st.selectbox(
        "Filter Documents By Client:",
        options=library_filter_options,
        format_func=lambda x: x[0], # Display name
        index=current_filter_index,
        key="document_library_client_filter_dropdown"
    )
    st.session_state.selected_library_filter_key = selected_filter_tuple[1] # Store the key (e.g., "ALL_VIEWABLE", client_id)
    selected_filter_display_name = selected_filter_tuple[0]

    # --- Upload Section (already modified) ---
    st.markdown("---") # Separator before upload if it wasn't there
    st.subheader("⬆️ Upload New Documents")

    try:
        # Fetch user's authorized clients for the dropdown
        # Each client_info in this list is expected to be a dict like {"id": "uuid", "name": "Client Name"}
        user_authorized_clients = auth_client.get_my_authorized_clients(user_token)
    except Exception as e:
        st.error(f"Error fetching your authorized clients: {e}")
        user_authorized_clients = []

    # Prepare options for the selectbox: (Display Name, client_id)
    # "None" option should have None as its ID for easy checking.
    client_options_for_upload = [("General (No Client Association)", None)] + \
                                [(client.get('name', 'Unnamed Client'), client.get('id')) for client in user_authorized_clients]

    selected_client_tuple = st.selectbox(
        "Associate with Client (Optional):",
        options=client_options_for_upload,
        format_func=lambda x: x[0],  # Display only the name part of the tuple
        index=0, 
        key="selected_client_for_upload_dropdown_v2",
        help="Select a client you are authorized for to associate these documents with."
    )
    selected_client_id_for_upload = selected_client_tuple[1] # Get the ID part of the tuple
    
    st.caption("Select files (PDF, DOCX, TXT - Max 200MB each).")
    can_upload = True 

    if can_upload:
        uploader_key_suffix = str(selected_client_id_for_upload).replace("-", "_").lower() if selected_client_id_for_upload else "general"
        uploader_key = f"doc_uploader_auth_{uploader_key_suffix}"
        
        uploaded_files = st.file_uploader(
            "Choose file(s)", 
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True, 
            key=uploader_key,
            help="You can upload multiple files at once."
        )
        if uploaded_files:
            num_files = len(uploaded_files)
            display_client_for_button = selected_client_tuple[0] # Use display name for button
            
            button_text = f"Process {num_files} file(s) for {display_client_for_button}"
            if num_files == 1: button_text = f"Process '{uploaded_files[0].name}' for {display_client_for_button}"

            process_button_key_suffix = str(selected_client_id_for_upload).replace("-", "_").lower() if selected_client_id_for_upload else "general"
            process_button_key = f"process_btn_auth_{process_button_key_suffix}_{num_files}"

            if st.button(button_text, key=process_button_key, type="primary"):
                progress_bar = st.progress(0.0)
                status_text_area = st.empty() # Use an area for richer status updates
                
                overall_success_count = 0
                
                for i, uploaded_file_item in enumerate(uploaded_files):
                    current_progress = (i + 1) / num_files
                    progress_bar.progress(current_progress)
                    status_text_area.markdown(f"**Processing {i + 1}/{num_files}:** `{uploaded_file_item.name}` for client: **{display_client_for_button}**")
                    
                    # Pass selected_client_id_for_upload to the wrapper
                    result = process_document_wrapper(uploaded_file_item, selected_client_id_for_upload, show_success=False)
                    
                    if result and result.get("task_id"):
                        overall_success_count +=1
                        status_text_area.markdown(f"**Submitting {i + 1}/{num_files}:** `{uploaded_file_item.name}` - ✅ Submitted (Task ID: {result.get('task_id')})")
                    else:
                        status_text_area.markdown(f"**Submitting {i + 1}/{num_files}:** `{uploaded_file_item.name}` - ❌ Failed")
                    time.sleep(0.1) # Small delay for UI update
                
                progress_bar.empty() # Clear progress bar
                status_text_area.empty() # Clear status text area
                
                if overall_success_count > 0:
                    st.success(f"✅ Successfully submitted {overall_success_count} out of {num_files} file(s)!")
                if overall_success_count < num_files:
                    st.error(f"❌ Failed to submit {num_files - overall_success_count} out of {num_files} file(s). Check logs.")
                
                # Clear uploaded files from UI by rerunning (common pattern)
                # Also helps to refresh document list if processing starts immediately
                st.rerun()
    
    st.markdown("---")

    # --- Document Library Display Section (NEW FILTERING LOGIC) ---
    # The subheader for the library is now part of the filter section above.
    # st.subheader(f"Document Library: {selected_filter_display_name}") # Display name from filter
    
    refresh_key = f"refresh_docs_{st.session_state.selected_library_filter_key}"
    if st.button("🔄 Refresh Document List & Processing Status", key=refresh_key):
        # Clear cache specific to the current filter view to force refetch AND re-filter
        cache_key_for_filter = 'documents_data_for_view-' + str(st.session_state.selected_library_filter_key)
        if cache_key_for_filter in st.session_state:
            del st.session_state[cache_key_for_filter]
        # Also, clear the general cache if it exists, as underlying data might have changed
        # This general cache key might need to be more dynamic or specific if used elsewhere.
        # For now, let's assume a general fetch is stored under a generic key or handled by selected_client_matter_id like before.
        # If selected_library_filter_key is the primary key for caching, then above is enough.
        st.rerun()

    # Fetch ALL documents the user might see (or from cache if available for this view)
    # For now, we assume fetch_documents_from_api() gets all relevant docs and we filter client-side.
    # A more advanced backend would allow passing client_id(s) for server-side filtering.
    
    # Using a more generic cache key for the raw, unfiltered data if possible,
    # or make fetch_documents_from_api aware of not caching if we always filter.
    # Let's try to cache the result of the current filter view.
    cache_key_for_current_view_data = 'documents_data_for_view-' + str(st.session_state.selected_library_filter_key)

    if cache_key_for_current_view_data not in st.session_state:
        with st.spinner("Fetching and filtering documents..."):
            # The backend (knowledge service) already handles authorization based on user's role and client access
            # Admin users will see all documents, regular users will see only their authorized documents
            # We don't need to do client-side filtering here
            all_potentially_viewable_docs = fetch_documents_from_api(token=user_token)
            
            # For now, trust the backend authorization and show all returned documents
            # The backend already filters based on user's role (admin sees all, users see authorized clients)
            filtered_docs_list = all_potentially_viewable_docs
            
            # Optional: Apply additional client-specific filtering only if a specific client is selected
            # This is for UI convenience, not security (security is handled by backend)
            current_filter_id = st.session_state.selected_library_filter_key
            
            if current_filter_id == "ALL_VIEWABLE":
                # Show all documents the backend returned (already filtered by authorization)
                pass  # filtered_docs_list already contains all authorized documents
            elif current_filter_id == "GENERAL_NO_CLIENT":
                # Show only documents with no specific client assignment
                filtered_docs_list = [
                    doc for doc in all_potentially_viewable_docs
                    if doc.get("metadata", {}).get("client_id") in [None, "all"]
                ]
            else:
                # Show documents for a specific client ID
                filtered_docs_list = [
                    doc for doc in all_potentially_viewable_docs
                    if doc.get("metadata", {}).get("client_id") == current_filter_id
                ]
            
            st.session_state[cache_key_for_current_view_data] = filtered_docs_list
    
    processed_docs_list_for_display = st.session_state.get(cache_key_for_current_view_data, [])

    # Consolidate with tasks currently being processed (from session_state.processing_tasks)
    # Filter these tasks as well based on the current library filter
    active_processing_docs_to_display = []
    user_authorized_client_ids_for_tasks = {c['id'] for c in user_authorized_clients_for_view}

    for task_id, task_info in list(st.session_state.processing_tasks.items()):
        task_client_id = task_info.get('associated_client_id')
        matches_filter = False
        current_filter_id_for_tasks = st.session_state.selected_library_filter_key

        if current_filter_id_for_tasks == "ALL_VIEWABLE":
            if task_client_id is None or task_client_id in user_authorized_client_ids_for_tasks:
                matches_filter = True
        elif current_filter_id_for_tasks == "GENERAL_NO_CLIENT":
            if task_client_id is None:
                matches_filter = True
        elif task_client_id == current_filter_id_for_tasks:
            matches_filter = True
        
        if matches_filter:
            # ... (code to fetch live progress and format task_info for display - largely same as before) ...
            # This part needs to be adapted from the existing loop that builds `all_documents_to_display`
            # For brevity, I'll represent this as adding a formatted task to active_processing_docs_to_display
            formatted_task_doc = { # Simplified representation
                "id": task_id, # Use task_id as a unique key for display if no doc_id yet
                "file_name": task_info.get("filename"),
                "status": task_info.get("status", "PROCESSING"),
                "chunk_progress": task_info.get("chunks_display", "N/A"), # Assuming chunks_display is updated
                "current_chunk": task_info.get("stage", "N/A"),
                "uploaded_at": task_info.get("upload_time"),
                "type": "processing_task" # Differentiator
            }
            # Fetch and update live progress for this task (copied & adapted from original logic)
            live_progress = fetch_task_progress(task_id)
            if live_progress:
                formatted_task_doc["status"] = live_progress.get("status", formatted_task_doc["status"])
                formatted_task_doc["current_chunk"] = live_progress.get("stage", formatted_task_doc["current_chunk"])
                cp = live_progress.get('chunks_processed', '-')
                ct = live_progress.get('chunks_total', '-')
                formatted_task_doc["chunk_progress"] = f"{cp}/{ct} ({live_progress.get('progress', 0.0)*100:.0f}%)"
                if formatted_task_doc["status"] in ["SUCCESS", "FAILURE"]:
                    if task_id in st.session_state.processing_tasks: del st.session_state.processing_tasks[task_id]
                    # This task is now complete, it should ideally be picked up by the main fetch_documents_from_api on next refresh
                    # So, we might not add it here if it's complete, to avoid duplicates once refreshed.
                    # For now, let's skip adding if complete, assuming it will appear in processed_docs_list_for_display on next full refresh.
                    if formatted_task_doc["status"] in ["SUCCESS", "FAILURE"]: continue 
            active_processing_docs_to_display.append(formatted_task_doc)

    # Combine and display
    # Ensure no duplicates if a processing task just completed and is now in processed_docs_list_for_display
    final_display_list = []
    processed_doc_ids_shown = set()

    for doc in active_processing_docs_to_display: # Display active tasks first
        final_display_list.append(doc)
        processed_doc_ids_shown.add(doc.get("file_name")) # Using file_name as a proxy for task uniqueness before doc_id exists

    for doc in processed_docs_list_for_display:
        # If a document was part of an active task that just finished, its filename might be in processed_doc_ids_shown.
        # The ideal way is to use actual document IDs from processed_docs_list_for_display if available.
        # For now, this simple check helps reduce immediate duplicates post-task completion.
        doc_identifier = doc.get("id", doc.get("file_name")) # Prefer actual ID if available
        if doc_identifier not in processed_doc_ids_shown: # Basic deduplication
            # Add type for styling if needed, or ensure common dict structure
            doc["type"] = "processed_document"
            final_display_list.append(doc)
            processed_doc_ids_shown.add(doc_identifier)

    if not final_display_list:
        st.info(f"No documents found for the selected filter: {selected_filter_display_name}")
    else:
        # Convert to DataFrame for st.data_editor or st.dataframe
        # Define columns carefully for a clean display
        # Ensure all dicts in final_display_list have consistent keys for DataFrame conversion
        # Example columns:
        cols_to_display = ["file_name", "status", "uploaded_at", "chunk_progress", "current_chunk", "id"]
        display_df_data = []
        for item in final_display_list:
            row = {
                "file_name": item.get("file_name", item.get("filename")), # Handle potential key variations
                "status": item.get("status", "N/A"),
                "uploaded_at": item.get("uploaded_at", item.get("created_at")), # Handle variations
                "chunk_progress": item.get("chunk_progress", ""),
                "current_chunk": item.get("current_chunk", ""),
                "id": item.get("id", "N/A") # Document ID or Task ID
            }
            display_df_data.append(row)

        df_to_show = pd.DataFrame(display_df_data)
        # Reorder or select specific columns if needed
        df_to_show = df_to_show[cols_to_display]

        st.dataframe(df_to_show, use_container_width=True, hide_index=True)
        # OR use st.data_editor for more interactive features if desired, but requires more setup for delete.
        # For delete with st.data_editor, you'd use on_change with selection enabled.
        # For now, st.dataframe provides a clean view. Delete functionality can be added per row later if needed.

if __name__ == "__main__":
    # Ensure session state initialization for processing_tasks happens early
    if 'processing_tasks' not in st.session_state:
        st.session_state.processing_tasks = {}
    display_document_management() 