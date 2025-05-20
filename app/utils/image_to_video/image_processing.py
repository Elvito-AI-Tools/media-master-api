"""
Image processing utilities for the image-to-video pipeline.
"""
import os
import logging
from PIL import Image
from typing import Tuple, Dict

from app.utils.download import download_image

logger = logging.getLogger(__name__)

async def process_image(image_url: str) -> Dict[str, any]:
    """
    Download and analyze an image for video conversion.
    
    Args:
        image_url: URL of the image to process
        
    Returns:
        Dictionary containing:
        - image_path: Path to the downloaded image
        - dimensions: Tuple of (width, height)
        - orientation: "landscape" or "portrait"
        - recommended_video_dims: Recommended video dimensions
    """
    try:
        # Download the image
        image_path = await download_image(image_url, temp_dir="temp")
        
        # Analyze image dimensions
        with Image.open(image_path) as img:
            width, height = img.size
        
        # Determine orientation and set dimensions
        if width > height:  # Landscape orientation
            orientation = "landscape"
            scale_dims = "7680x4320"  # 8K landscape dimensions
            output_dims = "1920x1080"  # Full HD
        else:  # Portrait orientation
            orientation = "portrait"
            scale_dims = "4320x7680"  # 8K portrait dimensions
            output_dims = "1080x1920"  # Full HD vertical video
        
        logger.info(f"Processed image: {width}x{height}, {orientation} orientation")
        
        return {
            "image_path": image_path,
            "dimensions": (width, height),
            "orientation": orientation,
            "scale_dims": scale_dims,
            "output_dims": output_dims
        }
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        raise 