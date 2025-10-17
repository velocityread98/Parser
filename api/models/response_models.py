"""
Response Models

Pydantic models for API responses.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ProcessingResponse(BaseModel):
    """Response model for processing results"""
    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(..., description="Processing status")
    message: str = Field(..., description="Status message")
    output_url: Optional[str] = Field(None, description="URL to the processed results")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Processing timestamp")


class TaskStatusResponse(BaseModel):
    """Response model for task status polling"""
    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(..., description="Task status (pending, processing, completed, failed)")
    created_at: str = Field(..., description="Task creation timestamp")
    started_at: Optional[str] = Field(None, description="Task start timestamp")
    completed_at: Optional[str] = Field(None, description="Task completion timestamp")
    progress: Optional[Dict] = Field(None, description="Progress information")
    result: Optional[Dict] = Field(None, description="Task result if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    source_url: Optional[str] = Field(None, description="Source PDF URL")
    source_filename: Optional[str] = Field(None, description="Source PDF filename")


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service status")
    model_loaded: bool = Field(..., description="Whether the model is loaded")
    blob_storage_available: bool = Field(..., description="Whether blob storage is available")
    device: str = Field(..., description="Processing device (CPU/GPU)")
    version: str = Field(..., description="API version")


class ElementData(BaseModel):
    """Individual element data model"""
    label: str = Field(..., description="Element type (text, tab, fig)")
    text: str = Field(..., description="Extracted text content")
    bbox: List[float] = Field(..., description="Bounding box coordinates [x1, y1, x2, y2]")
    reading_order: int = Field(..., description="Reading order in the document")


class PageData(BaseModel):
    """Page data model"""
    page_number: int = Field(..., description="Page number in the document")
    elements: List[ElementData] = Field(..., description="List of elements on this page")


class ProcessingResult(BaseModel):
    """Complete processing result model"""
    task_id: str = Field(..., description="Unique task identifier")
    source_url: Optional[str] = Field(None, description="Source PDF URL")
    source_filename: Optional[str] = Field(None, description="Source PDF filename")
    total_pages: int = Field(..., description="Total number of pages processed")
    processing_time: float = Field(..., description="Processing time in seconds")
    timestamp: str = Field(..., description="Processing timestamp")
    pages: List[PageData] = Field(..., description="List of processed pages")


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    task_id: Optional[str] = Field(None, description="Task ID if available")

