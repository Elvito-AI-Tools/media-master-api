"""
Service for overlaying images on top of a base image.

This service handles the process of overlaying one or more images onto a base image
with control over positioning, size, rotation, and opacity.
"""
import logging
import asyncio
from typing import Dict, Any

from app.utils.image_overlay import process_image_overlay

# Configure logging
logger = logging.getLogger(__name__)

class ImageOverlayService:
    """
    Service for overlaying images on top of a base image.
    
    This service processes requests to overlay one or more images onto a base image,
    with control over position, size, rotation, and opacity of each overlay.
    """
    
    def __init__(self):
        """Initialize the image overlay service."""
        self.executor = asyncio.get_event_loop().run_in_executor
        logger.info("Image overlay service initialized")
    
    async def overlay_images(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an image overlay request.
        
        Args:
            params: Job parameters including:
                - base_image_url: URL of the base image
                - overlay_images: List of overlay images with position information
                - output_format: Output image format (e.g., 'png', 'jpg', 'webp')
                - output_quality: Quality for lossy formats (1-100)
                - output_width: Width of the output image (optional)
                - output_height: Height of the output image (optional)
                - maintain_aspect_ratio: Whether to maintain aspect ratio when resizing
                
        Returns:
            Dictionary with result information
        """
        # Delegate to the modular implementation
        return await process_image_overlay(params)

# Create a singleton instance
image_overlay_service = ImageOverlayService() 