#!/usr/bin/env python3
"""
Direct test for email sending functionality.
This script directly calls the email service to test email sending.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

from app.services.email_service import email_service
from app.utils.supabase_singleton import get_supabase_client


async def test_direct_email_send():
    """Test sending an email directly using the email service."""

    print("=" * 70)
    print("📧 Direct Email Service Test")
    print("=" * 70)

    # Configuration
    recipient_email = "cmrn.hightower@gmail.com"
    recipient_name = "Cameron"
    subject = "Test Email from PDF Agent"
    body = "This is a test email to verify the email sending functionality."
    user_id = "703b410f-f50c-4bc8-b9a3-0991fed5a023"

    # Read a test PDF file
    test_pdf_path = "/Users/cameronhightower/Software_Projects/pdf_agent_fastapi/test_pdfs/Cameron_Hightower_Resume_ATS_Version_1.pdf"

    print(f"\n1️⃣  Reading test PDF: {test_pdf_path}")

    if not os.path.exists(test_pdf_path):
        print(f"❌ Test PDF not found at {test_pdf_path}")
        return

    with open(test_pdf_path, 'rb') as f:
        pdf_bytes = f.read()

    print(f"✅ PDF loaded successfully ({len(pdf_bytes)} bytes)")

    # Check email service configuration
    print("\n2️⃣  Checking email service configuration...")
    config = email_service.check_configuration()
    print(f"   SMTP Host: {config['smtp_host']}")
    print(f"   SMTP Port: {config['smtp_port']}")
    print(f"   SMTP User Set: {config['smtp_user_set']}")
    print(f"   SMTP Password Set: {config['smtp_password_set']}")
    print(f"   Configured: {config['configured']}")

    if not config['configured']:
        print("❌ Email service is not configured!")
        print("   Please set SMTP_USER and SMTP_PASSWORD in your .env file")
        return

    print("✅ Email service is configured")

    # Get Supabase client
    print("\n3️⃣  Initializing Supabase client...")
    supabase = get_supabase_client()
    print("✅ Supabase client initialized")

    # Send the email
    print(f"\n4️⃣  Sending email to {recipient_email}...")
    print(f"   Subject: {subject}")
    print(f"   Recipient: {recipient_name}")
    print(f"   PDF Filename: Cameron_Hightower_Resume.pdf")

    try:
        result = await email_service.send_email_with_pdf(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            body=body,
            pdf_bytes=pdf_bytes,
            pdf_filename="Cameron_Hightower_Resume.pdf",
            user_id=user_id,
            supabase=supabase,
            pdf_id=None  # No PDF ID since this is a direct file
        )

        print("\n" + "=" * 70)
        if result.get('success'):
            print("🎉 SUCCESS - Email sent successfully!")
            print("=" * 70)
            print(f"Email ID: {result.get('email_id')}")
            print(f"Recipient: {result.get('recipient')}")
            print(f"Message: {result.get('message')}")
            print("\n✅ Check your inbox at cmrn.hightower@gmail.com!")
        else:
            print("❌ FAILED - Email sending failed")
            print("=" * 70)
            print(f"Error: {result.get('error')}")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Exception occurred: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """Main function."""
    print("🧪 Testing direct email sending functionality")
    asyncio.run(test_direct_email_send())


if __name__ == "__main__":
    main()
