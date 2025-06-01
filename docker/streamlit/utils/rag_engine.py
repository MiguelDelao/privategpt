"""
RAG Engine for PrivateGPT Legal AI
Handles Weaviate integration and LLM response generation
"""

import os
import uuid
import requests
import weaviate
from typing import Dict, List, Optional

class RAGEngine:
    """RAG engine for document search and response generation"""
    
    def __init__(self, ollama_url: str, weaviate_url: str):
        self.ollama_url = ollama_url.rstrip('/')
        self.weaviate_url = weaviate_url.rstrip('/')
        
        # Initialize Weaviate client (anonymous access enabled)
        self.weaviate_client = weaviate.Client(
            url=self.weaviate_url,
            additional_headers={
                "X-OpenAI-Api-Key": "placeholder"  # Required even if not using OpenAI
            }
        )
        
        # Ensure schema exists
        self._ensure_schema()
    
    def _ensure_schema(self):
        """Ensure Weaviate schema exists for legal documents"""
        schema = {
            "class": "LegalDocument",
            "description": "Legal documents for AI analysis",
            "vectorizer": "text2vec-transformers",
            "moduleConfig": {
                "text2vec-transformers": {
                    "poolingStrategy": "masked_mean",
                    "vectorizeClassName": False
                }
            },
            "properties": [
                {
                    "name": "content",
                    "dataType": ["text"],
                    "description": "Full document text content"
                },
                {
                    "name": "source",
                    "dataType": ["string"],
                    "description": "Source document filename"
                },
                {
                    "name": "docType",
                    "dataType": ["string"],
                    "description": "Document type (contract, case_law, filing, memo, etc.)"
                },
                {
                    "name": "clientMatter",
                    "dataType": ["string"],
                    "description": "Client matter code"
                },
                {
                    "name": "documentId",
                    "dataType": ["string"],
                    "description": "Unique document identifier"
                },
                {
                    "name": "createdAt",
                    "dataType": ["date"],
                    "description": "Document ingestion timestamp"
                },
                {
                    "name": "uploadedBy",
                    "dataType": ["string"],
                    "description": "User who uploaded the document"
                }
            ]
        }
        
        # Check if class exists
        existing_schema = self.weaviate_client.schema.get()
        existing_classes = [cls["class"] for cls in existing_schema.get("classes", [])]
        
        if "LegalDocument" not in existing_classes:
            self.weaviate_client.schema.create_class(schema)
    
    def add_document(
        self,
        content: str,
        filename: str,
        client_matter: str,
        doc_type: str,
        uploaded_by: str = "system"
    ) -> str:
        """Add document to Weaviate (auto-chunking enabled)"""
        document_id = str(uuid.uuid4())
        
        # Create document object
        document_obj = {
            "content": content,
            "source": filename,
            "docType": doc_type,
            "clientMatter": client_matter,
            "documentId": document_id,
            "uploadedBy": uploaded_by
        }
        
        # Add to Weaviate (automatic chunking and embedding)
        self.weaviate_client.data_object.create(
            data_object=document_obj,
            class_name="LegalDocument"
        )
        
        return document_id
    
    def search_documents(self, query: str, limit: int = 5, client_matter: Optional[str] = None) -> List[Dict]:
        """Search documents using semantic search"""
        where_filter = None
        
        # Add client matter filter if specified
        if client_matter:
            where_filter = {
                "path": ["clientMatter"],
                "operator": "Equal",
                "valueString": client_matter
            }
        
        # Perform semantic search
        result = (
            self.weaviate_client.query
            .get("LegalDocument", ["content", "source", "docType", "clientMatter", "documentId"])
            .with_near_text({"concepts": [query]})
            .with_limit(limit)
            .with_additional(["certainty"])
        )
        
        if where_filter:
            result = result.with_where(where_filter)
        
        response = result.do()
        
        # Process results
        documents = response.get("data", {}).get("Get", {}).get("LegalDocument", [])
        
        search_results = []
        for doc in documents:
            search_results.append({
                "content": doc["content"],
                "source": doc["source"],
                "doc_type": doc["docType"],
                "client_matter": doc["clientMatter"],
                "document_id": doc["documentId"],
                "score": doc["_additional"]["certainty"]
            })
        
        return search_results
    
    def generate_response(self, query: str, context_documents: List[Dict]) -> Dict:
        """Generate response using Ollama with RAG context"""
        
        # Build context from relevant documents
        context_parts = []
        for doc in context_documents:
            context_parts.append(f"[{doc['source']}]: {doc['content'][:1000]}...")
        
        context = "\n\n".join(context_parts)
        
        # Create legal-focused prompt
        prompt = f"""You are a professional legal AI assistant. Based on the provided legal documents, answer the following question with accuracy and proper citations.

LEGAL DOCUMENTS:
{context}

QUESTION: {query}

Please provide a comprehensive answer that:
1. Directly addresses the question
2. Cites specific documents and sections when relevant
3. Notes any limitations or areas requiring further legal review
4. Uses professional legal language appropriate for attorneys

ANSWER:"""
        
        # Call Ollama
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "llama3:8b",  # Use configured model
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Lower temperature for factual responses
                        "top_p": 0.9,
                        "top_k": 40
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "answer": result["response"],
                    "model_used": "llama3:8b",
                    "context_sources": len(context_documents)
                }
            else:
                return {
                    "answer": "I apologize, but I encountered an error generating a response. Please try again.",
                    "error": f"Ollama API error: {response.status_code}"
                }
        
        except requests.exceptions.Timeout:
            return {
                "answer": "I apologize, but the response took too long to generate. Please try a simpler question or try again later.",
                "error": "Request timeout"
            }
        except Exception as e:
            return {
                "answer": "I apologize, but I encountered an error generating a response. Please try again.",
                "error": str(e)
            }
    
    def get_document_stats(self) -> Dict:
        """Get statistics about indexed documents"""
        try:
            # Get total document count
            result = (
                self.weaviate_client.query
                .aggregate("LegalDocument")
                .with_meta_count()
                .do()
            )
            
            total_docs = result["data"]["Aggregate"]["LegalDocument"][0]["meta"]["count"]
            
            # Get document types distribution
            doc_types_result = (
                self.weaviate_client.query
                .aggregate("LegalDocument")
                .with_group_by_filter(["docType"])
                .with_meta_count()
                .do()
            )
            
            doc_types = {}
            for group in doc_types_result["data"]["Aggregate"]["LegalDocument"]:
                doc_type = group["groupedBy"]["value"]
                count = group["meta"]["count"]
                doc_types[doc_type] = count
            
            return {
                "total_documents": total_docs,
                "document_types": doc_types,
                "status": "healthy"
            }
            
        except Exception as e:
            return {
                "total_documents": 0,
                "document_types": {},
                "status": "error",
                "error": str(e)
            }
    
    def health_check(self) -> Dict:
        """Check health of RAG components"""
        health_status = {"weaviate": False, "ollama": False}
        
        # Check Weaviate
        try:
            self.weaviate_client.schema.get()
            health_status["weaviate"] = True
        except Exception:
            pass
        
        # Check Ollama
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=10)
            health_status["ollama"] = response.status_code == 200
        except Exception:
            pass
        
        return health_status 