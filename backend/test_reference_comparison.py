"""
Reference Comparison Feature Test Script
Usage:
1. Prepare test files: main.docx, reference1.docx (optional: reference2.docx)
   Location: Project root (D:\VsCodeP\factguardian-main\)
2. Run: python test_reference_comparison.py
"""
import requests
import json
import os
import sys

BASE_URL = "http://localhost:8000"

def check_service():
    """Check if service is running"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            return True
    except:
        pass
    return False

def main():
    print("=" * 70)
    print("Reference Comparison Feature Test")
    print("=" * 70)
    
    # Check service
    if not check_service():
        print("\n[ERROR] Cannot connect to service")
        print("  Please ensure service is running: docker-compose up -d")
        sys.exit(1)
    
    print("\n[OK] Service connection normal")
    
    # Check files
    required_files = ['main.docx']
    optional_files = ['reference1.docx', 'reference2.docx']
    
    missing = [f for f in required_files if not os.path.exists(f)]
    if missing:
        current_dir = os.getcwd()
        print(f"\n[ERROR] Missing required files: {', '.join(missing)}")
        print(f"Current directory: {current_dir}")
        print("\nPlease prepare the following files (in project root):")
        print("  - main.docx (main document, required)")
        print("  - reference1.docx (reference document 1, at least one needed)")
        print("  - reference2.docx (reference document 2, optional)")
        print(f"\nHint: Files should be in: {current_dir}")
        sys.exit(1)
    
    available_refs = [f for f in optional_files if os.path.exists(f)]
    if not available_refs:
        print("\n[WARNING] No reference documents found")
        print("  At least one reference document (reference1.docx) is needed")
        sys.exit(1)
    
    print(f"\n[OK] Files found:")
    print(f"  - main.docx (main document)")
    for ref in available_refs:
        print(f"  - {ref}")
    
    # Step 1: Upload multiple files
    print("\n" + "-" * 70)
    print("Step 1: Upload main document and reference documents")
    print("-" * 70)
    
    files = [
        ('main_doc', ('main.docx', open('main.docx', 'rb'), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'))
    ]
    
    for ref_file in available_refs:
        files.append(('ref_docs', (ref_file, open(ref_file, 'rb'), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')))
    
    try:
        response = requests.post(f"{BASE_URL}/api/upload-multiple", files=files)
        response.raise_for_status()
        upload_result = response.json()
        
        print(f"[OK] Upload successful!")
        print(f"  Main document ID: {upload_result['main_document_id']}")
        print(f"  Reference document count: {len(upload_result['reference_document_ids'])}")
        for idx, ref_id in enumerate(upload_result['reference_document_ids'], 1):
            print(f"    Reference document {idx} ID: {ref_id}")
        
        main_doc_id = upload_result['main_document_id']
        ref_doc_ids = upload_result['reference_document_ids']
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Upload failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"  Error details: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
            except:
                print(f"  Error details: {e.response.text}")
        sys.exit(1)
    finally:
        # Close files
        for f in files:
            if hasattr(f[1][1], 'close'):
                f[1][1].close()
    
    # Step 2: Execute reference comparison
    print("\n" + "-" * 70)
    print("Step 2: Execute reference comparison")
    print("-" * 70)
    
    comparison_data = {
        "main_doc_id": main_doc_id,
        "ref_doc_ids": ref_doc_ids,
        "similarity_threshold": 0.3  # 30% similarity threshold
    }
    
    print(f"  Similarity threshold: {comparison_data['similarity_threshold'] * 100}%")
    print(f"  Comparing...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/compare-references",
            json=comparison_data,
            timeout=300  # 5 min timeout
        )
        response.raise_for_status()
        result = response.json()
        
        print(f"[OK] Comparison complete!")
        print(f"\nStatistics:")
        print(f"  Main document sections: {result['statistics']['total_main_sections']}")
        print(f"  Reference documents: {result['statistics']['total_reference_docs']}")
        print(f"  Total comparisons: {result['statistics']['total_comparisons']}")
        print(f"  Similar sections found: {result['statistics']['similar_sections_found']}")
        print(f"  Citations needed: {result['statistics']['citation_needed_count']}")
        
        if result['statistics']['similarity_types']:
            print(f"\nSimilarity type breakdown:")
            for sim_type, count in result['statistics']['similarity_types'].items():
                print(f"  - {sim_type}: {count} occurrences")
        
        # Show similarity details
        if result['similarities']:
            print(f"\nSimilarity details:")
            print("-" * 70)
            for idx, similarity in enumerate(result['similarities'][:5], 1):
                print(f"\nSimilar section #{idx}:")
                print(f"  Similarity score: {similarity['similarity_score']}%")
                print(f"  Similarity type: {similarity['similarity_type']}")
                print(f"  Citation needed: {'Yes' if similarity['needs_citation'] else 'No'}")
                print(f"  Reason: {similarity['reason']}")
                print(f"  Main doc section: {similarity['main_section']['title']}")
                print(f"  Reference doc: {similarity['reference_section']['filename']}")
                print(f"  Reference section: {similarity['reference_section']['title']}")
                print(f"  Main doc preview: {similarity['main_section']['content'][:150]}...")
                print(f"  Reference preview: {similarity['reference_section']['content'][:150]}...")
            
            if len(result['similarities']) > 5:
                print(f"\n  ... and {len(result['similarities']) - 5} more similar sections not shown")
        else:
            print(f"\n[WARNING] No similar sections found")
            print(f"  Suggestions:")
            print(f"    - Lower the similarity threshold (current: {comparison_data['similarity_threshold'] * 100}%)")
            print(f"    - Ensure documents have sufficient content")
            print(f"    - Ensure main and reference documents have similar content")
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Comparison failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"  Error details: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
            except:
                print(f"  Error details: {e.response.text}")
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("Test completed!")
    print("=" * 70)

if __name__ == "__main__":
    main()
