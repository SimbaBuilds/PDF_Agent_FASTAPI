"""
Perplexity AI API Tools

Provides Perplexity AI functionality for AI agents including:
- Perform web searches with AI-powered answers
- Ask questions with real-time information
- Generate responses with citations
- Handle different search modes and models
"""

import json
import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from app.agents.models import Action
from app.agents.primary_agent.base_service import (
    make_authenticated_request,
    create_service_action,
    parse_tool_input,
    AuthenticationError,
    APIError
)
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

async def increment_perplexity_usage(user_id: UUID) -> None:
    """Increment user's monthly Perplexity usage counter with cost tracking"""
    try:
        from app.auth import get_supabase_client
        from app.services.stripe_service import stripe_service
        supabase = await get_supabase_client()
        
        # Increment perplexity_usage_month for the user with automatic cost calculation
        result = supabase.rpc(
            'increment_user_usage_auto_cost',
            {
                'user_id': str(user_id),
                'usage_type': 'perplexity_usage_month'
            }
        ).execute()
        
        if result.data is None:
            logger.error(f"Failed to increment Perplexity usage for user {user_id}")
        else:
            logger.info(f"Incremented Perplexity usage and cost for user {user_id}")
            
            # Send Stripe meter event for Perplexity usage
            try:
                # Get user profile to get stripe_customer_id
                profile_result = supabase.from_('user_profiles').select('stripe_customer_id').eq('id', str(user_id)).execute()
                if profile_result.data and profile_result.data[0].get('stripe_customer_id'):
                    stripe_customer_id = profile_result.data[0]['stripe_customer_id']
                    await stripe_service.send_perplexity_event(
                        stripe_customer_id=stripe_customer_id,
                        user_id=user_id
                    )
                else:
                    logger.warning(f"No Stripe customer ID found for user {user_id} - skipping Perplexity meter event")
            except Exception as stripe_error:
                logger.error(f"Error sending Stripe meter event for Perplexity usage user {user_id}: {str(stripe_error)}")
                # Don't re-raise - Stripe failures shouldn't block the request
            
    except Exception as e:
        logger.error(f"Error incrementing Perplexity usage for user {user_id}: {str(e)}")

BASE_URL = "https://api.perplexity.ai"

async def search_web(params: Dict[str, Any], user_id: UUID = None) -> str:
    """Perform a web search with Perplexity AI"""
    try:
        # Check UBP limits before making API call
        if user_id:
            from app.auth import get_supabase_client, check_ubp_limits
            supabase = await get_supabase_client()
            
            try:
                # Get user profile for UBP checking
                profile_result = supabase.from_('user_profiles').select('ubp_current, ubp_max').eq('id', str(user_id)).execute()
                if profile_result.data:
                    user_profile = profile_result.data[0]
                    ubp_check = check_ubp_limits(user_profile)
                    
                    if not ubp_check['can_proceed']:
                        from app.config import WEB_APP_URL
                        return f"The user has reached their usage limit, please notify them and let them know they can manage their account in the web app at {WEB_APP_URL}."
            except Exception as limit_error:
                logger.error(f"Error checking UBP limits for user {user_id}: {str(limit_error)}")
                # Continue with request if limit check fails (fail-open)
        
        # Get API key from environment variables
        api_key = os.getenv("PERPLEXITY_API_KEY")
        if not api_key:
            return "Error: No Perplexity API key found in environment variables"
        
        query = params.get("query", "")
        if not query:
            return "Error: query is required"
            
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": params.get("model", "sonar"),
            "messages": [
                {
                    "role": "system",
                    "content": params.get("system_prompt", "Be precise and informative. Provide accurate, up-to-date information with proper citations.")
                },
                {
                    "role": "user", 
                    "content": query
                }
            ],
            "max_tokens": min(int(params.get("max_tokens", 2000)), 3000),
            "temperature": float(params.get("temperature", 0.2)),
            "top_p": float(params.get("top_p", 0.9)),
            "search_domain_filter": params.get("search_domain_filter", []),
            "return_images": params.get("return_images", False),
            "return_related_questions": params.get("return_related_questions", False),
            "search_recency_filter": params.get("search_recency_filter", "month"),
            "top_k": int(params.get("top_k", 0)),
            "stream": False,
            "presence_penalty": float(params.get("presence_penalty", 0)),
            "frequency_penalty": float(params.get("frequency_penalty", 1))
        }
        
        response = make_authenticated_request(
            "POST",
            f"{BASE_URL}/chat/completions",
            headers,
            "Perplexity",
            data
        )
        
        if not response.get("choices"):
            return "No response received from Perplexity"
            
        choice = response["choices"][0]
        message = choice.get("message", {})
        content = message.get("content", "")
        
        result = {
            "answer": content,
            "model": response.get("model", ""),
            "usage": response.get("usage", {}),
            "citations": response.get("citations", []),
            "images": response.get("images", []) if params.get("return_images") else [],
            "related_questions": response.get("related_questions", []) if params.get("return_related_questions") else []
        }
        
        # Increment usage counter on successful query
        if user_id:
            await increment_perplexity_usage(user_id)
        
        return json.dumps(result, indent=2)
        
    except (AuthenticationError, APIError) as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error performing search: {str(e)}"

# Action handlers
async def search_web_handler(input_str: str, user_id: str = None) -> str:
    params = parse_tool_input(input_str)
    user_uuid = UUID(user_id) if user_id else None
    return await search_web(params, user_uuid)


def get_perplexity_search_action(user_id: str = None) -> Action:
    """Get the Perplexity search action for the PDF agent."""
    return create_service_action(
        name="perplexity_search",
        description="Perform a general web search using Perplexity AI. Use this to find information that may not be in the uploaded PDFs.",
        parameters={
            "query": {"type": "string", "description": "Search query"},
            "max_tokens": {"type": "integer", "description": "Maximum tokens (default: 2000, max: 4000)"},
            "temperature": {"type": "number", "description": "Temperature (0.0-2.0, default: 0.1)"},
            "system_prompt": {"type": "string", "description": "System prompt for the model"}
        },
        returns="JSON object with search results and citations",
        handler_func=lambda input_str: search_web_handler(input_str, user_id),
        example='Action: perplexity_search: {"query": "latest research on renewable energy"}'
    )