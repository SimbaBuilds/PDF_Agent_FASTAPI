#!/usr/bin/env python3
"""
Test script to verify PDF readability and processing.
Tests both machine-readable and non-machine-readable PDFs.
"""

import os
import sys
import io
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import PyPDF2

def test_pdf_text_extraction(pdf_path: str) -> dict:
    """
    Test if a PDF is machine-readable using text extraction.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Dictionary with test results
    """
    print(f"\n{'=' * 70}")
    print(f"Testing: {os.path.basename(pdf_path)}")
    print(f"{'=' * 70}")

    if not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        return {"success": False, "error": "File not found"}

    file_size = os.path.getsize(pdf_path)
    print(f"📄 File size: {file_size:,} bytes ({file_size / 1024:.2f} KB)")

    try:
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))

            num_pages = len(pdf_reader.pages)
            print(f"📖 Number of pages: {num_pages}")

            results = {
                "success": True,
                "filename": os.path.basename(pdf_path),
                "file_size_bytes": file_size,
                "num_pages": num_pages,
                "pages": []
            }

            total_chars = 0

            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    # Extract text
                    text = page.extract_text()
                    char_count = len(text) if text else 0
                    total_chars += char_count

                    # Determine if machine-readable (threshold: 200 chars)
                    is_machine_readable = char_count >= 200

                    page_result = {
                        "page_number": page_num,
                        "char_count": char_count,
                        "is_machine_readable": is_machine_readable,
                        "text_preview": text[:200] if text else ""
                    }
                    results["pages"].append(page_result)

                    status = "✅ Machine-readable" if is_machine_readable else "⚠️  Non-machine-readable (needs OCR/Vision)"
                    print(f"\nPage {page_num}: {char_count} characters - {status}")

                    if char_count > 0:
                        print(f"Preview: {text[:150]}...")
                    else:
                        print("Preview: [No text extracted]")

                except Exception as e:
                    print(f"❌ Error processing page {page_num}: {str(e)}")
                    results["pages"].append({
                        "page_number": page_num,
                        "error": str(e),
                        "is_machine_readable": False
                    })

            # Overall summary
            print(f"\n{'=' * 70}")
            print("📊 Summary:")
            print(f"   Total characters extracted: {total_chars:,}")
            print(f"   Average per page: {total_chars / num_pages:.0f}")

            machine_readable_pages = sum(1 for p in results["pages"] if p.get("is_machine_readable", False))
            non_readable_pages = num_pages - machine_readable_pages

            print(f"   Machine-readable pages: {machine_readable_pages}/{num_pages}")
            print(f"   Non-readable pages: {non_readable_pages}/{num_pages}")

            if non_readable_pages > 0:
                print(f"\n⚠️  Recommendation: Use Vision Processor for {non_readable_pages} page(s)")
            else:
                print(f"\n✅ All pages are machine-readable - standard text extraction OK")

            print(f"{'=' * 70}")

            results["total_chars"] = total_chars
            results["machine_readable_pages"] = machine_readable_pages
            results["non_readable_pages"] = non_readable_pages
            results["needs_vision_processing"] = non_readable_pages > 0

            return results

    except Exception as e:
        print(f"❌ Error reading PDF: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def main():
    """Main test function."""
    print("\n🧪 PDF Readability Test Suite")
    print("Testing both machine-readable and non-machine-readable PDFs\n")

    # Test PDFs
    test_pdfs = [
        "/Users/cameronhightower/Software_Projects/pdf_agent_fastapi/test_pdfs/Cameron_Hightower_Resume_ATS_Version_1.pdf",
        "/Users/cameronhightower/Software_Projects/pdf_agent_fastapi/test_pdfs/Case_plan.pdf"
    ]

    all_results = []

    for pdf_path in test_pdfs:
        result = test_pdf_text_extraction(pdf_path)
        all_results.append(result)

    # Final summary
    print(f"\n\n{'=' * 70}")
    print("🎯 FINAL SUMMARY")
    print(f"{'=' * 70}")

    for i, result in enumerate(all_results, 1):
        if result.get("success"):
            filename = result["filename"]
            needs_vision = result.get("needs_vision_processing", False)
            print(f"\n{i}. {filename}")
            print(f"   Pages: {result['num_pages']}")
            print(f"   Machine-readable: {result['machine_readable_pages']}/{result['num_pages']}")
            print(f"   Needs vision processing: {'Yes' if needs_vision else 'No'}")
        else:
            print(f"\n{i}. Failed: {result.get('error', 'Unknown error')}")

    print(f"\n{'=' * 70}")
    print("Next Steps:")
    print("1. Update pdf_processor.py to use vision processing for non-readable pages")
    print("2. Test full PDF upload pipeline with both types of PDFs")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
