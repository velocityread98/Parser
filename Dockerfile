# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgcc-s1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY api_requirements.txt .
RUN pip install --no-cache-dir -r api_requirements.txt

# Copy the Dolphin module
COPY Dolphin/ ./Dolphin/

# Copy the API module and main entry point
COPY api/ ./api/
COPY main_api.py .

# Create directories for model and temporary files
RUN mkdir -p /app/models /app/temp

# Set environment variables
ENV PYTHONPATH=/app
ENV MODEL_PATH=/app/models
ENV MAX_BATCH_SIZE=16
ENV CONTAINER_NAME=dolphin-processing

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "main_api:app", "--host", "0.0.0.0", "--port", "8000"]
