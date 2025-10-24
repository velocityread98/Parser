# Dolphin PDF Processing API

A modern, well-structured FastAPI application for processing PDFs using the Dolphin document parsing model with async background processing.

## 📁 Project Structure

```
api/
├── config/              # Configuration Management
│   ├── __init__.py
│   └── settings.py     # Environment variables and settings
│
├── models/             # Data Models
│   ├── __init__.py
│   ├── request_models.py   # Request Pydantic models
│   └── response_models.py  # Response Pydantic models
│
├── managers/           # Business Logic Managers
│   ├── __init__.py
│   ├── blob_manager.py     # Azure Blob Storage operations
│   ├── file_manager.py     # File operations and PDF conversion
│   └── task_manager.py     # Background task management
│
├── processors/         # Document Processors
│   ├── __init__.py
│   └── dolphin_processor.py  # Dolphin model wrapper
│
├── services/           # Core Business Services
│   ├── __init__.py
│   ├── document_parser.py      # Document parsing logic
│   └── pdf_processing_service.py  # Main PDF processing service
│
├── controllers/        # API Endpoints (Controllers/Routers)
│   ├── __init__.py
│   ├── health_controller.py      # Health check endpoints
│   ├── processing_controller.py  # PDF processing endpoints
│   └── task_controller.py        # Task status endpoints
│
├── app.py             # Main FastAPI application
└── README.md          # This file
```

## 🏗️ Architecture Overview

### **Config Layer**
- **`settings.py`**: Centralized configuration management
  - Environment variables loading
  - Application settings
  - Validation and defaults

### **Models Layer**
- **`request_models.py`**: API request validation
- **`response_models.py`**: API response schemas
- All models use Pydantic for validation

### **Managers Layer**
- **`blob_manager.py`**: Azure Blob Storage operations
  - Upload/download files
  - Container management
- **`file_manager.py`**: File system operations
  - PDF to image conversion
  - Temporary file management
  - File validation
- **`task_manager.py`**: Async background tasks
  - Task queue management
  - Status tracking
  - Background worker

### **Processors Layer**
- **`dolphin_processor.py`**: Dolphin model interface
  - Model initialization
  - Inference operations
  - Device management

### **Services Layer**
- **`document_parser.py`**: Document parsing logic
  - Element recognition
  - Layout analysis
- **`pdf_processing_service.py`**: Orchestration service
  - Coordinates all operations
  - Handles both sync and async processing

### **Controllers Layer**
- **`health_controller.py`**: Health & info endpoints
  - `/` - Basic health check
  - `/health` - Detailed health check
  - `/service-info` - Service information
- **`processing_controller.py`**: Processing endpoints
  - `/process/pdf` - Process PDF from URL
  - `/process/pdf-upload` - Process uploaded PDF
  - `/process/upload-pdf` - Upload PDF to blob storage
- **`task_controller.py`**: Task management endpoints
  - `/tasks/{task_id}` - Get task status
  - `/tasks` - List all tasks

## 🚀 Key Features

### 1. **Async Background Processing**
- Submit PDFs for processing and get immediate response
- Poll for status using task ID
- Non-blocking operations

### 2. **Clean Separation of Concerns**
- **Config**: Application configuration
- **Models**: Data validation and schemas
- **Managers**: Reusable business logic components
- **Processors**: AI/ML model interfaces
- **Services**: Business logic orchestration
- **Controllers**: HTTP request handling

### 3. **Flexible Processing Modes**
- **Async Mode** (default): Background processing with polling
- **Sync Mode**: Wait for completion (legacy behavior)

## 📡 API Endpoints

### Health Checks
- `GET /` - Basic health check
- `GET /health` - Detailed health status
- `GET /service-info` - Service information

### Processing
- `POST /process/pdf` - Process PDF from blob storage URL
- `POST /process/pdf-upload` - Upload and process PDF
- `POST /process/upload-pdf` - Upload PDF without processing

### Task Management
- `GET /tasks/{task_id}` - Get task status
- `GET /tasks` - List all tasks

## 🔧 Configuration

All configuration is managed through environment variables in `.env` file:

```bash
# Azure Storage (Optional)
AZURE_STORAGE_CONNECTION_STRING=your_connection_string

# Model Configuration
MODEL_PATH=./Dolphin/hf_model
MAX_BATCH_SIZE=16

# Container Configuration
CONTAINER_NAME=dolphin-processing
DEFAULT_OUTPUT_CONTAINER=dolphin-results

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

## 🔄 Async Processing Flow

1. **Submit Task**
   ```bash
   POST /process/pdf-upload
   # Returns immediately with task_id
   ```

2. **Poll for Status**
   ```bash
   GET /tasks/{task_id}
   # Check status every 10 seconds
   ```

3. **Task Statuses**
   - `pending` - Task queued
   - `processing` - Currently processing
   - `completed` - Successfully completed
   - `failed` - Processing failed

4. **Retrieve Results**
   - When status is `completed`, result contains `output_url`
   - Download processed JSON from the URL

## 🧪 Example Usage

### Python Client Example
```python
import httpx
import time

# Submit PDF for processing
async with httpx.AsyncClient() as client:
    # Upload PDF
    with open("document.pdf", "rb") as f:
        response = await client.post(
            "http://localhost:8000/process/pdf-upload",
            files={"file": f}
        )
    
    task_id = response.json()["task_id"]
    print(f"Task submitted: {task_id}")
    
    # Poll for completion
    while True:
        status_response = await client.get(
            f"http://localhost:8000/tasks/{task_id}"
        )
        status_data = status_response.json()
        
        if status_data["status"] == "completed":
            print("Processing completed!")
            print(f"Results: {status_data['result']['output_url']}")
            break
        elif status_data["status"] == "failed":
            print(f"Processing failed: {status_data['error']}")
            break
        
        print(f"Status: {status_data['status']}")
        time.sleep(10)  # Poll every 10 seconds
```

## 🎯 Benefits of This Architecture

1. **Maintainability**: Clear separation makes code easy to understand and modify
2. **Testability**: Each layer can be tested independently
3. **Scalability**: Easy to add new endpoints, services, or features
4. **Reusability**: Managers and services can be reused across different controllers
5. **Documentation**: Self-documenting structure makes onboarding easier
6. **Type Safety**: Pydantic models ensure data validation
7. **Async Support**: Non-blocking operations for better performance

## 📝 Development Guidelines

### Adding New Endpoints
1. Create method in appropriate controller
2. Use existing services and managers
3. Follow existing patterns for error handling

### Adding New Services
1. Create service in `services/` directory
2. Import required managers and processors
3. Keep service focused on specific domain

### Adding New Managers
1. Create manager in `managers/` directory
2. Keep manager stateless when possible
3. Follow single responsibility principle

## 🔍 Error Handling

All endpoints follow consistent error handling:
- `400` - Bad Request (invalid input)
- `404` - Not Found (task/resource not found)
- `500` - Internal Server Error (processing errors)
- `503` - Service Unavailable (service not initialized)

## 📊 Logging

Structured logging throughout the application:
- INFO: Normal operations
- WARNING: Non-critical issues
- ERROR: Processing errors
- DEBUG: Detailed debugging information

Configure log level via `LOG_LEVEL` environment variable.

## 🤝 Contributing

When adding new features:
1. Follow the existing architecture patterns
2. Keep layers properly separated
3. Add appropriate type hints
4. Document new endpoints in this README
5. Update models as needed


