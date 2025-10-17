"""
PDF Processing Service

Main service class that orchestrates the document processing workflow.
"""

import logging
import os
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, UploadFile, status

from ..managers import BackgroundTaskManager, BlobStorageManager, FileManager
from ..models import ProcessingResult, ProcessingResponse
from ..processors import DolphinProcessor
from .document_parser import DocumentParser

logger = logging.getLogger(__name__)


class PDFProcessingService:
    """Main service for PDF processing operations"""
    
    def __init__(
        self,
        processor: DolphinProcessor,
        blob_manager: Optional[BlobStorageManager] = None,
        file_manager: Optional[FileManager] = None,
        task_manager: Optional[BackgroundTaskManager] = None
    ):
        """Initialize the PDF processing service
        
        Args:
            processor: Dolphin processor instance
            blob_manager: Blob storage manager instance
            file_manager: File manager instance
            task_manager: Background task manager instance
        """
        self.processor = processor
        self.parser = DocumentParser(processor)
        self.blob_manager = blob_manager
        self.file_manager = file_manager or FileManager()
        self.task_manager = task_manager
        
        # Set this service in the task manager
        if self.task_manager:
            self.task_manager.set_processing_service(self)
    
    async def process_pdf_from_blob(
        self,
        pdf_url: str,
        output_container: str,
        max_batch_size: int = 16,
        async_processing: bool = True
    ) -> ProcessingResponse:
        """Process a PDF from blob storage
        
        Args:
            pdf_url: URL to the PDF in blob storage
            output_container: Container name for output storage
            max_batch_size: Maximum batch size for processing
            async_processing: If True, process in background and return immediately
            
        Returns:
            ProcessingResponse with task ID and status
            
        Raises:
            HTTPException: If processing fails
        """
        if not self.blob_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Blob storage not configured"
            )
        
        task_id = self._generate_task_id()
        
        try:
            logger.info(f"Submitting PDF processing task {task_id}")
            
            # Download PDF from blob storage
            pdf_path = await self.blob_manager.download_blob_to_temp(pdf_url)
            
            if async_processing and self.task_manager:
                # Submit to background processing
                await self.task_manager.submit_task(
                    task_id=task_id,
                    pdf_path=pdf_path,
                    source_url=pdf_url,
                    source_filename=None,
                    output_container=output_container,
                    max_batch_size=max_batch_size
                )
                
                return ProcessingResponse(
                    task_id=task_id,
                    status="pending",
                    message=f"Task submitted for background processing. Use GET /task-status/{task_id} to check progress.",
                    timestamp=datetime.now().isoformat()
                )
            else:
                # Synchronous processing (original behavior)
                start_time = datetime.now()
                
                try:
                    # Process the PDF
                    result = await self._process_pdf_file(
                        pdf_path, task_id, pdf_url, None, max_batch_size
                    )
                    
                    # Upload results to blob storage
                    output_blob_name = f"processed_{task_id}.json"
                    output_url = await self.blob_manager.upload_json_to_blob(
                        result.dict(), output_container, output_blob_name
                    )
                    
                    processing_time = (datetime.now() - start_time).total_seconds()
                    
                    logger.info(f"Completed PDF processing task {task_id} in {processing_time:.2f} seconds")
                    
                    return ProcessingResponse(
                        task_id=task_id,
                        status="completed",
                        message=f"Successfully processed {result.total_pages} pages",
                        output_url=output_url,
                        processing_time=processing_time
                    )
                    
                finally:
                    # Clean up temporary file
                    self.file_manager.cleanup_temp_file(pdf_path)
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing PDF task {task_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process PDF: {str(e)}"
            )
    
    async def process_pdf_upload(
        self,
        file: UploadFile,
        output_container: str,
        max_batch_size: int = 16,
        async_processing: bool = True
    ) -> ProcessingResponse:
        """Process an uploaded PDF file
        
        Args:
            file: Uploaded file
            output_container: Container name for output storage
            max_batch_size: Maximum batch size for processing
            async_processing: If True, process in background and return immediately
            
        Returns:
            ProcessingResponse with task ID and status
            
        Raises:
            HTTPException: If processing fails
        """
        task_id = self._generate_task_id()
        
        try:
            if not file.filename.endswith('.pdf'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Only PDF files are supported"
                )
            
            logger.info(f"Submitting PDF upload processing task {task_id}")
            
            # Read file content
            file_content = await file.read()
            
            # Save to temporary file
            pdf_path = self.file_manager.save_upload_to_temp(
                file_content, file.filename
            )
            
            # Validate PDF
            if not self.file_manager.validate_pdf_file(pdf_path):
                self.file_manager.cleanup_temp_file(pdf_path)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid PDF file"
                )
            
            if async_processing and self.task_manager:
                # Submit to background processing
                await self.task_manager.submit_task(
                    task_id=task_id,
                    pdf_path=pdf_path,
                    source_url=None,
                    source_filename=file.filename,
                    output_container=output_container,
                    max_batch_size=max_batch_size
                )
                
                return ProcessingResponse(
                    task_id=task_id,
                    status="pending",
                    message=f"Task submitted for background processing. Use GET /task-status/{task_id} to check progress.",
                    timestamp=datetime.now().isoformat()
                )
            else:
                # Synchronous processing (original behavior)
                start_time = datetime.now()
                
                try:
                    # Process the PDF
                    result = await self._process_pdf_file(
                        pdf_path, task_id, None, file.filename, max_batch_size
                    )
                    
                    # Upload results to blob storage if available
                    output_url = None
                    if self.blob_manager:
                        output_blob_name = f"processed_{task_id}.json"
                        output_url = await self.blob_manager.upload_json_to_blob(
                            result.dict(), output_container, output_blob_name
                        )
                    
                    processing_time = (datetime.now() - start_time).total_seconds()
                    
                    logger.info(f"Completed PDF upload processing task {task_id} in {processing_time:.2f} seconds")
                    
                    return ProcessingResponse(
                        task_id=task_id,
                        status="completed",
                        message=f"Successfully processed {result.total_pages} pages",
                        output_url=output_url,
                        processing_time=processing_time
                    )
                    
                finally:
                    # Clean up temporary file
                    self.file_manager.cleanup_temp_file(pdf_path)
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing PDF upload task {task_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process PDF: {str(e)}"
            )
    
    async def _process_pdf_file(
        self,
        pdf_path: str,
        task_id: str,
        source_url: Optional[str],
        source_filename: Optional[str],
        max_batch_size: int
    ) -> ProcessingResult:
        """Process a PDF file and return results
        
        Args:
            pdf_path: Path to the PDF file
            task_id: Unique task identifier
            source_url: Source URL if from blob storage
            source_filename: Source filename if from upload
            max_batch_size: Maximum batch size for processing
            
        Returns:
            ProcessingResult with parsed data
        """
        try:
            # Convert PDF to images
            images = self.file_manager.convert_pdf_to_images(pdf_path)
            if not images:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to convert PDF to images"
                )
            
            all_results = []
            
            # Process each page
            for page_idx, pil_image in enumerate(images):
                logger.info(f"Processing page {page_idx + 1}/{len(images)}")
                
                # Process this page
                recognition_results = self.parser.process_single_image(
                    pil_image, max_batch_size
                )
                
                # Add page information to results
                page_results = {
                    "page_number": page_idx + 1,
                    "elements": recognition_results
                }
                all_results.append(page_results)
            
            # Prepare combined results
            processing_time = 0.0  # This will be set by the calling method
            combined_results = ProcessingResult(
                task_id=task_id,
                source_url=source_url,
                source_filename=source_filename,
                total_pages=len(all_results),
                processing_time=processing_time,
                timestamp=datetime.now().isoformat(),
                pages=all_results
            )
            
            return combined_results
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing PDF file: {str(e)}")
            raise
    
    def _generate_task_id(self) -> str:
        """Generate a unique task ID
        
        Returns:
            Unique task identifier
        """
        import uuid
        return str(uuid.uuid4())
    
    def get_service_info(self) -> dict:
        """Get information about the service
        
        Returns:
            Dictionary with service information
        """
        return {
            "processor_info": self.processor.get_device_info(),
            "blob_storage_available": self.blob_manager is not None,
            "blob_storage_info": self.blob_manager.get_storage_info() if self.blob_manager else None,
            "file_manager_temp_dir": self.file_manager.temp_dir
        }
