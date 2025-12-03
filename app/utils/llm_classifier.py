"""
LLM Classifier for Service Type Prediction

This module provides a lightweight classifier that predicts relevant service types
based on user commands to optimize context injection in the integrations agent.
"""

import json
from typing import List, Optional
from app.agents.model_providers import OpenAIProvider, RetryConfig
from app.config import LLM_CLASSIFIER_MODEL, LLM_CLASSIFIER_TEMPERATURE, MAX_PREDICTED_SERVICE_TYPES
from app.utils.logging.component_loggers import get_agent_logger, log_agent_event
from supabase import Client as SupabaseClient

logger = get_agent_logger("LLM Classifier", __name__)


# Available service types (exact tag names from database)
AVAILABLE_SERVICE_TYPES = [
    "Project Management",
    "Task Management",
    "Team Collaboration",
    "Team Communication",
    "Video Conferencing",
    "Cloud Storage",
    "Task Scheduling",
    "Reminders",
    "Search",
    "AI",
    "Research",
    "Cloud Spreadsheets",
    "Cloud Text Documents",
    "Email",
    "Calendar",
    "SMS",
    "Text Message",
    "Note-Taking"
]


def build_classifier_prompt() -> str:
    """Build the system prompt for service type classification."""
    service_types_list = "\n".join([f"- {st}" for st in AVAILABLE_SERVICE_TYPES])

    return f"""You are a service type classifier. Given the chat agent's request to the integrations agent, predict which service types are most relevant.

Available service types (use exact names):
{service_types_list}

Instructions:
1. Analyze the request to understand the user's intent
2. Return ONLY the service type names that are directly relevant
3. Return at most {MAX_PREDICTED_SERVICE_TYPES} service types
4. Order by relevance (most relevant first)
5. Return as a JSON array of strings
6. If no service types are clearly relevant, return an empty array []

Return the JSON array only, no other text.

Examples:
- "Send an email to John about the meeting" → ["Email"]
- "Create a calendar event for tomorrow at 2pm" → ["Calendar"]
- "Add a task to my todo list and set a reminder" → ["Task Management", "Reminders"]
- "Text my friend about dinner plans" → ["SMS", "Text Message"]
- "Upload the document to the cloud" → ["Cloud Storage"]
- "Schedule a video call with the team" → ["Video Conferencing", "Calendar"]
- "Create a spreadsheet to track expenses" → ["Cloud Spreadsheets"]
- "Search for information about Python" → ["Search", "AI", "Research"]

"""


async def classify_service_types(
    command: str,
    user_id: Optional[str] = None,
    supabase: Optional[SupabaseClient] = None
) -> List[str]:
    """
    Classify a user command to predict relevant service types.

    Args:
        command: The user's command/request string
        user_id: Optional user ID for logging
        supabase: Optional Supabase client (not used currently but available for future enhancements)

    Returns:
        List of predicted service type names (exact matches from AVAILABLE_SERVICE_TYPES)
    """
    try:
        # Log classification attempt
        log_agent_event(
            logger,
            "Classifying command for service types",
            agent_name="LLM Classifier",
            user_id=user_id if user_id else "unknown",
            action="classify_start",
            command_preview=command[:100] if command else None
        )

        # Initialize the model provider with retry configuration
        retry_config = RetryConfig(max_retries=2, base_delay=0.5, enable_fallback=True)
        provider = OpenAIProvider(model=LLM_CLASSIFIER_MODEL, retry_config=retry_config)

        # Build messages for the classifier
        messages = [
            {
                "role": "system",
                "content": build_classifier_prompt(),
                "type": "text"
            },
            {
                "role": "user",
                "content": command,
                "type": "text"
            }
        ]

        # Get classification from the model
        response = provider.generate_response(messages, LLM_CLASSIFIER_TEMPERATURE)

        # Parse the response
        try:
            # Clean the response (remove any markdown formatting if present)
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()

            predicted_types = json.loads(cleaned_response)

            # Validate that we got a list
            if not isinstance(predicted_types, list):
                raise ValueError("Response is not a list")

            # Filter to only valid service types and limit count
            valid_predictions = [
                st for st in predicted_types
                if st in AVAILABLE_SERVICE_TYPES
            ][:MAX_PREDICTED_SERVICE_TYPES]

            # Log successful classification
            log_agent_event(
                logger,
                f"Successfully classified command into {len(valid_predictions)} service types",
                agent_name="LLM Classifier",
                user_id=user_id if user_id else "unknown",
                action="classify_success",
                predicted_types=valid_predictions,
                raw_predictions=predicted_types,
                command_preview=command[:100] if command else None
            )

            return valid_predictions

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse classifier response: {response}, error: {str(e)}")
            log_agent_event(
                logger,
                "Failed to parse classifier response",
                level="WARNING",
                agent_name="LLM Classifier",
                user_id=user_id if user_id else "unknown",
                action="parse_error",
                error=str(e),
                raw_response=response[:200]
            )
            return []

    except Exception as e:
        logger.error(f"Error in service type classification: {str(e)}")
        log_agent_event(
            logger,
            "Service type classification failed",
            level="ERROR",
            agent_name="LLM Classifier",
            user_id=user_id if user_id else "unknown",
            action="classify_error",
            error=str(e)
        )
        return []
