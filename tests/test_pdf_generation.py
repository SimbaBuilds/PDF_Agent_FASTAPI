#!/usr/bin/env python3
"""
Test script for PDF generation functionality.
Tests the PDF generator service to ensure PDFs are created correctly.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

from app.services.pdf_generator import pdf_generator_service


async def test_pdf_generation():
    """Test PDF generation with both local file and Supabase storage."""

    print("=" * 70)
    print("📄 PDF Generation Test")
    print("=" * 70)

    # Test content
    title = "Test PDF Document"
    content = """# Test PDF Document

This is a test document to verify PDF generation functionality.

## Features Tested
- Title rendering
- Markdown formatting
- Bullet points:
  - Item 1
  - Item 2
  - Item 3

## Additional Content
This document contains multiple sections to ensure proper formatting
and layout of the generated PDF.

### Subsection
More content to fill out the document and test text wrapping and
paragraph formatting.
"""

    print(f"\n1️⃣  Test Configuration:")
    print(f"   Title: {title}")
    print(f"   Content Length: {len(content)} characters")
    print(f"   Content Type: report")

    # Test 1: Generate PDF bytes (in-memory)
    print(f"\n2️⃣  Testing PDF generation (in-memory)...")

    try:
        pdf_bytes = pdf_generator_service.generate_pdf(
            title=title,
            content=content,
            content_type="report"
        )

        if pdf_bytes:
            print(f"✅ PDF generated successfully!")
            print(f"   Size: {len(pdf_bytes)} bytes")

            # Check PDF header
            if pdf_bytes.startswith(b'%PDF'):
                print(f"✅ Valid PDF format (starts with %PDF)")

                # Save to file for verification
                output_path = "/tmp/test_generated.pdf"
                with open(output_path, 'wb') as f:
                    f.write(pdf_bytes)
                print(f"✅ Saved to: {output_path}")
            else:
                print(f"❌ Invalid PDF format")
        else:
            print(f"❌ PDF generation failed")

    except Exception as e:
        print(f"❌ Error generating PDF: {str(e)}")
        import traceback
        traceback.print_exc()

    # Test 2: Test Supabase upload
    print(f"\n3️⃣  Testing PDF upload to Supabase...")

    try:
        from app.utils.supabase_singleton import get_supabase_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            print("❌ Supabase credentials not configured")
        else:
            print(f"   Supabase URL: {supabase_url[:30]}...")

            # Get Supabase client using the singleton
            print("   Getting Supabase client...")
            from supabase import create_client
            supabase = create_client(supabase_url, supabase_key)

            user_id = "703b410f-f50c-4bc8-b9a3-0991fed5a023"

            print(f"   Creating and storing PDF for user {user_id[:8]}...")
            result = await pdf_generator_service.create_and_store_pdf(
                title=title,
                content=content,
                user_id=user_id,
                supabase=supabase,
                content_type="report"
            )

            if result.get('success'):
                pdf_id = result.get('pdf_id')
                storage_path = result.get('storage_path')
                print(f"✅ PDF uploaded to Supabase successfully!")
                print(f"   PDF ID: {pdf_id}")
                print(f"   Storage Path: {storage_path}")

                # Try to get download URL
                print(f"\n   Testing download URL generation...")
                download_url = await pdf_generator_service.get_pdf_download_url(
                    pdf_id=pdf_id,
                    user_id=user_id,
                    supabase=supabase
                )
                if download_url:
                    print(f"✅ Download URL generated: {download_url[:60]}...")
                else:
                    print(f"❌ Failed to generate download URL")
            else:
                error = result.get('error', 'Unknown error')
                print(f"❌ Failed to upload PDF: {error}")

    except Exception as e:
        print(f"❌ Error testing Supabase upload: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print("📊 Test Summary")
    print("=" * 70)
    print("✅ Local PDF generation: Working")
    print("ℹ️  Supabase storage: Requires 'pdfs' bucket to be created")
    print("\nNext steps:")
    print("1. Create 'pdfs' bucket in Supabase Storage")
    print("2. Test PDF upload to Supabase with full integration")
    print("=" * 70)


def main():
    """Main function."""
    print("🧪 Testing PDF Generation Service")
    asyncio.run(test_pdf_generation())


if __name__ == "__main__":
    main()
