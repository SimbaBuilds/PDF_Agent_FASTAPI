"""
Base Service Module

Provides common utilities for service integrations including:
- HTTP request helpers
- Action creation
- Input parsing
- Error handling
"""

import json
import requests
from typing import Dict, Any, Optional, Callable
from app.agents.models import Action


class AuthenticationError(Exception):
    """Raised when authentication fails"""
    pass


class APIError(Exception):
    """Raised when an API request fails"""
    pass


def make_authenticated_request(
    method: str,
    url: str,
    headers: Dict[str, str],
    service_name: str,
    data: Optional[Dict[str, Any]] = None,
    timeout: int = 60
) -> Dict[str, Any]:
    """
    Make an authenticated HTTP request to a service.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        url: Request URL
        headers: Request headers including authentication
        service_name: Name of the service for error messages
        data: Request body data (for POST/PUT)
        timeout: Request timeout in seconds

    Returns:
        Response JSON as a dictionary

    Raises:
        AuthenticationError: If authentication fails
        APIError: If the request fails
    """
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=timeout)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=timeout)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=timeout)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=timeout)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        if response.status_code == 401:
            raise AuthenticationError(f"{service_name} authentication failed")
        elif response.status_code == 403:
            raise AuthenticationError(f"{service_name} access forbidden")
        elif response.status_code >= 400:
            error_detail = response.text[:200] if response.text else "Unknown error"
            raise APIError(f"{service_name} API error ({response.status_code}): {error_detail}")

        return response.json()

    except requests.exceptions.Timeout:
        raise APIError(f"{service_name} request timed out")
    except requests.exceptions.ConnectionError:
        raise APIError(f"Failed to connect to {service_name}")
    except json.JSONDecodeError:
        raise APIError(f"Invalid JSON response from {service_name}")


def parse_tool_input(input_str: str) -> Dict[str, Any]:
    """
    Parse tool input string into a dictionary.

    Args:
        input_str: Input string (can be JSON or key=value pairs)

    Returns:
        Parsed parameters as a dictionary
    """
    if not input_str:
        return {}

    # Try parsing as JSON first
    try:
        return json.loads(input_str)
    except json.JSONDecodeError:
        pass

    # Try parsing as key=value pairs
    params = {}
    for part in input_str.split(","):
        if "=" in part:
            key, value = part.split("=", 1)
            params[key.strip()] = value.strip().strip('"\'')

    return params


def create_service_action(
    name: str,
    description: str,
    parameters: Dict[str, Dict[str, str]],
    returns: str,
    handler_func: Callable,
    example: str = ""
) -> Action:
    """
    Create a service action for use by agents.

    Args:
        name: Action name
        description: Description of what the action does
        parameters: Dictionary of parameter definitions
        returns: Description of return value
        handler_func: Async function to handle the action
        example: Example usage string

    Returns:
        Action object configured for the service
    """
    return Action(
        name=name,
        description=description,
        parameters=parameters,
        returns=returns,
        handler=handler_func,
        example=example
    )
