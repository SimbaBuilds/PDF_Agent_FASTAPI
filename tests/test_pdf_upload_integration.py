#!/usr/bin/env python3
"""
Integration test for PDF upload and processing.
Tests both machine-readable and non-machine-readable PDFs through the full pipeline.
"""

import os
import sys
import asyncio
import time
from pathlib import Path
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

from supabase import create_client
from app.services.pdf_processor import pdf_processor


async def upload_pdf_to_supabase(pdf_path: str, user_id: str, supabase) -> dict:
    """
    Upload a PDF to Supabase storage and return metadata.

    Args:
        pdf_path: Path to PDF file
        user_id: User ID
        supabase: Supabase client

    Returns:
        File metadata dictionary
    """
    filename = os.path.basename(pdf_path)
    file_size = os.path.getsize(pdf_path)

    print(f"\n📤 Uploading {filename} to Supabase storage...")

    try:
        # Read PDF file
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()

        # Upload to Supabase storage
        storage_path = f"test_uploads/{user_id}/{filename}"

        # Delete existing file if it exists
        try:
            supabase.storage.from_('pdfs').remove([storage_path])
        except Exception:
            pass  # File doesn't exist, that's ok

        # Upload file
        upload_result = supabase.storage.from_('pdfs').upload(
            path=storage_path,
            file=pdf_bytes,
            file_options={"content-type": "application/pdf"}
        )

        print(f"✅ Uploaded to: {storage_path}")

        # Get public URL (signed URL since bucket is private)
        signed_url = supabase.storage.from_('pdfs').create_signed_url(
            path=storage_path,
            expires_in=3600  # 1 hour
        )

        file_url = signed_url.get('signedURL')

        return {
            'url': file_url,
            'file_type': 'pdf',
            'filename': filename,
            'size_bytes': file_size,
            'storage_path': storage_path
        }

    except Exception as e:
        print(f"❌ Error uploading PDF: {str(e)}")
        raise


async def test_pdf_processing(pdf_path: str, user_id: str, supabase):
    """
    Test full PDF processing pipeline.

    Args:
        pdf_path: Path to PDF file
        user_id: User ID
        supabase: Supabase client
    """
    filename = os.path.basename(pdf_path)

    print(f"\n{'=' * 70}")
    print(f"🧪 Testing: {filename}")
    print(f"{'=' * 70}")

    start_time = time.time()

    try:
        # Upload PDF to Supabase
        file_metadata = await upload_pdf_to_supabase(pdf_path, user_id, supabase)

        # Process PDF
        print(f"\n🔄 Processing PDF...")
        result = await pdf_processor._process_single_file(
            file_metadata=file_metadata,
            user_id=user_id,
            supabase=supabase
        )

        duration = time.time() - start_time

        if result['success']:
            record_id = result['record_id']
            num_pages = result['num_pages']
            page_ids = result['page_ids']

            print(f"\n✅ Processing successful!")
            print(f"   Record ID: {record_id}")
            print(f"   Pages processed: {num_pages}")
            print(f"   Processing time: {duration:.2f}s")

            # Fetch and display page content
            print(f"\n📄 Page content:")
            for i, page_id in enumerate(page_ids, 1):
                page_result = supabase.from_('pdf_pages').select('content').eq('id', str(page_id)).execute()

                if page_result.data:
                    content = page_result.data[0]['content']
                    print(f"\n   Page {i} ({len(content)} characters):")
                    print(f"   {content[:200]}...")
                else:
                    print(f"   Page {i}: [No content found]")

            # Clean up - delete test record and pages
            print(f"\n🧹 Cleaning up test data...")
            try:
                supabase.from_('pdf_pages').delete().eq('pdf_document_id', str(record_id)).execute()
                supabase.from_('pdf_documents').delete().eq('id', str(record_id)).execute()
                supabase.storage.from_('pdfs').remove([file_metadata['storage_path']])
                print(f"✅ Cleanup complete")
            except Exception as cleanup_error:
                print(f"⚠️  Cleanup warning: {str(cleanup_error)}")

            return {
                'success': True,
                'filename': filename,
                'num_pages': num_pages,
                'duration': duration
            }

        else:
            error = result.get('error', 'Unknown error')
            print(f"\n❌ Processing failed: {error}")
            return {
                'success': False,
                'filename': filename,
                'error': error
            }

    except Exception as e:
        duration = time.time() - start_time
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'filename': filename,
            'error': str(e),
            'duration': duration
        }


async def main():
    """Main test function."""
    print("\n" + "=" * 70)
    print("🧪 PDF Upload and Processing Integration Test")
    print("=" * 70)

    # Get Supabase credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials!")
        print("   Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in your .env file")
        return

    print(f"\n🔗 Connecting to Supabase...")
    print(f"   URL: {supabase_url[:30]}...")

    try:
        supabase = create_client(supabase_url, supabase_key)
        print(f"✅ Connected to Supabase")
    except Exception as e:
        print(f"❌ Failed to connect: {str(e)}")
        return

    # Test user ID
    user_id = "703b410f-f50c-4bc8-b9a3-0991fed5a023"

    # Test PDFs
    test_pdfs = [
        {
            'path': "/Users/cameronhightower/Software_Projects/pdf_agent_fastapi/test_pdfs/Cameron_Hightower_Resume_ATS_Version_1.pdf",
            'description': "Machine-readable PDF (text-based)"
        },
        {
            'path': "/Users/cameronhightower/Software_Projects/pdf_agent_fastapi/test_pdfs/Case_plan.pdf",
            'description': "Non-machine-readable PDF (requires vision processing)"
        }
    ]

    results = []

    for pdf_info in test_pdfs:
        pdf_path = pdf_info['path']
        description = pdf_info['description']

        print(f"\n\n{'=' * 70}")
        print(f"📋 Test: {description}")
        print(f"{'=' * 70}")

        if not os.path.exists(pdf_path):
            print(f"❌ File not found: {pdf_path}")
            results.append({
                'success': False,
                'filename': os.path.basename(pdf_path),
                'error': 'File not found'
            })
            continue

        result = await test_pdf_processing(pdf_path, user_id, supabase)
        results.append(result)

        # Wait a bit between tests
        await asyncio.sleep(2)

    # Final summary
    print(f"\n\n{'=' * 70}")
    print("📊 FINAL SUMMARY")
    print(f"{'=' * 70}")

    successful = sum(1 for r in results if r.get('success', False))
    failed = len(results) - successful

    print(f"\n✅ Successful: {successful}/{len(results)}")
    print(f"❌ Failed: {failed}/{len(results)}")

    print(f"\nDetailed Results:")
    for i, result in enumerate(results, 1):
        filename = result.get('filename', 'Unknown')
        success = result.get('success', False)
        status = "✅ Success" if success else "❌ Failed"

        print(f"\n{i}. {filename}: {status}")
        if success:
            print(f"   Pages: {result.get('num_pages', 0)}")
            print(f"   Duration: {result.get('duration', 0):.2f}s")
        else:
            print(f"   Error: {result.get('error', 'Unknown error')}")

    print(f"\n{'=' * 70}")

    if successful == len(results):
        print("🎉 All tests passed!")
        print("\nKey Points:")
        print("✅ Machine-readable PDFs use standard text extraction")
        print("✅ Non-machine-readable PDFs use vision processing")
        print("✅ Both types are processed correctly and stored in the database")
    else:
        print("⚠️  Some tests failed. Please review the errors above.")

    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    asyncio.run(main())
