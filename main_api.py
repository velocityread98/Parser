"""
Main entry point for the Dolphin PDF Processing API

This file imports and runs the modular API from the api package.
"""

from api.app import app
from api.config import settings

if __name__ == "__main__":
    import uvicorn
    
    print(f"🚀 Starting {settings.API_TITLE} v{settings.API_VERSION}")
    print(f"📍 Host: {settings.API_HOST}:{settings.API_PORT}")
    print(f"🤖 Model: {settings.MODEL_PATH}")
    print(f"☁️  Blob Storage: {'Configured ✓' if settings.is_blob_storage_configured else 'Not Configured ✗'}")
    print(f"📊 Max Batch Size: {settings.MAX_BATCH_SIZE}")
    print()
    
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)
