"""
Controller for video overlay processing.

This module orchestrates the process of overlaying videos on a base image.
"""
import os
import logging
import uuid
import subprocess
import asyncio
from typing import Dict, Any, List, Optional
from PIL import Image

from app.utils.storage import storage_manager
from app.utils.image_to_video.image_processing import process_image
from app.utils.video_overlay.video_processing import (
    process_overlay_video, 
    build_ffmpeg_filter_complex
)
from app.utils.media import download_media_file

# Configure logging
logger = logging.getLogger(__name__)

async def process_video_overlay(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process the overlay of videos on top of a base image.
    
    Args:
        params: Dict containing the following keys:
            - base_image_url: URL of the base image
            - overlay_videos: List of overlay videos with position and timing information
            - output_duration: Duration of the output video (optional)
            - frame_rate: Frame rate of the output video
            - output_width: Width of the output video (optional)
            - output_height: Height of the output video (optional)
            - maintain_aspect_ratio: Whether to maintain aspect ratio when resizing
            - background_audio_url: URL of background audio (optional)
            - background_audio_volume: Volume for background audio
    
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
        
        # Get base image dimensions
        with Image.open(base_image_path) as img:
            original_width, original_height = img.size
        
        logger.info(f"Base image dimensions: {original_width}x{original_height}")
        
        # Apply any resizing if specified
        output_width = params.get('output_width', original_width)
        output_height = params.get('output_height', original_height)
        maintain_aspect_ratio = params.get('maintain_aspect_ratio', True)
        
        if maintain_aspect_ratio and (params.get('output_width') or params.get('output_height')):
            # Calculate dimensions maintaining aspect ratio
            if params.get('output_width') and not params.get('output_height'):
                output_height = int(original_height * (output_width / original_width))
            elif params.get('output_height') and not params.get('output_width'):
                output_width = int(original_width * (output_height / original_height))
        
        logger.info(f"Output video dimensions: {output_width}x{output_height}")
        
        # Process overlay videos
        overlay_videos = params['overlay_videos']
        processed_overlays = []
        
        # Determine output duration
        max_overlay_duration = 0.0
        for overlay_info in overlay_videos:
            processed_overlay = await process_overlay_video(
                overlay_info, output_width, output_height, temp_dir
            )
            processed_overlays.append(processed_overlay)
            
            # Log audio information for debugging
            has_audio = processed_overlay['metadata'].get('has_audio', False)
            volume = processed_overlay.get('volume', 0.0)
            logger.info(f"Overlay video: has_audio={has_audio}, volume={volume}, will_use_audio={has_audio and volume > 0}")
            
            # Calculate effective duration for this overlay
            overlay_duration = processed_overlay['metadata'].get('duration', 0.0)
            start_time = processed_overlay.get('start_time', 0.0)
            end_time = processed_overlay.get('end_time')
            
            if end_time is not None:
                effective_duration = end_time
            else:
                effective_duration = start_time + overlay_duration
            
            max_overlay_duration = max(max_overlay_duration, effective_duration)
        
        output_duration = params.get('output_duration', max_overlay_duration)
        if output_duration <= 0:
            output_duration = 10.0  # Default fallback
        
        logger.info(f"Output video duration: {output_duration} seconds")
        
        # Download background audio if provided
        background_audio_path = None
        if params.get('background_audio_url'):
            logger.info(f"Downloading background audio from {params['background_audio_url']}")
            background_audio_path, _ = await download_media_file(
                params['background_audio_url'], temp_dir=temp_dir
            )
        
        # Build FFmpeg filter complex
        frame_rate = params.get('frame_rate', 30)
        background_audio_volume = params.get('background_audio_volume', 0.2)
        
        filter_complex, input_files = build_ffmpeg_filter_complex(
            output_width,
            output_height,
            output_duration,
            frame_rate,
            processed_overlays,
            background_audio_path,
            background_audio_volume
        )
        
        # Create output file
        output_filename = f"{job_id}.mp4"
        output_path = os.path.join(temp_dir, output_filename)
        
        # Build FFmpeg command
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output if exists
            "-loop", "1",  # Loop the base image
            "-i", base_image_path,  # Base image input
        ]
        
        # Add overlay video inputs
        for input_file in input_files:
            cmd.extend(["-i", input_file])
        
        # Add filter complex and output options
        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "[vout]",  # Map video output
        ])
        
        # Add audio mapping if there are audio inputs
        has_audio = any(overlay['volume'] > 0 and overlay['metadata'].get('has_audio', False) for overlay in processed_overlays) or background_audio_path
        if has_audio:
            cmd.extend(["-map", "[aout]"])
        
        # Add encoding options
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-r", str(frame_rate),
            "-t", str(output_duration),
        ])
        
        if has_audio:
            cmd.extend([
                "-c:a", "aac",
                "-b:a", "192k",
            ])
        
        cmd.extend([
            "-movflags", "+faststart",
            output_path
        ])
        
        # Log and run FFmpeg command
        logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown FFmpeg error"
            logger.error(f"FFmpeg command failed: {error_msg}")
            raise RuntimeError(f"FFmpeg command failed: {error_msg}")
        
        # Verify output file exists and has content
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Output video was not created at {output_path}")
        
        file_size = os.path.getsize(output_path)
        if file_size == 0:
            raise RuntimeError(f"Output video was created but is empty: {output_path}")
        
        logger.info(f"Successfully created video at {output_path} ({file_size} bytes)")
        
        # Upload the result to S3
        logger.info(f"Uploading result video to storage")
        s3_path = f"video-overlay-results/{output_filename}"
        result_url = storage_manager.upload_file(output_path, s3_path)
        
        # Remove signature parameters from URL if present
        if '?' in result_url:
            result_url = result_url.split('?')[0]
        
        # Return the result
        result = {
            "video_url": result_url,
            "width": output_width,
            "height": output_height,
            "duration": output_duration,
            "frame_rate": frame_rate,
            "has_audio": has_audio,
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
        logger.error(f"Error in process_video_overlay: {str(e)}", exc_info=True)
        raise 