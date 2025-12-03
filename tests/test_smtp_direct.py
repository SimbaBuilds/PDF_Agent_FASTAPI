#!/usr/bin/env python3
"""
Direct SMTP test for email sending.
This bypasses the application layer and tests SMTP directly.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_smtp_email():
    """Test sending an email directly via SMTP."""

    print("=" * 70)
    print("📧 Direct SMTP Email Test")
    print("=" * 70)

    # Get SMTP configuration from environment
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    recipient_email = "cmrn.hightower@gmail.com"
    recipient_name = "Cameron"
    subject = "Test Email from PDF Agent"

    print(f"\n1️⃣  SMTP Configuration:")
    print(f"   Host: {smtp_host}")
    print(f"   Port: {smtp_port}")
    print(f"   User: {smtp_user}")
    print(f"   Password Set: {'Yes' if smtp_password else 'No'}")

    if not smtp_user or not smtp_password:
        print("\n❌ SMTP credentials not configured!")
        print("   Please set SMTP_USER and SMTP_PASSWORD in your .env file")
        return

    # Read test PDF
    test_pdf_path = "/Users/cameronhightower/Software_Projects/pdf_agent_fastapi/test_pdfs/Cameron_Hightower_Resume_ATS_Version_1.pdf"

    print(f"\n2️⃣  Reading test PDF: {test_pdf_path}")

    if not os.path.exists(test_pdf_path):
        print(f"❌ Test PDF not found!")
        return

    with open(test_pdf_path, 'rb') as f:
        pdf_bytes = f.read()

    print(f"✅ PDF loaded successfully ({len(pdf_bytes)} bytes)")

    # Create email message
    print(f"\n3️⃣  Creating email message...")
    print(f"   To: {recipient_name} <{recipient_email}>")
    print(f"   Subject: {subject}")

    msg = MIMEMultipart()
    msg['From'] = f"PDF Agent <{smtp_user}>"
    msg['To'] = f"{recipient_name} <{recipient_email}>"
    msg['Subject'] = subject

    # Add body
    body = f"Hi {recipient_name},\n\nThis is a test email from the PDF Agent to verify email sending functionality.\n\nThe PDF Agent system is working correctly!"
    msg.attach(MIMEText(body, 'plain'))

    # Attach PDF
    pdf_attachment = MIMEApplication(pdf_bytes, _subtype='pdf')
    pdf_attachment.add_header(
        'Content-Disposition',
        'attachment',
        filename="Cameron_Hightower_Resume.pdf"
    )
    msg.attach(pdf_attachment)

    print("✅ Email message created with PDF attachment")

    # Send email
    print(f"\n4️⃣  Sending email via SMTP...")
    print(f"   Connecting to {smtp_host}:{smtp_port}...")

    try:
        # Port 465 requires SMTP_SSL, port 587 uses SMTP with STARTTLS
        if smtp_port == 465:
            print("   Using SMTP_SSL for port 465...")
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                print(f"   Logging in as {smtp_user}...")
                server.login(smtp_user, smtp_password)

                print("   Sending message...")
                server.send_message(msg)
        else:
            print("   Using SMTP with STARTTLS...")
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                print("   Starting TLS...")
                server.starttls()

                print(f"   Logging in as {smtp_user}...")
                server.login(smtp_user, smtp_password)

                print("   Sending message...")
                server.send_message(msg)

        print("\n" + "=" * 70)
        print("🎉 SUCCESS - Email sent successfully!")
        print("=" * 70)
        print(f"✅ Email sent to: {recipient_email}")
        print(f"✅ With attachment: Cameron_Hightower_Resume.pdf")
        print(f"\n📬 Check your inbox at {recipient_email}!")
        print("=" * 70)

    except smtplib.SMTPAuthenticationError as e:
        print("\n" + "=" * 70)
        print("❌ SMTP Authentication Failed")
        print("=" * 70)
        print(f"Error: {str(e)}")
        print("\nPossible causes:")
        print("1. Incorrect SMTP username or password")
        print("2. Need to use an App Password (not regular Gmail password)")
        print("3. 2FA is enabled - must use App Password")
        print("\nFor Gmail:")
        print("- Go to: https://myaccount.google.com/apppasswords")
        print("- Generate an app password and use that instead")
        print("=" * 70)

    except smtplib.SMTPException as e:
        print("\n" + "=" * 70)
        print("❌ SMTP Error")
        print("=" * 70)
        print(f"Error: {str(e)}")
        print("=" * 70)

    except Exception as e:
        print("\n" + "=" * 70)
        print("❌ Unexpected Error")
        print("=" * 70)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print("=" * 70)


if __name__ == "__main__":
    print("🧪 Testing SMTP email sending directly")
    test_smtp_email()
