"""
Processing Controller

Handles PDF processing endpoints.
"""

import logging

from fastapi import APIRouter, HTTPException, UploadFile, status

from ..config import settings
from ..models import ProcessingRequest, ProcessingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/process", tags=["Processing"])

# Global service references (will be set by main.py)
_processing_service = None
_blob_manager = None


def set_services(processing_service, blob_manager):
    """Set the service instances"""
    global _processing_service, _blob_manager
    _processing_service = processing_service
    _blob_manager = blob_manager


@router.post("/pdf", response_model=ProcessingResponse)
async def process_pdf(request: ProcessingRequest, async_mode: bool = True):
    """Process a PDF file from blob storage
    
    Args:
        request: Processing request with PDF URL and settings
        async_mode: If True (default), process in background and return immediately
    
    Returns:
        ProcessingResponse with task ID and status
    """
    if not _processing_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )
    
    try:
        return await _processing_service.process_pdf_from_blob(
            pdf_url=request.pdf_url,
            output_container=request.output_container,
            max_batch_size=request.max_batch_size or settings.MAX_BATCH_SIZE,
            async_processing=async_mode
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in process_pdf endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process PDF: {str(e)}"
        )


@router.post("/pdf-upload", response_model=ProcessingResponse)
async def process_pdf_upload(
    file: UploadFile,
    output_container: str = "dolphin-results",
    max_batch_size: int = 16,
    async_mode: bool = True
):
    """Process an uploaded PDF file
    
    Args:
        file: Uploaded PDF file
        output_container: Container name for output storage
        max_batch_size: Maximum batch size for processing
        async_mode: If True (default), process in background and return immediately
    
    Returns:
        ProcessingResponse with task ID and status
    """
    if not _processing_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )
    
    try:
        return await _processing_service.process_pdf_upload(
            file=file,
            output_container=output_container,
            max_batch_size=max_batch_size,
            async_processing=async_mode
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in process_pdf_upload endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process PDF: {str(e)}"
        )


@router.post("/upload-pdf", response_model=dict)
async def upload_pdf_to_blob(
    file: UploadFile,
    container_name: str = "pdf-uploads",
    blob_name: str = None
):
    """Upload a PDF file to Azure Blob Storage without processing
    
    Args:
        file: PDF file to upload
        container_name: Target container name (default: pdf-uploads)
        blob_name: Optional blob name (default: original filename)
    
    Returns:
        Dictionary with upload information including blob URL
    """
    if not _processing_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )
    
    if not _blob_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Blob storage not configured"
        )
    
    try:
        # Validate PDF file
        if not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are supported"
            )
        
        # Use original filename if blob_name not provided
        if blob_name is None:
            blob_name = file.filename
        
        logger.info(f"Uploading PDF {file.filename} to blob storage")
        
        # Read file content
        file_content = await file.read()
        
        # Save to temporary file
        temp_file = _processing_service.file_manager.save_upload_to_temp(
            file_content, file.filename
        )
        
        try:
            # Upload to blob storage
            blob_url = await _blob_manager.upload_file_to_blob(
                temp_file, container_name, blob_name
            )
            
            logger.info(f"Successfully uploaded PDF to {blob_url}")
            
            return {
                "status": "success",
                "message": f"PDF uploaded successfully",
                "blob_url": blob_url,
                "container": container_name,
                "blob_name": blob_name,
                "original_filename": file.filename,
                "file_size": len(file_content)
            }
            
        finally:
            # Clean up temporary file
            _processing_service.file_manager.cleanup_temp_file(temp_file)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading PDF: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload PDF: {str(e)}"
        )

