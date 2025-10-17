"""
Request Models

Pydantic models for API requests.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ProcessingRequest(BaseModel):
    """Request model for PDF processing from blob storage"""
    pdf_url: str = Field(..., description="URL to the PDF file in blob storage")
    output_container: str = Field(default="dolphin-results", description="Container name for output storage")
    max_batch_size: Optional[int] = Field(default=16, description="Maximum batch size for processing")


class UploadProcessingRequest(BaseModel):
    """Request model for PDF upload processing"""
    output_container: str = Field(default="dolphin-results", description="Container name for output storage")
    max_batch_size: Optional[int] = Field(default=16, description="Maximum batch size for processing")

