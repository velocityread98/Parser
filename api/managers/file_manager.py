"""
File Manager

Handles file operations using existing Dolphin module functions.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import List, Optional

from PIL import Image

from Dolphin.utils.utils import convert_pdf_to_images, is_pdf_file

logger = logging.getLogger(__name__)


class FileManager:
    """Handles file extraction and conversion operations"""
    
    def __init__(self, temp_dir: Optional[str] = None):
        """Initialize file extractor
        
        Args:
            temp_dir: Directory for temporary files (defaults to system temp)
        """
        self.temp_dir = temp_dir or tempfile.gettempdir()
    
    def convert_pdf_to_images(self, pdf_path: str, target_size: int = 896) -> List[Image.Image]:
        """Convert PDF pages to images using existing Dolphin function
        
        Args:
            pdf_path: Path to the PDF file
            target_size: Target size for the longest dimension
            
        Returns:
            List of PIL Images
            
        Raises:
            Exception: If PDF conversion fails
        """
        try:
            logger.info(f"Converting PDF to images: {pdf_path}")
            images = convert_pdf_to_images(pdf_path, target_size)
            if not images:
                raise Exception(f"Failed to convert PDF {pdf_path} to images")
            logger.info(f"Successfully converted {len(images)} pages from PDF")
            return images
            
        except Exception as e:
            logger.error(f"Error converting PDF to images: {str(e)}")
            raise
    
    def save_upload_to_temp(self, file_content: bytes, filename: str, suffix: str = None) -> str:
        """Save uploaded file content to temporary file
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            suffix: File suffix (defaults to original extension)
            
        Returns:
            Path to the temporary file
        """
        try:
            # Determine suffix
            if suffix is None:
                suffix = Path(filename).suffix
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, 
                suffix=suffix,
                dir=self.temp_dir
            )
            temp_path = temp_file.name
            temp_file.close()
            
            # Write content to file
            with open(temp_path, 'wb') as f:
                f.write(file_content)
            
            logger.info(f"Saved upload to temporary file: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Error saving upload to temp file: {str(e)}")
            raise
    
    def validate_pdf_file(self, file_path: str) -> bool:
        """Validate that a file is a valid PDF using existing Dolphin function
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            True if valid PDF, False otherwise
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return False
            
            # Use existing Dolphin function to check if it's a PDF
            if not is_pdf_file(file_path):
                return False
            
            # Additional validation by trying to convert to images
            images = self.convert_pdf_to_images(file_path)
            return len(images) > 0
            
        except Exception as e:
            logger.warning(f"PDF validation failed: {str(e)}")
            return False
    
    def get_file_info(self, file_path: str) -> dict:
        """Get information about a file
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file information
        """
        try:
            file_path_obj = Path(file_path)
            stat = file_path_obj.stat()
            
            info = {
                "filename": file_path_obj.name,
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "extension": file_path_obj.suffix,
                "exists": file_path_obj.exists()
            }
            
            # Add PDF-specific info if it's a PDF
            if file_path_obj.suffix.lower() == '.pdf' and info["exists"]:
                try:
                    doc = pymupdf.open(file_path)
                    info["pdf_pages"] = len(doc)
                    doc.close()
                except Exception:
                    info["pdf_pages"] = "unknown"
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            return {"error": str(e)}
    
    def cleanup_temp_file(self, file_path: str) -> bool:
        """Clean up a temporary file
        
        Args:
            file_path: Path to the temporary file
            
        Returns:
            True if successfully deleted, False otherwise
        """
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(f"Cleaned up temporary file: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error cleaning up temp file: {str(e)}")
            return False
    
    def create_temp_directory(self, prefix: str = "dolphin_") -> str:
        """Create a temporary directory
        
        Args:
            prefix: Prefix for the temporary directory name
            
        Returns:
            Path to the created temporary directory
        """
        try:
            temp_dir = tempfile.mkdtemp(prefix=prefix, dir=self.temp_dir)
            logger.info(f"Created temporary directory: {temp_dir}")
            return temp_dir
        except Exception as e:
            logger.error(f"Error creating temp directory: {str(e)}")
            raise
    
    def cleanup_temp_directory(self, dir_path: str) -> bool:
        """Clean up a temporary directory and all its contents
        
        Args:
            dir_path: Path to the temporary directory
            
        Returns:
            True if successfully deleted, False otherwise
        """
        try:
            import shutil
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
                logger.info(f"Cleaned up temporary directory: {dir_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error cleaning up temp directory: {str(e)}")
            return False
