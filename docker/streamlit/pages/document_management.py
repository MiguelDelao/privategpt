"""
PrivateGPT Legal AI - Document Management Page
Clean and simple document management interface
"""

import streamlit as st
import time
from datetime import datetime
import sys
import os
import pandas as pd # For better table display

# Add parent directory to path to import pages_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pages_utils import (
    APP_TITLE, initialize_session_state, require_auth, 
    display_navigation_sidebar, apply_page_styling,
    get_logger, get_rag_engine, get_document_processor, add_demo_documents
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

# Add demo data if no documents are present (can be toggled)
if not st.session_state.get("uploaded_documents"): # Check if list is empty or doesn't exist
    add_demo_documents() 

def process_document_wrapper(uploaded_file):
    """Wraps the original process_document to fit new UI structure if needed"""
    try:
        processor = get_document_processor()
        rag_engine = get_rag_engine()
        logger = get_logger()
        
        user_info = st.session_state.user_info
        user_email = user_info.get("user", {}).get("email", "Unknown")
        
        is_valid, error_message = processor.validate_file(uploaded_file)
        if not is_valid:
            st.error(error_message)
            return False
        
        file_info = processor.get_file_info(uploaded_file)
        
        with st.spinner(f"Processing {uploaded_file.name}..."):
            text_content = processor.extract_text(uploaded_file)
            document_id = rag_engine.add_document(
                content=text_content,
                filename=uploaded_file.name,
                client_matter=st.session_state.get("current_matter", "General"), # This could be a per-upload setting
                doc_type=file_info["document_type"],
                uploaded_by=user_email
            )
            logger.log_document_upload(
                user_email=user_email, filename=uploaded_file.name, file_size=uploaded_file.size
            )
            doc_entry = {
                "Name": uploaded_file.name,
                "Status": "Processed",
                "Ingested At": datetime.now(),
                "Size (KB)": f"{uploaded_file.size / 1024:.1f}",
                "Type": file_info["document_type"],
                "ID": document_id,
                "Client Matter": st.session_state.get("current_matter", "General"),
                "Uploaded By": user_email
            }
            if "uploaded_documents" not in st.session_state or not isinstance(st.session_state.uploaded_documents, list):
                st.session_state.uploaded_documents = []
            st.session_state.uploaded_documents.insert(0, doc_entry)
            st.success(f"✅ Document '{uploaded_file.name}' processed successfully! Document ID: {document_id}")
            return True
    
    except Exception as e:
        logger = get_logger() # Ensure logger is available
        user_email = st.session_state.get("user_info", {}).get("user", {}).get("email", "Unknown")
        error_msg = f"Failed to process document '{uploaded_file.name if uploaded_file else 'Unknown'}': {str(e)}"
        logger.log_error(user_email=user_email, error_message=error_msg, error_type="document_processing")
        st.error(error_msg)
        return False

def display_document_management():
    """Display the clean document management interface"""
    st.markdown(f'<div class="main-header">📂 Document Management</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">Upload, process, and manage your legal documents.</div>', unsafe_allow_html=True)
    
    # Upload section in an expander for a cleaner look
    with st.expander("📤 Upload New Documents", expanded=True):
        uploaded_files = st.file_uploader(
            "Choose legal documents (PDF, DOCX, TXT)", 
            type=["pdf", "docx", "txt"], 
            accept_multiple_files=True,
            key="doc_uploader_main"
        )
        # Placeholder for client matter per upload - can be enhanced
        # selected_client_matter = st.text_input("Assign to Client/Matter (optional):", st.session_state.get("current_matter", "General"))

        if uploaded_files:
            if st.button("🚀 Process Selected Documents", type="primary", use_container_width=True):
                success_count = 0
                total_files = len(uploaded_files)
                progress_bar = st.progress(0)
                status_text = st.empty() # For individual file status updates
                
                for i, uploaded_file in enumerate(uploaded_files):
                    # Basic check for existing name to avoid re-processing in same session click
                    # More robust check would involve checking against document IDs in Weaviate
                    if any(doc['Name'] == uploaded_file.name for doc in st.session_state.get("uploaded_documents", [])):
                        st.warning(f"Document '{uploaded_file.name}' appears to be already listed. Skipping.")
                        # total_files -=1 # Adjust total if skipping, or handle progress differently
                        continue
                    
                    status_text.info(f"Processing {uploaded_file.name} ({i+1}/{total_files})...")
                    if process_document_wrapper(uploaded_file):
                        success_count += 1
                    progress_bar.progress((i + 1) / total_files)
                
                if success_count > 0:
                    status_text.success(f"✅ Successfully processed {success_count} / {total_files} documents!")
                    time.sleep(2) # Brief pause to show message
                    st.rerun() 
                elif total_files > 0 : # If files were attempted but none succeeded
                     status_text.error("❌ No new documents were processed successfully.")
                else: # No files were attempted (e.g. all skipped)
                    status_text.info("No new files to process.")
    
    st.markdown("### 📋 Document Library")
    
    # Search and filter
    cols = st.columns([3, 2, 1])
    with cols[0]:
        search_query = st.text_input("🔍 Search by name or ID", placeholder="Enter filename or document ID...")
    with cols[1]:
        # Get unique document types from session state for filter options
        doc_types = sorted(list(set(doc.get("Type", "Unknown") for doc in st.session_state.get("uploaded_documents", []))))
        type_filter = st.selectbox("Filter by type", ["All Types"] + doc_types)
    with cols[2]:
        sort_order = st.selectbox("Sort by", ["Ingested At (Newest First)", "Name (A-Z)"])

    documents_to_display = st.session_state.get("uploaded_documents", [])
    
    # Apply filtering
    if search_query:
        documents_to_display = [doc for doc in documents_to_display if search_query.lower() in doc['Name'].lower() or search_query.lower() in doc.get('ID', '').lower()]
    if type_filter != "All Types":
        documents_to_display = [doc for doc in documents_to_display if doc.get('Type') == type_filter]
    
    # Apply sorting
    if sort_order == "Name (A-Z)":
        documents_to_display = sorted(documents_to_display, key=lambda x: x['Name'])
    else: # Default to Ingested At (Newest First) which is the natural order of insertion
        documents_to_display = sorted(documents_to_display, key=lambda x: x.get('Ingested At', datetime.min), reverse=True)

    if documents_to_display:
        st.caption(f"Showing {len(documents_to_display)} of {len(st.session_state.get("uploaded_documents", []))} documents.")
        
        # Using st.dataframe for a cleaner table, can be customized further
        df_display = pd.DataFrame(documents_to_display)
        # Select and reorder columns for display
        display_columns = ['Name', 'Type', 'Status', 'Size (KB)', 'Ingested At', 'Uploaded By', 'Client Matter', 'ID']
        df_display = df_display[[col for col in display_columns if col in df_display.columns]]
        
        # Format datetime column for better readability
        if 'Ingested At' in df_display.columns:
            df_display['Ingested At'] = pd.to_datetime(df_display['Ingested At']).dt.strftime('%Y-%m-%d %H:%M')

        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        # Placeholder for actions on selected documents (e.g., delete, re-process)
        # selected_docs = st.multiselect("Select documents for action:", options=[doc['Name'] for doc in documents_to_display])
        # if selected_docs and st.button("Delete Selected"): ...

    else:
        st.info("No documents match your current filters, or no documents have been uploaded yet.")

    # --- For Demo/Testing: Clear all documents ---
    st.markdown("---")
    if st.session_state.user_role == 'admin': # Only admin can see this
        if st.button("⚠️ Clear All Uploaded Documents (Demo Reset)", key="clear_all_docs_admin"):
            if "confirm_clear_all_docs" not in st.session_state:
                st.session_state.confirm_clear_all_docs = True
                st.warning("This will remove all documents from the UI list. Are you sure? Click again to confirm.")
            else:
                st.session_state.uploaded_documents = []
                del st.session_state.confirm_clear_all_docs
                # Note: This only clears the UI list. For a true reset, Weaviate data would also need clearing.
                st.success("All documents cleared from the list.")
                st.rerun()
        elif "confirm_clear_all_docs" in st.session_state: # Reset confirmation if button not clicked again
             del st.session_state.confirm_clear_all_docs

if __name__ == "__main__":
    display_navigation_sidebar(current_page="Documents")
    display_document_management() 