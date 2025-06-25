#!/usr/bin/env python3
"""
Test collection API endpoints manually.
"""
import asyncio
import json
import httpx

BASE_URL = "http://localhost:8002"  # RAG service port
API_BASE = f"{BASE_URL}/rag"

async def test_collection_endpoints():
    """Test collection CRUD endpoints."""
    print("🔧 Testing Collection API Endpoints...")
    
    async with httpx.AsyncClient() as client:
        try:
            # Test 1: Create a root collection
            print("\n📁 Test 1: Creating root collection...")
            collection_data = {
                "name": "API Test Collection",
                "description": "Testing collection API",
                "icon": "🧪",
                "color": "#FFB6C1"
            }
            
            response = await client.post(f"{API_BASE}/collections", json=collection_data)
            if response.status_code == 201:
                root_collection = response.json()
                print(f"✅ Created: {root_collection['name']} (ID: {root_collection['id']})")
                print(f"   Path: {root_collection['path']}")
                print(f"   Type: {root_collection['collection_type']}")
                collection_id = root_collection['id']
            else:
                print(f"❌ Failed to create collection: {response.status_code} - {response.text}")
                return
            
            # Test 2: Get collection by ID
            print("\n🔍 Test 2: Getting collection by ID...")
            response = await client.get(f"{API_BASE}/collections/{collection_id}")
            if response.status_code == 200:
                collection = response.json()
                print(f"✅ Retrieved: {collection['name']}")
                print(f"   Description: {collection['description']}")
                print(f"   Documents: {collection.get('document_count', 0)}")
            else:
                print(f"❌ Failed to get collection: {response.status_code} - {response.text}")
            
            # Test 3: List root collections
            print("\n📋 Test 3: Listing root collections...")
            response = await client.get(f"{API_BASE}/collections")
            if response.status_code == 200:
                collections = response.json()
                print(f"✅ Found {len(collections)} root collections:")
                for collection in collections:
                    print(f"   - {collection['name']} ({collection['path']})")
            else:
                print(f"❌ Failed to list collections: {response.status_code} - {response.text}")
            
            # Test 4: Create a child folder
            print("\n📂 Test 4: Creating child folder...")
            child_data = {
                "name": "Child Folder",
                "description": "Testing nested folder",
                "parent_id": collection_id,
                "icon": "📄"
            }
            
            response = await client.post(f"{API_BASE}/collections", json=child_data)
            if response.status_code == 201:
                child_collection = response.json()
                print(f"✅ Created: {child_collection['name']} (ID: {child_collection['id']})")
                print(f"   Path: {child_collection['path']}")
                print(f"   Depth: {child_collection['depth']}")
                child_id = child_collection['id']
            else:
                print(f"❌ Failed to create child: {response.status_code} - {response.text}")
                return
            
            # Test 5: List children
            print("\n👶 Test 5: Listing child collections...")
            response = await client.get(f"{API_BASE}/collections/{collection_id}/children")
            if response.status_code == 200:
                children = response.json()
                print(f"✅ Found {len(children)} child collections:")
                for child in children:
                    print(f"   - {child['name']} ({child['path']})")
            else:
                print(f"❌ Failed to list children: {response.status_code} - {response.text}")
            
            # Test 6: Get breadcrumb path
            print("\n🍞 Test 6: Getting breadcrumb path...")
            response = await client.get(f"{API_BASE}/collections/{child_id}/path")
            if response.status_code == 200:
                breadcrumbs = response.json()
                print(f"✅ Breadcrumb path:")
                for breadcrumb in breadcrumbs:
                    print(f"   - {breadcrumb['name']} ({breadcrumb['path']})")
            else:
                print(f"❌ Failed to get breadcrumb: {response.status_code} - {response.text}")
            
            # Test 7: Update collection
            print("\n✏️ Test 7: Updating collection...")
            update_data = {
                "description": "Updated description for API test",
                "color": "#98FB98"
            }
            
            response = await client.patch(f"{API_BASE}/collections/{child_id}", json=update_data)
            if response.status_code == 200:
                updated = response.json()
                print(f"✅ Updated: {updated['description']}")
                print(f"   New color: {updated['color']}")
            else:
                print(f"❌ Failed to update: {response.status_code} - {response.text}")
            
            # Test 8: Test document upload to collection
            print("\n📄 Test 8: Testing document upload to collection...")
            document_data = {
                "title": "Test Document",
                "text": "This is a test document uploaded to a collection for testing purposes."
            }
            
            response = await client.post(f"{API_BASE}/collections/{collection_id}/documents", json=document_data)
            if response.status_code == 202:
                upload_result = response.json()
                print(f"✅ Document uploaded: {upload_result}")
                print(f"   Task ID: {upload_result.get('task_id')}")
                print(f"   Document ID: {upload_result.get('document_id')}")
                print(f"   Collection ID: {upload_result.get('collection_id')}")
            else:
                print(f"❌ Failed to upload document: {response.status_code} - {response.text}")
            
            print("\n🎉 All API endpoint tests completed!")
            
        except httpx.ConnectError:
            print("❌ Could not connect to RAG service. Make sure it's running on port 8001")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(test_collection_endpoints())