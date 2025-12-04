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
from app.agents.tools.perplexity_tools import get_perplexity_search_action
from app.config.config import PDF_AGENT_LLM_MODEL, PDF_AGENT_MAX_TURNS

logger = logging.getLogger(__name__)


# System prompt for the PDF Agent
PDF_AGENT_CONTEXT = """You are a helpful AI assistant. Your capabilties are outlined in the tool descriptions below.
"""
PDF_AGENT_INSTRUCTIONS = """
- Current date/time: {current_time}
Guidelines:
- Keep responses concise unless the user asks for more detail
- Always cite which PDF/page the information came from when retrieving content
"""

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
        response = await agent.query(messages, user_id, request_id, supabase)

        logger.info(f"PDF Agent response generated for request {request_id}")

        return response, True, False

    except Exception as e:
        logger.error(f"Error in PDF Agent: {str(e)}")
        return f"I encountered an error processing your request: {str(e)}", True, False
