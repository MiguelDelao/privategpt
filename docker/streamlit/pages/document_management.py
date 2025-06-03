"""
PrivateGPT Legal AI - Document Management Page
Modern table-style document management interface
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

def fetch_documents_from_api():
    """Fetch documents from the knowledge service API."""
    logger = get_logger()
    try:
        response = requests.get(f"{KNOWLEDGE_SERVICE_URL}/documents/", timeout=60)
        if response.status_code == 200:
            data = response.json()
            documents = data.get("documents", [])
            return documents
        else:
            logger.log_error(
                user_email=st.session_state.get("user_email", "system"),
                error_message=f"Failed to fetch documents: {response.status_code} - {response.text}",
                error_type="api_fetch_documents"
            )
            return []
    except requests.exceptions.RequestException as e:
        logger.log_error(
            user_email=st.session_state.get("user_email", "system"),
            error_message=f"Network error fetching documents: {str(e)}",
            error_type="api_fetch_documents_network"
        )
        return []
    except Exception as e:
        logger.log_error(
            user_email=st.session_state.get("user_email", "system"),
            error_message=f"Unexpected error fetching documents: {str(e)}",
            error_type="api_fetch_documents_unexpected"
        )
        return []

def delete_document_from_api(document_id: str):
    """Delete a document using the knowledge service API."""
    logger = get_logger()
    try:
        response = requests.delete(f"{KNOWLEDGE_SERVICE_URL}/documents/{document_id}", timeout=30)
        if response.status_code == 200:
            return True, "Document deleted successfully."
        elif response.status_code == 404:
            return False, "Document not found."
        else:
            error_detail = response.json().get("detail", response.text)
            return False, f"Failed to delete: {error_detail}"
    except requests.exceptions.RequestException as e:
        return False, f"Network error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def upload_to_knowledge_service(uploaded_file, metadata=None, progress_callback=None):
    """Upload file to the knowledge service API with progress tracking"""
    try:
        # Prepare the file data
        content_type = uploaded_file.type if uploaded_file.type else "application/octet-stream"
        
        # Debug logging
        print(f"DEBUG: Uploading file: {uploaded_file.name}")
        print(f"DEBUG: Content type: {content_type}")
        print(f"DEBUG: File size: {len(uploaded_file.getvalue())} bytes")
        
        # Prepare files dict for multipart upload
        files = {
            "file": (
                uploaded_file.name, 
                uploaded_file.getvalue(), 
                content_type
            )
        }
        
        # Prepare form data - ensure metadata is JSON string
        if metadata:
            if isinstance(metadata, str):
                data = {"metadata": metadata}
            else:
                import json
                data = {"metadata": json.dumps(metadata)}
        else:
            data = {"metadata": "{}"}
        
        print(f"DEBUG: Metadata: {data['metadata']}")
        
        if progress_callback:
            progress_callback("📤 Uploading to knowledge service...", 0.1)
        
        # Upload to knowledge service
        timeout = max(120, len(uploaded_file.getvalue()) / 1024 / 1024 * 10)
        
        print(f"DEBUG: Making request to: {KNOWLEDGE_SERVICE_URL}/documents/upload")
        
        response = requests.post(
            f"{KNOWLEDGE_SERVICE_URL}/documents/upload",
            files=files,
            data=data,
            timeout=timeout
        )
        
        print(f"DEBUG: Response status: {response.status_code}")
        print(f"DEBUG: Response headers: {dict(response.headers)}")
        print(f"DEBUG: Response content: {response.text[:500]}")
        
        if progress_callback:
            progress_callback("✅ Upload accepted, starting processing...", 0.3)
        
        # Handle response
        if response.status_code == 200:
            upload_result = response.json()
            task_id = upload_result.get("task_id")
            
            if not task_id:
                raise Exception("No task_id returned from upload")
            
            # For now, just return success - we'll check progress separately
            return {
                "task_id": task_id,
                "document_id": task_id,  # Use task_id as temp document_id
                "id": task_id,
                "filename": uploaded_file.name,
                "content_type": content_type,
                "chunk_count": 0,
                "size": len(uploaded_file.getvalue()),
                "status": "Processing",
                "message": "Document uploaded and processing started"
            }
            
        elif response.status_code == 400:
            try:
                error_detail = response.json()
                error_msg = error_detail.get("detail", "Unknown error")
                print(f"DEBUG: 400 Error detail: {error_detail}")
                raise Exception(f"Bad request (400): {error_msg}")
            except (ValueError, KeyError):
                error_text = response.text[:500] if response.text else "No error details provided"
                print(f"DEBUG: 400 Error raw text: {error_text}")
                raise Exception(f"Bad request (400): {error_text}")
        else:
            try:
                error_detail = response.json().get("detail", response.text)
            except:
                error_detail = response.text
            raise Exception(f"Knowledge service error ({response.status_code}): {error_detail}")
    
    except requests.exceptions.Timeout:
        raise Exception(f"Upload timed out after {timeout} seconds.")
    except requests.exceptions.ConnectionError:
        raise Exception("Cannot connect to knowledge service. Please check if the service is running.")
    except requests.exceptions.RequestException as e:
        print(f"DEBUG: RequestException: {str(e)}")
        raise Exception(f"Network error uploading to knowledge service: {str(e)}")
    except Exception as e:
        print(f"DEBUG: General exception: {str(e)}")
        if "Knowledge service error" in str(e) or "Bad request" in str(e):
            raise
        else:
            raise Exception(f"Unexpected error during upload: {str(e)}")

def process_document_wrapper(uploaded_file):
    """Process document using the knowledge-service API with live progress updates"""
    try:
        logger = get_logger()
        user_email = st.session_state.get("user_email", "unknown@example.com")
        
        # Validate file size (200MB max)
        max_size = 200 * 1024 * 1024  # 200MB
        if uploaded_file.size > max_size:
            st.error(f"File too large. Maximum size is {max_size // (1024*1024)}MB")
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
        
        def update_progress(message, progress):
            stage_text.text(message)
            overall_progress.progress(progress)
        
        update_progress("🔍 Starting document processing...", 0.05)
        
        # Prepare metadata
        metadata = {
            "client_matter": st.session_state.get("current_matter", "General"),
            "uploaded_by": user_email,
            "file_size": uploaded_file.size,
            "upload_timestamp": datetime.now().isoformat()
        }
        
        # Upload to knowledge service
        result = upload_to_knowledge_service(
            uploaded_file, 
            metadata=metadata,
            progress_callback=update_progress
        )
        
        update_progress("✅ Document processing started!", 1.0)
        
        # Log the upload
        logger.log_document_upload(
            user_email=user_email, 
            filename=uploaded_file.name, 
            file_size=uploaded_file.size
        )
        
        with status_container:
            st.success(f"✅ Document '{uploaded_file.name}' uploaded successfully! Processing in background...")
        
        return True
    
    except Exception as e:
        logger = get_logger()
        user_email = st.session_state.get("user_email", "unknown")
        error_msg = f"Failed to process document '{uploaded_file.name if uploaded_file else 'Unknown'}': {str(e)}"
        logger.log_error(user_email=user_email, error_message=error_msg, error_type="document_processing")
        
        with status_container:
            st.error(f"❌ Upload failed: {str(e)}")
        return False

def display_document_management():
    """Display the modern document management interface"""
    st.markdown(f'<div class="main-header">📂 Document Management</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">Upload, process, and manage your legal documents.</div>', unsafe_allow_html=True)
    
    # Upload Section
    st.markdown("### ⬆️ Upload New Document")
    
    uploaded_file = st.file_uploader(
        "Choose a file (PDF, DOCX, TXT - Max 200MB)",
        type=["pdf", "docx", "txt"],
        key="doc_uploader"
    )
    
    if uploaded_file:
        if st.button(
            f"📤 Process Document: {uploaded_file.name}", 
            type="primary", 
            use_container_width=True
        ):
            with st.spinner(f"Processing {uploaded_file.name}..."):
                success = process_document_wrapper(uploaded_file)
                if success:
                    time.sleep(2)  # Give a moment for processing to start
                    # Clear the cache to refresh document list
                    if "documents_cache" in st.session_state:
                        del st.session_state["documents_cache"]
                    st.rerun()

    st.markdown("---")
    
    # Document Library Section
    st.markdown("### 📚 Document Library")
    
    # Refresh button
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("🔄 Refresh", use_container_width=True):
            if "documents_cache" in st.session_state:
                del st.session_state["documents_cache"]
            st.rerun()
    
    # Fetch documents with caching
    if "documents_cache" not in st.session_state or time.time() - st.session_state.get("documents_cache_time", 0) > 30:
        with st.spinner("Loading documents..."):
            documents = fetch_documents_from_api()
            st.session_state["documents_cache"] = documents
            st.session_state["documents_cache_time"] = time.time()
    else:
        documents = st.session_state["documents_cache"]
    
    if documents:
        st.markdown(f"**Found {len(documents)} document(s)**")
        
        # Create a proper data table
        df_data = []
        for doc in documents:
            created_at = doc.get("created_at", "")
            if created_at:
                try:
                    # Parse the datetime and format it nicely
                    dt = pd.to_datetime(created_at)
                    created_at_formatted = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    created_at_formatted = created_at
            else:
                created_at_formatted = "N/A"
                
            df_data.append({
                "📄 Document": doc.get("filename", "Unknown"),
                "📅 Uploaded": created_at_formatted,
                "📊 Size": f"{doc.get('size', 0) / (1024*1024):.1f} MB" if doc.get('size') else "N/A",
                "🧩 Chunks": doc.get("chunk_count", 0),
                "📋 Type": doc.get("content_type", "").split('/')[-1].upper() if doc.get("content_type") else "Unknown",
                "🆔 ID": doc.get("id", "")
            })
        
        if df_data:
            df = pd.DataFrame(df_data)
            
            # Display the table with styling
            st.markdown("""
            <style>
            .stDataFrame {
                width: 100%;
            }
            .stDataFrame > div {
                width: 100%;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Display table
            st.dataframe(
                df.drop(columns=['🆔 ID']),  # Hide ID column from display
                use_container_width=True,
                hide_index=True
            )
            
            # Delete functionality
            st.markdown("### 🗑️ Delete Documents")
            
            if len(df_data) > 0:
                # Create select box for deletion
                doc_options = [f"{doc['📄 Document']} (ID: {doc['🆔 ID'][:8]}...)" for doc in df_data]
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    selected_doc = st.selectbox(
                        "Select document to delete:",
                        options=range(len(doc_options)),
                        format_func=lambda x: doc_options[x],
                        key="delete_selector"
                    )
                
                with col2:
                    if st.button("🗑️ Delete", type="secondary", use_container_width=True):
                        doc_to_delete = df_data[selected_doc]
                        doc_id = doc_to_delete['🆔 ID']
                        
                        with st.spinner(f"Deleting {doc_to_delete['📄 Document']}..."):
                            success, message = delete_document_from_api(doc_id)
                            
                            if success:
                                st.success(message)
                                # Clear cache and refresh
                                if "documents_cache" in st.session_state:
                                    del st.session_state["documents_cache"]
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(message)
    else:
        st.info("📝 No documents found. Upload some documents to get started!")
        
        # Show helpful tips
        st.markdown("""
        **💡 Tips:**
        - Supported formats: PDF, DOCX, TXT
        - Maximum file size: 200MB
        - Documents are processed automatically after upload
        - Use the refresh button to check processing status
        """)

if __name__ == "__main__":
    display_navigation_sidebar(current_page="Document Management")
    display_document_management() 