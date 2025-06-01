"""
Utilities for media file operations.
"""
import os
import logging
import tempfile
import subprocess
import requests
from urllib.parse import urlparse
from typing import Tuple, Optional

from app.services.s3 import s3_service
from app.utils.youtube import is_youtube_url

# Configure logging
logger = logging.getLogger(__name__)

# Define supported file extensions
SUPPORTED_AUDIO_FORMATS = ['.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg']
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.webm', '.mov', '.avi', '.mkv']
SUPPORTED_FORMATS = SUPPORTED_AUDIO_FORMATS + SUPPORTED_VIDEO_FORMATS

async def download_media_file(media_url: str, temp_dir: str = "temp") -> Tuple[str, str]:
    """
    Download media file from URL.
    
    Args:
        media_url: URL of the media file
        temp_dir: Directory to save temporary files
        
    Returns:
        Tuple of (local file path, file extension)
        
    Raises:
        RuntimeError: If download fails
    """
    # Parse URL to get hostname and path
    parsed_url = urlparse(media_url)
    hostname = parsed_url.netloc
    path = parsed_url.path
    
    # Get file extension
    _, file_extension = os.path.splitext(path)
    file_extension = file_extension.lower()
    
    # If no extension or not recognized, use defaults
    if not file_extension:
        file_extension = ".mp4"  # Default to mp4 if no extension
    
    # Create temporary file
    os.makedirs(temp_dir, exist_ok=True)
    temp_file = tempfile.NamedTemporaryFile(suffix=file_extension, delete=False, dir=temp_dir)
    temp_file.close()
    local_file_path = temp_file.name
    
    logger.info(f"Downloading media from {media_url} to {local_file_path}")
    
    # Check if URL is from our internal systems
    is_from_minio = "minio" in hostname
    bucket_name = os.environ.get("S3_BUCKET_NAME", "")
    is_from_our_s3 = bucket_name and bucket_name in hostname
    
    try:
        if is_from_minio:
            # Use storage_manager for Minio requests instead of direct HTTP requests
            logger.info(f"Detected Minio URL, using storage_manager to download media: {media_url}")
            
            # Extract the object key from the path
            # Remove bucket name from path if present
            object_path = path.lstrip('/')
            if object_path.startswith(f"{bucket_name}/"):
                object_key = object_path[len(bucket_name)+1:]
            else:
                object_key = object_path
                
            logger.info(f"Extracting object key from path: {object_key}")
            
            from app.utils.storage import storage_manager
            
            # Download using storage_manager
            try:
                storage_manager.client.fget_object(
                    bucket_name=storage_manager.bucket_name,
                    object_name=object_key,
                    file_path=local_file_path
                )
                logger.info(f"Successfully downloaded media from Minio: {local_file_path}")
            except Exception as e:
                logger.error(f"Error using storage_manager to download media: {e}")
                # If URL has a presigned signature, try direct HTTP download as fallback
                if '?' in media_url:
                    logger.info("Trying direct HTTP download with presigned URL as fallback")
                    response = requests.get(media_url, timeout=30)
                    response.raise_for_status()
                    
                    with open(local_file_path, 'wb') as f:
                        f.write(response.content)
                    
                    logger.info(f"Successfully downloaded media with presigned URL: {local_file_path}")
                else:
                    raise
        elif is_from_our_s3:
            # Extract object key from path
            object_key = path.lstrip('/')
            logger.info(f"Detected S3 URL, downloading object: {object_key}")
            
            # Use S3 service to download the file
            from app.services.s3 import s3_service
            local_file_path = await s3_service.download_file(object_key, local_file_path)
        elif is_youtube_url(media_url):
            # Use yt-dlp for YouTube URLs
            logger.info(f"Detected YouTube URL, using yt-dlp: {media_url}")
            download_with_ytdlp(media_url, local_file_path)
        else:
            # Use direct HTTP download for external URLs (like Cloudinary)
            logger.info(f"Detected external URL, using direct HTTP download: {media_url}")
            response = requests.get(media_url, timeout=30)
            response.raise_for_status()
            
            with open(local_file_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Successfully downloaded media via HTTP: {local_file_path}")
            
        logger.info(f"Media downloaded successfully to {local_file_path}")
        return local_file_path, file_extension
    except Exception as e:
        # Clean up temporary file if download failed
        if os.path.exists(local_file_path):
            os.unlink(local_file_path)
        logger.error(f"Failed to download media from {media_url}: {e}")
        raise RuntimeError(f"Failed to download media: {e}")

def download_with_ytdlp(url: str, output_path: str):
    """
    Download media using yt-dlp.
    
    Args:
        url: URL to download from
        output_path: Path to save the downloaded file
        
    Raises:
        RuntimeError: If download fails
    """
    try:
        # For videos, use best video with audio
        format_option = "bestaudio/best"
        if output_path.lower().endswith(tuple(SUPPORTED_VIDEO_FORMATS)):
            format_option = "bestvideo+bestaudio/best"
            
        # Run yt-dlp with appropriate options
        cmd = [
            "yt-dlp",
            "-o", output_path,
            "--no-playlist",
            "--quiet",
            "--format", format_option,
            url
        ]
        
        logger.info(f"Running yt-dlp command: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True)
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            logger.info(f"Download successful, file size: {file_size} bytes")
        else:
            logger.error("Download failed: Output file does not exist")
            raise RuntimeError("Download completed but file doesn't exist")
    except subprocess.CalledProcessError as e:
        logger.error(f"yt-dlp failed: {e.stderr.decode() if e.stderr else str(e)}")
        raise RuntimeError(f"yt-dlp failed: {e.stderr.decode() if e.stderr else str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during download: {e}")
        raise 

async def download_subtitle_file(subtitle_url: str, temp_dir: str = "temp") -> str:
    """
    Download a subtitle file from a URL.
    
    Args:
        subtitle_url: URL of the subtitle file to download
        temp_dir: Directory to save temporary files
        
    Returns:
        Local path to the downloaded subtitle file
        
    Raises:
        RuntimeError: If download fails or format is unsupported
    """
    # Parse URL to get hostname and path
    parsed_url = urlparse(subtitle_url)
    hostname = parsed_url.netloc
    path = parsed_url.path
    file_extension = os.path.splitext(path)[1].lower()
    
    # Validate subtitle format
    if file_extension not in [".srt", ".ass", ".vtt"]:
        raise RuntimeError(f"Unsupported subtitle format: {file_extension}")
    
    # Create temporary file
    os.makedirs(temp_dir, exist_ok=True)
    temp_file = tempfile.NamedTemporaryFile(
        delete=False, 
        suffix=file_extension,
        dir=temp_dir
    )
    temp_file_path = temp_file.name
    temp_file.close()
    
    logger.info(f"Downloading subtitle file from URL: {subtitle_url}")
    
    # Check if URL is from our internal systems
    is_from_minio = "minio" in hostname
    bucket_name = os.environ.get("S3_BUCKET_NAME", "")
    is_from_our_s3 = bucket_name and bucket_name in hostname
    
    try:
        if is_from_minio:
            # Use storage_manager for Minio requests instead of direct HTTP requests
            logger.info(f"Detected Minio URL, using storage_manager to download subtitle: {subtitle_url}")
            
            # Extract the object key from the path
            # Remove bucket name from path if present
            object_path = path.lstrip('/')
            if object_path.startswith(f"{bucket_name}/"):
                object_key = object_path[len(bucket_name)+1:]
            else:
                object_key = object_path
                
            logger.info(f"Extracting object key from path: {object_key}")
            
            from app.utils.storage import storage_manager
            
            # Download using storage_manager
            try:
                storage_manager.client.fget_object(
                    bucket_name=storage_manager.bucket_name,
                    object_name=object_key,
                    file_path=temp_file_path
                )
                logger.info(f"Successfully downloaded subtitle from Minio: {temp_file_path}")
            except Exception as e:
                logger.error(f"Error using storage_manager to download subtitle: {e}")
                # If URL has a presigned signature, try direct HTTP download as fallback
                if '?' in subtitle_url:
                    logger.info("Trying direct HTTP download with presigned URL as fallback")
                    import requests
                    response = requests.get(subtitle_url, timeout=30)
                    response.raise_for_status()
                    
                    with open(temp_file_path, 'wb') as f:
                        f.write(response.content)
                    
                    logger.info(f"Successfully downloaded subtitle with presigned URL: {temp_file_path}")
                else:
                    raise
        elif is_from_our_s3:
            # Extract object key from path and use S3 service
            object_key = path.lstrip('/')
            logger.info(f"Detected S3 URL, downloading subtitle: {object_key}")
            
            from app.services.s3 import s3_service
            temp_file_path = await s3_service.download_file(object_key, temp_file_path)
        else:
            # Use regular HTTP download for non-S3 URLs
            import requests
            response = requests.get(subtitle_url, timeout=30)
            response.raise_for_status()
            
            with open(temp_file_path, 'wb') as f:
                f.write(response.content)
        
        logger.info(f"Subtitle file downloaded successfully to {temp_file_path}")
        return temp_file_path
    except Exception as e:
        # Clean up temporary file if download failed
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        logger.error(f"Failed to download subtitle file from {subtitle_url}: {e}")
        raise RuntimeError(f"Failed to download subtitle file: {str(e)}") 