"""
Email PDF Tool

Agent tool for sending PDF documents via email.
"""

import json
import logging
import re
from typing import Dict, Any, Optional

from supabase import Client as SupabaseClient

from app.agents.models import Action
from app.services.pdf_generator import pdf_generator_service
from app.services.email_service import email_service

logger = logging.getLogger(__name__)


def _validate_email(email: str) -> bool:
    """Basic email validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


async def email_pdf(
    params: Dict[str, Any],
    user_id: str,
    supabase: SupabaseClient,
    request_id: Optional[str] = None
) -> str:
    """
    Email a PDF document to a recipient.

    Args:
        params: Dictionary with:
            - pdf_id: ID of the generated PDF to send
            - recipient_email: Email address to send to
            - recipient_name: Name of the recipient
            - subject: Optional email subject
            - message: Optional message body
        user_id: User ID
        supabase: Supabase client
        request_id: Optional request ID for logging

    Returns:
        JSON string with send result
    """
    try:
        pdf_id = params.get("pdf_id", "").strip()
        recipient_email = params.get("recipient_email", "").strip()
        recipient_name = params.get("recipient_name", "").strip()
        subject = params.get("subject", "").strip()
        message = params.get("message", "").strip()

        # Validate required fields
        if not pdf_id:
            return json.dumps({
                "success": False,
                "error": "pdf_id is required. Use create_pdf first to generate a PDF."
            })

        if not recipient_email:
            return json.dumps({
                "success": False,
                "error": "recipient_email is required. Please ask the user for their email address."
            })

        if not recipient_name:
            return json.dumps({
                "success": False,
                "error": "recipient_name is required. Please ask the user for their name."
            })

        if not _validate_email(recipient_email):
            return json.dumps({
                "success": False,
                "error": f"Invalid email address format: {recipient_email}"
            })

        logger.info(f"Emailing PDF {pdf_id} to {recipient_email} for user {user_id}")

        # Get the PDF record to get title and filename
        pdf_record = supabase.from_('generated_pdfs').select(
            'title, storage_path'
        ).eq('id', pdf_id).eq('user_id', user_id).execute()

        if not pdf_record.data:
            return json.dumps({
                "success": False,
                "error": f"PDF {pdf_id} not found or not owned by user"
            })

        pdf_title = pdf_record.data[0].get('title', 'Document')

        # Download the PDF bytes
        pdf_bytes = await pdf_generator_service.get_pdf_bytes(
            pdf_id=pdf_id,
            user_id=user_id,
            supabase=supabase
        )

        if not pdf_bytes:
            return json.dumps({
                "success": False,
                "error": "Failed to retrieve PDF file"
            })

        # Set defaults for optional fields
        if not subject:
            subject = f"PDF Document: {pdf_title}"

        if not message:
            message = f"Please find attached the document: {pdf_title}"

        # Generate filename
        safe_title = "".join(c for c in pdf_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        pdf_filename = f"{safe_title[:50]}.pdf"

        # Send the email
        result = await email_service.send_email_with_pdf(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            body=message,
            pdf_bytes=pdf_bytes,
            pdf_filename=pdf_filename,
            user_id=user_id,
            supabase=supabase,
            pdf_id=pdf_id
        )

        if result.get('success'):
            logger.info(f"Successfully sent email to {recipient_email}")
            return json.dumps({
                "success": True,
                "message": f"Email sent successfully to {recipient_name} at {recipient_email}",
                "email_id": result.get('email_id'),
                "recipient": recipient_email,
                "pdf_title": pdf_title
            }, indent=2)
        else:
            logger.error(f"Failed to send email: {result.get('error')}")
            return json.dumps({
                "success": False,
                "error": result.get('error', 'Unknown error sending email')
            })

    except Exception as e:
        logger.error(f"Error emailing PDF: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"Failed to email PDF: {str(e)}"
        })


async def email_pdf_handler(
    input_str: str,
    user_id: str,
    supabase: SupabaseClient,
    request_id: Optional[str] = None
) -> str:
    """
    Handler function for the email_pdf action.

    Args:
        input_str: JSON string with parameters
        user_id: User ID
        supabase: Supabase client
        request_id: Optional request ID

    Returns:
        JSON string with results
    """
    try:
        params = json.loads(input_str) if isinstance(input_str, str) else input_str
    except json.JSONDecodeError:
        return json.dumps({
            "success": False,
            "error": "Invalid JSON input. Expected: {pdf_id, recipient_email, recipient_name, subject?, message?}"
        })

    return await email_pdf(params, user_id, supabase, request_id)


def create_email_pdf_action(
    user_id: str,
    supabase: SupabaseClient,
    request_id: Optional[str] = None
) -> Action:
    """
    Create the email_pdf action for the agent.

    Args:
        user_id: User ID
        supabase: Supabase client
        request_id: Optional request ID

    Returns:
        Action object configured for PDF emailing
    """
    async def handler_wrapper(input_str: str) -> str:
        """Async wrapper for email_pdf_handler."""
        return await email_pdf_handler(input_str, user_id, supabase, request_id)

    return Action(
        name="email_pdf",
        description="Send a PDF document to a recipient via email. You will need the user's name and email so if you don't it, please ask them. Use create_pdf first to generate the document, then use this tool to send it.",
        parameters={
            "pdf_id": {
                "type": "string",
                "description": "ID of the PDF to send (obtained from create_pdf tool)"
            },
            "recipient_email": {
                "type": "string",
                "description": "Email address of the recipient"
            },
            "recipient_name": {
                "type": "string",
                "description": "Name of the recipient"
            },
            "subject": {
                "type": "string",
                "description": "Optional email subject line. Defaults to the PDF title."
            },
            "message": {
                "type": "string",
                "description": "Optional message to include in the email body"
            }
        },
        returns="JSON object with success status and email ID",
        handler=handler_wrapper
    )
