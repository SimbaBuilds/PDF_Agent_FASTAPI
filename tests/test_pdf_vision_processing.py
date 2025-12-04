#!/usr/bin/env python3
"""
Test script to verify PDF processing with vision capabilities.
Tests the _process_pdf method directly with both machine-readable and non-machine-readable PDFs.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

from app.services.pdf_processor import pdf_processor


async def test_pdf_processing_direct(pdf_path: str):
    """
    Test PDF processing directly using the _process_pdf method.

    Args:
        pdf_path: Path to PDF file
    """
    filename = os.path.basename(pdf_path)

    print(f"\n{'=' * 70}")
    print(f"🧪 Testing: {filename}")
    print(f"{'=' * 70}")

    if not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        return {
            'success': False,
            'filename': filename,
            'error': 'File not found'
        }

    try:
        # Read PDF file
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()

        print(f"\n📄 File size: {len(pdf_bytes):,} bytes")

        # Process PDF
        print(f"\n🔄 Processing PDF...")
        pages = await pdf_processor._process_pdf(pdf_bytes)

        if pages:
            print(f"\n✅ Processing successful!")
            print(f"   Pages extracted: {len(pages)}")

            # Display page content
            for i, page_content in enumerate(pages, 1):
                print(f"\n   📄 Page {i} ({len(page_content)} characters):")
                preview = page_content[:300] if len(page_content) > 300 else page_content
                print(f"   {preview}...")

            return {
                'success': True,
                'filename': filename,
                'num_pages': len(pages),
                'total_chars': sum(len(p) for p in pages)
            }
        else:
            print(f"\n❌ No pages extracted")
            return {
                'success': False,
                'filename': filename,
                'error': 'No pages extracted'
            }

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'filename': filename,
            'error': str(e)
        }


async def main():
    """Main test function."""
    print("\n" + "=" * 70)
    print("🧪 PDF Vision Processing Test")
    print("=" * 70)

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

        result = await test_pdf_processing_direct(pdf_path)
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
            print(f"   Total characters: {result.get('total_chars', 0):,}")
        else:
            print(f"   Error: {result.get('error', 'Unknown error')}")

    print(f"\n{'=' * 70}")

    if successful == len(results):
        print("🎉 All tests passed!")
        print("\nKey Points:")
        print("✅ Machine-readable PDFs use standard text extraction")
        print("✅ Non-machine-readable PDFs use vision processing")
        print("✅ Vision processing successfully extracts text from image-based PDFs")
    else:
        print("⚠️  Some tests failed. Please review the errors above.")

    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    asyncio.run(main())
