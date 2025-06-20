#!/usr/bin/env python3
"""
PrivateGPT MCP Server

A Model Context Protocol server that provides tools for:
- Document search and retrieval (RAG)
- File management operations
- System information and utilities
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.models import Tool, Resource
from mcp.types import TextContent, EmbeddedResource

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("PrivateGPT")

# Configuration
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://rag-service:8000")
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://llm-service:8000")
GATEWAY_SERVICE_URL = os.getenv("GATEWAY_SERVICE_URL", "http://gateway-service:8000")

# HTTP client for API calls
http_client = httpx.AsyncClient(timeout=30.0)


# =============================================================================
# RAG TOOLS
# =============================================================================

@mcp.tool()
async def search_documents(
    query: str,
    limit: int = 10,
    include_sources: bool = True
) -> str:
    """
    Search through uploaded documents using semantic similarity.
    
    Args:
        query: The search query
        limit: Maximum number of results to return (default: 10)
        include_sources: Whether to include source document information
    
    Returns:
        JSON string with search results and sources
    """
    try:
        response = await http_client.post(
            f"{RAG_SERVICE_URL}/rag/search",
            json={
                "query": query,
                "limit": limit,
                "include_metadata": include_sources
            }
        )
        response.raise_for_status()
        results = response.json()
        
        return json.dumps({
            "query": query,
            "results": results.get("chunks", []),
            "total_found": len(results.get("chunks", [])),
            "search_time": results.get("search_time_ms", 0)
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Document search failed: {e}")
        return json.dumps({
            "error": f"Search failed: {str(e)}",
            "query": query
        }, indent=2)


# Document upload removed - AI doesn't need this capability
# Users upload documents through the UI, AI only searches existing documents


@mcp.tool()
async def rag_chat(
    question: str,
    conversation_context: Optional[str] = None
) -> str:
    """
    Ask a question using RAG (Retrieval-Augmented Generation).
    
    Args:
        question: The question to ask
        conversation_context: Optional previous conversation context
    
    Returns:
        JSON string with answer and sources
    """
    try:
        payload = {"question": question}
        if conversation_context:
            payload["context"] = conversation_context
            
        response = await http_client.post(
            f"{RAG_SERVICE_URL}/rag/chat",
            json=payload
        )
        response.raise_for_status()
        result = response.json()
        
        return json.dumps({
            "question": question,
            "answer": result.get("answer", ""),
            "sources": result.get("citations", []),
            "confidence": result.get("confidence", 0.0)
        }, indent=2)
        
    except Exception as e:
        logger.error(f"RAG chat failed: {e}")
        return json.dumps({
            "error": f"RAG chat failed: {str(e)}",
            "question": question
        }, indent=2)


# =============================================================================
# FILE MANAGEMENT TOOLS
# =============================================================================

@mcp.tool()
async def create_file(
    file_path: str,
    content: str,
    encoding: str = "utf-8"
) -> str:
    """
    Create a new file with the specified content.
    
    Args:
        file_path: Path where the file should be created
        content: Content to write to the file
        encoding: File encoding (default: utf-8)
    
    Returns:
        JSON string with creation status
    """
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding=encoding) as f:
            f.write(content)
        
        return json.dumps({
            "status": "created",
            "file_path": str(path.absolute()),
            "size_bytes": len(content.encode(encoding)),
            "created_at": datetime.utcnow().isoformat()
        }, indent=2)
        
    except Exception as e:
        logger.error(f"File creation failed: {e}")
        return json.dumps({
            "error": f"File creation failed: {str(e)}",
            "file_path": file_path
        }, indent=2)


@mcp.tool()
async def read_file(
    file_path: str,
    encoding: str = "utf-8",
    max_lines: Optional[int] = None
) -> str:
    """
    Read the contents of a file.
    
    Args:
        file_path: Path to the file to read
        encoding: File encoding (default: utf-8)
        max_lines: Maximum number of lines to read (optional)
    
    Returns:
        JSON string with file contents and metadata
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return json.dumps({
                "error": "File not found",
                "file_path": file_path
            }, indent=2)
        
        with open(path, 'r', encoding=encoding) as f:
            if max_lines:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line.rstrip('\n'))
                content = '\n'.join(lines)
                truncated = True
            else:
                content = f.read()
                truncated = False
        
        stat = path.stat()
        
        return json.dumps({
            "file_path": str(path.absolute()),
            "content": content,
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "truncated": truncated,
            "lines_read": len(content.split('\n')) if content else 0
        }, indent=2)
        
    except Exception as e:
        logger.error(f"File read failed: {e}")
        return json.dumps({
            "error": f"File read failed: {str(e)}",
            "file_path": file_path
        }, indent=2)


@mcp.tool()
async def edit_file(
    file_path: str,
    new_content: str,
    backup: bool = True,
    encoding: str = "utf-8"
) -> str:
    """
    Edit an existing file by replacing its content.
    
    Args:
        file_path: Path to the file to edit
        new_content: New content for the file
        backup: Whether to create a backup before editing
        encoding: File encoding (default: utf-8)
    
    Returns:
        JSON string with edit status
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return json.dumps({
                "error": "File not found",
                "file_path": file_path
            }, indent=2)
        
        # Create backup if requested
        backup_path = None
        if backup:
            backup_path = path.with_suffix(path.suffix + '.bak')
            path.rename(backup_path)
        
        # Write new content
        with open(path, 'w', encoding=encoding) as f:
            f.write(new_content)
        
        return json.dumps({
            "status": "edited",
            "file_path": str(path.absolute()),
            "backup_created": str(backup_path.absolute()) if backup_path else None,
            "new_size_bytes": len(new_content.encode(encoding)),
            "edited_at": datetime.utcnow().isoformat()
        }, indent=2)
        
    except Exception as e:
        logger.error(f"File edit failed: {e}")
        return json.dumps({
            "error": f"File edit failed: {str(e)}",
            "file_path": file_path
        }, indent=2)


@mcp.tool()
async def list_directory(
    directory_path: str,
    show_hidden: bool = False,
    recursive: bool = False,
    max_depth: int = 3
) -> str:
    """
    List contents of a directory.
    
    Args:
        directory_path: Path to the directory
        show_hidden: Whether to show hidden files (starting with .)
        recursive: Whether to list subdirectories recursively
        max_depth: Maximum depth for recursive listing
    
    Returns:
        JSON string with directory contents
    """
    try:
        path = Path(directory_path)
        if not path.exists():
            return json.dumps({
                "error": "Directory not found",
                "directory_path": directory_path
            }, indent=2)
        
        if not path.is_dir():
            return json.dumps({
                "error": "Path is not a directory",
                "directory_path": directory_path
            }, indent=2)
        
        def scan_directory(dir_path: Path, current_depth: int = 0) -> List[Dict]:
            items = []
            try:
                for item in dir_path.iterdir():
                    if not show_hidden and item.name.startswith('.'):
                        continue
                    
                    stat = item.stat()
                    item_info = {
                        "name": item.name,
                        "path": str(item.absolute()),
                        "type": "directory" if item.is_dir() else "file",
                        "size_bytes": stat.st_size if item.is_file() else None,
                        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    }
                    
                    if recursive and item.is_dir() and current_depth < max_depth:
                        item_info["children"] = scan_directory(item, current_depth + 1)
                    
                    items.append(item_info)
            except PermissionError:
                pass  # Skip directories we can't read
            
            return sorted(items, key=lambda x: (x["type"] == "file", x["name"]))
        
        contents = scan_directory(path)
        
        return json.dumps({
            "directory_path": str(path.absolute()),
            "contents": contents,
            "total_items": len(contents),
            "scanned_at": datetime.utcnow().isoformat()
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Directory listing failed: {e}")
        return json.dumps({
            "error": f"Directory listing failed: {str(e)}",
            "directory_path": directory_path
        }, indent=2)


# =============================================================================
# SYSTEM TOOLS
# =============================================================================

@mcp.tool()
async def get_system_info() -> str:
    """
    Get basic system information.
    
    Returns:
        JSON string with system information
    """
    try:
        import platform
        import psutil
        
        # Get system info
        system_info = {
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor()
            },
            "python": {
                "version": platform.python_version(),
                "implementation": platform.python_implementation()
            },
            "memory": {
                "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
                "percent_used": psutil.virtual_memory().percent
            },
            "disk": {
                "total_gb": round(psutil.disk_usage('/').total / (1024**3), 2),
                "free_gb": round(psutil.disk_usage('/').free / (1024**3), 2),
                "percent_used": round((psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100, 1)
            },
            "cpu": {
                "cores": psutil.cpu_count(),
                "percent_used": psutil.cpu_percent(interval=1)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return json.dumps(system_info, indent=2)
        
    except Exception as e:
        logger.error(f"System info failed: {e}")
        return json.dumps({
            "error": f"System info failed: {str(e)}"
        }, indent=2)


@mcp.tool()
async def check_service_health() -> str:
    """
    Check the health status of PrivateGPT services.
    
    Returns:
        JSON string with service health information
    """
    services = {
        "rag_service": RAG_SERVICE_URL,
        "llm_service": LLM_SERVICE_URL,
        "gateway_service": GATEWAY_SERVICE_URL
    }
    
    health_status = {}
    
    for service_name, base_url in services.items():
        try:
            response = await http_client.get(
                f"{base_url}/health",
                timeout=5.0
            )
            health_status[service_name] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "status_code": response.status_code,
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "url": base_url
            }
        except Exception as e:
            health_status[service_name] = {
                "status": "unreachable",
                "error": str(e),
                "url": base_url
            }
    
    overall_status = "healthy" if all(
        s["status"] == "healthy" for s in health_status.values()
    ) else "degraded"
    
    return json.dumps({
        "overall_status": overall_status,
        "services": health_status,
        "checked_at": datetime.utcnow().isoformat()
    }, indent=2)


# =============================================================================
# RESOURCES
# =============================================================================

@mcp.resource("document://{doc_id}")
async def get_document_resource(doc_id: str) -> str:
    """Get a specific document by ID."""
    try:
        response = await http_client.get(f"{RAG_SERVICE_URL}/rag/documents/{doc_id}")
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"Error retrieving document {doc_id}: {str(e)}"


@mcp.resource("config://privategpt")
async def get_privategpt_config() -> str:
    """Get PrivateGPT configuration information."""
    config = {
        "mcp_server": {
            "name": "PrivateGPT MCP Server",
            "version": "1.0.0",
            "tools_count": len(mcp._tools),
            "resources_count": len(mcp._resources)
        },
        "services": {
            "rag_service_url": RAG_SERVICE_URL,
            "llm_service_url": LLM_SERVICE_URL,
            "gateway_service_url": GATEWAY_SERVICE_URL
        },
        "capabilities": [
            "document_search",
            "document_upload", 
            "rag_chat",
            "file_management",
            "system_information"
        ]
    }
    return json.dumps(config, indent=2)


# =============================================================================
# SERVER STARTUP
# =============================================================================

async def main():
    """Main entry point for the MCP server."""
    logger.info("Starting PrivateGPT MCP Server...")
    
    # Verify service connections
    logger.info("Checking service health...")
    health_result = await check_service_health()
    logger.info(f"Service health: {health_result}")
    
    # Start the server
    await mcp.run()


if __name__ == "__main__":
    asyncio.run(main())