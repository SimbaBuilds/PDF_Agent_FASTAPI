#!/usr/bin/env python3
"""
Test script for sending emails using the email_pdf tool.
This script will create a PDF and send it via email to a specified recipient.
"""

import json
import requests
import time
import jwt
import os
import argparse
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

from app.utils.logging.logging_config import setup_logging_from_env

# Configuration
DEFAULT_PORT = 8000
USER_ID = "703b410f-f50c-4bc8-b9a3-0991fed5a023"

# Default test values
DEFAULT_RECIPIENT_EMAIL = "cmrn.hightower@gmail.com"
DEFAULT_RECIPIENT_NAME = "Cameron"


def generate_test_jwt_token(user_id: str) -> str:
    """Generate a test JWT token for the given user ID."""
    jwt_secret = os.environ.get("SUPABASE_JWT_SECRET")
    if not jwt_secret:
        raise ValueError("SUPABASE_JWT_SECRET environment variable not found")

    current_time = int(time.time())

    payload = {
        'iss': 'supabase',
        'sub': user_id,
        'aud': 'authenticated',
        'exp': current_time + 3600,
        'iat': current_time - 300,
        'role': 'authenticated',
        'email': f'test-{user_id}@example.com'
    }

    token = jwt.encode(payload, jwt_secret, algorithm='HS256')
    return token


def test_email_sending(
    recipient_email: str = DEFAULT_RECIPIENT_EMAIL,
    recipient_name: str = DEFAULT_RECIPIENT_NAME,
    port: int = DEFAULT_PORT,
    log_file: str = None,
    timeout: int = 360
):
    """Test sending an email via the chat endpoint."""

    if log_file:
        if not log_file.endswith('.log'):
            log_file += '.log'
        from app.utils.logging.logging_config import setup_logging_with_custom_file
        setup_logging_with_custom_file(log_file)
        print(f"📝 Application logs will be written to: logs/{log_file}")
    else:
        setup_logging_from_env()
        print(f"📝 Application logs will be written to: logs/app.log")

    base_url = f"http://localhost:{port}"

    print("=" * 70)
    print("📧 Email Sending Test Script")
    print("=" * 70)
    print(f"Base URL: {base_url}")
    print(f"User ID: {USER_ID}")
    print(f"Recipient Email: {recipient_email}")
    print(f"Recipient Name: {recipient_name}")
    print("-" * 70)

    try:
        # Generate JWT token
        print("\n1️⃣  Generating JWT token...")
        token = generate_test_jwt_token(USER_ID)
        print("✅ JWT token generated successfully")

        # Step 1: First, create a PDF document
        print("\n2️⃣  Creating a PDF document first...")
        current_timestamp = int(time.time())

        create_pdf_message = f"Please create a simple test PDF with the title 'Test Email Document' and some sample content. The PDF should contain: Title: Test Email Document, Content: This is a test document created to verify email sending functionality."

        user_message = {
            "role": "user",
            "content": create_pdf_message,
            "type": "text",
            "timestamp": current_timestamp
        }

        chat_request = {
            "message": create_pdf_message,
            "timestamp": current_timestamp,
            "history": [user_message],
            "preferences": None,
            "request_id": f"test_create_pdf_{current_timestamp}",
            "integration_in_progress": False
        }

        form_data = {
            "json_data": json.dumps(chat_request)
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        print(f"Making request to {base_url}/api/chat to create PDF...")
        response = requests.post(
            f"{base_url}/api/chat",
            data=form_data,
            headers=headers,
            timeout=timeout
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code != 200:
            print(f"❌ Failed to create PDF")
            print(f"Response: {response.text}")
            return

        create_response = response.json()
        print(f"✅ PDF Creation Response: {create_response.get('response', 'No response')[:200]}...")

        # Give it a moment and then send email
        print("\n3️⃣  Waiting a moment before sending email...")
        time.sleep(2)

        # Step 2: Now send the email
        print(f"\n4️⃣  Sending email to {recipient_email}...")
        current_timestamp = int(time.time())

        email_message = f"Please send an email to {recipient_name} at {recipient_email} with a test PDF document. The subject should be 'Test PDF Document' and the message should say 'Please find attached the test PDF document.'."

        user_message = {
            "role": "user",
            "content": email_message,
            "type": "text",
            "timestamp": current_timestamp
        }

        chat_request = {
            "message": email_message,
            "timestamp": current_timestamp,
            "history": [user_message],
            "preferences": None,
            "request_id": f"test_send_email_{current_timestamp}",
            "integration_in_progress": False
        }

        form_data = {
            "json_data": json.dumps(chat_request)
        }

        print(f"Making request to {base_url}/api/chat to send email...")
        response = requests.post(
            f"{base_url}/api/chat",
            data=form_data,
            headers=headers,
            timeout=timeout
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            email_response = response.json()
            print("\n🎉 SUCCESS - Email endpoint responded successfully!")
            print("=" * 70)
            print(f"Response: {email_response.get('response', 'No response field')}")
            print(f"Timestamp: {email_response.get('timestamp', 'No timestamp')}")
            print("=" * 70)

        elif response.status_code == 401:
            print(f"\n🔐 AUTH ERROR - Status Code: {response.status_code}")
            print("This likely means:")
            print("1. JWT secret is incorrect")
            print("2. User doesn't exist in user_profiles table")
            print("3. Token format is invalid")
            print(f"Response: {response.text}")

        else:
            print(f"\n❌ ERROR - Status Code: {response.status_code}")
            print(f"Response: {response.text}")

    except ValueError as e:
        print(f"\n⚙️  CONFIGURATION ERROR: {e}")
        print("Make sure your .env file contains SUPABASE_JWT_SECRET")

    except requests.exceptions.Timeout:
        print(f"\n⏰ TIMEOUT - Request took longer than {timeout} seconds")

    except requests.exceptions.ConnectionError:
        print(f"\n🔌 CONNECTION ERROR - Could not connect to {base_url}")
        print("Make sure your FastAPI server is running:")
        print("  python -m app.main")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ REQUEST ERROR: {e}")

    except Exception as e:
        print(f"\n💥 UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()


def verify_environment():
    """Verify that required environment variables are present."""
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_JWT_SECRET"
    ]

    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please add these to your .env file")
        return False

    print("✅ All required environment variables found")

    # Check email configuration
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")

    if not smtp_user or not smtp_password:
        print("⚠️  Email service may not be configured (SMTP_USER or SMTP_PASSWORD not set)")
        print("   Email sending will fail without these credentials")
        return False

    print("✅ Email service configured with SMTP credentials")
    return True


def main():
    """Main function with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Test sending emails via the PDF Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tests/test_email_send.py
  python tests/test_email_send.py --email "recipient@example.com" --name "John"
  python tests/test_email_send.py -e "test@gmail.com" -n "Test User" -t 300
  python tests/test_email_send.py -l "email_test" --port 8000
        """
    )

    parser.add_argument(
        "-e", "--email",
        type=str,
        default=DEFAULT_RECIPIENT_EMAIL,
        help=f"Recipient email address (default: {DEFAULT_RECIPIENT_EMAIL})"
    )

    parser.add_argument(
        "-n", "--name",
        type=str,
        default=DEFAULT_RECIPIENT_NAME,
        help=f"Recipient name (default: {DEFAULT_RECIPIENT_NAME})"
    )

    parser.add_argument(
        "-l", "--log-file",
        type=str,
        help="Name of the log file for application logs (without .log extension)"
    )

    parser.add_argument(
        "-t", "--timeout",
        type=int,
        default=360,
        help="Request timeout in seconds (default: 360)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port number for the server (default: {DEFAULT_PORT})"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("📧 PDF Agent Email Sending Test")
    print("=" * 70)

    if verify_environment():
        test_email_sending(
            recipient_email=args.email,
            recipient_name=args.name,
            log_file=args.log_file,
            timeout=args.timeout,
            port=args.port
        )
    else:
        print("\n🛑 Test aborted due to missing configuration")


if __name__ == "__main__":
    main()
