"""
PDF Processing Service

Service for processing PDF files and converting them into database records
with text extraction and embedding generation.
"""

import io
import logging
import time
import base64
import os
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID, uuid4
from datetime import datetime
import requests
import PyPDF2
from pdf2image import convert_from_bytes
from PIL import Image
from supabase import Client as SupabaseClient

from app.services.ocr_processor import ocr_processor
from app.services.semantic_search import semantic_search_service
from app.services.vision_processor import process_image_with_vision
from app.utils.logging.component_loggers import get_api_logger

# Increase PIL image size limit to handle large PDFs
# Default is ~89 million pixels, we'll set to 200 million to handle large scanned documents
Image.MAX_IMAGE_PIXELS = 200000000

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

    async def _trigger_embedding_processor(self, supabase: SupabaseClient) -> None:
        """
        Trigger the Supabase Edge Function to process pending embedding jobs.
        This is a fire-and-forget operation - errors are logged but not raised.

        Args:
            supabase: Supabase client for authentication
        """
        try:
            logger.info("=== EMBEDDING TRIGGER START ===")

            # Get Supabase URL and anon key from environment
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_anon_key = os.getenv('SUPABASE_ANON_KEY')

            logger.info(f"Environment check - SUPABASE_URL: {'SET' if supabase_url else 'NOT SET'}")
            logger.info(f"Environment check - SUPABASE_ANON_KEY: {'SET' if supabase_anon_key else 'NOT SET'}")

            if not supabase_url or not supabase_anon_key:
                logger.warning("Supabase credentials not found, skipping embedding trigger")
                return

            # Build edge function URL
            edge_function_url = f"{supabase_url}/functions/v1/process-embeddings"
            logger.info(f"Edge function URL: {edge_function_url}")

            # Trigger the edge function (fire and forget)
            logger.info("Creating async task to trigger embedding processor")

            # Use asyncio.create_task for true fire-and-forget
            async def invoke_edge_function():
                try:
                    logger.info("Inside invoke_edge_function - about to make HTTP request")

                    response = await asyncio.to_thread(
                        requests.post,
                        edge_function_url,
                        headers={
                            'Authorization': f'Bearer {supabase_anon_key}',
                            'Content-Type': 'application/json'
                        },
                        json={'batchSize': 50},  # Process up to 50 jobs per invocation
                        timeout=5  # Short timeout since we don't wait for completion
                    )

                    logger.info(f"HTTP request completed - Status: {response.status_code}")

                    if response.ok:
                        logger.info(f"Successfully triggered embedding processor: {response.json()}")
                    else:
                        logger.warning(f"Embedding processor trigger returned status {response.status_code}: {response.text}")
                except Exception as e:
                    logger.error(f"Failed to trigger embedding processor: {str(e)}", exc_info=True)

            # Fire and forget - don't await
            task = asyncio.create_task(invoke_edge_function())
            logger.info(f"Async task created: {task}")
            logger.info("=== EMBEDDING TRIGGER END ===")

        except Exception as e:
            logger.error(f"Error in embedding processor trigger: {str(e)}", exc_info=True)

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
                    pdf_document_id=record_id,
                    page_number=page_num,
                    content=page_content,
                    supabase=supabase
                )
                page_ids.append(page_id)

                # Collect embedding job data for batch processing
                embedding_jobs.append({
                    'pdf_page_id': str(page_id),
                    'content': page_content
                })

            # Batch queue all embedding jobs in a single database operation
            if embedding_jobs:
                logger.info(f"About to batch queue {len(embedding_jobs)} embedding jobs for record {record_id}")
                embedding_queued = await semantic_search_service.batch_queue_embedding_jobs_for_pdf_pages(
                    page_jobs=embedding_jobs,
                    user_id=user_id,
                    pdf_document_id=record_id,
                    supabase=supabase
                )

                if not embedding_queued:
                    logger.warning(f"Failed to batch queue {len(embedding_jobs)} embedding jobs for record {record_id}")
                else:
                    logger.info(f"Successfully queued {len(embedding_jobs)} embedding jobs. Now triggering processor...")
                    # Trigger immediate embedding processing (fire and forget)
                    await self._trigger_embedding_processor(supabase)
            else:
                logger.warning(f"No embedding jobs to queue for record {record_id}")

            # Status will be updated to 'completed' by database trigger after all embeddings finish

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
                await self._update_pdf_document_status(record_id, 'failed', supabase)

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

    def _pil_image_to_data_url(self, pil_image, max_size_mb: float = 4.5, max_dimension: int = 8000) -> str:
        """
        Convert PIL image to base64 data URL, with automatic resizing to stay under size and dimension limits.

        Args:
            pil_image: PIL Image object
            max_size_mb: Maximum size in megabytes (default 4.5 MB for Anthropic API)
            max_dimension: Maximum width or height in pixels (default 8000 for Anthropic API)

        Returns:
            Base64 data URL string
        """
        import io as io_module
        from PIL import Image

        # Convert image to RGB if needed
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')

        # Check if dimensions exceed limit and resize if needed
        if pil_image.width > max_dimension or pil_image.height > max_dimension:
            # Calculate scale factor to fit within max dimension
            scale_factor = min(max_dimension / pil_image.width, max_dimension / pil_image.height)
            new_width = int(pil_image.width * scale_factor)
            new_height = int(pil_image.height * scale_factor)
            logger.info(f"Image dimensions ({pil_image.width}x{pil_image.height}) exceed max {max_dimension}px, resizing to {new_width}x{new_height}")
            pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Try saving at full size first
        img_byte_arr = io_module.BytesIO()
        pil_image.save(img_byte_arr, format='PNG', optimize=True)
        img_bytes = img_byte_arr.getvalue()
        format_type = 'png'

        # Check size and resize if needed
        max_size_bytes = int(max_size_mb * 1024 * 1024)

        if len(img_bytes) > max_size_bytes:
            logger.info(f"Image too large ({len(img_bytes) / 1024 / 1024:.2f} MB), resizing to fit under {max_size_mb} MB")

            # Calculate resize factor to achieve target size
            # Start with a conservative estimate
            scale_factor = 0.7
            format_type = 'jpeg'  # Switch to JPEG for smaller file size

            while len(img_bytes) > max_size_bytes and scale_factor > 0.1:
                # Resize image
                new_width = int(pil_image.width * scale_factor)
                new_height = int(pil_image.height * scale_factor)
                resized_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # Save resized image
                img_byte_arr = io_module.BytesIO()
                resized_image.save(img_byte_arr, format='JPEG', quality=85, optimize=True)
                img_bytes = img_byte_arr.getvalue()

                logger.debug(f"Resized to {new_width}x{new_height} (scale: {scale_factor:.2f}), size: {len(img_bytes) / 1024 / 1024:.2f} MB")

                # Reduce scale factor for next iteration
                scale_factor *= 0.8

            logger.info(f"Final image size: {len(img_bytes) / 1024 / 1024:.2f} MB (format: {format_type})")

        # Encode to base64
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')

        # Return as data URL
        return f"data:image/{format_type};base64,{img_base64}"

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
                        # Insufficient text, try vision processing first, then OCR as fallback
                        logger.info(f"PDF page {page_num + 1}: text extraction insufficient ({len(text) if text else 0} chars), trying vision processing")

                        # Convert PDF page to image
                        page_images = convert_from_bytes(
                            pdf_data,
                            first_page=page_num + 1,
                            last_page=page_num + 1,
                            dpi=300
                        )

                        if page_images:
                            # Try vision processing first
                            try:
                                # Convert image to base64 data URL
                                image_data_url = self._pil_image_to_data_url(page_images[0])

                                # Use vision processing to extract text
                                vision_text = process_image_with_vision(
                                    user_message="Extract all text from this document page. Preserve formatting and structure.",
                                    image_url=image_data_url
                                )

                                if vision_text and len(vision_text.strip()) > 50:
                                    pages.append(vision_text.strip())
                                    logger.info(f"PDF page {page_num + 1}: extracted {len(vision_text)} characters via vision processing")
                                    continue
                                else:
                                    logger.warning(f"PDF page {page_num + 1}: vision processing returned insufficient text, falling back to OCR")
                            except Exception as vision_error:
                                logger.warning(f"PDF page {page_num + 1}: vision processing failed ({str(vision_error)}), falling back to OCR")

                            # Fallback to OCR if vision processing failed
                            ocr_text = ocr_processor.extract_text_from_pil_image(page_images[0])
                            if ocr_text:
                                pages.append(ocr_text)
                                logger.debug(f"PDF page {page_num + 1}: extracted {len(ocr_text)} characters via OCR")
                            else:
                                logger.warning(f"PDF page {page_num + 1}: OCR failed, skipping page")
                        else:
                            logger.warning(f"PDF page {page_num + 1}: failed to convert to image")

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

            result = supabase.from_('pdf_documents').insert(record_data).execute()

            if result.data:
                record_id = UUID(result.data[0]['id'])
                logger.info(f"Created PDF document record {record_id}")
                return record_id
            else:
                raise ValueError("Failed to create medical record")

        except Exception as e:
            raise ValueError(f"Database error creating medical record: {str(e)}")

    async def _create_record_page(
        self,
        user_id: str,
        pdf_document_id: UUID,
        page_number: int,
        content: str,
        supabase: SupabaseClient
    ) -> UUID:
        """Create record page in database."""
        try:
            page_data = {
                'id': str(uuid4()),
                'user_id': user_id,
                'pdf_document_id': str(pdf_document_id),
                'page_number': page_number,
                'content': content
            }

            result = supabase.from_('pdf_pages').insert(page_data).execute()

            if result.data:
                page_id = UUID(result.data[0]['id'])
                logger.debug(f"Created PDF page {page_id} for PDF document {pdf_document_id}")
                return page_id
            else:
                raise ValueError("Failed to create record page")

        except Exception as e:
            raise ValueError(f"Database error creating record page: {str(e)}")

    async def _update_pdf_document_status(
        self,
        record_id: UUID,
        status: str,
        supabase: SupabaseClient
    ) -> None:
        """Update medical record status."""
        try:
            result = supabase.from_('pdf_documents').update({
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

                result = supabase.from_('pdf_documents').insert(record_data).execute()

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
                    pdf_document_id=record_id,
                    page_number=page_num,
                    content=page_content,
                    supabase=supabase
                )
                page_ids.append(page_id)

                # Collect embedding job data for batch processing
                embedding_jobs.append({
                    'pdf_page_id': str(page_id),
                    'content': page_content
                })

            # Batch queue all embedding jobs in a single database operation
            if embedding_jobs:
                logger.info(f"About to batch queue {len(embedding_jobs)} embedding jobs for record {record_id}")
                embedding_queued = await semantic_search_service.batch_queue_embedding_jobs_for_pdf_pages(
                    page_jobs=embedding_jobs,
                    user_id=user_id,
                    pdf_document_id=record_id,
                    supabase=supabase
                )

                if not embedding_queued:
                    logger.warning(f"Failed to batch queue {len(embedding_jobs)} embedding jobs for record {record_id}")
                else:
                    logger.info(f"Successfully queued {len(embedding_jobs)} embedding jobs. Now triggering processor...")
                    # Trigger immediate embedding processing (fire and forget)
                    await self._trigger_embedding_processor(supabase)
            else:
                logger.warning(f"No embedding jobs to queue for record {record_id}")

            # Update medical record with page count and status
            await self._update_pdf_document_after_processing(
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
            await self._update_pdf_document_status(record_id, 'failed', supabase)

            return {
                'success': False,
                'error': str(e),
                'processing_time': duration
            }

    async def _update_pdf_document_after_processing(
        self,
        record_id: UUID,
        num_pages: int,
        page_ids: List[UUID],
        supabase: SupabaseClient
    ) -> None:
        """Update medical record after successful page processing.

        Note: Status remains 'processing' until all embeddings complete.
        The status will be updated to 'completed' by database trigger.
        """
        try:
            result = supabase.from_('pdf_documents').update({
                'num_pages': num_pages,
                # Status remains 'processing' - will be updated by trigger after embeddings complete
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