"""
Search PDF Documents Tool

Agent tool for searching PDF documents by filename and retrieving metadata.
Returns document information like ID, filename, number of pages, etc.
"""

import json
import logging
from typing import Dict, Any, Optional
from uuid import UUID

from supabase import Client as SupabaseClient

from app.agents.models import Action

logger = logging.getLogger(__name__)


async def search_pdf_documents(
    params: Dict[str, Any],
    user_id: str,
    supabase: SupabaseClient,
    request_id: Optional[str] = None
) -> str:
    """
    Search for PDF documents by filename.

    Args:
        params: Dictionary with:
            - filename_query: Search term for filename (required)
            - max_results: Maximum results (default: 10)
        user_id: User ID
        supabase: Supabase client
        request_id: Optional request ID for logging

    Returns:
        JSON string with document metadata
    """
    try:
        filename_query = params.get("filename_query", "")
        max_results = int(params.get("max_results", 10))

        if not filename_query:
            return json.dumps({
                "success": False,
                "error": "filename_query is required"
            })

        logger.info(f"Searching PDF documents for user {user_id}, query: {filename_query[:50]}...")

        # Query pdf_documents table
        query = supabase.from_('pdf_documents').select(
            'id, original_filename, title, num_pages, file_size_bytes, status, created_at'
        ).eq('user_id', user_id).eq('status', 'completed').ilike(
            'original_filename', f'%{filename_query}%'
        ).order('created_at', desc=True).limit(max_results)

        response = query.execute()

        if not response.data:
            return json.dumps({
                "success": True,
                "message": f"No PDF documents found matching '{filename_query}'",
                "query": filename_query,
                "total_results": 0,
                "documents": []
            })

        # Format results
        formatted_documents = []
        for doc in response.data:
            formatted_doc = {
                "document_id": str(doc.get('id')),
                "filename": doc.get('original_filename'),
                "title": doc.get('title'),
                "num_pages": doc.get('num_pages', 0),
                "file_size_bytes": doc.get('file_size_bytes', 0),
                "status": doc.get('status'),
                "created_at": doc.get('created_at')
            }
            formatted_documents.append(formatted_doc)

        logger.info(f"Found {len(formatted_documents)} PDF documents matching query")

        return json.dumps({
            "success": True,
            "query": filename_query,
            "total_results": len(formatted_documents),
            "documents": formatted_documents
        }, indent=2)

    except Exception as e:
        logger.error(f"Error searching PDF documents: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"Failed to search PDF documents: {str(e)}"
        })


async def search_pdf_documents_handler(
    input_str: str,
    user_id: str,
    supabase: SupabaseClient,
    request_id: Optional[str] = None
) -> str:
    """
    Handler function for the search_pdf_documents action.

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
        # Try to extract as simple query
        params = {"filename_query": input_str}

    return await search_pdf_documents(params, user_id, supabase, request_id)


def create_search_pdf_documents_action(
    user_id: str,
    supabase: SupabaseClient,
    request_id: Optional[str] = None
) -> Action:
    """
    Create the search_pdf_documents action for the agent.

    Args:
        user_id: User ID
        supabase: Supabase client
        request_id: Optional request ID

    Returns:
        Action object configured for PDF document search
    """
    async def handler_wrapper(input_str: str) -> str:
        """Async wrapper for search_pdf_documents_handler."""
        return await search_pdf_documents_handler(input_str, user_id, supabase, request_id)

    return Action(
        name="search_pdf_documents",
        description="Search for PDF documents by filename. Returns document metadata including document ID, filename, number of pages, and file size. Use this to find which PDFs are available before searching their content with fetch_pdf_content.",
        parameters={
            "filename_query": {
                "type": "string",
                "description": "Search term to match against PDF filenames (case-insensitive partial match)"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return. Default: 10"
            }
        },
        returns="JSON object with document metadata including document_id, filename, title, num_pages, file_size_bytes, status, and created_at",
        example='Action: search_pdf_documents: {"filename_query": "report"}',
        handler=handler_wrapper
    )
