"""
PDF Generator Service

Service for generating PDF documents from content.
Uses ReportLab for PDF creation.
"""

import io
import logging
import time
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

from supabase import Client as SupabaseClient

logger = logging.getLogger(__name__)


class PDFGeneratorService:
    """
    Service for generating PDF documents.

    Supports creating summaries and reports from text/markdown content.
    """

    def __init__(self):
        """Initialize the PDF generator service."""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        logger.info("Initialized PDF generator service")

    def _setup_custom_styles(self) -> None:
        """Set up custom paragraph styles."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1a1a1a')
        ))

        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#666666')
        ))

        # Body text style
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=16,
            spaceAfter=12,
            alignment=TA_JUSTIFY,
            textColor=colors.HexColor('#333333')
        ))

        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#2c3e50')
        ))

    def generate_pdf(
        self,
        title: str,
        content: str,
        content_type: str = "summary",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Generate a PDF document from content.

        Args:
            title: Document title
            content: Text or markdown content to include
            content_type: Type of document ("summary" or "report")
            metadata: Optional metadata to include

        Returns:
            PDF file as bytes
        """
        start_time = time.time()
        logger.info(f"Generating PDF: {title}, type: {content_type}")

        buffer = io.BytesIO()

        # Create the PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        # Build the story (content elements)
        story = []

        # Add title
        story.append(Paragraph(self._escape_html(title), self.styles['CustomTitle']))

        # Add subtitle with date and type
        date_str = datetime.now().strftime("%B %d, %Y")
        type_label = content_type.capitalize()
        story.append(Paragraph(
            f"{type_label} - Generated {date_str}",
            self.styles['CustomSubtitle']
        ))

        story.append(Spacer(1, 0.5 * inch))

        # Process and add content
        paragraphs = self._parse_content(content)
        for para_type, para_text in paragraphs:
            if para_type == 'header':
                story.append(Paragraph(
                    self._escape_html(para_text),
                    self.styles['SectionHeader']
                ))
            elif para_type == 'body':
                story.append(Paragraph(
                    self._escape_html(para_text),
                    self.styles['CustomBody']
                ))
            elif para_type == 'spacer':
                story.append(Spacer(1, 0.2 * inch))

        # Build the PDF
        doc.build(story)

        # Get the PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()

        duration = time.time() - start_time
        logger.info(f"Generated PDF ({len(pdf_bytes)} bytes) in {duration:.2f}s")

        return pdf_bytes

    def _parse_content(self, content: str) -> list:
        """
        Parse content into structured paragraphs.

        Handles basic markdown-style formatting.

        Args:
            content: Raw content text

        Returns:
            List of (type, text) tuples
        """
        paragraphs = []
        lines = content.split('\n')

        current_para = []

        for line in lines:
            line = line.strip()

            if not line:
                # Empty line - flush current paragraph
                if current_para:
                    paragraphs.append(('body', ' '.join(current_para)))
                    current_para = []
                    paragraphs.append(('spacer', ''))
            elif line.startswith('# '):
                # Header level 1
                if current_para:
                    paragraphs.append(('body', ' '.join(current_para)))
                    current_para = []
                paragraphs.append(('header', line[2:]))
            elif line.startswith('## '):
                # Header level 2
                if current_para:
                    paragraphs.append(('body', ' '.join(current_para)))
                    current_para = []
                paragraphs.append(('header', line[3:]))
            elif line.startswith('### '):
                # Header level 3
                if current_para:
                    paragraphs.append(('body', ' '.join(current_para)))
                    current_para = []
                paragraphs.append(('header', line[4:]))
            elif line.startswith('- ') or line.startswith('* '):
                # Bullet point
                if current_para:
                    paragraphs.append(('body', ' '.join(current_para)))
                    current_para = []
                paragraphs.append(('body', f"• {line[2:]}"))
            else:
                # Regular text - accumulate
                current_para.append(line)

        # Flush any remaining paragraph
        if current_para:
            paragraphs.append(('body', ' '.join(current_para)))

        return paragraphs

    def _escape_html(self, text: str) -> str:
        """
        Escape HTML special characters for ReportLab.

        Args:
            text: Raw text

        Returns:
            Escaped text safe for ReportLab
        """
        # ReportLab uses XML-style escaping
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        return text

    async def create_and_store_pdf(
        self,
        title: str,
        content: str,
        content_type: str,
        user_id: str,
        supabase: SupabaseClient,
        source_pdf_ids: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Create a PDF and store it in Supabase storage.

        Args:
            title: Document title
            content: Content to include
            content_type: "summary" or "report"
            user_id: User ID
            supabase: Supabase client
            source_pdf_ids: Optional list of source PDF IDs

        Returns:
            Dictionary with pdf_id, storage_path, and success status
        """
        try:
            # Generate the PDF
            pdf_bytes = self.generate_pdf(title, content, content_type)

            # Create unique filename
            pdf_id = uuid4()
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_title = safe_title[:50]  # Limit length
            filename = f"{safe_title}_{pdf_id}.pdf"
            storage_path = f"generated_pdfs/{user_id}/{filename}"

            # Upload to Supabase storage
            upload_result = supabase.storage.from_('pdfs').upload(
                storage_path,
                pdf_bytes,
                file_options={"content-type": "application/pdf"}
            )

            if not upload_result:
                raise ValueError("Failed to upload PDF to storage")

            # Record in database
            record_data = {
                'id': str(pdf_id),
                'user_id': user_id,
                'title': title,
                'content_type': content_type,
                'source_pdf_ids': source_pdf_ids or [],
                'storage_path': storage_path,
                'created_at': datetime.now().isoformat()
            }

            result = supabase.from_('generated_pdfs').insert(record_data).execute()

            if not result.data:
                logger.warning(f"Failed to record generated PDF in database")

            logger.info(f"Created and stored PDF: {pdf_id}")

            return {
                'success': True,
                'pdf_id': str(pdf_id),
                'storage_path': storage_path,
                'filename': filename,
                'size_bytes': len(pdf_bytes)
            }

        except Exception as e:
            logger.error(f"Failed to create and store PDF: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def get_pdf_download_url(
        self,
        pdf_id: str,
        user_id: str,
        supabase: SupabaseClient,
        expires_in: int = 3600
    ) -> Optional[str]:
        """
        Get a signed download URL for a generated PDF.

        Args:
            pdf_id: ID of the generated PDF
            user_id: User ID for verification
            supabase: Supabase client
            expires_in: URL expiration time in seconds

        Returns:
            Signed URL or None if not found
        """
        try:
            # Get the PDF record
            result = supabase.from_('generated_pdfs').select('storage_path').eq(
                'id', pdf_id
            ).eq('user_id', user_id).execute()

            if not result.data:
                logger.warning(f"PDF {pdf_id} not found for user {user_id}")
                return None

            storage_path = result.data[0]['storage_path']

            # Generate signed URL
            signed_url = supabase.storage.from_('pdfs').create_signed_url(
                storage_path,
                expires_in
            )

            return signed_url.get('signedURL') if signed_url else None

        except Exception as e:
            logger.error(f"Failed to get PDF download URL: {str(e)}")
            return None

    async def get_pdf_bytes(
        self,
        pdf_id: str,
        user_id: str,
        supabase: SupabaseClient
    ) -> Optional[bytes]:
        """
        Download PDF bytes from storage.

        Args:
            pdf_id: ID of the generated PDF
            user_id: User ID for verification
            supabase: Supabase client

        Returns:
            PDF bytes or None if not found
        """
        try:
            # Get the PDF record
            result = supabase.from_('generated_pdfs').select('storage_path').eq(
                'id', pdf_id
            ).eq('user_id', user_id).execute()

            if not result.data:
                logger.warning(f"PDF {pdf_id} not found for user {user_id}")
                return None

            storage_path = result.data[0]['storage_path']

            # Download the file
            pdf_bytes = supabase.storage.from_('pdfs').download(storage_path)

            return pdf_bytes

        except Exception as e:
            logger.error(f"Failed to download PDF: {str(e)}")
            return None


# Global instance
pdf_generator_service = PDFGeneratorService()
