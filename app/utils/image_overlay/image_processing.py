"""
Image processing utilities for the image overlay functionality.

This module contains functions for processing and manipulating images
for overlay operations.
"""
import os
import logging
import math
from typing import Dict, Any, Tuple
from PIL import Image, ImageOps

from app.utils.download import download_image

# Configure logging
logger = logging.getLogger(__name__)

async def process_overlay_image(base_image: Image.Image, overlay_info: Dict[str, Any], temp_dir: str) -> Image.Image:
    """
    Process a single overlay image and apply it to the base image.
    
    Args:
        base_image: The PIL Image object of the base image
        overlay_info: Dictionary with overlay information including:
            - url: URL of the overlay image
            - x, y: Position (0-1) where to place the overlay
            - width, height: Optional size (0-1) relative to base image
            - rotation: Optional rotation angle in degrees
            - opacity: Optional opacity (0-1)
        temp_dir: Directory for temporary files
    
    Returns:
        Updated PIL Image with the overlay applied
    """
    try:
        # Download the overlay image
        url = overlay_info['url']
        logger.info(f"Downloading overlay image from {url}")
        overlay_path = await download_image(url, temp_dir=temp_dir)
        
        # Open the overlay image and ensure it has alpha channel
        overlay_img = Image.open(overlay_path).convert("RGBA")
        
        # Get the base image dimensions
        base_width, base_height = base_image.size
        
        # Process overlay sizing
        overlay_width, overlay_height = calculate_overlay_size(
            base_width, 
            base_height, 
            overlay_img.width, 
            overlay_img.height,
            overlay_info.get('width'),
            overlay_info.get('height')
        )
        
        # Resize the overlay if needed
        if overlay_width != overlay_img.width or overlay_height != overlay_img.height:
            overlay_img = overlay_img.resize((overlay_width, overlay_height), Image.LANCZOS)
        
        # Apply rotation if specified
        rotation = overlay_info.get('rotation', 0.0)
        if rotation != 0:
            # Create a larger transparent image to handle rotation without clipping
            diagonal = int(math.sqrt(overlay_width**2 + overlay_height**2))
            rot_overlay = Image.new('RGBA', (diagonal, diagonal), (0, 0, 0, 0))
            
            # Paste the overlay in the center of the rotation canvas
            offset = ((diagonal - overlay_width) // 2, (diagonal - overlay_height) // 2)
            rot_overlay.paste(overlay_img, offset, overlay_img)
            
            # Rotate the overlay
            overlay_img = rot_overlay.rotate(rotation, resample=Image.BICUBIC, expand=False)
        
        # Calculate position in pixels
        x_pos = int(overlay_info['x'] * base_width)
        y_pos = int(overlay_info['y'] * base_height)
        
        # Adjust position to center the overlay at the specified point
        x_pos -= overlay_img.width // 2
        y_pos -= overlay_img.height // 2
        
        # Apply opacity/transparency
        opacity = overlay_info.get('opacity', 1.0)
        if opacity < 1.0:
            # Create a copy of the overlay with the specified opacity
            overlay_img = apply_opacity(overlay_img, opacity)
        
        # Create a new image with the overlay applied
        new_base = base_image.copy()
        
        # Paste the overlay onto the base image
        new_base.paste(overlay_img, (x_pos, y_pos), overlay_img)
        
        return new_base
    
    except Exception as e:
        logger.error(f"Error processing overlay image: {str(e)}", exc_info=True)
        raise

def calculate_overlay_size(
    base_width: int, 
    base_height: int, 
    overlay_width: int, 
    overlay_height: int,
    rel_width: float = None,
    rel_height: float = None
) -> Tuple[int, int]:
    """
    Calculate the size of the overlay image based on relative width/height.
    
    Args:
        base_width: Width of the base image
        base_height: Height of the base image
        overlay_width: Original width of the overlay image
        overlay_height: Original height of the overlay image
        rel_width: Relative width (0-1) of the overlay compared to the base
        rel_height: Relative height (0-1) of the overlay compared to the base
    
    Returns:
        Tuple of (width, height) for the resized overlay
    """
    # If neither width nor height is specified, keep original size
    if rel_width is None and rel_height is None:
        return overlay_width, overlay_height
    
    # Calculate aspect ratio of the overlay
    aspect_ratio = overlay_width / overlay_height
    
    # If only width is specified, calculate height based on aspect ratio
    if rel_width is not None and rel_height is None:
        new_width = int(base_width * rel_width)
        new_height = int(new_width / aspect_ratio)
        return new_width, new_height
    
    # If only height is specified, calculate width based on aspect ratio
    if rel_height is not None and rel_width is None:
        new_height = int(base_height * rel_height)
        new_width = int(new_height * aspect_ratio)
        return new_width, new_height
    
    # If both width and height are specified, use them directly
    new_width = int(base_width * rel_width)
    new_height = int(base_height * rel_height)
    return new_width, new_height

def apply_opacity(img: Image.Image, opacity: float) -> Image.Image:
    """
    Apply opacity to an RGBA image.
    
    Args:
        img: The RGBA PIL Image
        opacity: Opacity value (0-1)
    
    Returns:
        RGBA image with applied opacity
    """
    # Get the alpha channel
    alpha = img.getchannel('A')
    
    # Apply the opacity
    alpha = alpha.point(lambda x: int(x * opacity))
    
    # Create a new image with the modified alpha channel
    result = img.copy()
    result.putalpha(alpha)
    
    return result 