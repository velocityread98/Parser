"""
Azure Blob Storage Manager

Handles blob storage operations for downloading PDFs and uploading results.
"""

import json
import logging
import tempfile
from typing import Dict, Optional
from urllib.parse import urlparse

from azure.storage.blob.aio import BlobServiceClient

logger = logging.getLogger(__name__)


class BlobStorageManager:
    """Manages Azure blob storage operations"""
    
    def __init__(self, connection_string: str):
        """Initialize blob storage client
        
        Args:
            connection_string: Azure Storage connection string
        """
        self.connection_string = connection_string
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    
    async def download_blob_to_temp(self, blob_url: str) -> str:
        """Download blob to temporary file and return path
        
        Args:
            blob_url: Full URL to the blob
            
        Returns:
            Path to the temporary file
            
        Raises:
            ValueError: If blob URL format is invalid
            Exception: If download fails
        """
        try:
            # Parse blob URL to get container and blob name
            parsed_url = urlparse(blob_url)
            path_parts = parsed_url.path.lstrip('/').split('/', 1)
            if len(path_parts) != 2:
                raise ValueError("Invalid blob URL format")
            
            container_name, blob_name = path_parts
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_path = temp_file.name
            temp_file.close()
            
            # Download blob
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name, 
                blob=blob_name
            )
            
            async with blob_client as client:
                with open(temp_path, 'wb') as f:
                    download_stream = await client.download_blob()
                    async for chunk in download_stream.chunks():
                        f.write(chunk)
            
            logger.info(f"Downloaded blob to temporary file: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Error downloading blob: {str(e)}")
            raise
    
    async def upload_json_to_blob(self, data: Dict, container_name: str, blob_name: str) -> str:
        """Upload JSON data to blob storage
        
        Args:
            data: Dictionary to upload as JSON
            container_name: Target container name
            blob_name: Target blob name
            
        Returns:
            URL of the uploaded blob
            
        Raises:
            Exception: If upload fails
        """
        try:
            # Ensure container exists
            container_client = self.blob_service_client.get_container_client(container_name)
            try:
                await container_client.create_container()
                logger.info(f"Created container: {container_name}")
            except Exception:
                # Container might already exist, which is fine
                pass
            
            # Upload JSON data
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            
            json_data = json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')
            
            async with blob_client as client:
                await client.upload_blob(json_data, overwrite=True)
            
            blob_url = f"https://{self.blob_service_client.account_name}.blob.core.windows.net/{container_name}/{blob_name}"
            logger.info(f"Uploaded JSON to blob: {blob_url}")
            return blob_url
            
        except Exception as e:
            logger.error(f"Error uploading to blob: {str(e)}")
            raise
    
    async def upload_file_to_blob(self, file_path: str, container_name: str, blob_name: str) -> str:
        """Upload a file to blob storage
        
        Args:
            file_path: Path to the file to upload
            container_name: Target container name
            blob_name: Target blob name
            
        Returns:
            URL of the uploaded blob
            
        Raises:
            Exception: If upload fails
        """
        try:
            # Ensure container exists
            container_client = self.blob_service_client.get_container_client(container_name)
            try:
                await container_client.create_container()
                logger.info(f"Created container: {container_name}")
            except Exception:
                # Container might already exist, which is fine
                pass
            
            # Upload file
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            
            async with blob_client as client:
                with open(file_path, 'rb') as f:
                    await client.upload_blob(f, overwrite=True)
            
            blob_url = f"https://{self.blob_service_client.account_name}.blob.core.windows.net/{container_name}/{blob_name}"
            logger.info(f"Uploaded file to blob: {blob_url}")
            return blob_url
            
        except Exception as e:
            logger.error(f"Error uploading file to blob: {str(e)}")
            raise
    
    async def blob_exists(self, blob_url: str) -> bool:
        """Check if a blob exists
        
        Args:
            blob_url: Full URL to the blob
            
        Returns:
            True if blob exists, False otherwise
        """
        try:
            # Parse blob URL to get container and blob name
            parsed_url = urlparse(blob_url)
            path_parts = parsed_url.path.lstrip('/').split('/', 1)
            if len(path_parts) != 2:
                return False
            
            container_name, blob_name = path_parts
            
            # Check if blob exists
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            
            async with blob_client as client:
                return await client.exists()
                
        except Exception as e:
            logger.error(f"Error checking blob existence: {str(e)}")
            return False
    
    def get_storage_info(self) -> Dict:
        """Get information about the storage account
        
        Returns:
            Dictionary with storage information
        """
        return {
            "account_name": self.blob_service_client.account_name,
            "connection_string_configured": bool(self.connection_string),
        }
