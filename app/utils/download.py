"""
Utilities for downloading files from URLs.
"""
import os
import tempfile
import logging
import uuid
from pathlib import Path
from typing import Optional
import requests
import aiohttp
from urllib.parse import urlparse, unquote
from PIL import Image
from fastapi import HTTPException

# Configure logging
logger = logging.getLogger(__name__)

async def download_image(url: str, temp_dir: str = "temp") -> str:
    """
    Download an image from a URL and save it to a temporary file.
    Supports local file paths, S3 URLs, and public URLs.
    
    Args:
        url: The URL or local path of the image to download
        temp_dir: Directory to save the temporary file (default: 'temp')
        
    Returns:
        Path to the downloaded/verified file
        
    Raises:
        HTTPException: If download fails or image is invalid
    """
    # Ensure the temp directory exists
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # Check if it's a local file (already downloaded)
        if os.path.exists(url):
            logger.info(f"Using existing local file: {url}")
            # Verify it's a valid image
            try:
                img = Image.open(url)
                img.verify()  # Verify it's a valid image
                return url
            except Exception as e:
                logger.error(f"Local file is not a valid image: {e}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Local file is not a valid image: {str(e)}"
                )
        
        # Get file extension from URL
        file_extension = _get_file_extension_from_url(url) or ".jpg"
        temp_file_path = os.path.join(temp_dir, f"image_{uuid.uuid4().hex}{file_extension}")
        
        # Parse URL to check if it's from our S3 bucket or Minio
        parsed_url = urlparse(url)
        hostname = parsed_url.netloc
        path = parsed_url.path
        
        # Check if URL is from our internal systems
        is_from_minio = "minio" in hostname
        bucket_name = os.environ.get("S3_BUCKET_NAME", "")
        is_from_our_s3 = bucket_name and bucket_name in hostname
        
        if is_from_minio:
            # Use storage_manager for Minio requests instead of direct HTTP requests
            logger.info(f"Detected Minio URL, using storage_manager to download image: {url}")
            
            # Extract the object key from the path
            # Remove bucket name from path if present
            object_path = path.lstrip('/')
            if object_path.startswith(f"{bucket_name}/"):
                object_key = object_path[len(bucket_name)+1:]
            else:
                object_key = object_path
            
            # URL decode the object key to handle spaces and special characters
            object_key = unquote(object_key)
                
            logger.info(f"Extracting object key from path: {object_key}")
            
            from app.utils.storage import storage_manager
            
            # Download using storage_manager
            try:
                storage_manager.client.fget_object(
                    bucket_name=storage_manager.bucket_name,
                    object_name=object_key,
                    file_path=temp_file_path
                )
                logger.info(f"Successfully downloaded image from Minio: {temp_file_path}")
            except Exception as e:
                logger.error(f"Error using storage_manager to download image: {e}")
                # If URL has a presigned signature, try direct HTTP download as fallback
                if '?' in url:
                    logger.info("Trying direct HTTP download with presigned URL as fallback")
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url) as response:
                            if response.status != 200:
                                raise HTTPException(
                                    status_code=400,
                                    detail=f"Failed to download image: HTTP {response.status}"
                                )
                            
                            # Check if the response is an image
                            content_type = response.headers.get('Content-Type', '')
                            if not content_type.startswith('image/'):
                                logger.error(f"URL does not point to an image. Content-Type: {content_type}")
                                raise HTTPException(
                                    status_code=400, 
                                    detail=f"URL does not point to an image. Content-Type: {content_type}"
                                )
                            
                            # Read image data and save to file
                            image_data = await response.read()
                            with open(temp_file_path, "wb") as f:
                                f.write(image_data)
                    
                    logger.info(f"Successfully downloaded image with presigned URL: {temp_file_path}")
                else:
                    raise
        elif is_from_our_s3:
            # Import here to avoid circular imports
            from app.services.s3 import s3_service
            
            # Extract object key from path
            object_key = path.lstrip('/')
            logger.info(f"Detected S3 URL, downloading image: {object_key}")
            
            # Use S3 service to download the file
            temp_file_path = await s3_service.download_file(object_key, temp_file_path)
        else:
            # Download from public URL
            logger.info(f"Downloading image from URL: {url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Failed to download image: HTTP {response.status}"
                        )
                    
                    # Check if the response is an image
                    content_type = response.headers.get('Content-Type', '')
                    if not content_type.startswith('image/'):
                        logger.error(f"URL does not point to an image. Content-Type: {content_type}")
                        raise HTTPException(
                            status_code=400, 
                            detail=f"URL does not point to an image. Content-Type: {content_type}"
                        )
                    
                    # Read image data and save to file
                    image_data = await response.read()
                    with open(temp_file_path, "wb") as f:
                        f.write(image_data)
        
        # Verify it's a valid image
        try:
            img = Image.open(temp_file_path)
            img.verify()  # Verify it's a valid image
            logger.info(f"Image downloaded successfully to {temp_file_path}")
            return temp_file_path
        except Exception as e:
            # Clean up invalid image file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            logger.error(f"Downloaded file is not a valid image: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Downloaded file is not a valid image: {str(e)}"
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions directly
        raise
    except Exception as e:
        logger.error(f"Error downloading image: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error downloading image: {str(e)}"
        )

# Keep backward compatibility with the old function name
async def download_image_from_url(url: str, temp_dir: str = "temp") -> str:
    """
    Backward compatibility wrapper for download_image.
    
    Args:
        url: The URL of the image to download
        temp_dir: Directory to save the temporary file (default: 'temp')
        
    Returns:
        Path to the downloaded file
        
    Raises:
        HTTPException: If download fails
    """
    return await download_image(url, temp_dir)

def _get_file_extension_from_url(url: str) -> Optional[str]:
    """
    Extract the file extension from a URL.
    
    Args:
        url: The URL to extract the extension from
        
    Returns:
        File extension with dot (e.g., '.jpg') or None if can't be determined
    """
    path = url.split('?')[0]  # Remove query parameters
    file_extension = os.path.splitext(path)[1].lower()
    
    # Validate the extension is for an image
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    if file_extension in valid_extensions:
        return file_extension
    
    return None 