"""
Supabase configuration for different environments with optimized connection pooling
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ConnectionPoolConfig:
    """Configuration for connection pooling"""
    max_connections: int
    max_keepalive_connections: int
    keepalive_expiry: float  # seconds
    connect_timeout: float  # seconds
    read_timeout: float  # seconds
    write_timeout: float  # seconds
    pool_timeout: float  # seconds


@dataclass
class SupabaseConfig:
    """Supabase client configuration"""
    url: str
    service_role_key: str
    jwt_secret: str
    pool_config: ConnectionPoolConfig
    query_timeout: int  # seconds
    retry_attempts: int


# Environment-specific connection pool configurations
DEV_POOL_CONFIG = ConnectionPoolConfig(
    max_connections=20,
    max_keepalive_connections=5,
    keepalive_expiry=30.0,
    connect_timeout=10.0,
    read_timeout=15.0,
    write_timeout=15.0,
    pool_timeout=10.0
)

STAGING_POOL_CONFIG = ConnectionPoolConfig(
    max_connections=50,
    max_keepalive_connections=15,
    keepalive_expiry=60.0,
    connect_timeout=10.0,
    read_timeout=15.0,
    write_timeout=15.0,
    pool_timeout=10.0
)

PROD_POOL_CONFIG = ConnectionPoolConfig(
    max_connections=100,
    max_keepalive_connections=30,
    keepalive_expiry=120.0,
    connect_timeout=10.0,
    read_timeout=15.0,
    write_timeout=15.0,
    pool_timeout=15.0
)


def get_pool_config() -> ConnectionPoolConfig:
    """Get connection pool configuration based on environment"""
    env = os.getenv("ENV", "DEV").upper()
    
    if env == "PROD":
        return PROD_POOL_CONFIG
    elif env == "STAGING":
        return STAGING_POOL_CONFIG
    else:  # DEV or any other environment
        return DEV_POOL_CONFIG


def get_supabase_config() -> SupabaseConfig:
    """Get complete Supabase configuration"""
    
    # Get required environment variables
    url = os.getenv("SUPABASE_URL")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    
    if not url:
        raise ValueError("SUPABASE_URL environment variable is required")
    if not service_role_key:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY environment variable is required")
    if not jwt_secret:
        raise ValueError("SUPABASE_JWT_SECRET environment variable is required")
    
    # Strip quotes that might be in environment variables
    url = url.strip('"').strip("'")
    service_role_key = service_role_key.strip('"').strip("'")
    jwt_secret = jwt_secret.strip('"').strip("'")
    
    return SupabaseConfig(
        url=url,
        service_role_key=service_role_key,
        jwt_secret=jwt_secret,
        pool_config=get_pool_config(),
        query_timeout=15,  # seconds
        retry_attempts=3
    )