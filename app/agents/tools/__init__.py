"""
Agent Tools Package

Contains tools for the PDF Agent including:
- fetch_pdf_content: Search and retrieve PDF content
- create_pdf: Generate PDF documents
- email_pdf: Send PDFs via email
"""

from app.agents.tools.fetch_pdf_content import (
    create_fetch_pdf_content_action,
    fetch_pdf_content_handler
)
from app.agents.tools.create_pdf import (
    create_create_pdf_action,
    create_pdf_handler
)
from app.agents.tools.email_pdf import (
    create_email_pdf_action,
    email_pdf_handler
)

__all__ = [
    'create_fetch_pdf_content_action',
    'fetch_pdf_content_handler',
    'create_create_pdf_action',
    'create_pdf_handler',
    'create_email_pdf_action',
    'email_pdf_handler',
]
