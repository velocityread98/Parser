"""
Health Check Controller

Handles health check and service information endpoints.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from ..config import settings
from ..models import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])

# Global service reference (will be set by main.py)
_processing_service = None


def set_processing_service(service):
    """Set the processing service instance"""
    global _processing_service
    _processing_service = service


@router.get("/", response_model=dict)
async def root():
    """Basic health check endpoint"""
    return {
        "message": "Dolphin PDF Processing API is running",
        "status": "healthy",
        "version": settings.API_VERSION
    }


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check endpoint"""
    if not _processing_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )
    
    service_info = _processing_service.get_service_info()
    
    return HealthResponse(
        status="healthy",
        model_loaded=_processing_service.processor is not None,
        blob_storage_available=service_info["blob_storage_available"],
        device=service_info["processor_info"]["device"],
        version=settings.API_VERSION
    )


@router.get("/service-info", response_model=dict)
async def get_service_info():
    """Get detailed service information"""
    if not _processing_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )
    
    return _processing_service.get_service_info()


