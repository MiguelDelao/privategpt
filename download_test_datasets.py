#!/usr/bin/env python3
"""
Legal Dataset Downloader for PrivateGPT Testing
Downloads sample legal documents for testing the Legal AI system
"""

import requests
import os
from pathlib import Path

def download_cuad_sample():
    """Download CUAD sample contracts"""
    print("📥 Downloading CUAD dataset...")
    cuad_url = "https://zenodo.org/record/4595826/files/CUAD_v1.zip"
    
    try:
        response = requests.get(cuad_url, stream=True)
        response.raise_for_status()
        
        Path("test_datasets").mkdir(exist_ok=True)
        
        with open("test_datasets/CUAD_v1.zip", "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print("✅ CUAD dataset downloaded to test_datasets/CUAD_v1.zip")
        print("💡 Extract this zip file to get 510 legal contracts in PDF format")
        
    except Exception as e:
        print(f"❌ Error downloading CUAD: {e}")

def download_sample_contracts():
    """Download some sample legal documents"""
    print("📥 Downloading sample legal documents...")
    
    # Sample legal documents (these are examples, adjust URLs as needed)
    samples = [
        {
            "name": "sample_nda.pdf",
            "url": "https://example.com/sample_nda.pdf",  # Replace with actual URL
            "description": "Non-Disclosure Agreement Template"
        },
        {
            "name": "employment_contract.pdf", 
            "url": "https://example.com/employment_contract.pdf",  # Replace with actual URL
            "description": "Employment Contract Template"
        }
    ]
    
    Path("test_datasets/samples").mkdir(parents=True, exist_ok=True)
    
    print("💡 Note: You'll need to manually download sample contracts from:")
    print("   - SEC EDGAR: https://www.sec.gov/edgar.shtml")
    print("   - US Courts: https://www.uscourts.gov/")
    print("   - Legal Templates: https://legaltemplates.net/")

def create_test_txt_documents():
    """Create some sample TXT legal documents for testing"""
    print("📝 Creating sample TXT legal documents...")
    
    Path("test_datasets/txt_samples").mkdir(parents=True, exist_ok=True)
    
    # Sample NDA
    nda_content = """
NON-DISCLOSURE AGREEMENT

This Non-Disclosure Agreement ("Agreement") is entered into on [DATE] by and between [COMPANY NAME], a [STATE] corporation ("Company"), and [RECIPIENT NAME] ("Recipient").

1. CONFIDENTIAL INFORMATION
Company may disclose certain confidential and proprietary information to Recipient. "Confidential Information" means any technical data, trade secrets, know-how, research, product plans, products, services, customers, customer lists, markets, software, developments, inventions, processes, formulas, technology, designs, drawings, engineering, hardware configuration information, marketing, finances, or other business information disclosed by Company.

2. OBLIGATIONS
Recipient agrees to:
a) Hold and maintain the Confidential Information in strict confidence
b) Not disclose the Confidential Information to any third parties
c) Use the Confidential Information solely for evaluation purposes

3. TERM
This Agreement shall remain in effect for a period of three (3) years from the date first written above.

4. GOVERNING LAW
This Agreement shall be governed by the laws of [STATE].

IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first written above.

[COMPANY NAME]

By: _______________________
Name: [NAME]
Title: [TITLE]

[RECIPIENT NAME]

_______________________
Signature
"""

    with open("test_datasets/txt_samples/sample_nda.txt", "w") as f:
        f.write(nda_content)
    
    # Sample Employment Agreement
    employment_content = """
EMPLOYMENT AGREEMENT

This Employment Agreement ("Agreement") is made between [COMPANY NAME] ("Company") and [EMPLOYEE NAME] ("Employee").

1. POSITION AND DUTIES
Employee shall serve as [JOB TITLE] and shall perform duties typically associated with such position.

2. COMPENSATION
a) Base Salary: $[AMOUNT] per year, payable bi-weekly
b) Benefits: Health insurance, dental insurance, 401(k) plan
c) Vacation: [NUMBER] days per year

3. CONFIDENTIALITY
Employee agrees to maintain confidentiality of all proprietary information.

4. TERMINATION
Either party may terminate this agreement with [NUMBER] days written notice.

5. GOVERNING LAW
This Agreement is governed by [STATE] law.

Date: [DATE]

[COMPANY NAME]

By: _______________________
[NAME], [TITLE]

_______________________
[EMPLOYEE NAME]
"""

    with open("test_datasets/txt_samples/employment_agreement.txt", "w") as f:
        f.write(employment_content)
    
    print("✅ Created sample TXT legal documents:")
    print("   - test_datasets/txt_samples/sample_nda.txt")
    print("   - test_datasets/txt_samples/employment_agreement.txt")

def main():
    print("🚀 PrivateGPT Legal AI Dataset Downloader")
    print("=" * 50)
    
    # Create test datasets directory
    Path("test_datasets").mkdir(exist_ok=True)
    
    print("\n1. Creating sample TXT documents...")
    create_test_txt_documents()
    
    print("\n2. Downloading CUAD dataset...")
    download_cuad_sample()
    
    print("\n3. Sample sources for manual download...")
    download_sample_contracts()
    
    print("\n" + "=" * 50)
    print("📁 Your test datasets are ready in: ./test_datasets/")
    print("\n🎯 Next Steps:")
    print("1. Extract CUAD_v1.zip to get 510 PDF contracts")
    print("2. Upload TXT samples via your Document Management page")
    print("3. Test RAG queries like 'What are the key terms?'")
    print("4. Download additional PDFs from SEC EDGAR or US Courts")
    print("\n💡 Start with the TXT samples - they'll work immediately!")

if __name__ == "__main__":
    main() 