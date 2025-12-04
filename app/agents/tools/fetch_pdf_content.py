"""
Fetch PDF Content Tool

Agent tool for searching and retrieving content from uploaded PDFs.
Supports semantic search (vector similarity) and grep search (text pattern matching).
"""

import json
import logging
from typing import Dict, Any, Optional
from uuid import UUID

from supabase import Client as SupabaseClient

from app.agents.models import Action
from app.services.semantic_search import semantic_search_service

logger = logging.getLogger(__name__)


async def fetch_pdf_content(
    params: Dict[str, Any],
    user_id: str,
    supabase: SupabaseClient,
    request_id: Optional[str] = None
) -> str:
    """
    Fetch content from uploaded PDFs.

    Args:
        params: Dictionary with:
            - search_type: "semantic" (default) or "grep"
            - query: Search query text
            - pdf_id: Optional PDF ID to limit search
            - max_results: Maximum results (default: 5)
        user_id: User ID
        supabase: Supabase client
        request_id: Optional request ID for logging

    Returns:
        JSON string with search results
    """
    try:
        search_type = params.get("search_type", "semantic").lower()
        query = params.get("query", "")
        pdf_id = params.get("pdf_id")
        max_results = int(params.get("max_results", 5))

        if not query:
            return json.dumps({
                "success": False,
                "error": "Query is required"
            })

        logger.info(f"Fetching PDF content for user {user_id}, search_type: {search_type}, query: {query[:50]}...")

        if search_type == "semantic":
            # Use vector similarity search
            results = semantic_search_service.search_pdf_pages_by_embedding(
                query=query,
                user_id=user_id,
                supabase=supabase,
                pdf_id=pdf_id,
                max_results=max_results
            )
        elif search_type == "grep":
            # Use text pattern matching
            results = semantic_search_service.search_pdf_pages_by_text(
                pattern=query,
                user_id=user_id,
                supabase=supabase,
                pdf_id=pdf_id,
                max_results=max_results
            )
        else:
            return json.dumps({
                "success": False,
                "error": f"Invalid search_type: {search_type}. Use 'semantic' or 'grep'."
            })

        if not results:
            # Try to provide helpful feedback
            return json.dumps({
                "success": True,
                "message": "No matching content found in the uploaded PDFs.",
                "results": [],
                "search_type": search_type,
                "query": query
            })

        # Format results for the agent
        formatted_results = []
        for result in results:
            content = result.get('content', '')
            # Truncate very long content for display
            if len(content) > 2000:
                content = content[:2000] + "... [truncated]"

            formatted_result = {
                "page_number": result.get('page_number'),
                "pdf_id": str(result.get('pdf_id')),
                "content": content
            }

            # Add search-type specific fields
            if search_type == "semantic":
                formatted_result["similarity_score"] = round(result.get('similarity', 0), 3)
            else:
                formatted_result["match_count"] = result.get('match_count', 0)

            formatted_results.append(formatted_result)

        logger.info(f"Found {len(formatted_results)} results for query")

        return json.dumps({
            "success": True,
            "search_type": search_type,
            "query": query,
            "total_results": len(formatted_results),
            "results": formatted_results
        }, indent=2)

    except Exception as e:
        logger.error(f"Error fetching PDF content: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"Failed to fetch PDF content: {str(e)}"
        })


async def fetch_pdf_content_handler(
    input_str: str,
    user_id: str,
    supabase: SupabaseClient,
    request_id: Optional[str] = None
) -> str:
    """
    Handler function for the fetch_pdf_content action.

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
        params = {"query": input_str, "search_type": "semantic"}

    return await fetch_pdf_content(params, user_id, supabase, request_id)


def create_fetch_pdf_content_action(
    user_id: str,
    supabase: SupabaseClient,
    request_id: Optional[str] = None
) -> Action:
    """
    Create the fetch_pdf_content action for the agent.

    Args:
        user_id: User ID
        supabase: Supabase client
        request_id: Optional request ID

    Returns:
        Action object configured for PDF content fetching
    """
    async def handler_wrapper(input_str: str) -> str:
        """Async wrapper for fetch_pdf_content_handler."""
        return await fetch_pdf_content_handler(input_str, user_id, supabase, request_id)

    return Action(
        name="fetch_pdf_content",
        description="Search and retrieve content from uploaded PDF documents. Use 'semantic' search for natural language queries about topics or concepts. Use 'grep' search for specific terms, codes, or exact text patterns.",
        parameters={
            "search_type": {
                "type": "string",
                "description": "Search method: 'semantic' for natural language similarity search, 'grep' for exact text pattern matching. Default: 'semantic'",
                "enum": ["semantic", "grep"]
            },
            "query": {
                "type": "string",
                "description": "Search query - for semantic: describe what you're looking for; for grep: the exact text pattern to find"
            },
            "pdf_id": {
                "type": "string",
                "description": "Optional: Specific PDF ID to search within. If not provided, searches all user's PDFs."
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return. Default: 5"
            }
        },
        returns="JSON object with search results containing page content, page numbers, and relevance scores",
        example='Action: fetch_pdf_content: {"search_type": "semantic", "query": "information about AI iterations and human intervention"}',
        handler=handler_wrapper
    )
