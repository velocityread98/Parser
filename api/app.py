"""
Dolphin PDF Processing API

Main application file that initializes and configures the FastAPI application.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .config import settings
from .controllers import health_controller, processing_controller, task_controller
from .managers import BackgroundTaskManager, BlobStorageManager, FileManager
from .models import ErrorResponse
from .processors import DolphinProcessor
from .services import PDFProcessingService

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
processing_service = None
task_manager = None
blob_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global processing_service, task_manager, blob_manager
    
    try:
        # Initialize Dolphin processor
        logger.info(f"Initializing Dolphin processor from {settings.MODEL_PATH}...")
        processor = DolphinProcessor(settings.MODEL_PATH)
        
        # Initialize blob storage manager if configured
        if settings.is_blob_storage_configured:
            logger.info("Initializing blob storage manager...")
            blob_manager = BlobStorageManager(settings.AZURE_STORAGE_CONNECTION_STRING)
        else:
            logger.warning("AZURE_STORAGE_CONNECTION_STRING not set. Blob storage features will be disabled.")
        
        # Initialize file manager
        file_manager = FileManager()
        
        # Initialize task manager with thread pool
        logger.info(f"Initializing background task manager with {settings.MAX_WORKERS} worker(s)...")
        task_manager = BackgroundTaskManager(max_workers=settings.MAX_WORKERS)
        
        # Initialize processing service
        processing_service = PDFProcessingService(
            processor=processor,
            blob_manager=blob_manager,
            file_manager=file_manager,
            task_manager=task_manager
        )
        
        # Set service references in controllers
        health_controller.set_processing_service(processing_service)
        processing_controller.set_services(processing_service, blob_manager)
        task_controller.set_task_manager(task_manager)
        
        # Start background worker
        logger.info("Starting background worker...")
        await task_manager.start_worker()
        
        logger.info(f"Dolphin API started successfully on {settings.API_HOST}:{settings.API_PORT}")
        logger.info(f"Model: {settings.MODEL_PATH}")
        logger.info(f"Blob Storage: {'Configured' if settings.is_blob_storage_configured else 'Not Configured'}")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize API: {str(e)}")
        raise
    finally:
        # Stop background worker
        if task_manager:
            logger.info("Stopping background worker...")
            await task_manager.stop_worker()
        logger.info("Shutting down Dolphin API")


# Initialize FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    lifespan=lifespan
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc)
        ).dict()
    )


# Include routers from controllers
app.include_router(health_controller.router)
app.include_router(processing_controller.router)
app.include_router(task_controller.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT
    )

