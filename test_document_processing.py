#!/usr/bin/env python3
"""Test document processing with progress tracking."""
import time
import json
import subprocess

BASE_URL = "http://localhost:8002/rag"

def test_document_processing():
    print("🚀 Testing Document Processing with Progress Tracking...")
    
    # Step 1: Create a collection
    print("\n1. Creating test collection...")
    create_cmd = f'''curl -s -X POST {BASE_URL}/collections \
      -H "Content-Type: application/json" \
      -d '{{"name": "Test Processing Collection", "icon": "📊"}}'
    '''
    
    result = subprocess.run(create_cmd, shell=True, capture_output=True, text=True)
    collection = json.loads(result.stdout)
    collection_id = collection["id"]
    print(f"✅ Created collection: {collection_id}")
    
    # Step 2: Upload a document
    print("\n2. Uploading test document...")
    
    # Create a larger test document for better progress visualization
    test_content = """
    This is a comprehensive test document for demonstrating the document processing pipeline.
    
    Chapter 1: Introduction to Document Processing
    The process of ingesting documents into a RAG system involves several key steps:
    splitting the text into manageable chunks, generating embeddings for each chunk,
    storing the embeddings in a vector database, and saving the chunks for retrieval.
    
    Chapter 2: Text Splitting Strategies
    Text splitting is crucial for maintaining context while keeping chunks at a reasonable size.
    Common strategies include splitting by paragraphs, sentences, or fixed token counts.
    The choice of splitting strategy can significantly impact retrieval quality.
    
    Chapter 3: Embedding Generation
    Embeddings are dense vector representations of text that capture semantic meaning.
    Modern embedding models like BGE (BAAI General Embedding) provide high-quality
    representations that enable semantic search across documents.
    
    Chapter 4: Vector Storage
    Vector databases like Weaviate provide efficient storage and retrieval of embeddings.
    They support similarity search, filtering, and hybrid search combining vectors and keywords.
    
    Chapter 5: Retrieval and Generation
    The final step in RAG is retrieving relevant chunks and using them to generate responses.
    This involves finding the most similar chunks to a query and providing them as context.
    """ * 5  # Repeat to make it larger
    
    upload_cmd = f'''curl -s -X POST {BASE_URL}/collections/{collection_id}/documents \
      -H "Content-Type: application/json" \
      -d '{{"title": "Test Document for Progress Tracking", "text": {json.dumps(test_content)}}}'
    '''
    
    result = subprocess.run(upload_cmd, shell=True, capture_output=True, text=True)
    response = json.loads(result.stdout)
    
    task_id = response.get("task_id")
    document_id = response.get("document_id")
    
    if not task_id:
        print(f"❌ Failed to upload document: {response}")
        return
    
    print(f"✅ Document uploaded: ID={document_id}, Task={task_id}")
    
    # Step 3: Monitor progress
    print("\n3. Monitoring processing progress...")
    
    last_stage = ""
    last_progress = -1
    
    while True:
        # Check task progress
        progress_cmd = f"curl -s {BASE_URL}/progress/{task_id}"
        result = subprocess.run(progress_cmd, shell=True, capture_output=True, text=True)
        
        try:
            progress = json.loads(result.stdout)
        except:
            print(f"Failed to parse progress: {result.stdout}")
            break
        
        state = progress.get("state")
        stage = progress.get("stage", "")
        percent = progress.get("progress", 0)
        message = progress.get("message", "")
        
        # Print updates when progress changes
        if stage != last_stage or percent != last_progress:
            if state == "PROGRESS":
                bar_length = 30
                filled = int(bar_length * percent / 100)
                bar = "█" * filled + "░" * (bar_length - filled)
                print(f"\r[{bar}] {percent:3d}% - {stage}: {message}", end="", flush=True)
            elif state == "SUCCESS":
                print(f"\n✅ Processing complete!")
                break
            elif state == "FAILURE":
                print(f"\n❌ Processing failed: {progress.get('error', 'Unknown error')}")
                break
            
            last_stage = stage
            last_progress = percent
        
        time.sleep(0.5)
    
    # Step 4: Check document status
    print("\n\n4. Checking final document status...")
    status_cmd = f"curl -s {BASE_URL}/documents/{document_id}/status"
    result = subprocess.run(status_cmd, shell=True, capture_output=True, text=True)
    
    try:
        status = json.loads(result.stdout)
        print(f"📄 Document: {status['title']}")
        print(f"📊 Status: {status['status']}")
        print(f"🧩 Chunks: {status['chunk_count']}")
        print(f"📁 Collection: {status['collection_id']}")
        
        if status.get("processing_progress"):
            print(f"⚙️  Progress details: {json.dumps(status['processing_progress'], indent=2)}")
    except:
        print(f"Failed to get status: {result.stdout}")
    
    # Cleanup
    print("\n5. Cleaning up...")
    subprocess.run(f"curl -s -X DELETE {BASE_URL}/collections/{collection_id}?hard_delete=true", 
                   shell=True, capture_output=True)
    print("✅ Cleanup complete")

if __name__ == "__main__":
    test_document_processing()