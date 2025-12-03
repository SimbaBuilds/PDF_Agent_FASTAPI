"""
PDF Upload Endpoint

FastAPI router for processing PDF files with authentication,
file processing, and database storage.
"""

import json
import time
from typing import List, Dict, Any, Annotated
from uuid import uuid4, UUID
from datetime import datetime
from fastapi import APIRouter, Request, Form, Depends, HTTPException, BackgroundTasks
from supabase import Client as SupabaseClient
from pydantic import BaseModel

from app.auth import get_current_user, get_supabase_client
from app.services.pdf_processor import pdf_processor
from app.services.request_cache import RequestCacheService
from app.utils.logging.component_loggers import get_api_logger

logger = get_api_logger(__name__)

router = APIRouter()

# Supported file types - PDF only
SUPPORTED_FILE_TYPES = ['pdf']


class FileMetadata(BaseModel):
    """Metadata for a PDF file"""
    url: str
    file_type: str
    filename: str
    size_bytes: int


class ProcessPDFsRequest(BaseModel):
    """Request model for processing PDFs"""
    files: List[FileMetadata]
    request_id: str = None


class ProcessPDFsResponse(BaseModel):
    """Response model for processing PDFs (immediate response)"""
    success: bool
    message: str
    request_id: str
    total_files: int
    record_ids: List[str]  # UUIDs of created placeholder records


async def process_pdfs_background(
    file_metadata_list: List[Dict[str, Any]],
    user_id: str,
    record_ids: List[UUID],
    request_id: str
) -> None:
    """
    Background task to process PDFs asynchronously.

    Args:
        file_metadata_list: List of file metadata objects
        user_id: User ID for the records
        record_ids: List of placeholder record IDs to update
        request_id: Request ID for logging
    """
    logger.info(f"Starting background PDF processing for request {request_id}")

    try:
        # Get fresh Supabase client for background task
        from app.utils.supabase_singleton import get_supabase_client_async
        supabase = await get_supabase_client_async()

        # Process each file and update the corresponding placeholder record
        for i, (file_metadata, record_id) in enumerate(zip(file_metadata_list, record_ids)):
            try:
                logger.info(f"Processing PDF {i+1}/{len(file_metadata_list)}: {file_metadata.get('filename')}")

                # Process the single file with existing record ID
                result = await pdf_processor.process_file_for_existing_record(
                    file_metadata=file_metadata,
                    record_id=record_id,
                    user_id=user_id,
                    supabase=supabase
                )

                if result['success']:
                    logger.info(f"Successfully processed PDF: {file_metadata.get('filename')}")
                else:
                    logger.error(f"Failed to process {file_metadata.get('filename')}: {result.get('error')}")

            except Exception as e:
                logger.error(f"Error processing {file_metadata.get('filename')}: {str(e)}")
                await _mark_record_failed(
                    record_id=record_id,
                    error=str(e),
                    supabase=supabase
                )

        logger.info(f"Background PDF processing completed for request {request_id}")

    except Exception as e:
        logger.error(f"Background processing failed for request {request_id}: {str(e)}")


async def _update_placeholder_record(
    record_id: UUID,
    processing_result: Dict[str, Any],
    supabase: SupabaseClient
) -> None:
    """Update placeholder record with processing results."""
    try:
        result = supabase.from_('medical_records').update({
            'num_pages': processing_result['num_pages'],
            'status': 'completed',
            'metadata': {
                'placeholder': False,
                'processing_completed': datetime.now().isoformat(),
                'page_ids': [str(pid) for pid in processing_result['page_ids']],
                'processing_time': processing_result['processing_time']
            },
            'updated_at': datetime.now().isoformat()
        }).eq('id', str(record_id)).execute()

        if not result.data:
            logger.warning(f"Failed to update placeholder record {record_id}")

    except Exception as e:
        logger.error(f"Error updating placeholder record {record_id}: {str(e)}")


async def _mark_record_failed(
    record_id: UUID,
    error: str,
    supabase: SupabaseClient
) -> None:
    """Mark a record as failed with error details."""
    try:
        result = supabase.from_('medical_records').update({
            'status': 'failed',
            'metadata': {
                'placeholder': False,
                'processing_failed': datetime.now().isoformat(),
                'error': error
            },
            'updated_at': datetime.now().isoformat()
        }).eq('id', str(record_id)).execute()

        if not result.data:
            logger.warning(f"Failed to mark record {record_id} as failed")

    except Exception as e:
        logger.error(f"Error marking record {record_id} as failed: {str(e)}")


@router.post("/api/upload_pdfs", response_model=ProcessPDFsResponse)
async def upload_pdfs_endpoint(
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: Annotated[str, Depends(get_current_user)],
    supabase: Annotated[SupabaseClient, Depends(get_supabase_client)],
    json_data: str = Form(...)
) -> ProcessPDFsResponse:
    """
    Process PDF files and store them in the database.

    Returns immediately with confirmation that PDFs will be processed.
    Actual processing happens asynchronously in the background.
    """
    try:
        # Parse request data
        request_data = ProcessPDFsRequest(**json.loads(json_data))

        # Handle request ID for caching consistency
        request_id = request_data.request_id
        if not request_id:
            request_id = getattr(request.state, 'request_id', None)
            if not request_id:
                request_id = str(uuid4())

        # Update request state
        request.state.request_id = request_id

        # Cache the original request for debugging
        cache_key = f"pdf_upload_request_{request_id}"
        RequestCacheService.store(request_id, cache_key, request_data.model_dump())

        logger.info(
            f"Received PDF upload request: "
            f"files_count={len(request_data.files)}, request_id={request_id}"
        )

        # Validate request
        if not request_data.files:
            raise HTTPException(
                status_code=400,
                detail="No files provided for processing"
            )

        # Validate file types - PDF only
        for file_meta in request_data.files:
            if file_meta.file_type.lower() not in SUPPORTED_FILE_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {file_meta.file_type}. "
                           f"Only PDF files are supported."
                )

        # Log file details
        for i, file_meta in enumerate(request_data.files):
            logger.debug(
                f"PDF {i + 1}: {file_meta.filename}, "
                f"size: {file_meta.size_bytes} bytes"
            )

        # Create placeholder records for immediate response
        record_ids = await pdf_processor.create_placeholder_records(
            file_metadata_list=[file_meta.model_dump() for file_meta in request_data.files],
            user_id=user_id,
            supabase=supabase
        )

        if not record_ids:
            raise HTTPException(
                status_code=500,
                detail="Failed to create placeholder records"
            )

        # Calculate processing time estimate (12 seconds per page)
        # Estimate pages: ~20 pages per MB for PDFs
        estimated_pages = 0
        for file_meta in request_data.files:
            file_size_bytes = file_meta.size_bytes
            estimated_pdf_pages = max(1, int((file_size_bytes / 1_000_000) * 20))
            estimated_pages += estimated_pdf_pages

        total_seconds = estimated_pages * 12
        minutes = total_seconds // 60
        seconds = total_seconds % 60

        if minutes > 0:
            time_estimate = f"{minutes}m {seconds}s" if seconds > 0 else f"{minutes}m"
        else:
            time_estimate = f"{seconds}s"

        # Return immediately with success message
        response = ProcessPDFsResponse(
            success=True,
            message=f"Your PDFs will be processed and available shortly.",
            request_id=request_id,
            total_files=len(request_data.files),
            record_ids=[str(record_id) for record_id in record_ids]
        )

        # Queue background processing AFTER preparing the response
        background_tasks.add_task(
            process_pdfs_background,
            file_metadata_list=[file_meta.model_dump() for file_meta in request_data.files],
            user_id=user_id,
            record_ids=record_ids,
            request_id=request_id
        )

        logger.info(f"Queued background PDF processing for {len(request_data.files)} files")

        return response

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Failed to process PDF upload request: {str(e)}")

        raise HTTPException(
            status_code=500,
            detail=f"Failed to process PDF upload: {str(e)}"
        )


@router.get("/api/pdfs")
async def get_pdfs(
    user_id: Annotated[str, Depends(get_current_user)],
    supabase: Annotated[SupabaseClient, Depends(get_supabase_client)],
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Get user's uploaded PDFs with pagination.
    """
    try:
        logger.info(f"Fetching PDFs for user {user_id}, limit={limit}, offset={offset}")

        # Query PDF records (stored in medical_records table for backwards compatibility)
        result = supabase.from_('medical_records').select(
            'id, title, original_file_type, original_filename, '
            'file_size_bytes, num_pages, status, created_at, updated_at'
        ).eq(
            'user_id', user_id
        ).order(
            'created_at', desc=True
        ).range(
            offset, offset + limit - 1
        ).execute()

        if not result.data:
            records = []
        else:
            records = result.data

        # Get total count
        count_result = supabase.from_('medical_records').select(
            'id', count='exact'
        ).eq('user_id', user_id).execute()

        total_count = count_result.count if count_result.count is not None else 0

        logger.info(f"Retrieved {len(records)} medical records (total: {total_count})")

        return {
            'records': records,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'has_more': offset + len(records) < total_count
        }

    except Exception as e:
        logger.error(f"Failed to fetch medical records: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch medical records: {str(e)}"
        )


@router.get("/api/medical_records/{record_id}")
async def get_medical_record_details(
    record_id: str,
    user_id: Annotated[str, Depends(get_current_user)],
    supabase: Annotated[SupabaseClient, Depends(get_supabase_client)]
) -> Dict[str, Any]:
    """
    Get detailed information about a specific medical record including its pages.
    """
    try:
        logger.info(f"Fetching medical record {record_id} for user {user_id}")

        # Get medical record
        record_result = supabase.from_('medical_records').select('*').eq(
            'id', record_id
        ).eq(
            'user_id', user_id
        ).execute()

        if not record_result.data:
            raise HTTPException(
                status_code=404,
                detail="Medical record not found"
            )

        record = record_result.data[0]

        # Get record pages
        pages_result = supabase.from_('record_pages').select(
            'id, page_number, content, processed_at, created_at'
        ).eq(
            'medical_record_id', record_id
        ).eq(
            'user_id', user_id
        ).order('page_number').execute()

        pages = pages_result.data if pages_result.data else []

        logger.info(f"Retrieved medical record {record_id} with {len(pages)} pages")

        return {
            'record': record,
            'pages': pages,
            'total_pages': len(pages)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch medical record details: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch medical record details: {str(e)}"
        )


@router.delete("/api/medical_records/{record_id}")
async def delete_medical_record(
    record_id: str,
    user_id: Annotated[str, Depends(get_current_user)],
    supabase: Annotated[SupabaseClient, Depends(get_supabase_client)]
) -> Dict[str, str]:
    """
    Delete a medical record and all its associated pages.
    """
    try:
        logger.info(f"Deleting medical record {record_id} for user {user_id}")

        # Verify ownership
        record_result = supabase.from_('medical_records').select('id').eq(
            'id', record_id
        ).eq(
            'user_id', user_id
        ).execute()

        if not record_result.data:
            raise HTTPException(
                status_code=404,
                detail="Medical record not found"
            )

        # Delete record pages (will cascade due to foreign key)
        pages_result = supabase.from_('record_pages').delete().eq(
            'medical_record_id', record_id
        ).eq(
            'user_id', user_id
        ).execute()

        # Delete medical record
        record_delete_result = supabase.from_('medical_records').delete().eq(
            'id', record_id
        ).eq(
            'user_id', user_id
        ).execute()

        if not record_delete_result.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete medical record"
            )

        logger.info(f"Successfully deleted medical record {record_id}")

        return {
            'message': f"Medical record {record_id} deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete medical record: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete medical record: {str(e)}"
        )