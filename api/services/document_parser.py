"""
Document Parser

Handles document parsing logic using existing Dolphin module functions.
"""

import logging
from typing import Dict, List

from PIL import Image


from Dolphin.utils.utils import prepare_image
from Dolphin.demo_page_hf import process_elements
from ..processors import DolphinProcessor

logger = logging.getLogger(__name__)


class DocumentParser:
    """Handles document parsing operations using existing Dolphin functions"""
    
    def __init__(self, processor: DolphinProcessor):
        """Initialize document parser
        
        Args:
            processor: Dolphin processor instance
        """
        self.processor = processor
    
    def process_single_image(self, image: Image.Image, max_batch_size: int = 16) -> List[Dict]:
        """Process a single image for document parsing using existing Dolphin functions
        
        Args:
            image: PIL Image to process
            max_batch_size: Maximum batch size for processing
            
        Returns:
            List of parsed elements with their content
        """
        try:
            # Stage 1: Page-level layout and reading order parsing
            layout_output = self.processor.chat("Parse the reading order of this document.", image)
            
            # Stage 2: Element-level content parsing using existing Dolphin functions
            padded_image, dims = prepare_image(image)
            recognition_results = process_elements(
                layout_output, 
                padded_image, 
                dims, 
                self.processor.model, 
                max_batch_size, 
                None,  # save_dir - not needed for API
                None   # image_name - not needed for API
            )
            
            return recognition_results
            
        except Exception as e:
            logger.error(f"Error processing single image: {str(e)}")
            raise
