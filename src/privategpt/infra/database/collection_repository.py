"""Collection repository for hierarchical document organization."""
from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime

from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from privategpt.core.domain.collection import Collection, CollectionSettings
from privategpt.infra.database.models import Collection as CollectionModel


logger = logging.getLogger(__name__)


class CollectionRepository:
    """Repository for managing document collections."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, collection: Collection) -> Collection:
        """Create a new collection."""
        # Generate UUID if not provided
        if not collection.id:
            collection.id = str(uuid4())
        
        # Build path if this is a child collection
        if collection.parent_id:
            parent = await self.get_by_id(collection.parent_id)
            if not parent:
                raise ValueError(f"Parent collection {collection.parent_id} not found")
            collection.path = f"{parent.path}/{collection.name}"
            collection.depth = parent.depth + 1
        else:
            # Root collection
            collection.path = f"/{collection.name}"
            collection.depth = 0
        
        # Convert settings to dict
        settings_dict = {}
        if hasattr(collection, 'settings') and collection.settings:
            if isinstance(collection.settings, CollectionSettings):
                settings_dict = collection.settings.to_dict()
            else:
                settings_dict = collection.settings
        
        # Create database model
        db_collection = CollectionModel(
            id=collection.id,
            user_id=collection.user_id,
            parent_id=collection.parent_id,
            name=collection.name,
            description=collection.description,
            collection_type=collection.collection_type,
            icon=collection.icon,
            color=collection.color,
            path=collection.path,
            depth=collection.depth,
            settings=settings_dict,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.session.add(db_collection)
        await self.session.commit()
        await self.session.refresh(db_collection)
        
        return self._to_domain(db_collection)
    
    async def get_by_id(self, collection_id: str) -> Optional[Collection]:
        """Get collection by ID."""
        stmt = select(CollectionModel).where(
            and_(
                CollectionModel.id == collection_id,
                CollectionModel.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(stmt)
        db_collection = result.scalar_one_or_none()
        
        if db_collection:
            return self._to_domain(db_collection)
        return None
    
    async def get_by_path(self, user_id: int, path: str) -> Optional[Collection]:
        """Get collection by full path."""
        stmt = select(CollectionModel).where(
            and_(
                CollectionModel.user_id == user_id,
                CollectionModel.path == path,
                CollectionModel.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(stmt)
        db_collection = result.scalar_one_or_none()
        
        if db_collection:
            return self._to_domain(db_collection)
        return None
    
    async def list_roots(self, user_id: int) -> List[Collection]:
        """List root collections for a user."""
        stmt = select(CollectionModel).where(
            and_(
                CollectionModel.user_id == user_id,
                CollectionModel.parent_id.is_(None),
                CollectionModel.deleted_at.is_(None)
            )
        ).order_by(CollectionModel.name)
        
        result = await self.session.execute(stmt)
        db_collections = result.scalars().all()
        
        return [self._to_domain(c) for c in db_collections]
    
    async def list_children(self, parent_id: str) -> List[Collection]:
        """List child collections."""
        stmt = select(CollectionModel).where(
            and_(
                CollectionModel.parent_id == parent_id,
                CollectionModel.deleted_at.is_(None)
            )
        ).order_by(CollectionModel.name)
        
        result = await self.session.execute(stmt)
        db_collections = result.scalars().all()
        
        return [self._to_domain(c) for c in db_collections]
    
    async def get_breadcrumb_path(self, collection_id: str) -> List[Collection]:
        """Get the full breadcrumb path from root to this collection."""
        collection = await self.get_by_id(collection_id)
        if not collection:
            return []
        
        path_parts = collection.get_breadcrumb_parts()
        breadcrumbs = []
        
        # Build path progressively to find each collection
        current_path = ""
        for part in path_parts:
            current_path = f"{current_path}/{part}" if current_path else f"/{part}"
            
            stmt = select(CollectionModel).where(
                and_(
                    CollectionModel.user_id == collection.user_id,
                    CollectionModel.path == current_path,
                    CollectionModel.deleted_at.is_(None)
                )
            ).limit(1)  # Add limit to ensure only one row
            result = await self.session.execute(stmt)
            db_collection = result.scalar_one_or_none()
            
            if db_collection:
                breadcrumbs.append(self._to_domain(db_collection))
        
        return breadcrumbs
    
    async def update(self, collection_id: str, updates: Dict[str, Any]) -> Optional[Collection]:
        """Update collection properties."""
        # Don't allow updating certain fields
        protected_fields = {'id', 'user_id', 'parent_id', 'path', 'depth', 'created_at'}
        updates = {k: v for k, v in updates.items() if k not in protected_fields}
        
        # Handle settings update
        if 'settings' in updates and isinstance(updates['settings'], CollectionSettings):
            updates['settings'] = updates['settings'].to_dict()
        
        # Add updated_at
        updates['updated_at'] = datetime.utcnow()
        
        stmt = (
            update(CollectionModel)
            .where(
                and_(
                    CollectionModel.id == collection_id,
                    CollectionModel.deleted_at.is_(None)
                )
            )
            .values(**updates)
            .returning(CollectionModel)
        )
        
        result = await self.session.execute(stmt)
        await self.session.commit()
        
        db_collection = result.scalar_one_or_none()
        if db_collection:
            return self._to_domain(db_collection)
        return None
    
    async def move(self, collection_id: str, new_parent_id: Optional[str]) -> Optional[Collection]:
        """Move collection to a new parent."""
        collection = await self.get_by_id(collection_id)
        if not collection:
            return None
        
        # Calculate new path and depth
        if new_parent_id:
            new_parent = await self.get_by_id(new_parent_id)
            if not new_parent:
                raise ValueError(f"New parent collection {new_parent_id} not found")
            
            # Check for circular reference
            if await self._is_descendant(new_parent_id, collection_id):
                raise ValueError("Cannot move collection to its own descendant")
            
            new_path = f"{new_parent.path}/{collection.name}"
            new_depth = new_parent.depth + 1
        else:
            # Moving to root
            new_path = f"/{collection.name}"
            new_depth = 0
        
        # Update this collection and all descendants
        await self._update_paths_recursive(collection_id, collection.path, new_path, new_depth)
        
        # Update parent_id
        stmt = (
            update(CollectionModel)
            .where(CollectionModel.id == collection_id)
            .values(
                parent_id=new_parent_id,
                updated_at=datetime.utcnow()
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()
        
        return await self.get_by_id(collection_id)
    
    async def delete(self, collection_id: str, hard_delete: bool = False) -> bool:
        """Delete collection (soft delete by default)."""
        if hard_delete:
            # Hard delete - remove from database
            stmt = delete(CollectionModel).where(CollectionModel.id == collection_id)
            await self.session.execute(stmt)
        else:
            # Soft delete - set deleted_at timestamp
            stmt = (
                update(CollectionModel)
                .where(CollectionModel.id == collection_id)
                .values(deleted_at=datetime.utcnow())
            )
            await self.session.execute(stmt)
        
        await self.session.commit()
        return True
    
    async def count_documents(self, collection_id: str) -> int:
        """Count documents in a collection (not including sub-folders)."""
        from privategpt.infra.database.models import Document
        
        stmt = select(func.count(Document.id)).where(
            and_(
                Document.collection_id == collection_id,
                Document.status != "deleted"
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def count_all_documents(self, collection_id: str) -> int:
        """Count all documents in collection and sub-folders."""
        collection = await self.get_by_id(collection_id)
        if not collection:
            return 0
        
        from privategpt.infra.database.models import Document
        
        # Get all descendant collection IDs
        descendant_ids = await self._get_descendant_ids(collection_id)
        all_ids = [collection_id] + descendant_ids
        
        stmt = select(func.count(Document.id)).where(
            and_(
                Document.collection_id.in_(all_ids),
                Document.status != "deleted"
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    # Helper methods
    
    def _to_domain(self, db_collection: CollectionModel) -> Collection:
        """Convert database model to domain model."""
        # Parse settings
        settings = None
        if db_collection.settings:
            settings = CollectionSettings.from_dict(db_collection.settings)
        
        return Collection(
            id=db_collection.id,
            user_id=db_collection.user_id,
            parent_id=db_collection.parent_id,
            name=db_collection.name,
            description=db_collection.description,
            collection_type=db_collection.collection_type,
            icon=db_collection.icon,
            color=db_collection.color,
            path=db_collection.path,
            depth=db_collection.depth,
            settings=settings,
            created_at=db_collection.created_at,
            updated_at=db_collection.updated_at,
            deleted_at=db_collection.deleted_at
        )
    
    async def _is_descendant(self, potential_descendant_id: str, ancestor_id: str) -> bool:
        """Check if a collection is a descendant of another."""
        descendants = await self._get_descendant_ids(ancestor_id)
        return potential_descendant_id in descendants
    
    async def _get_descendant_ids(self, collection_id: str) -> List[str]:
        """Get all descendant collection IDs."""
        # Use a simpler recursive approach for now - get immediate children and their children
        from sqlalchemy import text
        
        # Recursive CTE to get all descendants
        stmt = text("""
        WITH RECURSIVE descendants AS (
            SELECT id FROM collections WHERE parent_id = :collection_id AND deleted_at IS NULL
            UNION ALL
            SELECT c.id FROM collections c
            INNER JOIN descendants d ON c.parent_id = d.id
            WHERE c.deleted_at IS NULL
        )
        SELECT id FROM descendants
        """)
        
        result = await self.session.execute(stmt, {"collection_id": collection_id})
        return [row[0] for row in result]
    
    async def _update_paths_recursive(
        self,
        collection_id: str,
        old_path: str,
        new_path: str,
        new_depth: int
    ):
        """Recursively update paths for a collection and its descendants."""
        # Update the collection itself
        stmt = (
            update(CollectionModel)
            .where(CollectionModel.id == collection_id)
            .values(
                path=new_path,
                depth=new_depth,
                updated_at=datetime.utcnow()
            )
        )
        await self.session.execute(stmt)
        
        # Update all descendants
        descendants = await self._get_descendant_ids(collection_id)
        if descendants:
            # Build CASE statement for updating paths
            path_updates = f"REPLACE(path, '{old_path}/', '{new_path}/')"
            depth_diff = new_depth - (await self.get_by_id(collection_id)).depth
            
            stmt = (
                update(CollectionModel)
                .where(CollectionModel.id.in_(descendants))
                .values(
                    path=func.replace(CollectionModel.path, f"{old_path}/", f"{new_path}/"),
                    depth=CollectionModel.depth + depth_diff,
                    updated_at=datetime.utcnow()
                )
            )
            await self.session.execute(stmt)