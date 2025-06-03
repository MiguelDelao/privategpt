"""
PrivateGPT Legal AI - Document Management Page
Clean and simple document management interface
"""

import streamlit as st
import time
from datetime import datetime
import sys
import os
import pandas as pd
import requests

# Add parent directory to path to import pages_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pages_utils import (
    APP_TITLE, initialize_session_state, require_auth, 
    display_navigation_sidebar, apply_page_styling,
    get_logger
)

# Page configuration
st.set_page_config(
    page_title=f"Documents - {APP_TITLE}", 
    page_icon="📂",
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Apply styling and authentication
apply_page_styling()
initialize_session_state()
require_auth()

# Knowledge Service Configuration
KNOWLEDGE_SERVICE_URL = os.getenv("KNOWLEDGE_SERVICE_URL", "http://knowledge-service:8000")

def upload_to_knowledge_service(uploaded_file, metadata=None, progress_callback=None):
    """Upload file to the knowledge service API with progress tracking"""
    try:
        # Prepare the file data - be more explicit about content type
        content_type = uploaded_file.type if uploaded_file.type else "application/octet-stream"
        
        # Prepare files dict for multipart upload
        files = {
            "file": (
                uploaded_file.name, 
                uploaded_file.getvalue(), 
                content_type
            )
        }
        
        # Prepare form data
        data = {"metadata": metadata or "{}"}
        
        if progress_callback:
            progress_callback("📤 Uploading to knowledge service...", 0.1)
        
        # Upload to knowledge service with increased timeout for large files
        timeout = max(120, len(uploaded_file.getvalue()) / 1024 / 1024 * 10)  # 10 seconds per MB, minimum 2 minutes
        
        response = requests.post(
            f"{KNOWLEDGE_SERVICE_URL}/documents/upload",
            files=files,
            data=data,
            timeout=timeout
        )
        
        if progress_callback:
            progress_callback("✅ Upload complete, processing response...", 0.9)
        
        # More detailed error handling
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 400:
            # Try to get specific error message from response
            try:
                error_detail = response.json().get("detail", response.text)
            except:
                error_detail = response.text
            raise Exception(f"Bad request (400): {error_detail}")
        else:
            raise Exception(f"Knowledge service error: {response.status_code} - {response.text}")
    
    except requests.exceptions.Timeout:
        raise Exception(f"Upload timed out after {timeout} seconds. Large documents may take longer to process.")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error uploading to knowledge service: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to upload to knowledge service: {str(e)}")

def process_document_wrapper(uploaded_file):
    """Process document using the knowledge-service API with live progress updates"""
    try:
        logger = get_logger()
        
        user_info = st.session_state.user_info
        user_email = user_info.get("user", {}).get("email", "unknown@example.com")
        
        # Validate file size (200MB max for better UX)
        max_size = 200 * 1024 * 1024  # 200MB
        if uploaded_file.size > max_size:
            st.error(f"File too large. Maximum size is {max_size // (1024*1024)}MB for optimal processing")
            return False
        
        # Validate file type
        allowed_types = ['.pdf', '.docx', '.txt']
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        if file_extension not in allowed_types:
            st.error(f"Unsupported file format. Supported formats: {', '.join(allowed_types)}")
            return False
        
        # Create progress containers
        progress_container = st.container()
        status_container = st.container()
        
        with progress_container:
            overall_progress = st.progress(0)
            stage_text = st.empty()
            detail_text = st.empty()
        
        def update_progress(message, progress):
            stage_text.text(message)
            overall_progress.progress(progress)
        
        # Estimate processing time based on file size
        estimated_time = max(30, uploaded_file.size / 1024 / 1024 * 15)  # 15 seconds per MB
        detail_text.info(f"📊 Processing {uploaded_file.name} ({uploaded_file.size / 1024 / 1024:.1f}MB) - Estimated time: {estimated_time:.0f}s")
        
        update_progress("🔍 Starting enhanced PDF extraction...", 0.05)
        
        # Upload to knowledge service with progress tracking
        result = upload_to_knowledge_service(
            uploaded_file, 
            metadata=f'{{"client_matter": "{st.session_state.get("current_matter", "General")}", "uploaded_by": "{user_email}"}}',
            progress_callback=update_progress
        )
        
        update_progress("✅ Document processing complete!", 1.0)
        
        # Log the upload
        logger.log_document_upload(
            user_email=user_email, 
            filename=uploaded_file.name, 
            file_size=uploaded_file.size
        )
        
        # Create document entry for UI
        doc_entry = {
            "Name": uploaded_file.name,
            "Status": "Processed",
            "Ingested At": datetime.now(),
            "Size (KB)": f"{uploaded_file.size / 1024:.1f}",
            "Type": result.get("content_type", "unknown"),
            "ID": result.get("id", "unknown"),
            "Client Matter": st.session_state.get("current_matter", "General"),
            "Uploaded By": user_email,
            "Chunk Count": result.get("chunk_count", 0)
        }
        
        # Add to session state
        if "uploaded_documents" not in st.session_state:
            st.session_state.uploaded_documents = []
        st.session_state.uploaded_documents.insert(0, doc_entry)
        
        with status_container:
            st.success(f"✅ Document '{uploaded_file.name}' processed successfully! "
                      f"Document ID: {result.get('id', 'unknown')} "
                      f"({result.get('chunk_count', 0)} chunks created)")
        
        return True
    
    except Exception as e:
        logger = get_logger()
        user_email = st.session_state.get("user_info", {}).get("user", {}).get("email", "unknown")
        error_msg = f"Failed to process document '{uploaded_file.name if uploaded_file else 'Unknown'}': {str(e)}"
        logger.log_error(user_email=user_email, error_message=error_msg, error_type="document_processing")
        
        with status_container:
            st.error(error_msg)
        return False

def display_document_management():
    """Display the clean document management interface"""
    st.markdown(f'<div class="main-header">📂 Document Management</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">Upload, process, and manage your legal documents.</div>', unsafe_allow_html=True)
    
    # Add refresh functionality
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🔄 Refresh", key="refresh_docs"):
            # Clear session state to force refresh from API
            if "api_documents" in st.session_state:
                del st.session_state["api_documents"]
            st.rerun()
    
    # Load documents from API
    if "api_documents" not in st.session_state:
        try:
            response = requests.get(f"{KNOWLEDGE_SERVICE_URL}/documents/", timeout=60)
            if response.status_code == 200:
                api_data = response.json()
                st.session_state.api_documents = api_data.get("documents", [])
            else:
                st.session_state.api_documents = []
        except Exception as e:
            st.error(f"Failed to load documents from API: {e}")
            st.session_state.api_documents = []
    
    # Upload section in an expander for a cleaner look
    with st.expander("📤 Upload New Documents", expanded=True):
        st.info("💡 **Pro Tip**: Large documents (>5MB) may take several minutes to process. The upload will continue in the background.")
        
        uploaded_files = st.file_uploader(
            "Choose legal documents (PDF, DOCX, TXT)", 
            type=["pdf", "docx", "txt"], 
            accept_multiple_files=True,
            key="doc_uploader_main"
        )
        
        # Show current processing queue status
        processing_count = len([doc for doc in st.session_state.get("uploaded_documents", []) if doc.get("Status") == "Processing"])
        if processing_count > 0:
            st.info(f"📋 {processing_count} document(s) currently processing in background...")

        if uploaded_files:
            if st.button("🚀 Process Selected Documents", type="primary", use_container_width=True):
                success_count = 0
                total_files = len(uploaded_files)
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, uploaded_file in enumerate(uploaded_files):
                    # Check for existing files in both session and API
                    existing_session_names = [
                        doc.get('Name', doc.get('name', '')) 
                        for doc in st.session_state.get("uploaded_documents", [])
                    ]
                    existing_api_names = [
                        doc.get('filename', '') 
                        for doc in st.session_state.get("api_documents", [])
                    ]
                    
                    if uploaded_file.name in existing_session_names or uploaded_file.name in existing_api_names:
                        st.warning(f"Document '{uploaded_file.name}' appears to already exist. Skipping.")
                        continue
                    
                    status_text.info(f"Processing {uploaded_file.name} ({i+1}/{total_files})...")
                    
                    # For large files, show different message
                    file_size_mb = uploaded_file.size / (1024 * 1024)
                    if file_size_mb > 5:
                        st.warning(f"⏳ Large file detected ({file_size_mb:.1f}MB). This may take 5-10 minutes to process.")
                        st.info("💡 You can continue using the app - processing happens in background!")
                    
                    if process_document_wrapper(uploaded_file):
                        success_count += 1
                    progress_bar.progress((i + 1) / total_files)
                
                # Refresh API documents after upload
                if success_count > 0:
                    status_text.success(f"✅ Successfully processed {success_count} / {total_files} documents!")
                    time.sleep(2)
                    # Clear API cache to force refresh
                    if "api_documents" in st.session_state:
                        del st.session_state["api_documents"]
                    st.rerun()
                elif total_files > 0:
                    status_text.error("❌ No new documents were processed successfully.")
                else:
                    status_text.info("No new files to process.")
    
    st.markdown("### 📋 Document Library")
    
    # Combine session state and API documents
    session_docs = st.session_state.get("uploaded_documents", [])
    api_docs = st.session_state.get("api_documents", [])
    
    # Convert API docs to display format
    converted_api_docs = []
    for doc in api_docs:
        converted_doc = {
            "Name": doc.get("filename", "Unknown"),
            "Status": "Processed",
            "Ingested At": doc.get("created_at", "Unknown"),
            "Size (KB)": f"{doc.get('metadata', {}).get('size', 0) / 1024:.1f}" if doc.get('metadata', {}).get('size') else "Unknown",
            "Type": doc.get("content_type", "Unknown"),
            "ID": doc.get("id", "Unknown"),
            "Client Matter": "API Loaded",
            "Uploaded By": "System",
            "Chunk Count": doc.get("chunk_count", 0)
        }
        converted_api_docs.append(converted_doc)
    
    # Combine and deduplicate
    all_documents = []
    seen_names = set()
    
    # Add session docs first (these are current session uploads)
    for doc in session_docs:
        name = doc.get('Name', doc.get('name', ''))
        if name not in seen_names:
            all_documents.append(doc)
            seen_names.add(name)
    
    # Add API docs that aren't already in session
    for doc in converted_api_docs:
        name = doc.get('Name', '')
        if name not in seen_names:
            all_documents.append(doc)
            seen_names.add(name)
    
    # Search and filter
    cols = st.columns([3, 2, 1])
    with cols[0]:
        search_query = st.text_input("🔍 Search by name or ID", placeholder="Enter filename or document ID...")
    with cols[1]:
        # Get unique document types
        doc_types = sorted(list(set(
            doc.get("Type", doc.get("type", "Unknown")) 
            for doc in all_documents
        )))
        type_filter = st.selectbox("Filter by type", ["All Types"] + doc_types)
    with cols[2]:
        sort_order = st.selectbox("Sort by", ["Ingested At (Newest First)", "Name (A-Z)"])

    documents_to_display = all_documents.copy()
    
    # Apply filtering
    if search_query:
        documents_to_display = [
            doc for doc in documents_to_display 
            if (search_query.lower() in doc.get('Name', doc.get('name', '')).lower() or 
                search_query.lower() in doc.get('ID', doc.get('document_id', '')).lower())
        ]
    if type_filter != "All Types":
        documents_to_display = [
            doc for doc in documents_to_display 
            if doc.get('Type', doc.get('type', 'Unknown')) == type_filter
        ]
    
    # Apply sorting
    if sort_order == "Name (A-Z)":
        documents_to_display = sorted(
            documents_to_display, 
            key=lambda x: x.get('Name', x.get('name', ''))
        )
    else:
        documents_to_display = sorted(
            documents_to_display, 
            key=lambda x: x.get('Ingested At', x.get('ingested_at', datetime.min)), 
            reverse=True
        )

    if documents_to_display:
        st.caption(f"Showing {len(documents_to_display)} of {len(all_documents)} total documents.")
        
        # Display documents table
        df_display = pd.DataFrame(documents_to_display)
        display_columns = ['Name', 'Type', 'Status', 'Size (KB)', 'Ingested At', 'Uploaded By', 'Client Matter', 'Chunk Count', 'ID']
        df_display = df_display[[col for col in display_columns if col in df_display.columns]]
        
        # Format datetime column
        if 'Ingested At' in df_display.columns:
            df_display['Ingested At'] = pd.to_datetime(df_display['Ingested At'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M')

        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
    else:
        st.info("No documents match your current filters, or no documents have been uploaded yet.")
        if len(all_documents) == 0:
            st.info("💡 Try uploading a document above or click 'Refresh' to load from the knowledge service.")

    # Show API status
    api_doc_count = len(st.session_state.get("api_documents", []))
    session_doc_count = len(st.session_state.get("uploaded_documents", []))
    
    st.markdown("---")
    st.caption(f"📊 Status: {api_doc_count} documents in knowledge base, {session_doc_count} in current session")
    
    # Admin section for clearing documents  
    if st.session_state.user_role == 'admin':
        with st.expander("⚠️ Admin Actions", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Clear Session Documents", key="clear_session_docs"):
                    st.session_state.uploaded_documents = []
                    st.success("Session documents cleared.")
                    st.rerun()
            with col2:
                if st.button("🔄 Force Refresh from API", key="force_refresh_api"):
                    if "api_documents" in st.session_state:
                        del st.session_state["api_documents"]
                    st.success("API cache cleared. Refreshing...")
                    st.rerun()

if __name__ == "__main__":
    display_navigation_sidebar(current_page="Documents")
    display_document_management() 