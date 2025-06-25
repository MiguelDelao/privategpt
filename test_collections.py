#!/usr/bin/env python3
"""
Test script for collection endpoints.
"""
import asyncio
import json
import sys
from pathlib import Path

# Add the source directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from privategpt.core.domain.collection import Collection, CollectionSettings
from privategpt.infra.database.collection_repository import CollectionRepository
from privategpt.infra.database.models import Base

# Database configuration
DATABASE_URL = "postgresql+asyncpg://privategpt:secret@localhost:5432/privategpt"

async def test_collections():
    """Test collection CRUD operations."""
    print("🧪 Testing Collection CRUD operations...")
    
    # Create async engine and session
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created")
        
        async with async_session() as session:
            # Create a test user if it doesn't exist
            from privategpt.infra.database.models import User
            
            # Check if user exists
            from sqlalchemy import select
            result = await session.execute(select(User).where(User.id == 1))
            existing_user = result.scalar_one_or_none()
            
            if not existing_user:
                test_user = User(
                    id=1,
                    email="test@example.com",
                    role="user",
                    is_active=True
                )
                session.add(test_user)
                await session.commit()
                print("✅ Created test user")
            else:
                print("✅ Test user already exists")
            
            repo = CollectionRepository(session)
            
            # Test 1: Create root collection
            print("\n📁 Test 1: Creating root collection...")
            root_collection = Collection(
                user_id=1,
                name="Legal Cases",
                description="All legal case documents",
                icon="⚖️",
                color="#FF6B6B"
            )
            
            created_root = await repo.create(root_collection)
            print(f"✅ Created root collection: {created_root.name} (ID: {created_root.id})")
            print(f"   Path: {created_root.path}")
            print(f"   Type: {created_root.collection_type}")
            
            # Test 2: Create child folder
            print("\n📂 Test 2: Creating child folder...")
            child_folder = Collection(
                user_id=1,
                parent_id=created_root.id,
                name="Smith v Jones",
                description="Documents for Smith v Jones case",
                icon="📄",
                color="#4ECDC4"
            )
            
            created_child = await repo.create(child_folder)
            print(f"✅ Created child folder: {created_child.name} (ID: {created_child.id})")
            print(f"   Path: {created_child.path}")
            print(f"   Depth: {created_child.depth}")
            
            # Test 3: List root collections
            print("\n📋 Test 3: Listing root collections...")
            roots = await repo.list_roots(1)
            print(f"✅ Found {len(roots)} root collections:")
            for root in roots:
                print(f"   - {root.name} ({root.path})")
            
            # Test 4: List children
            print("\n👶 Test 4: Listing child collections...")
            children = await repo.list_children(created_root.id)
            print(f"✅ Found {len(children)} child collections:")
            for child in children:
                print(f"   - {child.name} ({child.path})")
            
            # Test 5: Get breadcrumb path
            print("\n🍞 Test 5: Getting breadcrumb path...")
            breadcrumbs = await repo.get_breadcrumb_path(created_child.id)
            print(f"✅ Breadcrumb path for '{created_child.name}':")
            for breadcrumb in breadcrumbs:
                print(f"   - {breadcrumb.name} ({breadcrumb.path})")
            
            # Test 6: Update collection
            print("\n✏️ Test 6: Updating collection...")
            updated = await repo.update(created_child.id, {
                "description": "Updated: Documents for Smith v Jones case",
                "color": "#A8E6CF"
            })
            print(f"✅ Updated collection: {updated.description}")
            print(f"   New color: {updated.color}")
            
            # Test 7: Create nested folder
            print("\n📁📁 Test 7: Creating nested folder...")
            nested_folder = Collection(
                user_id=1,
                parent_id=created_child.id,
                name="Depositions",
                description="Deposition documents",
                icon="🎤"
            )
            
            created_nested = await repo.create(nested_folder)
            print(f"✅ Created nested folder: {created_nested.name}")
            print(f"   Path: {created_nested.path}")
            print(f"   Depth: {created_nested.depth}")
            
            # Test 8: Move collection
            print("\n🚚 Test 8: Moving collection...")
            moved = await repo.move(created_nested.id, created_root.id)
            print(f"✅ Moved collection to root level")
            print(f"   New path: {moved.path}")
            print(f"   New depth: {moved.depth}")
            
            # Test 9: Get all collections for breadcrumb display
            print("\n📋 Test 9: Final collection structure...")
            all_roots = await repo.list_roots(1)
            for root in all_roots:
                print(f"📁 {root.name} ({root.path})")
                children = await repo.list_children(root.id)
                for child in children:
                    print(f"  └── 📂 {child.name} ({child.path})")
                    nested = await repo.list_children(child.id)
                    for n in nested:
                        print(f"      └── 📄 {n.name} ({n.path})")
            
            print("\n🎉 All collection tests passed!")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_collections())