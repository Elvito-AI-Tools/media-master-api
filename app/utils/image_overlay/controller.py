"""
Controller for image overlay processing.

This module orchestrates the process of overlaying images on a base image.
"""
import os
import logging
import uuid
from typing import Dict, Any, List
import asyncio
from PIL import Image, ImageEnhance

from app.utils.media import download_media_file
from app.utils.storage import storage_manager
from app.utils.image_overlay.image_processing import process_overlay_image
from app.utils.image_to_video.image_processing import process_image

# Configure logging
logger = logging.getLogger(__name__)

async def process_image_overlay(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process the overlay of images on top of a base image.
    
    Args:
        params: Dict containing the following keys:
            - base_image_url: URL of the base image
            - overlay_images: List of overlay images with position information
            - output_format: Output image format (e.g., 'png', 'jpg', 'webp')
            - output_quality: Quality for lossy formats (1-100)
            - output_width: Width of the output image (optional)
            - output_height: Height of the output image (optional)
            - maintain_aspect_ratio: Whether to maintain the aspect ratio when resizing
    
    Returns:
        Dict containing the result information
    """
    try:
        # Generate a unique identifier for this job
        job_id = str(uuid.uuid4())
        temp_dir = os.path.join("temp", job_id)
        os.makedirs(temp_dir, exist_ok=True)
        
        # Download base image using process_image from image_to_video utilities
        logger.info(f"Downloading base image from {params['base_image_url']}")
        base_image_result = await process_image(params['base_image_url'])
        base_image_path = base_image_result['image_path']
        
        # Load the base image
        base_image = Image.open(base_image_path).convert("RGBA")
        
        # Get original dimensions
        original_width, original_height = base_image.size
        logger.info(f"Base image dimensions: {original_width}x{original_height}")
        
        # Process overlay images
        overlay_images = params['overlay_images']
        
        # Sort overlay images by z-index
        overlay_images = sorted(overlay_images, key=lambda x: x.get('z_index', 0))
        
        # Apply each overlay
        for overlay_info in overlay_images:
            # Process one overlay at a time
            base_image = await process_overlay_image(base_image, overlay_info, temp_dir)
        
        # Apply any resizing if specified
        output_width = params.get('output_width')
        output_height = params.get('output_height')
        maintain_aspect_ratio = params.get('maintain_aspect_ratio', True)
        
        if output_width or output_height:
            if maintain_aspect_ratio:
                # Calculate dimensions maintaining aspect ratio
                if output_width and not output_height:
                    output_height = int(original_height * (output_width / original_width))
                elif output_height and not output_width:
                    output_width = int(original_width * (output_height / original_height))
            
            # Resize the image
            if output_width and output_height:
                logger.info(f"Resizing output image to {output_width}x{output_height}")
                base_image = base_image.resize((output_width, output_height), Image.LANCZOS)
        
        # Save the result image
        output_format = params.get('output_format', 'png').upper()
        if output_format == 'JPG':
            output_format = 'JPEG'  # PIL uses JPEG, not JPG
        
        output_quality = params.get('output_quality', 90)
        
        # Convert to RGB if saving as JPEG (which doesn't support alpha)
        if output_format == 'JPEG':
            # Create a white background
            white_bg = Image.new('RGB', base_image.size, (255, 255, 255))
            # Paste the image with alpha onto the white background
            white_bg.paste(base_image, (0, 0), base_image)
            base_image = white_bg
        
        # Save the result to a temporary file
        output_filename = f"{job_id}.{output_format.lower()}"
        output_path = os.path.join(temp_dir, output_filename)
        
        # Save with quality parameter for JPEG
        if output_format == 'JPEG':
            base_image.save(output_path, format=output_format, quality=output_quality)
        else:
            base_image.save(output_path, format=output_format)
        
        # Upload the result to S3
        logger.info(f"Uploading result image to storage")
        s3_path = f"image-overlay-results/{output_filename}"
        result_url = storage_manager.upload_file(output_path, s3_path)
        
        # Remove signature parameters from URL if present
        if '?' in result_url:
            result_url = result_url.split('?')[0]
        
        # Get final dimensions
        final_width, final_height = base_image.size
        
        # Return the result
        result = {
            "image_url": result_url,
            "width": final_width,
            "height": final_height,
            "format": output_format.lower(),
            "storage_path": s3_path
        }
        
        # Clean up temporary files
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"Failed to clean up temporary files: {str(e)}")
        
        return result
    
    except Exception as e:
        logger.error(f"Error in process_image_overlay: {str(e)}", exc_info=True)
        raise 