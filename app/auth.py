"""
Authentication Module

Provides authentication and authorization utilities for the PDF Agent API.
Handles JWT token validation and user extraction from Supabase Auth.
"""

import os
import logging
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, Depends
from jose import jwt, JWTError
from supabase import Client as SupabaseClient

from app.utils.supabase_singleton import get_supabase_client as get_singleton_client

logger = logging.getLogger(__name__)


async def get_current_user(request: Request) -> str:
    """
    Extract user_id from Authorization header JWT.

    Args:
        request: FastAPI request object

    Returns:
        User ID string from JWT payload

    Raises:
        HTTPException: If token is missing or invalid
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header"
        )

    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected 'Bearer <token>'"
        )

    token = auth_header.replace("Bearer ", "")

    try:
        # Get JWT secret from environment
        jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
        if not jwt_secret:
            logger.error("SUPABASE_JWT_SECRET not configured")
            raise HTTPException(
                status_code=500,
                detail="Server authentication configuration error"
            )

        # Decode and validate the JWT
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            audience="authenticated"
        )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid token: missing user ID"
            )

        return user_id

    except JWTError as e:
        logger.warning(f"JWT validation failed: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )


async def get_supabase_client() -> SupabaseClient:
    """
    Get the singleton Supabase client.

    Returns:
        Supabase client instance
    """
    return get_singleton_client()


def check_user_limits(user_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if user can proceed based on usage limits.

    Args:
        user_profile: User profile data from database

    Returns:
        Dictionary with:
        - can_proceed: Boolean indicating if user can continue
        - reason: Optional string explaining why they can't proceed
    """
    # For PDF agent, we use a simplified limit check
    # Can be expanded later for tiered access

    ubp_current = user_profile.get('ubp_current', 0)
    ubp_max = user_profile.get('ubp_max', 1000)

    if ubp_current >= ubp_max:
        return {
            'can_proceed': False,
            'reason': 'Usage limit reached'
        }

    return {
        'can_proceed': True,
        'reason': None
    }


async def check_ubp_limits(user_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Async version of check_user_limits for compatibility.

    Args:
        user_profile: User profile data from database

    Returns:
        Dictionary with can_proceed and reason
    """
    return check_user_limits(user_profile)
