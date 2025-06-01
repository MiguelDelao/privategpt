"""
PrivateGPT Legal AI - Document Management Page
Clean and simple document management interface
"""

import streamlit as st
import time
from datetime import datetime
import sys
import os

# Add parent directory to path to import pages_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pages_utils import (
    APP_TITLE, VECTOR_DB_NAME, WORKFLOW_ENGINE,
    initialize_session_state, require_auth, display_navigation_sidebar, apply_page_styling,
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
require_auth(main_app_file="../main_app.py")

# Add demo data
add_demo_documents()

def process_document(uploaded_file):
    """Process uploaded document using existing infrastructure"""
    try:
        processor = get_document_processor()
        rag_engine = get_rag_engine()
        logger = get_logger()
        
        user_info = st.session_state.user_info
        user_email = user_info.get("user", {}).get("email", "Unknown")
        
        # Validate file first
        is_valid, error_message = processor.validate_file(uploaded_file)
        if not is_valid:
            st.error(error_message)
            return False
        
        # Get file info
        file_info = processor.get_file_info(uploaded_file)
        
        with st.spinner(f"Processing {uploaded_file.name}..."):
            # Extract text from document
            text_content = processor.extract_text(uploaded_file)
            
            # Add to vector database
            document_id = rag_engine.add_document(
                content=text_content,
                filename=uploaded_file.name,
                client_matter=st.session_state.get("current_matter", "General"),
                doc_type=file_info["document_type"],
                uploaded_by=user_email
            )
            
            # Log document processing
            logger.log_document_upload(
                user_email=user_email,
                filename=uploaded_file.name,
                file_size=uploaded_file.size
            )
            
            # Add to session state for UI display
            doc_entry = {
                "name": uploaded_file.name,
                "status": "Processed",
                "ingested_at": datetime.now(),
                "size": f"{uploaded_file.size / 1024:.1f}KB",
                "type": file_info["document_type"],
                "document_id": document_id,
                "client_matter": st.session_state.get("current_matter", "General"),
                "uploaded_by": user_email
            }
            
            if "uploaded_documents" not in st.session_state:
                st.session_state.uploaded_documents = []
            st.session_state.uploaded_documents.insert(0, doc_entry)
            
            st.success(f"✅ Document '{uploaded_file.name}' processed successfully!")
            st.info(f"Document ID: {document_id}")
            return True
    
    except Exception as e:
        # Log error using existing compliance logger
        logger = get_logger()
        user_email = st.session_state.user_info.get("user", {}).get("email", "Unknown")
        
        error_msg = f"Failed to process document: {str(e)}"
        logger.log_error(
            user_email=user_email,
            error_message=error_msg,
            error_type="document_processing"
        )
        st.error(error_msg)
        return False

def display_document_management():
    """Display the clean document management interface"""
    # Main header
    st.markdown('<div class="main-header">📂 Document Management</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Upload, process, and manage your legal documents</div>', unsafe_allow_html=True)
    
    # Upload section
    st.subheader("📤 Upload New Documents")
    
    # File upload interface
    uploaded_files = st.file_uploader(
        "Choose legal documents", 
        type=["pdf", "docx", "txt"], 
        accept_multiple_files=True,
        key="doc_uploader",
        help="Supported formats: PDF, DOCX, TXT"
    )
    
    if uploaded_files and st.button("🚀 Process Documents", type="primary"):
        success_count = 0
        total_files = len(uploaded_files)
        
        # Create progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, uploaded_file in enumerate(uploaded_files):
            # Check if document already exists
            existing_docs = st.session_state.get("uploaded_documents", [])
            if any(doc['name'] == uploaded_file.name for doc in existing_docs):
                st.warning(f"Document '{uploaded_file.name}' appears to already exist. Skipping.")
                continue
            
            # Update progress
            progress = (i + 1) / total_files
            progress_bar.progress(progress)
            status_text.text(f"Processing {uploaded_file.name}...")
            
            # Process document
            if process_document(uploaded_file):
                success_count += 1
        
        # Final status
        progress_bar.progress(1.0)
        if success_count > 0:
            status_text.text(f"✅ Successfully processed {success_count}/{total_files} documents!")
            time.sleep(2)
            st.rerun()  # Refresh to show new documents
        else:
            status_text.text("❌ No documents were processed successfully.")
    
    st.markdown("---")
    
    # Document library
    st.subheader("📋 Document Library")
    
    # Search and filter
    col1, col2 = st.columns([2, 1])
    with col1:
        search_filter = st.text_input("🔍 Search documents", placeholder="Enter filename or content...")
    with col2:
        type_filter = st.selectbox("Filter by type", ["All", "contract", "case_law", "filing", "memo", "statute", "document"])
    
    # Display documents
    documents = st.session_state.get("uploaded_documents", [])
    
    if documents:
        # Apply filters
        filtered_docs = documents
        
        if search_filter:
            filtered_docs = [doc for doc in filtered_docs if search_filter.lower() in doc['name'].lower()]
        
        if type_filter != "All":
            filtered_docs = [doc for doc in filtered_docs if doc.get('type') == type_filter]
        
        if filtered_docs:
            st.caption(f"Showing {len(filtered_docs)} of {len(documents)} documents")
            
            # Display documents in a clean list
            for doc in filtered_docs:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    
                    with col1:
                        st.write(f"📄 **{doc['name']}**")
                        st.caption(f"{doc['type'].title()} • {doc['client_matter']} • by {doc['uploaded_by']}")
                    
                    with col2:
                        st.write(doc['size'])
                    
                    with col3:
                        st.write(doc['status'])
                    
                    with col4:
                        if isinstance(doc['ingested_at'], datetime):
                            st.write(doc['ingested_at'].strftime("%m/%d/%Y"))
                        else:
                            st.write("Recent")
                    
                    st.markdown("---")
            
            # Actions
            st.markdown("### 🛠️ Actions")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔍 Test Document Search"):
                    if search_filter:
                        try:
                            rag_engine = get_rag_engine()
                            results = rag_engine.search_documents(search_filter, limit=3)
                            
                            if results:
                                st.success(f"Found {len(results)} relevant chunks!")
                                for i, result in enumerate(results, 1):
                                    with st.expander(f"Result {i}: {result['source']} (Score: {result['score']:.3f})"):
                                        st.text(result['content'][:300] + "..." if len(result['content']) > 300 else result['content'])
                            else:
                                st.info("No results found for that search term.")
                        except Exception as e:
                            st.error(f"Search failed: {str(e)}")
                    else:
                        st.warning("Enter a search term above first.")
            
            with col2:
                if st.button("📊 System Health"):
                    try:
                        rag_engine = get_rag_engine()
                        health = rag_engine.health_check()
                        
                        if health['weaviate'] and health['ollama']:
                            st.success("✅ All systems operational")
                        else:
                            st.warning("⚠️ Some systems offline")
                        
                        st.text(f"Weaviate: {'✅' if health['weaviate'] else '❌'}")
                        st.text(f"Ollama: {'✅' if health['ollama'] else '❌'}")
                    except Exception as e:
                        st.error(f"Health check failed: {str(e)}")
            
            with col3:
                if st.button("🗑️ Clear Demo Data"):
                    if st.session_state.get("confirm_clear", False):
                        st.session_state.uploaded_documents = []
                        st.session_state.confirm_clear = False
                        st.success("Demo data cleared!")
                        st.rerun()
                    else:
                        st.session_state.confirm_clear = True
                        st.warning("Click again to confirm.")
        else:
            st.info("No documents match your current filters.")
    else:
        st.info("No documents uploaded yet. Use the upload section above to get started.")

# Sidebar navigation
display_navigation_sidebar()

# Main content
if __name__ == "__main__":
    display_document_management() 