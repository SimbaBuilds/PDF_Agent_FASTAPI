"""
Email Service

Service for sending emails with PDF attachments using Gmail SMTP.
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import uuid4

from supabase import Client as SupabaseClient

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service for sending emails with attachments.

    Uses Gmail SMTP for email delivery.
    """

    def __init__(self):
        """Initialize the email service."""
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.contact_email = os.getenv("CONTACT_EMAIL", self.smtp_user)

        if not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP credentials not configured. Email sending will fail.")

        logger.info(f"Initialized email service with host: {self.smtp_host}")

    def _validate_email(self, email: str) -> bool:
        """
        Basic email validation.

        Args:
            email: Email address to validate

        Returns:
            True if email appears valid
        """
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    async def send_email_with_pdf(
        self,
        recipient_email: str,
        recipient_name: str,
        subject: str,
        body: str,
        pdf_bytes: bytes,
        pdf_filename: str,
        user_id: str,
        supabase: SupabaseClient,
        pdf_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an email with a PDF attachment.

        Args:
            recipient_email: Recipient's email address
            recipient_name: Recipient's name
            subject: Email subject
            body: Email body text
            pdf_bytes: PDF file as bytes
            pdf_filename: Filename for the attachment
            user_id: User ID for logging
            supabase: Supabase client for recording history
            pdf_id: Optional ID of the generated PDF

        Returns:
            Dictionary with success status and details
        """
        # Validate email
        if not self._validate_email(recipient_email):
            logger.warning(f"Invalid email address: {recipient_email}")
            return {
                'success': False,
                'error': f"Invalid email address: {recipient_email}"
            }

        # Check SMTP credentials
        if not self.smtp_user or not self.smtp_password:
            logger.error("SMTP credentials not configured")
            return {
                'success': False,
                'error': "Email service not configured"
            }

        email_id = str(uuid4())

        try:
            # Create the email message
            msg = MIMEMultipart()
            msg['From'] = f"PDF Agent <{self.smtp_user}>"
            msg['To'] = f"{recipient_name} <{recipient_email}>"
            msg['Subject'] = subject

            # Add body text
            body_with_greeting = f"Hi {recipient_name},\n\n{body}"
            msg.attach(MIMEText(body_with_greeting, 'plain'))

            # Attach the PDF
            pdf_attachment = MIMEApplication(pdf_bytes, _subtype='pdf')
            pdf_attachment.add_header(
                'Content-Disposition',
                'attachment',
                filename=pdf_filename
            )
            msg.attach(pdf_attachment)

            # Record pending email in database
            await self._record_email_history(
                email_id=email_id,
                user_id=user_id,
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                subject=subject,
                pdf_id=pdf_id,
                status='pending',
                supabase=supabase
            )

            # Send the email - use SMTP_SSL for port 465, SMTP with STARTTLS for 587
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)

            logger.info(f"Successfully sent email to {recipient_email}")

            # Update status to sent
            await self._update_email_status(
                email_id=email_id,
                status='sent',
                supabase=supabase
            )

            return {
                'success': True,
                'email_id': email_id,
                'recipient': recipient_email,
                'message': f"Email sent successfully to {recipient_name}"
            }

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {str(e)}")
            await self._update_email_status(
                email_id=email_id,
                status='failed',
                error_message="Authentication failed",
                supabase=supabase
            )
            return {
                'success': False,
                'error': "Email authentication failed. Please check SMTP credentials."
            }

        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {str(e)}")
            await self._update_email_status(
                email_id=email_id,
                status='failed',
                error_message=str(e),
                supabase=supabase
            )
            return {
                'success': False,
                'error': f"Failed to send email: {str(e)}"
            }

        except Exception as e:
            logger.error(f"Unexpected error sending email: {str(e)}")
            await self._update_email_status(
                email_id=email_id,
                status='failed',
                error_message=str(e),
                supabase=supabase
            )
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}"
            }

    async def _record_email_history(
        self,
        email_id: str,
        user_id: str,
        recipient_email: str,
        recipient_name: str,
        subject: str,
        pdf_id: Optional[str],
        status: str,
        supabase: SupabaseClient
    ) -> None:
        """Record email in history table."""
        try:
            record_data = {
                'id': email_id,
                'user_id': user_id,
                'recipient_email': recipient_email,
                'recipient_name': recipient_name,
                'subject': subject,
                'pdf_id': pdf_id,
                'status': status,
                'created_at': datetime.now().isoformat()
            }

            supabase.from_('email_history').insert(record_data).execute()
            logger.debug(f"Recorded email {email_id} in history")

        except Exception as e:
            logger.error(f"Failed to record email history: {str(e)}")

    async def _update_email_status(
        self,
        email_id: str,
        status: str,
        supabase: SupabaseClient,
        error_message: Optional[str] = None
    ) -> None:
        """Update email status in history table."""
        try:
            update_data = {
                'status': status
            }

            if status == 'sent':
                update_data['sent_at'] = datetime.now().isoformat()

            if error_message:
                update_data['error_message'] = error_message

            supabase.from_('email_history').update(update_data).eq('id', email_id).execute()
            logger.debug(f"Updated email {email_id} status to {status}")

        except Exception as e:
            logger.error(f"Failed to update email status: {str(e)}")

    def check_configuration(self) -> Dict[str, Any]:
        """
        Check if the email service is properly configured.

        Returns:
            Dictionary with configuration status
        """
        return {
            'configured': bool(self.smtp_user and self.smtp_password),
            'smtp_host': self.smtp_host,
            'smtp_port': self.smtp_port,
            'smtp_user_set': bool(self.smtp_user),
            'smtp_password_set': bool(self.smtp_password)
        }


# Global instance
email_service = EmailService()
