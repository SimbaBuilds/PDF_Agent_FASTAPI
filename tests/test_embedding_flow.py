"""
Test script to verify the full embedding flow:
1. Upload a PDF
2. Verify embedding jobs are created automatically via trigger
3. Call the edge function to process embeddings
4. Verify embeddings are stored in pdf_pages table
"""

import os
import sys
import asyncio
import time
import requests
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
TEST_USER_ID = os.getenv("TEST_USER_ID", "703b410f-f50c-4bc8-b9a3-0991fed5a023")  # Use default test user if not in env

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Test PDF path
TEST_PDF = Path(__file__).parent.parent / "test_pdfs" / "Cameron_Hightower_Resume_ATS_Version_1.pdf"


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)


def test_upload_pdf():
    """Upload a test PDF and return the document ID"""
    print_section("Step 1: Upload PDF")

    # Upload PDF file to Supabase storage
    with open(TEST_PDF, 'rb') as f:
        file_data = f.read()

    file_name = TEST_PDF.name
    storage_path = f"{TEST_USER_ID}/{file_name}"

    print(f"Uploading {file_name} to storage...")

    # Upload to storage
    result = supabase.storage.from_('pdfs').upload(
        path=storage_path,
        file=file_data,
        file_options={"content-type": "application/pdf", "upsert": "true"}
    )

    print(f"✓ File uploaded to: {storage_path}")

    # Create PDF document record
    doc_data = {
        'user_id': TEST_USER_ID,
        'original_filename': file_name,
        'file_size_bytes': len(file_data),
        'storage_path': storage_path,
        'status': 'pending',  # Use 'pending' instead of 'uploaded' (per constraint)
        'title': file_name
    }

    result = supabase.from_('pdf_documents').insert(doc_data).execute()
    pdf_doc_id = result.data[0]['id']

    print(f"✓ PDF document created with ID: {pdf_doc_id}")

    return pdf_doc_id, file_data


def test_process_pdf(pdf_doc_id: str, file_data: bytes):
    """Process the PDF using the pdf_processor service"""
    print_section("Step 2: Process PDF (extract pages)")

    # Import the PDF processor
    from app.services.pdf_processor import PDFProcessor

    processor = PDFProcessor()

    # Process the PDF
    print("Processing PDF to extract pages...")
    pages = asyncio.run(processor._process_pdf(file_data))

    print(f"✓ Extracted {len(pages)} pages")

    # Insert pages into database (this should trigger the embedding queue)
    page_data_list = []
    for i, content in enumerate(pages, start=1):
        page_data = {
            'user_id': TEST_USER_ID,
            'pdf_document_id': pdf_doc_id,
            'page_number': i,
            'content': content
        }
        page_data_list.append(page_data)

    print(f"Inserting {len(page_data_list)} pages into database...")
    result = supabase.from_('pdf_pages').insert(page_data_list).execute()

    print(f"✓ Inserted {len(result.data)} pages")

    return [page['id'] for page in result.data]


def test_verify_embedding_jobs(expected_count: int):
    """Verify that embedding jobs were created by the trigger"""
    print_section("Step 3: Verify Embedding Jobs Created")

    # Wait a moment for triggers to fire
    time.sleep(1)

    result = supabase.from_('embedding_jobs')\
        .select('*')\
        .eq('status', 'pending')\
        .execute()

    jobs = result.data

    print(f"✓ Found {len(jobs)} pending embedding jobs")

    if len(jobs) < expected_count:
        print(f"⚠ Warning: Expected {expected_count} jobs, but found {len(jobs)}")

    for job in jobs[:3]:  # Show first 3 jobs
        print(f"  - Job {job['id']}: table={job['table_name']}, content_length={len(job['content'])}")

    return len(jobs)


def test_process_embeddings():
    """Call the edge function to process embeddings"""
    print_section("Step 4: Process Embeddings via Edge Function")

    # Call the edge function
    edge_function_url = f"{SUPABASE_URL}/functions/v1/process-embeddings"

    print("Calling process-embeddings edge function...")

    response = requests.post(
        edge_function_url,
        headers={
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
            "Content-Type": "application/json"
        },
        json={"batchSize": 10}
    )

    if response.status_code != 200:
        print(f"✗ Edge function failed: {response.status_code}")
        print(f"  Response: {response.text}")
        return False

    result = response.json()

    print(f"✓ Edge function completed successfully")
    print(f"  Processed: {result.get('processed', 0)}")
    print(f"  Failed: {result.get('failed', 0)}")

    if result.get('errors'):
        print(f"  Errors: {result['errors']}")

    return result.get('processed', 0) > 0


def test_verify_embeddings(page_ids: list):
    """Verify that embeddings were stored in pdf_pages"""
    print_section("Step 5: Verify Embeddings Stored")

    # Wait for edge function to complete
    time.sleep(2)

    # Check if embeddings exist
    result = supabase.from_('pdf_pages')\
        .select('id, page_number, embedding')\
        .in_('id', page_ids)\
        .execute()

    pages_with_embeddings = [p for p in result.data if p['embedding'] is not None]

    print(f"✓ {len(pages_with_embeddings)} / {len(result.data)} pages have embeddings")

    if len(pages_with_embeddings) > 0:
        # Show embedding dimensions
        first_embedding = pages_with_embeddings[0]['embedding']
        print(f"  Embedding dimensions: {len(first_embedding)}")
        print(f"  Sample values: {first_embedding[:5]}")

    return len(pages_with_embeddings) == len(page_ids)


def test_cleanup(pdf_doc_id: str):
    """Clean up test data"""
    print_section("Step 6: Cleanup")

    # Delete pages (will cascade delete embedding jobs)
    supabase.from_('pdf_pages').delete().eq('pdf_document_id', pdf_doc_id).execute()
    print("✓ Deleted pdf_pages")

    # Delete PDF document
    supabase.from_('pdf_documents').delete().eq('id', pdf_doc_id).execute()
    print("✓ Deleted pdf_document")

    # Delete from storage
    storage_path = f"{TEST_USER_ID}/Cameron_Hightower_Resume_ATS_Version_1.pdf"
    try:
        supabase.storage.from_('pdfs').remove([storage_path])
        print("✓ Deleted from storage")
    except Exception as e:
        print(f"⚠ Storage cleanup warning: {e}")


def main():
    """Run the complete embedding flow test"""
    print("=" * 70)
    print("  PDF Embedding Flow Integration Test")
    print("=" * 70)
    print(f"\nTest PDF: {TEST_PDF.name}")
    print(f"User ID: {TEST_USER_ID}")

    try:
        # Step 1: Upload PDF
        pdf_doc_id, file_data = test_upload_pdf()

        # Step 2: Process PDF and insert pages
        page_ids = test_process_pdf(pdf_doc_id, file_data)

        # Step 3: Verify embedding jobs were created
        job_count = test_verify_embedding_jobs(len(page_ids))

        # Step 4: Process embeddings
        success = test_process_embeddings()

        if not success:
            print("\n✗ Embedding processing failed")
            return False

        # Step 5: Verify embeddings were stored
        all_embedded = test_verify_embeddings(page_ids)

        # Final summary
        print_section("Test Summary")

        if all_embedded and success:
            print("✅ All tests passed!")
            print(f"  - PDF uploaded and processed")
            print(f"  - {len(page_ids)} pages extracted")
            print(f"  - {job_count} embedding jobs created")
            print(f"  - All embeddings generated and stored")
        else:
            print("⚠ Some tests failed")
            if not all_embedded:
                print(f"  - Not all pages have embeddings")

        return all_embedded and success

    finally:
        # Always cleanup
        try:
            test_cleanup(pdf_doc_id)
        except Exception as e:
            print(f"Cleanup error: {e}")


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
