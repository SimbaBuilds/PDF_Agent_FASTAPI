"""
Primary Agent for PDF Agent Application

The main user-facing agent that handles chat interactions for PDF document assistance.
Provides tools for searching PDFs, creating documents, and emailing files.

Key Features:
- PDF content search (semantic and grep)
- PDF document generation (summaries/reports)
- Email PDF documents to recipients
- Web search via Perplexity
"""

import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.agents.base_agent import BaseAgent
from app.agents.models import Message, Action
from supabase import Client as SupabaseClient

from app.agents.tools.fetch_pdf_content import create_fetch_pdf_content_action
from app.agents.tools.create_pdf import create_create_pdf_action
from app.agents.tools.email_pdf import create_email_pdf_action
from app.agents.primary_agent.perplexity_tools import get_perplexity_search_action
from app.config.config import PDF_AGENT_LLM_MODEL, PDF_AGENT_MAX_TURNS

logger = logging.getLogger(__name__)


# System prompt for the PDF Agent
PDF_AGENT_CONTEXT = """You are a PDF document assistant that helps users interact with their uploaded PDF documents.

Your capabilities:
1. **Search PDFs**: Find and retrieve content from uploaded PDF documents using semantic search (for concepts/topics) or grep search (for exact text patterns)
2. **Create PDFs**: Generate summary or report documents from content you've gathered
3. **Web Search**: Search the web for additional information using Perplexity
4. **Email PDFs**: Send generated PDF documents to recipients via email

Important guidelines:
- When users ask about content in their PDFs, use fetch_pdf_content with semantic search for natural language queries
- Use grep search when looking for specific terms, codes, or exact phrases
- When users want a document emailed, you MUST ask for their name and email address before sending
- Keep responses concise unless the user asks for more detail
- Always cite which PDF/page the information came from when retrieving content"""

PDF_AGENT_INSTRUCTIONS = """
- Current date/time: {current_time}
- You have access to the user's uploaded PDF documents
- Use semantic search for questions like "what does the document say about X"
- Use grep search for specific terms or exact text matching
- When creating PDFs, include clear titles and well-organized content
- Always confirm email recipient details before sending"""


class PrimaryAgent(BaseAgent):
    """
    Primary agent for PDF document assistance.

    Handles user interactions and provides tools for:
    - Searching PDF content
    - Creating new PDF documents
    - Sending PDFs via email
    - Web search for additional information
    """

    def __init__(
        self,
        messages: List[Message],
        user_id: str,
        supabase: SupabaseClient,
        request_id: Optional[str] = None
    ):
        """
        Initialize the Primary Agent.

        Args:
            messages: Conversation history
            user_id: User ID
            supabase: Supabase client
            request_id: Optional request ID for tracking
        """
        self.user_id = user_id
        self.supabase = supabase
        self.request_id = request_id

        # Create the 4 PDF agent tools
        fetch_pdf_action = create_fetch_pdf_content_action(
            user_id=user_id,
            supabase=supabase,
            request_id=request_id
        )

        create_pdf_action = create_create_pdf_action(
            user_id=user_id,
            supabase=supabase,
            request_id=request_id
        )

        email_pdf_action = create_email_pdf_action(
            user_id=user_id,
            supabase=supabase,
            request_id=request_id
        )

        perplexity_action = get_perplexity_search_action(user_id=user_id)

        # Build instructions with current time
        instructions = PDF_AGENT_INSTRUCTIONS.format(
            current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        # Initialize base agent
        super().__init__(
            messages=messages,
            actions=[
                fetch_pdf_action,
                create_pdf_action,
                email_pdf_action,
                perplexity_action
            ],
            additional_context=PDF_AGENT_CONTEXT,
            general_instructions=instructions,
            model=PDF_AGENT_LLM_MODEL,
            max_turns=PDF_AGENT_MAX_TURNS,
            agent_name="PDF Agent"
        )

        logger.info(f"Initialized PDF Agent for user {user_id}")


async def get_chat_response(
    messages: List[Message],
    user_id: UUID = None,
    supabase: SupabaseClient = None,
    request_id: str = None,
    **kwargs
) -> tuple[str, bool, bool]:
    """
    Create the primary agent and get response for messages.

    Args:
        messages: List of chat messages
        user_id: User ID
        supabase: Supabase client
        request_id: Optional request ID for tracking
        **kwargs: Additional arguments (ignored for compatibility)

    Returns:
        Tuple of (response_text, is_complete, is_cancelled)
    """
    if not user_id:
        logger.error("No user_id provided to get_chat_response")
        return "Error: User authentication required", True, False

    if not supabase:
        logger.error("No supabase client provided to get_chat_response")
        return "Error: Database connection required", True, False

    try:
        # Create the PDF agent
        agent = PrimaryAgent(
            messages=messages,
            user_id=str(user_id),
            supabase=supabase,
            request_id=request_id
        )

        # Get response from agent
        response = await agent.get_response(messages)

        logger.info(f"PDF Agent response generated for request {request_id}")

        return response, True, False

    except Exception as e:
        logger.error(f"Error in PDF Agent: {str(e)}")
        return f"I encountered an error processing your request: {str(e)}", True, False
