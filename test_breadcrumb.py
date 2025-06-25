#!/usr/bin/env python3
"""Test breadcrumb endpoint specifically"""
import requests
import json

BASE_URL = "http://localhost:8002/rag"

def test_breadcrumb():
    print("Testing breadcrumb path endpoint...")
    
    # Create root collection
    print("\n1. Creating root collection...")
    root_data = {
        "name": "Breadcrumb Test Root",
        "description": "Root for testing breadcrumbs",
        "icon": "🏠"
    }
    
    resp = requests.post(f"{BASE_URL}/collections", json=root_data)
    if resp.status_code != 201:
        print(f"Failed to create root: {resp.status_code} - {resp.text}")
        return
    
    root = resp.json()
    root_id = root["id"]
    print(f"Created root: {root['name']} (ID: {root_id})")
    
    # Create child
    print("\n2. Creating child collection...")
    child_data = {
        "name": "Child Collection",
        "parent_id": root_id,
        "icon": "📁"
    }
    
    resp = requests.post(f"{BASE_URL}/collections", json=child_data)
    if resp.status_code != 201:
        print(f"Failed to create child: {resp.status_code} - {resp.text}")
        return
    
    child = resp.json()
    child_id = child["id"]
    print(f"Created child: {child['name']} (ID: {child_id})")
    print(f"Child path: {child['path']}")
    
    # Get breadcrumb path
    print("\n3. Getting breadcrumb path for child...")
    resp = requests.get(f"{BASE_URL}/collections/{child_id}/path")
    
    if resp.status_code == 200:
        breadcrumbs = resp.json()
        print("✅ Breadcrumb path retrieved successfully!")
        print("\nBreadcrumb trail:")
        for i, crumb in enumerate(breadcrumbs):
            print(f"  {i+1}. {crumb['name']} ({crumb['path']})")
    else:
        print(f"❌ Failed to get breadcrumb: {resp.status_code}")
        print(f"Response: {resp.text}")
    
    # Clean up
    print("\n4. Cleaning up test collections...")
    requests.delete(f"{BASE_URL}/collections/{child_id}?hard_delete=true")
    requests.delete(f"{BASE_URL}/collections/{root_id}?hard_delete=true")
    print("✅ Cleanup complete")

if __name__ == "__main__":
    test_breadcrumb()