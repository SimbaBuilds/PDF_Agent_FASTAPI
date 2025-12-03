"""
Create PDF Tool

Agent tool for generating PDF documents (summaries and reports).
"""

import json
import logging
from typing import Dict, Any, Optional

from supabase import Client as SupabaseClient

from app.agents.models import Action
from app.services.pdf_generator import pdf_generator_service

logger = logging.getLogger(__name__)


async def create_pdf(
    params: Dict[str, Any],
    user_id: str,
    supabase: SupabaseClient,
    request_id: Optional[str] = None
) -> str:
    """
    Create a PDF document.

    Args:
        params: Dictionary with:
            - title: Document title
            - content: Text/markdown content to include
            - content_type: "summary" or "report" (default: "summary")
            - source_pdf_ids: Optional list of source PDF IDs
        user_id: User ID
        supabase: Supabase client
        request_id: Optional request ID for logging

    Returns:
        JSON string with creation result including PDF ID
    """
    try:
        title = params.get("title", "").strip()
        content = params.get("content", "").strip()
        content_type = params.get("content_type", "summary").lower()
        source_pdf_ids = params.get("source_pdf_ids", [])

        # Validate required fields
        if not title:
            return json.dumps({
                "success": False,
                "error": "Title is required"
            })

        if not content:
            return json.dumps({
                "success": False,
                "error": "Content is required"
            })

        if content_type not in ["summary", "report"]:
            return json.dumps({
                "success": False,
                "error": f"Invalid content_type: {content_type}. Use 'summary' or 'report'."
            })

        logger.info(f"Creating PDF for user {user_id}: {title}")

        # Create and store the PDF
        result = await pdf_generator_service.create_and_store_pdf(
            title=title,
            content=content,
            content_type=content_type,
            user_id=user_id,
            supabase=supabase,
            source_pdf_ids=source_pdf_ids
        )

        if result.get('success'):
            logger.info(f"Successfully created PDF: {result.get('pdf_id')}")
            return json.dumps({
                "success": True,
                "message": f"PDF '{title}' created successfully",
                "pdf_id": result.get('pdf_id'),
                "filename": result.get('filename'),
                "size_bytes": result.get('size_bytes'),
                "content_type": content_type
            }, indent=2)
        else:
            logger.error(f"Failed to create PDF: {result.get('error')}")
            return json.dumps({
                "success": False,
                "error": result.get('error', 'Unknown error creating PDF')
            })

    except Exception as e:
        logger.error(f"Error creating PDF: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"Failed to create PDF: {str(e)}"
        })


async def create_pdf_handler(
    input_str: str,
    user_id: str,
    supabase: SupabaseClient,
    request_id: Optional[str] = None
) -> str:
    """
    Handler function for the create_pdf action.

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
            "error": "Invalid JSON input. Expected: {title, content, content_type}"
        })

    return await create_pdf(params, user_id, supabase, request_id)


def create_create_pdf_action(
    user_id: str,
    supabase: SupabaseClient,
    request_id: Optional[str] = None
) -> Action:
    """
    Create the create_pdf action for the agent.

    Args:
        user_id: User ID
        supabase: Supabase client
        request_id: Optional request ID

    Returns:
        Action object configured for PDF creation
    """
    async def handler_wrapper(input_str: str) -> str:
        """Async wrapper for create_pdf_handler."""
        return await create_pdf_handler(input_str, user_id, supabase, request_id)

    return Action(
        name="create_pdf",
        description="Create a new PDF document containing a summary or report. Use this to generate documents from content you've gathered or created during the conversation.",
        parameters={
            "title": {
                "type": "string",
                "description": "Title for the PDF document"
            },
            "content": {
                "type": "string",
                "description": "The text content to include in the PDF. Supports basic markdown formatting (headers with #, bullet points with -)."
            },
            "content_type": {
                "type": "string",
                "description": "Type of document: 'summary' for brief summaries, 'report' for detailed reports. Default: 'summary'",
                "enum": ["summary", "report"]
            },
            "source_pdf_ids": {
                "type": "array",
                "description": "Optional list of PDF IDs that were used as sources for this document"
            }
        },
        returns="JSON object with success status, PDF ID, and filename. The PDF ID can be used with email_pdf to send the document.",
        handler=handler_wrapper
    )
