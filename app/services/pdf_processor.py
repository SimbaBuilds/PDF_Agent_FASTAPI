"""
PDF Processing Service

Service for processing PDF files and converting them into database records
with text extraction and embedding generation.
"""

import io
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID, uuid4
from datetime import datetime
import requests
import PyPDF2
from pdf2image import convert_from_bytes
from supabase import Client as SupabaseClient

from app.services.ocr_processor import ocr_processor
from app.services.semantic_search import semantic_search_service
from app.utils.logging.component_loggers import get_api_logger

logger = get_api_logger(__name__)


class PDFProcessor:
    """
    Service for processing PDF files and storing them in the database.

    Features:
    - PDF text extraction with OCR fallback
    - Page-by-page chunking
    - Automatic embedding generation via queue
    """

    def __init__(self):
        """Initialize the PDF processor."""
        self.supported_types = ['pdf']
        self.text_threshold = 200  # Minimum characters for PDF text extraction

        logger.info("Initialized PDF processor")

    async def process_pdfs(
        self,
        file_metadata_list: List[Dict[str, Any]],
        user_id: str,
        supabase: SupabaseClient
    ) -> Dict[str, Any]:
        """
        Process a list of PDF files.

        Args:
            file_metadata_list: List of file metadata objects with URLs, types, sizes
            user_id: User ID for the records
            supabase: Supabase client

        Returns:
            Processing results summary
        """
        results = {
            'processed_pdfs': [],
            'failed_pdfs': [],
            'total_pages': 0,
            'total_files': len(file_metadata_list)
        }

        logger.info(f"Starting processing of {len(file_metadata_list)} PDFs for user {user_id}")

        for file_metadata in file_metadata_list:
            try:
                record_result = await self._process_single_file(file_metadata, user_id, supabase)

                if record_result['success']:
                    results['processed_pdfs'].append(record_result)
                    results['total_pages'] += record_result['num_pages']
                else:
                    results['failed_pdfs'].append({
                        'file_metadata': file_metadata,
                        'error': record_result['error']
                    })

            except Exception as e:
                logger.error(f"Error processing PDF {file_metadata.get('filename', 'unknown')}: {str(e)}")
                results['failed_pdfs'].append({
                    'file_metadata': file_metadata,
                    'error': str(e)
                })

        logger.info(f"Processing complete: {len(results['processed_pdfs'])} successful, {len(results['failed_pdfs'])} failed")
        return results

    async def _process_single_file(
        self,
        file_metadata: Dict[str, Any],
        user_id: str,
        supabase: SupabaseClient,
        existing_record_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Process a single medical record file.

        Args:
            file_metadata: File metadata with URL, type, size, etc.
            user_id: User ID
            supabase: Supabase client

        Returns:
            Processing result
        """
        start_time = time.time()

        # Extract file information
        file_url = file_metadata.get('url')
        file_type = file_metadata.get('file_type', '').lower()
        original_filename = file_metadata.get('filename')
        file_size = file_metadata.get('size_bytes')

        logger.info(f"Processing file: {original_filename}, type: {file_type}, size: {file_size}")

        try:
            # Validate file type
            if file_type not in self.supported_types:
                raise ValueError(f"Unsupported file type: {file_type}")

            # Download file
            file_data = await self._download_file(file_url)

            # Extract pages based on file type
            pages = await self._extract_pages(file_data, file_type, original_filename)

            if not pages:
                raise ValueError("No content could be extracted from file")

            # Use existing record ID if provided, otherwise create new record
            if existing_record_id:
                record_id = existing_record_id
                logger.info(f"Using existing medical record {record_id}")
            else:
                # Create medical record in database
                record_id = await self._create_pdf_record(
                    user_id=user_id,
                    title=original_filename or f"PDF Document {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    original_file_type=file_type,
                    original_filename=original_filename,
                    file_size_bytes=file_size,
                    num_pages=len(pages),
                    upload_url=file_url,
                    supabase=supabase
                )

            # Create page records and collect embedding jobs for batch processing
            page_ids = []
            embedding_jobs = []

            for page_num, page_content in enumerate(pages, 1):
                page_id = await self._create_record_page(
                    user_id=user_id,
                    medical_record_id=record_id,
                    page_number=page_num,
                    content=page_content,
                    supabase=supabase
                )
                page_ids.append(page_id)

                # Collect embedding job data for batch processing
                embedding_jobs.append({
                    'record_page_id': str(page_id),
                    'content': page_content
                })

            # Batch queue all embedding jobs in a single database operation
            if embedding_jobs:
                embedding_queued = await semantic_search_service.batch_queue_embedding_jobs_for_record_pages(
                    page_jobs=embedding_jobs,
                    user_id=user_id,
                    supabase=supabase
                )

                if not embedding_queued:
                    logger.warning(f"Failed to batch queue {len(embedding_jobs)} embedding jobs for record {record_id}")

            # Update medical record status to completed
            await self._update_medical_record_status(record_id, 'completed', supabase)

            duration = time.time() - start_time
            logger.info(f"Successfully processed file {original_filename} in {duration:.2f}s")

            return {
                'success': True,
                'record_id': record_id,
                'num_pages': len(pages),
                'page_ids': page_ids,
                'processing_time': duration
            }

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Failed to process file {original_filename}: {str(e)}")

            # If we created a record, mark it as failed
            if 'record_id' in locals():
                await self._update_medical_record_status(record_id, 'failed', supabase)

            return {
                'success': False,
                'error': str(e),
                'processing_time': duration
            }

    async def _download_file(self, file_url: str) -> bytes:
        """Download file from URL."""
        logger.debug(f"Downloading file from: {file_url}")

        try:
            response = requests.get(file_url, timeout=30)
            response.raise_for_status()
            return response.content
        except Exception as e:
            raise ValueError(f"Failed to download file: {str(e)}")

    async def _extract_pages(self, file_data: bytes, file_type: str, filename: str) -> List[str]:
        """Extract text content from PDF file."""
        if file_type == 'pdf':
            return await self._process_pdf(file_data)
        else:
            raise ValueError(f"Unsupported file type: {file_type}. Only PDF files are supported.")

    async def _process_pdf(self, pdf_data: bytes) -> List[str]:
        """Process PDF file and extract text from each page."""
        pages = []

        try:
            # Try text extraction first
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))

            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    # Extract text
                    text = page.extract_text()

                    if text and len(text.strip()) >= self.text_threshold:
                        # Sufficient text extracted
                        pages.append(text.strip())
                        logger.debug(f"PDF page {page_num + 1}: extracted {len(text)} characters via text extraction")
                    else:
                        # Insufficient text, use OCR
                        logger.info(f"PDF page {page_num + 1}: text extraction insufficient ({len(text)} chars), using OCR")

                        # Convert PDF page to image for OCR
                        page_images = convert_from_bytes(
                            pdf_data,
                            first_page=page_num + 1,
                            last_page=page_num + 1,
                            dpi=300
                        )

                        if page_images:
                            ocr_text = ocr_processor.extract_text_from_pil_image(page_images[0])
                            if ocr_text:
                                pages.append(ocr_text)
                                logger.debug(f"PDF page {page_num + 1}: extracted {len(ocr_text)} characters via OCR")
                            else:
                                logger.warning(f"PDF page {page_num + 1}: OCR failed, skipping page")
                        else:
                            logger.warning(f"PDF page {page_num + 1}: failed to convert to image for OCR")

                except Exception as e:
                    logger.error(f"Error processing PDF page {page_num + 1}: {str(e)}")
                    continue

        except Exception as e:
            raise ValueError(f"Failed to process PDF: {str(e)}")

        return pages

    async def _create_pdf_record(
        self,
        user_id: str,
        title: str,
        original_file_type: str,
        original_filename: Optional[str],
        file_size_bytes: Optional[int],
        num_pages: int,
        upload_url: Optional[str],
        supabase: SupabaseClient
    ) -> UUID:
        """Create medical record in database."""
        try:
            record_data = {
                'id': str(uuid4()),
                'user_id': user_id,
                'title': title,
                'original_file_type': original_file_type,
                'original_filename': original_filename,
                'file_size_bytes': file_size_bytes,
                'num_pages': num_pages,
                'status': 'processing',
                'upload_url': upload_url,
                'metadata': {},
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            result = supabase.from_('medical_records').insert(record_data).execute()

            if result.data:
                record_id = UUID(result.data[0]['id'])
                logger.info(f"Created medical record {record_id}")
                return record_id
            else:
                raise ValueError("Failed to create medical record")

        except Exception as e:
            raise ValueError(f"Database error creating medical record: {str(e)}")

    async def _create_record_page(
        self,
        user_id: str,
        medical_record_id: UUID,
        page_number: int,
        content: str,
        supabase: SupabaseClient
    ) -> UUID:
        """Create record page in database."""
        try:
            page_data = {
                'id': str(uuid4()),
                'user_id': user_id,
                'medical_record_id': str(medical_record_id),
                'page_number': page_number,
                'content': content,
                'processed_at': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            result = supabase.from_('record_pages').insert(page_data).execute()

            if result.data:
                page_id = UUID(result.data[0]['id'])
                logger.debug(f"Created record page {page_id} for medical record {medical_record_id}")
                return page_id
            else:
                raise ValueError("Failed to create record page")

        except Exception as e:
            raise ValueError(f"Database error creating record page: {str(e)}")

    async def _update_medical_record_status(
        self,
        record_id: UUID,
        status: str,
        supabase: SupabaseClient
    ) -> None:
        """Update medical record status."""
        try:
            result = supabase.from_('medical_records').update({
                'status': status,
                'updated_at': datetime.now().isoformat()
            }).eq('id', str(record_id)).execute()

            if not result.data:
                logger.warning(f"Failed to update status for medical record {record_id}")
            else:
                logger.info(f"Updated medical record {record_id} status to {status}")

        except Exception as e:
            logger.error(f"Error updating medical record status: {str(e)}")

    async def create_placeholder_records(
        self,
        file_metadata_list: List[Dict[str, Any]],
        user_id: str,
        supabase: SupabaseClient
    ) -> List[UUID]:
        """
        Create placeholder medical records for immediate response.

        Args:
            file_metadata_list: List of file metadata objects
            user_id: User ID for the records
            supabase: Supabase client

        Returns:
            List of created record IDs
        """
        record_ids = []

        logger.info(f"Creating {len(file_metadata_list)} placeholder medical records for user {user_id}")

        for file_metadata in file_metadata_list:
            try:
                record_id = uuid4()

                record_data = {
                    'id': str(record_id),
                    'user_id': user_id,
                    'title': file_metadata.get('filename', 'Medical Record'),
                    'original_file_type': file_metadata.get('file_type'),
                    'original_filename': file_metadata.get('filename'),
                    'file_size_bytes': file_metadata.get('size_bytes'),
                    'num_pages': 0,  # Will be updated during processing
                    'status': 'processing',
                    'upload_url': file_metadata.get('url'),
                    'metadata': {
                        'placeholder': True,
                        'processing_started': datetime.now().isoformat()
                    },
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }

                result = supabase.from_('medical_records').insert(record_data).execute()

                if result.data:
                    record_ids.append(record_id)
                    logger.debug(f"Created placeholder record {record_id} for {file_metadata.get('filename')}")
                else:
                    logger.error(f"Failed to create placeholder record for {file_metadata.get('filename')}")

            except Exception as e:
                logger.error(f"Error creating placeholder record for {file_metadata.get('filename')}: {str(e)}")
                continue

        logger.info(f"Successfully created {len(record_ids)} placeholder records")
        return record_ids

    async def process_file_for_existing_record(
        self,
        file_metadata: Dict[str, Any],
        record_id: UUID,
        user_id: str,
        supabase: SupabaseClient
    ) -> Dict[str, Any]:
        """
        Process a file and update an existing medical record (for background processing).

        Args:
            file_metadata: File metadata with URL, type, size, etc.
            record_id: Existing medical record ID to update
            user_id: User ID
            supabase: Supabase client

        Returns:
            Processing result
        """
        start_time = time.time()

        # Extract file information
        file_url = file_metadata.get('url')
        file_type = file_metadata.get('file_type', '').lower()
        original_filename = file_metadata.get('filename')

        logger.info(f"Processing file for existing record {record_id}: {original_filename}")

        try:
            # Validate file type
            if file_type not in self.supported_types:
                raise ValueError(f"Unsupported file type: {file_type}")

            # Download file
            file_data = await self._download_file(file_url)

            # Extract pages based on file type
            pages = await self._extract_pages(file_data, file_type, original_filename)

            if not pages:
                raise ValueError("No content could be extracted from file")

            # Create page records and collect embedding jobs for batch processing
            page_ids = []
            embedding_jobs = []

            for page_num, page_content in enumerate(pages, 1):
                page_id = await self._create_record_page(
                    user_id=user_id,
                    medical_record_id=record_id,
                    page_number=page_num,
                    content=page_content,
                    supabase=supabase
                )
                page_ids.append(page_id)

                # Collect embedding job data for batch processing
                embedding_jobs.append({
                    'record_page_id': str(page_id),
                    'content': page_content
                })

            # Batch queue all embedding jobs in a single database operation
            if embedding_jobs:
                embedding_queued = await semantic_search_service.batch_queue_embedding_jobs_for_record_pages(
                    page_jobs=embedding_jobs,
                    user_id=user_id,
                    supabase=supabase
                )

                if not embedding_queued:
                    logger.warning(f"Failed to batch queue {len(embedding_jobs)} embedding jobs for record {record_id}")

            # Update medical record with page count and status
            await self._update_medical_record_after_processing(
                record_id=record_id,
                num_pages=len(pages),
                page_ids=page_ids,
                supabase=supabase
            )

            duration = time.time() - start_time
            logger.info(f"Successfully processed file {original_filename} for record {record_id} in {duration:.2f}s")

            return {
                'success': True,
                'record_id': record_id,
                'num_pages': len(pages),
                'page_ids': page_ids,
                'processing_time': duration
            }

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Failed to process file {original_filename} for record {record_id}: {str(e)}")

            # Mark the existing record as failed
            await self._update_medical_record_status(record_id, 'failed', supabase)

            return {
                'success': False,
                'error': str(e),
                'processing_time': duration
            }

    async def _update_medical_record_after_processing(
        self,
        record_id: UUID,
        num_pages: int,
        page_ids: List[UUID],
        supabase: SupabaseClient
    ) -> None:
        """Update medical record after successful processing."""
        try:
            result = supabase.from_('medical_records').update({
                'num_pages': num_pages,
                'status': 'completed',
                'metadata': {
                    'placeholder': False,
                    'processing_completed': datetime.now().isoformat(),
                    'page_ids': [str(pid) for pid in page_ids]
                },
                'updated_at': datetime.now().isoformat()
            }).eq('id', str(record_id)).execute()

            if not result.data:
                logger.warning(f"Failed to update medical record {record_id} after processing")
            else:
                logger.info(f"Updated medical record {record_id} with {num_pages} pages")

        except Exception as e:
            logger.error(f"Error updating medical record {record_id} after processing: {str(e)}")


# Global instance for use across the application
pdf_processor = PDFProcessor()