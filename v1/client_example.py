#!/usr/bin/env python3
"""
Legal AI Weaviate Service Client Example
Demonstrates how to interact with the FastAPI service
"""

import requests
import json
from typing import Dict, List, Optional

class LegalAIClient:
    """Client for the Legal AI Weaviate Service"""
    
    def __init__(self, base_url: str = "http://localhost:8002"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def add_document(self, content: str, filename: str, client_matter: str, 
                    doc_type: str, uploaded_by: str = "system") -> Dict:
        """Add a document to the legal AI system"""
        url = f"{self.base_url}/documents/add"
        
        payload = {
            "content": content,
            "filename": filename,
            "client_matter": client_matter,
            "doc_type": doc_type,
            "uploaded_by": uploaded_by
        }
        
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    
    def search_documents(self, query: str, limit: int = 5, 
                        client_matter: Optional[str] = None,
                        doc_type: Optional[str] = None,
                        min_score: float = 0.0) -> Dict:
        """Search documents using semantic search"""
        url = f"{self.base_url}/documents/search"
        
        payload = {
            "query": query,
            "limit": limit,
            "min_score": min_score
        }
        
        if client_matter:
            payload["client_matter"] = client_matter
        
        if doc_type:
            payload["doc_type"] = doc_type
        
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        url = f"{self.base_url}/documents/stats"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def health_check(self) -> Dict:
        """Check service health"""
        url = f"{self.base_url}/health"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

def main():
    """Example usage of the Legal AI client"""
    
    # Initialize client
    client = LegalAIClient("http://localhost:8002")
    
    print("🏛️ Legal AI Weaviate Service Client Demo\n")
    
    try:
        # 1. Health check
        print("1. Checking service health...")
        health = client.health_check()
        print(f"   Status: {health['status']}")
        print(f"   Weaviate Connected: {health['weaviate_connected']}")
        print(f"   Schema Exists: {health['schema_exists']}\n")
        
        # 2. Add sample documents
        print("2. Adding sample legal documents...")
        
        sample_docs = [
            {
                "content": """
                EMPLOYMENT AGREEMENT
                
                This Employment Agreement is entered into between ABC Legal Firm and John Smith.
                
                TERMS OF EMPLOYMENT:
                1. Position: Senior Associate Attorney
                2. Start Date: January 1, 2024
                3. Salary: $150,000 annually
                4. Benefits: Health insurance, dental, vision, 401k matching
                
                CONFIDENTIALITY:
                Employee agrees to maintain strict confidentiality of all client matters
                and proprietary information of the firm.
                
                TERMINATION:
                Either party may terminate this agreement with 30 days written notice.
                """,
                "filename": "employment_agreement_john_smith.pdf",
                "client_matter": "Internal_HR_2024",
                "doc_type": "contract",
                "uploaded_by": "hr@legalfirm.com"
            },
            {
                "content": """
                CASE LAW ANALYSIS: SMITH v. JONES
                
                Citation: 123 F.3d 456 (1st Cir. 2023)
                
                FACTS:
                Plaintiff Smith sued defendant Jones for breach of contract regarding
                a commercial lease agreement. The dispute centered on whether force
                majeure clauses applied during the COVID-19 pandemic.
                
                HOLDING:
                The court held that general force majeure language did not excuse
                performance when the pandemic's effects were foreseeable at the
                time of contract formation.
                
                SIGNIFICANCE:
                This case establishes important precedent for interpreting force
                majeure clauses in commercial contracts during extraordinary events.
                """,
                "filename": "smith_v_jones_analysis.docx",
                "client_matter": "ClientA_Contract_Dispute_2024",
                "doc_type": "case_law",
                "uploaded_by": "attorney@legalfirm.com"
            },
            {
                "content": """
                MEMORANDUM
                
                TO: Partner Review Committee
                FROM: Associate Attorney
                DATE: March 15, 2024
                RE: Client Matter - Contract Negotiation Strategy
                
                EXECUTIVE SUMMARY:
                This memo analyzes the proposed merger agreement between our client
                TechCorp and StartupInc, focusing on intellectual property provisions
                and liability limitations.
                
                KEY ISSUES:
                1. IP ownership and licensing terms
                2. Indemnification clauses
                3. Termination provisions
                4. Regulatory compliance requirements
                
                RECOMMENDATIONS:
                We recommend strengthening the IP warranty provisions and adding
                specific carve-outs for pre-existing technology.
                """,
                "filename": "merger_strategy_memo.pdf",
                "client_matter": "TechCorp_Merger_2024",
                "doc_type": "memo",
                "uploaded_by": "junior.associate@legalfirm.com"
            }
        ]
        
        document_ids = []
        for doc in sample_docs:
            result = client.add_document(**doc)
            document_ids.append(result['document_id'])
            print(f"   ✓ Added: {doc['filename']} (ID: {result['document_id'][:8]}...)")
        
        print(f"\n   Successfully added {len(document_ids)} documents!\n")
        
        # 3. Search examples
        print("3. Running search examples...")
        
        search_queries = [
            {
                "query": "employment contract salary benefits",
                "description": "General employment terms"
            },
            {
                "query": "force majeure pandemic COVID contract",
                "description": "Force majeure and pandemic clauses"
            },
            {
                "query": "intellectual property licensing merger",
                "client_matter": "TechCorp_Merger_2024",
                "description": "IP terms for specific client matter"
            },
            {
                "query": "confidentiality agreement",
                "doc_type": "contract",
                "description": "Confidentiality in contracts only"
            }
        ]
        
        for i, search in enumerate(search_queries, 1):
            print(f"\n   Search {i}: {search['description']}")
            print(f"   Query: '{search['query']}'")
            
            # Prepare search parameters
            search_params = {
                "query": search["query"],
                "limit": 3
            }
            
            if "client_matter" in search:
                search_params["client_matter"] = search["client_matter"]
                print(f"   Filter: Client Matter = {search['client_matter']}")
            
            if "doc_type" in search:
                search_params["doc_type"] = search["doc_type"]
                print(f"   Filter: Document Type = {search['doc_type']}")
            
            results = client.search_documents(**search_params)
            
            print(f"   Found {results['count']} results in {results['search_time_ms']:.1f}ms:")
            
            for j, result in enumerate(results['results'], 1):
                print(f"     {j}. {result['source']} (Score: {result['score']:.3f})")
                print(f"        Type: {result['doc_type']}, Matter: {result['client_matter']}")
                preview = result['content'][:100].replace('\n', ' ').strip()
                print(f"        Preview: {preview}...")
        
        # 4. Get statistics
        print("\n\n4. Database Statistics:")
        stats = client.get_statistics()
        print(f"   Total Documents: {stats['total_documents']}")
        print(f"   Document Types: {dict(stats['document_types'])}")
        print(f"   Client Matters: {dict(stats['client_matters'])}")
        print(f"   Status: {stats['status']}")
        
        print("\n✅ Demo completed successfully!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to the service.")
        print("   Make sure the FastAPI service is running on http://localhost:8002")
        print("   Run: python weaviate_service.py")
    
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        if e.response:
            try:
                error_detail = e.response.json()
                print(f"   Detail: {error_detail.get('detail', 'Unknown error')}")
            except:
                print(f"   Response: {e.response.text}")
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main() 