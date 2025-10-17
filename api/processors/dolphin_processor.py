"""
Dolphin Model Processor

Wrapper around the existing Dolphin module's DOLPHIN class.
"""

import logging
from typing import List
from PIL import Image

from Dolphin.demo_page_hf import DOLPHIN

logger = logging.getLogger(__name__)


class DolphinProcessor:
    """Wrapper around the existing Dolphin module's DOLPHIN class"""
    
    def __init__(self, model_path: str):
        """Initialize the Dolphin model using the existing DOLPHIN class
        
        Args:
            model_path: Path to the Dolphin model directory
        """
        self.model_path = model_path
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the Dolphin model using the existing DOLPHIN class"""
        try:
            logger.info(f"Loading Dolphin model from {self.model_path}")
            self.model = DOLPHIN(self.model_path)
            logger.info(f"Model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise RuntimeError(f"Failed to load Dolphin model: {str(e)}")
    
    def chat(self, prompt: str, image: Image.Image) -> str:
        """Process an image with the given prompt using the existing DOLPHIN chat method
        
        Args:
            prompt: Text prompt to guide the model
            image: PIL Image to process
            
        Returns:
            Generated text from the model
        """
        try:
            return self.model.chat(prompt, image)
        except Exception as e:
            logger.error(f"Error in chat processing: {str(e)}")
            raise
    
    def chat_batch(self, prompts: List[str], images: List[Image.Image]) -> List[str]:
        """Process multiple images with prompts in batch using the existing DOLPHIN chat method
        
        Args:
            prompts: List of text prompts
            images: List of PIL Images
            
        Returns:
            List of generated texts
        """
        try:
            return self.model.chat(prompts, images)
        except Exception as e:
            logger.error(f"Error in batch chat processing: {str(e)}")
            raise
    
    def get_device_info(self) -> dict:
        """Get information about the current device
        
        Returns:
            Dictionary with device information
        """
        return {
            "device": self.model.device,
            "cuda_available": hasattr(self.model, 'device') and 'cuda' in str(self.model.device),
            "model_path": self.model_path
        }
