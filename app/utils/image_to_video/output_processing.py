"""
Output processing and cleanup utilities for the image-to-video pipeline.
"""
import os
import json
import logging
import subprocess
from typing import Dict, Any, List, Optional, Tuple

from app.utils.storage import storage_manager

logger = logging.getLogger(__name__)

async def upload_to_storage(file_path: str) -> Tuple[str, str]:
    """
    Upload a file to storage and return the URL and object name.
    
    Args:
        file_path: Path to the file to upload
        
    Returns:
        URL of the uploaded file
    """
    try:
        # Generate a unique object name
        filename = os.path.basename(file_path)
        object_name = f"videos/{filename}"
        
        # Upload to storage
        result_url = storage_manager.upload_file(file_path, object_name)
        
        # Remove signature parameters from URL
        if '?' in result_url:
            result_url = result_url.split('?')[0]
        
        logger.info(f"Uploaded {file_path} to storage as {object_name}")
        return result_url, object_name
        
    except Exception as e:
        logger.error(f"Error uploading file to storage: {e}")
        raise

def get_video_metadata(video_path: str) -> Dict[str, Any]:
    """
    Get metadata for a video file.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Dictionary containing video metadata
    """
    try:
        # Use FFprobe to get video metadata
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration,size,bit_rate:stream=width,height,codec_name,avg_frame_rate",
            "-of", "json",
            video_path
        ]
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        info = json.loads(result.stdout)
        
        metadata = {
            "duration": float(info["format"]["duration"]) if "format" in info and "duration" in info["format"] else None,
            "size_bytes": int(info["format"]["size"]) if "format" in info and "size" in info["format"] else None,
            "bit_rate": int(info["format"]["bit_rate"]) if "format" in info and "bit_rate" in info["format"] else None,
        }
        
        # Get video stream info if available
        if "streams" in info:
            for stream in info["streams"]:
                if stream.get("codec_type") == "video":
                    metadata["width"] = stream.get("width")
                    metadata["height"] = stream.get("height")
                    metadata["codec"] = stream.get("codec_name")
                    
                    # Parse frame rate
                    if "avg_frame_rate" in stream:
                        try:
                            num, den = stream["avg_frame_rate"].split("/")
                            metadata["frame_rate"] = round(float(num) / float(den), 2)
                        except (ValueError, ZeroDivisionError):
                            metadata["frame_rate"] = None
                    
                    break
        
        return metadata
        
    except Exception as e:
        logger.error(f"Error getting video metadata: {e}")
        return {}

def cleanup_temp_files(file_paths: List[str]) -> None:
    """
    Clean up temporary files.
    
    Args:
        file_paths: List of file paths to clean up
    """
    for file_path in file_paths:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Removed temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temporary file {file_path}: {e}")
        elif file_path:
            logger.warning(f"Temporary file not found during cleanup: {file_path}")

async def prepare_result(
    video_path: str, 
    has_audio: bool = False, 
    has_captions: bool = False, 
    srt_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Prepare the final result dictionary.
    
    Args:
        video_path: Path to the final video file
        has_audio: Whether the video has audio
        has_captions: Whether the video has captions
        srt_url: URL of the subtitle file (optional)
        
    Returns:
        Dictionary containing result information
    """
    try:
        # Upload video to storage
        video_url, object_name = await upload_to_storage(video_path)
        
        # Get video metadata
        metadata = get_video_metadata(video_path)
        

        # Prepare result
        result = {
            "final_video_url": video_url,
            "final_video_path": object_name,
            "has_audio": has_audio,
            "has_captions": has_captions,
            "video_duration": metadata.get("duration"),
        }
        
        # Add SRT URL if available
        if srt_url:
            result["srt_url"] = srt_url
        
        # Add additional metadata
        result["metadata"] = metadata
        
        return result
        
    except Exception as e:
        logger.error(f"Error preparing result: {e}")
        raise 