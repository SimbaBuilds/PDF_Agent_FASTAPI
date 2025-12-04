"""
PDF Agent Configuration

Configuration settings for the PDF Agent application.
"""

import os

# Model Definitions
SONNET_4_5 = "claude-sonnet-4-5-20250929"  # $3,$15/M I/O
HAIKU_4_5 = "claude-haiku-4-5-20251001"
O3MINI = "o3-mini-2025-01-31"  # $1,$5/M I/O
GPT_4_1 = "gpt-4.1-2025-04-14"  # ROUGHLY $.1,$.5/M I/O
GPT_4_1_MINI = "gpt-4.1-mini-2025-04-14"  # ROUGHLY $.01,$.05/M I/O
GPT_4_1_NANO = "gpt-4.1-nano-2025-04-14"  # ROUGHLY $.001,$.005/M I/O
GEMINI_2_5_PRO = "gemini-2.5-pro"  # $1.25,$5/M I/O
GEMINI_2_5_FLASH = "gemini-2.5-flash"  # $0.075,$0.30/M I/O

# Cache Configuration
CACHE_CONTENT_THRESHOLD = 1000
CACHE_MAX_CHARS = 15000  # Maximum characters to store in cache
USE_ONE_HOUR_CACHE = True  # Use 1-hour cache TTL (2x write cost) vs 5-minute (1.25x write cost)

# System Configuration
SYSTEM_MODEL = SONNET_4_5
THIRD_PARTY_SERVICE_TIMEOUT = 240  # seconds
SERVICE_TOOL_DEFAULT_TIMEOUT = 240  # seconds - default timeout for service tools
SERVICE_TOOL_MAX_TIMEOUT = 3600  # seconds - maximum allowed timeout


# PDF Agent Configuration
PDF_AGENT_LLM_MODEL = SONNET_4_5
PDF_AGENT_MAX_TURNS = 8
PDF_SIMILARITY_THRESHOLD = 0.3  # Minimum similarity score for semantic search
PDF_SEMANTIC_SEARCH_MAX_RESULTS = 5  # Max results from semantic search
PDF_MAX_FILE_SIZE_MB = 50  # Maximum PDF file size in MB

# Email Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL")

# Legacy aliases for backwards compatibility (used by other parts of the app)
PRIMARY_AGENT_LLM_MODEL = PDF_AGENT_LLM_MODEL
PRIMARY_AGENT_MAX_TURNS = PDF_AGENT_MAX_TURNS
PRIMARY_AGENT_SIMILARITY_THRESHOLD = PDF_SIMILARITY_THRESHOLD
PRIMARY_AGENT_SEMANTIC_SEARCH_MAX_RESULTS = PDF_SEMANTIC_SEARCH_MAX_RESULTS
PRIMARY_AGENT_SS_TRUNC_THRESHOLD = 200
PRIMARY_AGENT_TAG_NAME = "PDF Agent"

# Web App Configuration
WEB_APP_URL = os.getenv("WEB_APP_URL", "http://localhost:3000")

# LLM Classifier Configuration
LLM_CLASSIFIER_MODEL = GPT_4_1_MINI
LLM_CLASSIFIER_TEMPERATURE = 0.1
MAX_PREDICTED_SERVICE_TYPES = 5

# Intelligence Model Map (maps intelligence levels to model names)
INTELLIGENCE_MODEL_MAP = {
    "low": HAIKU_4_5,
    "medium": SONNET_4_5,
    "high": SONNET_4_5,
    "default": HAIKU_4_5,
}





