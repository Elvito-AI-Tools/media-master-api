"""
Video generation utilities for the image-to-video pipeline.
"""
import os
import uuid
import json
import logging
import asyncio
import subprocess
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

async def create_video_with_effects(
    image_path: str,
    video_length: float,
    frame_rate: int,
    zoom_speed: float,
    output_dims: str,
    scale_dims: str,
    effect_type: str = "none",
    pan_direction: Optional[str] = None,
    ken_burns_keypoints: Optional[List[Dict[str, float]]] = None
) -> str:
    """
    Create a video from an image with various motion effects.
    
    Args:
        image_path: Path to the input image
        video_length: Length of output video in seconds
        frame_rate: Frame rate of output video
        zoom_speed: Speed of zoom effect (0-100)
        output_dims: Output video dimensions (e.g., "1920x1080")
        scale_dims: Scale dimensions for high-quality processing
        effect_type: Type of animation effect to apply ('none', 'zoom', 'pan', 'ken_burns')
        pan_direction: Direction of pan effect when effect_type is 'pan'
        ken_burns_keypoints: List of keypoints for Ken Burns effect when effect_type is 'ken_burns'
        
    Returns:
        Path to the generated video file
    """
    try:
        # Calculate total frames
        total_frames = int(frame_rate * video_length)
        
        # Normalize zoom_speed to a reasonable range (0.1 to 0.5 per second)
        zoom_speed_normalized = (zoom_speed / 100.0) * 0.4 + 0.1
        
        # Calculate final zoom factor
        zoom_factor = 1 + (zoom_speed_normalized * video_length)
        
        # Create output path
        temp_dir = "temp"
        if not os.path.exists(temp_dir):
            try:
                # Create with explicit permissions (0o755 = rwxr-xr-x)
                os.makedirs(temp_dir, mode=0o755, exist_ok=True)
                logger.info(f"Created temp directory at {os.path.abspath(temp_dir)}")
            except Exception as e:
                logger.error(f"Failed to create temp directory: {e}")
                # Try using /tmp as a fallback
                temp_dir = "/tmp"
                logger.info(f"Using fallback temp directory: {temp_dir}")
                
        # Ensure the temp directory is writable
        if not os.access(temp_dir, os.W_OK):
            logger.error(f"Temp directory {temp_dir} is not writable")
            # Try using /tmp as a fallback
            temp_dir = "/tmp"
            logger.info(f"Using fallback temp directory: {temp_dir}")
            
        output_path = os.path.join(temp_dir, f"video_only_{uuid.uuid4()}.mp4")
        
        # Debug logging
        logger.info(f"Creating video with effect_type={effect_type}, pan_direction={pan_direction}")
        if ken_burns_keypoints:
            logger.info(f"Ken Burns keypoints: {ken_burns_keypoints}")

        # Parse output dimensions
        width, height = map(int, output_dims.split('x'))
        
        # Build filter based on effect type
        if effect_type == "none":
            # No motion effect - just convert the image to video with the specified duration
            # Use a simpler filter chain to avoid potential syntax issues
            filter_complex = f"scale=w={width}:h={height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
            
            # Build FFmpeg command with the filter
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output if exists
                "-loop", "1",  # Loop the input
                "-i", image_path,  # Input image
                "-vf", filter_complex,  # Video filter
                "-c:v", "libx264",  # Video codec
                "-t", str(video_length),  # Duration
                "-pix_fmt", "yuv420p",  # Pixel format
                "-preset", "medium",  # Quality preset
                "-crf", "23",  # Quality level
                "-movflags", "+faststart",  # Optimize for web
                output_path  # Output file
            ]
            
            # Log the full command for debugging
            logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
            
            # Run FFmpeg command with detailed error handling
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                # Log the output regardless of success
                if stdout:
                    logger.debug(f"FFmpeg stdout: {stdout.decode()}")
                if stderr:
                    stderr_text = stderr.decode()
                    if process.returncode != 0:
                        logger.error(f"FFmpeg stderr: {stderr_text}")
                    else:
                        logger.debug(f"FFmpeg stderr: {stderr_text}")
                
                if process.returncode != 0:
                    error_msg = stderr.decode() if stderr else "Unknown FFmpeg error"
                    logger.error(f"FFmpeg command failed with return code {process.returncode}: {error_msg}")
                    raise RuntimeError(f"FFmpeg command failed: {error_msg}")
                
                # Verify the output file exists and has content
                if not os.path.exists(output_path):
                    logger.error(f"Output file not created: {output_path}")
                    raise FileNotFoundError(f"Output video was not created at {output_path}")
                    
                file_size = os.path.getsize(output_path)
                if file_size == 0:
                    logger.error(f"Output file is empty: {output_path}")
                    raise RuntimeError(f"Output video was created but is empty: {output_path}")
                    
                logger.info(f"Successfully created video at {output_path} ({file_size} bytes)")
                
            except Exception as e:
                logger.error(f"Error executing FFmpeg command: {str(e)}", exc_info=True)
                raise
        elif effect_type == "zoom":
            # Standard zoom effect (centered)
            filter_complex = (
                f"scale={scale_dims},"
                f"zoompan=z='min(1+({zoom_speed_normalized}*{video_length})*on/{total_frames}, {zoom_factor})':"
                f"d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"s={output_dims}"
            )
            
            # Build FFmpeg command with the filter
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output if exists
                "-loop", "1",  # Loop the input
                "-framerate", str(frame_rate),  # Input framerate
                "-i", image_path,  # Input image
                "-vf", filter_complex,  # Video filter
                "-c:v", "libx264",  # Video codec
                "-r", str(frame_rate),  # Output framerate
                "-pix_fmt", "yuv420p",  # Pixel format
                "-preset", "medium",  # Quality preset
                "-crf", "23",  # Quality level
                "-t", str(video_length),  # Duration
                "-movflags", "+faststart",  # Optimize for web
                output_path  # Output file
            ]
            
            # Log the full command for debugging
            logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
            
            # Run FFmpeg command with detailed error handling
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                # Log the output regardless of success
                if stdout:
                    logger.debug(f"FFmpeg stdout: {stdout.decode()}")
                if stderr:
                    stderr_text = stderr.decode()
                    if process.returncode != 0:
                        logger.error(f"FFmpeg stderr: {stderr_text}")
                    else:
                        logger.debug(f"FFmpeg stderr: {stderr_text}")
                
                if process.returncode != 0:
                    error_msg = stderr.decode() if stderr else "Unknown FFmpeg error"
                    logger.error(f"FFmpeg command failed with return code {process.returncode}: {error_msg}")
                    raise RuntimeError(f"FFmpeg command failed: {error_msg}")
                
                # Verify the output file exists and has content
                if not os.path.exists(output_path):
                    logger.error(f"Output file not created: {output_path}")
                    raise FileNotFoundError(f"Output video was not created at {output_path}")
                    
                file_size = os.path.getsize(output_path)
                if file_size == 0:
                    logger.error(f"Output file is empty: {output_path}")
                    raise RuntimeError(f"Output video was created but is empty: {output_path}")
                    
                logger.info(f"Successfully created video at {output_path} ({file_size} bytes)")
                
            except Exception as e:
                logger.error(f"Error executing FFmpeg command: {str(e)}", exc_info=True)
                raise
        elif effect_type == "pan":
            # Pan effect with simple expressions, using zoompan for consistency
            # Adding a subtle zoom factor for more visual appeal
            start_zoom = 1.0
            end_zoom = 1.5  # Add a subtle zoom throughout the pan
            
            if not pan_direction or pan_direction == "left_to_right":
                filter_complex = (
                    f"scale={scale_dims},"
                    f"zoompan=z='min({start_zoom}+({end_zoom-start_zoom})*on/{total_frames},{end_zoom})':"
                    f"d={total_frames}:"
                    f"x='0+(iw-iw/zoom)*on/{total_frames}':"  # Properly move from left edge to right edge considering zoom
                    f"y='ih/2-(ih/zoom/2)':"  # Keep centered vertically considering zoom
                    f"s={output_dims},fps={frame_rate}"
                )
            elif pan_direction == "right_to_left":
                filter_complex = (
                    f"scale={scale_dims},"
                    f"zoompan=z='min({start_zoom}+({end_zoom-start_zoom})*on/{total_frames},{end_zoom})':"
                    f"d={total_frames}:"
                    f"x='(iw-iw/zoom)-(iw-iw/zoom)*on/{total_frames}':"  # Properly move from right edge to left edge considering zoom
                    f"y='ih/2-(ih/zoom/2)':"  # Keep centered vertically considering zoom
                    f"s={output_dims},fps={frame_rate}"
                )
            elif pan_direction == "top_to_bottom":
                filter_complex = (
                    f"scale={scale_dims},"
                    f"zoompan=z='min({start_zoom}+({end_zoom-start_zoom})*on/{total_frames},{end_zoom})':"
                    f"d={total_frames}:"
                    f"x='iw/2-(iw/zoom/2)':"  # Keep centered horizontally considering zoom
                    f"y='0+(ih-ih/zoom)*on/{total_frames}':"  # Properly move from top edge to bottom edge considering zoom
                    f"s={output_dims},fps={frame_rate}"
                )
            elif pan_direction == "bottom_to_top":
                filter_complex = (
                    f"scale={scale_dims},"
                    f"zoompan=z='min({start_zoom}+({end_zoom-start_zoom})*on/{total_frames},{end_zoom})':"
                    f"d={total_frames}:"
                    f"x='iw/2-(iw/zoom/2)':"  # Keep centered horizontally considering zoom
                    f"y='(ih-ih/zoom)-(ih-ih/zoom)*on/{total_frames}':"  # Properly move from bottom edge to top edge considering zoom
                    f"s={output_dims},fps={frame_rate}"
                )
            elif pan_direction == "diagonal_top_left":
                filter_complex = (
                    f"scale={scale_dims},"
                    f"zoompan=z='min({start_zoom}+({end_zoom-start_zoom})*on/{total_frames},{end_zoom})':"
                    f"d={total_frames}:"
                    f"x='0+(iw-iw/zoom)*on/{total_frames}':"  # Move from left to right considering zoom
                    f"y='0+(ih-ih/zoom)*on/{total_frames}':"  # Move from top to bottom considering zoom
                    f"s={output_dims},fps={frame_rate}"
                )
            elif pan_direction == "diagonal_top_right":
                filter_complex = (
                    f"scale={scale_dims},"
                    f"zoompan=z='min({start_zoom}+({end_zoom-start_zoom})*on/{total_frames},{end_zoom})':"
                    f"d={total_frames}:"
                    f"x='(iw-iw/zoom)-(iw-iw/zoom)*on/{total_frames}':"  # Move from right to left considering zoom
                    f"y='0+(ih-ih/zoom)*on/{total_frames}':"  # Move from top to bottom considering zoom
                    f"s={output_dims},fps={frame_rate}"
                )
            elif pan_direction == "diagonal_bottom_left":
                filter_complex = (
                    f"scale={scale_dims},"
                    f"zoompan=z='min({start_zoom}+({end_zoom-start_zoom})*on/{total_frames},{end_zoom})':"
                    f"d={total_frames}:"
                    f"x='0+(iw-iw/zoom)*on/{total_frames}':"  # Move from left to right considering zoom
                    f"y='(ih-ih/zoom)-(ih-ih/zoom)*on/{total_frames}':"  # Move from bottom to top considering zoom
                    f"s={output_dims},fps={frame_rate}"
                )
            elif pan_direction == "diagonal_bottom_right":
                filter_complex = (
                    f"scale={scale_dims},"
                    f"zoompan=z='min({start_zoom}+({end_zoom-start_zoom})*on/{total_frames},{end_zoom})':"
                    f"d={total_frames}:"
                    f"x='(iw-iw/zoom)-(iw-iw/zoom)*on/{total_frames}':"  # Move from right to left considering zoom
                    f"y='(ih-ih/zoom)-(ih-ih/zoom)*on/{total_frames}':"  # Move from bottom to top considering zoom
                    f"s={output_dims},fps={frame_rate}"
                )
            else:
                # Default to left-to-right
                logger.warning(f"Invalid pan direction: {pan_direction}. Using left_to_right.")
                filter_complex = (
                    f"scale={scale_dims},"
                    f"zoompan=z='min({start_zoom}+({end_zoom-start_zoom})*on/{total_frames},{end_zoom})':"
                    f"d={total_frames}:"
                    f"x='0+(iw-iw/zoom)*on/{total_frames}':"  # Properly move from left edge to right edge considering zoom
                    f"y='ih/2-(ih/zoom/2)':"  # Keep centered vertically considering zoom
                    f"s={output_dims}"
                )
            
            # Build FFmpeg command with the filter
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output if exists
                "-loop", "1",  # Loop the input
                "-framerate", str(frame_rate),  # Input framerate
                "-i", image_path,  # Input image
                "-vf", filter_complex,  # Video filter
                "-c:v", "libx264",  # Video codec
                "-r", str(frame_rate),  # Output framerate
                "-pix_fmt", "yuv420p",  # Pixel format
                "-preset", "medium",  # Quality preset
                "-crf", "23",  # Quality level
                "-t", str(video_length),  # Duration
                "-movflags", "+faststart",  # Optimize for web
                output_path  # Output file
            ]
            
            # Log the full command for debugging
            logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
            
            # Run FFmpeg command with detailed error handling
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                # Log the output regardless of success
                if stdout:
                    logger.debug(f"FFmpeg stdout: {stdout.decode()}")
                if stderr:
                    stderr_text = stderr.decode()
                    if process.returncode != 0:
                        logger.error(f"FFmpeg stderr: {stderr_text}")
                    else:
                        logger.debug(f"FFmpeg stderr: {stderr_text}")
                
                if process.returncode != 0:
                    error_msg = stderr.decode() if stderr else "Unknown FFmpeg error"
                    logger.error(f"FFmpeg command failed with return code {process.returncode}: {error_msg}")
                    raise RuntimeError(f"FFmpeg command failed: {error_msg}")
                
                # Verify the output file exists and has content
                if not os.path.exists(output_path):
                    logger.error(f"Output file not created: {output_path}")
                    raise FileNotFoundError(f"Output video was not created at {output_path}")
                    
                file_size = os.path.getsize(output_path)
                if file_size == 0:
                    logger.error(f"Output file is empty: {output_path}")
                    raise RuntimeError(f"Output video was created but is empty: {output_path}")
                    
                logger.info(f"Successfully created video at {output_path} ({file_size} bytes)")
                
            except Exception as e:
                logger.error(f"Error executing FFmpeg command: {str(e)}", exc_info=True)
                raise
        elif effect_type == "ken_burns":
            # Use a simpler ken burns approach with sendzoom filter if available
            # Otherwise fallback to a simpler implementation with just two points
            
            # If no valid keypoints, create a default effect
            if not ken_burns_keypoints or len(ken_burns_keypoints) < 2:
                logger.warning("No valid keypoints for Ken Burns effect. Using default effect.")
                
                # Simple Ken Burns from top-left to bottom-right with zoom
                # Calculate zoom factor change
                start_zoom = 1.0
                end_zoom = 1.0 + zoom_speed_normalized
                
                # Create a simple version with trim, scale, and settb filters
                filter_complex = (
                    f"scale={scale_dims},"
                    f"zoompan=z='min({start_zoom}+({end_zoom-start_zoom})*on/{total_frames},{end_zoom})':"
                    f"d={total_frames}:"
                    f"x='iw/2-(iw/zoom/2)+(iw/4)*on/{total_frames}':"
                    f"y='ih/2-(ih/zoom/2)+(ih/4)*on/{total_frames}':"
                    f"s={output_dims},fps={frame_rate}"
                )
                
                # Build FFmpeg command with the filter
                cmd = [
                    "ffmpeg",
                    "-y",  # Overwrite output if exists
                    "-framerate", str(frame_rate),  # Set input framerate
                    "-loop", "1",  # Loop the input
                    "-i", image_path,  # Input image
                    "-vf", filter_complex,  # Video filter
                    "-c:v", "libx264",  # Video codec
                    "-r", str(frame_rate),  # Output framerate
                    "-pix_fmt", "yuv420p",  # Pixel format
                    "-preset", "medium",  # Quality preset
                    "-crf", "23",  # Quality level
                    "-t", str(video_length),  # Duration
                    "-movflags", "+faststart",  # Optimize for web
                    output_path  # Output file
                ]
                
                # Log the full command for debugging
                logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
                
                # Run FFmpeg command
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    error_msg = stderr.decode() if stderr else "Unknown FFmpeg error"
                    logger.error(f"FFmpeg error: {error_msg}")
                    raise RuntimeError(f"FFmpeg command failed: {error_msg}")
            else:
                # Multi-segment Ken Burns implementation
                # This creates a separate video for each segment and then concatenates them
                logger.info(f"Creating multi-segment Ken Burns effect with {len(ken_burns_keypoints)} keypoints")
                
                # Ensure keypoints are sorted by time
                keypoints = sorted(ken_burns_keypoints, key=lambda k: k.get('time', 0))
                
                # Safety check - need at least 2 keypoints
                if len(keypoints) < 2:
                    logger.warning("Not enough valid keypoints. Using default effect.")
                    return await create_video_with_effects(
                        image_path=image_path,
                        video_length=video_length,
                        frame_rate=frame_rate,
                        zoom_speed=zoom_speed,
                        output_dims=output_dims,
                        scale_dims=scale_dims,
                        effect_type="zoom"  # Fallback to standard zoom
                    )
                
                # Normalize keypoint times to the full video duration
                first_time = keypoints[0].get('time', 0)
                last_time = keypoints[-1].get('time', video_length)
                duration_scale = video_length / max(0.001, last_time - first_time)
                
                # Create a segment list file for concatenation
                segment_list_path = os.path.join(temp_dir, f"segments_{uuid.uuid4()}.txt")
                segment_paths = []
                
                # Process each pair of consecutive keypoints as a segment
                for i in range(len(keypoints) - 1):
                    start_point = keypoints[i]
                    end_point = keypoints[i+1]
                    
                    # Extract values with safety bounds
                    start_x = max(0, min(1, start_point.get('x', 0.2)))
                    start_y = max(0, min(1, start_point.get('y', 0.2)))
                    end_x = max(0, min(1, end_point.get('x', 0.8)))
                    end_y = max(0, min(1, end_point.get('y', 0.8)))
                    start_zoom = max(1, min(3, start_point.get('zoom', 1.0)))
                    end_zoom = max(1, min(3, end_point.get('zoom', 1.5)))
                    
                    # Calculate segment duration based on keypoint times
                    start_time = start_point.get('time', 0)
                    end_time = end_point.get('time', video_length)
                    segment_duration = (end_time - start_time) * duration_scale
                    segment_frames = int(segment_duration * frame_rate)
                    
                    # Skip segments with zero or negative duration
                    if segment_duration <= 0 or segment_frames <= 1:
                        logger.warning(f"Skipping segment {i} with invalid duration: {segment_duration}")
                        continue
                    
                    # Create a segment output path
                    segment_path = os.path.join(temp_dir, f"segment_{i}_{uuid.uuid4()}.mp4")
                    segment_paths.append(segment_path)
                    
                    # Use simple linear interpolation for this segment
                    segment_filter = (
                        f"scale={scale_dims},"
                        f"zoompan=z='{start_zoom}+({end_zoom-start_zoom})*on/{segment_frames}':"
                        f"d={segment_frames}:"
                        f"x='iw*{start_x}-(iw/zoom/2)+(iw*({end_x-start_x}))*on/{segment_frames}':"
                        f"y='ih*{start_y}-(ih/zoom/2)+(ih*({end_y-start_y}))*on/{segment_frames}':"
                        f"s={output_dims},fps={frame_rate}"
                    )
                    
                    # Build FFmpeg command for this segment
                    segment_cmd = [
                        "ffmpeg",
                        "-y",  # Overwrite output if exists
                        "-framerate", str(frame_rate),  # Set input framerate
                        "-loop", "1",  # Loop the input
                        "-i", image_path,  # Input image
                        "-vf", segment_filter,  # Video filter
                        "-c:v", "libx264",  # Video codec
                        "-r", str(frame_rate),  # Output framerate
                        "-pix_fmt", "yuv420p",  # Pixel format
                        "-preset", "ultrafast",  # Use faster preset for segments
                        "-crf", "23",  # Quality level
                        "-t", str(segment_duration),  # Duration
                        "-movflags", "+faststart",  # Optimize for web
                        segment_path  # Output file
                    ]
                    
                    # Log segment info
                    logger.info(f"Creating segment {i}: {start_x},{start_y},z={start_zoom} -> {end_x},{end_y},z={end_zoom}, duration={segment_duration:.2f}s")
                    logger.debug(f"Segment {i} command: {' '.join(segment_cmd)}")
                    
                    # Run FFmpeg command for this segment
                    process = await asyncio.create_subprocess_exec(
                        *segment_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode != 0:
                        error_msg = stderr.decode() if stderr else "Unknown FFmpeg error"
                        logger.error(f"FFmpeg error for segment {i}: {error_msg}")
                        # Continue with other segments instead of failing
                        segment_paths.pop()  # Remove failed segment
                
                # If no segments were created successfully, fall back to a simple approach
                if not segment_paths:
                    logger.error("No segments were created successfully. Falling back to simple Ken Burns effect.")
                    start_point = keypoints[0]
                    end_point = keypoints[-1]
                    
                    # Extract values with safety bounds
                    start_x = max(0, min(1, start_point.get('x', 0.2)))
                    start_y = max(0, min(1, start_point.get('y', 0.2)))
                    end_x = max(0, min(1, end_point.get('x', 0.8)))
                    end_y = max(0, min(1, end_point.get('y', 0.8)))
                    start_zoom = max(1, min(3, start_point.get('zoom', 1.0)))
                    end_zoom = max(1, min(3, end_point.get('zoom', 1.5)))
                    
                    # Use simple approach with just first and last keypoints
                    filter_complex = (
                        f"scale={scale_dims},"
                        f"zoompan=z='{start_zoom}+({end_zoom-start_zoom})*on/{total_frames}':"
                        f"d={total_frames}:"
                        f"x='iw*{start_x}-(iw/zoom/2)+(iw*({end_x-start_x}))*on/{total_frames}':"
                        f"y='ih*{start_y}-(ih/zoom/2)+(ih*({end_y-start_y}))*on/{total_frames}':"
                        f"s={output_dims},fps={frame_rate}"
                    )
                    
                    # Build FFmpeg command with the filter
                    cmd = [
                        "ffmpeg",
                        "-y",  # Overwrite output if exists
                        "-framerate", str(frame_rate),  # Set input framerate
                        "-loop", "1",  # Loop the input
                        "-i", image_path,  # Input image
                        "-vf", filter_complex,  # Video filter
                        "-c:v", "libx264",  # Video codec
                        "-r", str(frame_rate),  # Output framerate
                        "-pix_fmt", "yuv420p",  # Pixel format
                        "-preset", "medium",  # Quality preset
                        "-crf", "23",  # Quality level
                        "-t", str(video_length),  # Duration
                        "-movflags", "+faststart",  # Optimize for web
                        output_path  # Output file
                    ]
                    
                    # Run FFmpeg command
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode != 0:
                        error_msg = stderr.decode() if stderr else "Unknown FFmpeg error"
                        logger.error(f"FFmpeg error: {error_msg}")
                        raise RuntimeError(f"FFmpeg command failed: {error_msg}")
                else:
                    # Create a list file for concatenation
                    segment_list_path = os.path.join(temp_dir, f"segments_{uuid.uuid4()}.txt")
                    
                    # Ensure segment_list_path is absolute
                    segment_list_path = os.path.abspath(segment_list_path)
                    
                    # Log the paths for debugging
                    logger.info(f"Writing segment list to: {segment_list_path}")
                    logger.info(f"Segments to concatenate: {len(segment_paths)}")
                    for i, path in enumerate(segment_paths):
                        logger.info(f"  Segment {i}: {path}")
                    
                    try:
                        # Create the list file with absolute paths
                        with open(segment_list_path, 'w') as f:
                            for segment_path in segment_paths:
                                # Use absolute paths to avoid any directory issues
                                abs_segment_path = os.path.abspath(segment_path)
                                f.write(f"file '{abs_segment_path}'\n")
                        
                        # Verify the list file was created
                        if not os.path.exists(segment_list_path):
                            raise FileNotFoundError(f"Failed to create segment list file at {segment_list_path}")
                        
                        # Check if the file has content
                        with open(segment_list_path, 'r') as f:
                            content = f.read()
                            logger.info(f"Segment list file content size: {len(content)} bytes")
                            
                        # Concatenate all segments
                        concat_cmd = [
                            "ffmpeg",
                            "-y",  # Overwrite output if exists
                            "-f", "concat",  # Use concat demuxer
                            "-safe", "0",  # Allow absolute paths
                            "-i", segment_list_path,  # Input list file
                            "-c", "copy",  # Just copy streams without re-encoding
                            output_path  # Final output file
                        ]
                        
                        logger.info(f"Concatenating {len(segment_paths)} segments into final video")
                        logger.debug(f"Concat command: {' '.join(concat_cmd)}")
                        
                        # Run concat command
                        process = await asyncio.create_subprocess_exec(
                            *concat_cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        
                        stdout, stderr = await process.communicate()
                        
                        if process.returncode != 0:
                            error_msg = stderr.decode() if stderr else "Unknown FFmpeg error"
                            logger.error(f"FFmpeg concat error: {error_msg}")
                            raise RuntimeError(f"FFmpeg concat failed: {error_msg}")
                        
                    except Exception as e:
                        logger.error(f"Error during concatenation: {str(e)}")
                        # Fall back to using the first segment as the output
                        if segment_paths:
                            logger.warning(f"Falling back to using first segment as output")
                            # Copy the first segment to the output path
                            import shutil
                            shutil.copy2(segment_paths[0], output_path)
                        else:
                            # If we have no segments, we have to fail
                            raise RuntimeError("No segments were created successfully")
                    finally:
                        # Clean up segment files
                        for segment_path in segment_paths:
                            try:
                                if os.path.exists(segment_path):
                                    os.remove(segment_path)
                            except Exception as e:
                                logger.warning(f"Failed to remove segment file {segment_path}: {e}")
                        
                        # Clean up list file
                        try:
                            if os.path.exists(segment_list_path):
                                os.remove(segment_list_path)
                        except Exception as e:
                            logger.warning(f"Failed to remove segment list file {segment_list_path}: {e}")
                
                logger.info(f"Successfully created Ken Burns effect with {len(keypoints)} keypoints")
        else:
            # Fallback to no motion effect if unknown effect type
            logger.warning(f"Unknown effect type: {effect_type}. Using no motion effect.")
            # Use a simpler filter chain to avoid potential syntax issues
            filter_complex = f"scale=w={width}:h={height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
            
            # Build FFmpeg command with the filter
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output if exists
                "-loop", "1",  # Loop the input
                "-i", image_path,  # Input image
                "-vf", filter_complex,  # Video filter
                "-c:v", "libx264",  # Video codec
                "-t", str(video_length),  # Duration
                "-pix_fmt", "yuv420p",  # Pixel format
                "-preset", "medium",  # Quality preset
                "-crf", "23",  # Quality level
                "-movflags", "+faststart",  # Optimize for web
                output_path  # Output file
            ]
            
            # Log the full command for debugging
            logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
            
            # Run FFmpeg command with detailed error handling
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                # Log the output regardless of success
                if stdout:
                    logger.debug(f"FFmpeg stdout: {stdout.decode()}")
                if stderr:
                    stderr_text = stderr.decode()
                    if process.returncode != 0:
                        logger.error(f"FFmpeg stderr: {stderr_text}")
                    else:
                        logger.debug(f"FFmpeg stderr: {stderr_text}")
                
                if process.returncode != 0:
                    error_msg = stderr.decode() if stderr else "Unknown FFmpeg error"
                    logger.error(f"FFmpeg command failed with return code {process.returncode}: {error_msg}")
                    raise RuntimeError(f"FFmpeg command failed: {error_msg}")
                
                # Verify the output file exists and has content
                if not os.path.exists(output_path):
                    logger.error(f"Output file not created: {output_path}")
                    raise FileNotFoundError(f"Output video was not created at {output_path}")
                    
                file_size = os.path.getsize(output_path)
                if file_size == 0:
                    logger.error(f"Output file is empty: {output_path}")
                    raise RuntimeError(f"Output video was created but is empty: {output_path}")
                    
                logger.info(f"Successfully created video at {output_path} ({file_size} bytes)")
                
            except Exception as e:
                logger.error(f"Error executing FFmpeg command: {str(e)}", exc_info=True)
                raise
        
        # Return the output path
        return output_path
        
    except Exception as e:
        logger.error(f"Error in create_video_with_effects: {e}", exc_info=True)
        raise

async def combine_video_audio_captions(
    video_path: str,
    audio_path: Optional[str] = None,
    srt_path: Optional[str] = None,
    caption_properties: Optional[Dict] = None,
    match_length: str = "audio",
    frame_rate: int = 30
) -> str:
    """
    Combine video with audio and captions.
    
    Args:
        video_path: Path to the input video
        audio_path: Path to the audio file (optional)
        srt_path: Path to the subtitle file (optional)
        caption_properties: Caption styling properties (optional)
        match_length: Whether to match the output length to 'audio' or 'video'
        frame_rate: Frame rate of the output video
        
    Returns:
        Path to the final output video
    """
    try:
        # Create output path
        temp_dir = "temp"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
            
        output_path = os.path.join(temp_dir, f"final_{uuid.uuid4()}.mp4")
        
        # Get video duration
        video_info_cmd = [
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "json", 
            video_path
        ]
        video_info_result = subprocess.run(
            video_info_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        video_duration = None
        if video_info_result.returncode == 0:
            video_info = json.loads(video_info_result.stdout)
            video_duration = float(video_info["format"]["duration"])
        else:
            # Fallback if we can't get video duration
            logger.warning("Could not determine video duration, using default")
        
        # Get audio duration if available
        audio_duration = None
        if audio_path:
            audio_info_cmd = [
                "ffprobe", 
                "-v", "error", 
                "-show_entries", "format=duration", 
                "-of", "json", 
                audio_path
            ]
            audio_info_result = subprocess.run(
                audio_info_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if audio_info_result.returncode == 0:
                audio_info = json.loads(audio_info_result.stdout)
                audio_duration = float(audio_info["format"]["duration"])
        
        # Determine final video duration based on match_length
        if match_length == "audio" and audio_duration:
            final_duration = audio_duration
            loop_video = audio_duration > video_duration if video_duration else True
        else:
            final_duration = video_duration
            loop_video = False
        
        # Start building FFmpeg command
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output if exists
        ]
        
        # Add stream loop BEFORE the video input if needed
        if loop_video:
            cmd.extend(["-stream_loop", "-1"])  # Loop video infinitely
        
        # Add video input
        cmd.extend(["-i", video_path])
        
        # Add audio input if provided
        if audio_path:
            cmd.extend(["-i", audio_path])
        
        # Filter complex parts
        filter_complex = []
        
        # Add subtitles if provided
        if srt_path:
            # Check if it's an ASS file or standard SRT
            is_ass = srt_path.lower().endswith('.ass')
            
            if is_ass:
                # For ASS subtitles, we can directly use the file
                cmd.extend(["-i", srt_path])
                filter_complex.append(f"ass='{srt_path}'")
            else:
                # Prepare subtitle styling
                style_options = prepare_subtitle_styling(caption_properties) if caption_properties else {}
                subtitle_filter = f"subtitles='{srt_path}'"
                
                if style_options:
                    # Convert dictionary to style string
                    style_parts = [f"{key}={value}" for key, value in style_options.items()]
                    force_style = ','.join(style_parts)
                    subtitle_filter += f":force_style='{force_style}'"
                
                # Add subtitle filter
                filter_complex.append(subtitle_filter)
        
        # Combine all filters
        if filter_complex:
            cmd.extend(["-filter_complex", ",".join(filter_complex)])
        
        # Add audio mapping if needed
        if audio_path:
            cmd.extend(["-map", "0:v"])  # Map video from first input
            cmd.extend(["-map", "1:a"])  # Map audio from second input
            cmd.extend(["-c:a", "aac"])  # Audio codec
        
        # Add output settings
        cmd.extend([
            "-c:v", "libx264",  # Video codec
            "-r", str(frame_rate),  # Output framerate
            "-pix_fmt", "yuv420p",  # Pixel format
            "-preset", "medium",  # Quality preset
            "-crf", "23",  # Quality level
            "-t", str(final_duration),  # Duration
            "-movflags", "+faststart",  # Optimize for web
            output_path  # Output file
        ])
        
        logger.info(f"Running FFmpeg command to combine video, audio, and captions: {' '.join(cmd)}")
        
        # Run FFmpeg command
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown FFmpeg error"
            logger.error(f"FFmpeg error: {error_msg}")
            raise RuntimeError(f"FFmpeg command failed: {error_msg}")
        
        # Check if output was created
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Output video was not created at {output_path}")
        
        logger.info(f"Successfully created final video at {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error in combine_video_audio_captions: {e}")
        raise

def prepare_subtitle_styling(caption_properties: Optional[Dict] = None) -> Dict[str, str]:
    """
    Prepare subtitle styling options from caption properties.
    
    Args:
        caption_properties: Caption styling properties
        
    Returns:
        Dictionary of FFmpeg subtitle styling options
    """
    if not caption_properties:
        return {}
        
    # Default styling
    style_options = {
        "Fontname": "Arial",
        "Fontsize": "24",
        "PrimaryColour": "white",
        "BackColour": "black@0.5",
        "Outline": "1",
        "Alignment": "2",  # Center-bottom alignment
        "MarginV": "30"  # Bottom margin
    }
    
    # Update with user preferences if provided
    if "font_name" in caption_properties:
        style_options["Fontname"] = caption_properties["font_name"]
        
    if "font_size" in caption_properties:
        style_options["Fontsize"] = str(caption_properties["font_size"])
        
    if "font_color" in caption_properties:
        style_options["PrimaryColour"] = caption_properties["font_color"]
        
    if "background_color" in caption_properties:
        style_options["BackColour"] = caption_properties["background_color"]
        
    if "outline" in caption_properties:
        style_options["Outline"] = str(caption_properties["outline"])
        
    if "position" in caption_properties:
        position = caption_properties["position"]
        if position == "top":
            style_options["Alignment"] = "8"  # Center-top alignment
            style_options["MarginV"] = "30"  # Top margin
        elif position == "middle":
            style_options["Alignment"] = "5"  # Center-middle alignment
            style_options["MarginV"] = "0"  # No margin
        # Default is bottom (Alignment=2)
        
    return style_options

async def create_video_with_audio_captions(
    image_path: str,
    video_length: float,
    frame_rate: int,
    zoom_speed: float,
    audio_path: Optional[str] = None,
    srt_path: Optional[str] = None,
    caption_properties: Optional[Dict] = None,
    match_length: str = "audio",
    effect_type: str = "zoom",
    pan_direction: Optional[str] = None,
    ken_burns_keypoints: Optional[List[Dict[str, float]]] = None
) -> str:
    """
    Create video from image with optional audio and captions in a single pipeline.
    
    This is a convenience function that combines create_video_with_effects and
    combine_video_audio_captions into a single operation.
    
    Args:
        image_path: Path to the input image
        video_length: Length of output video in seconds
        frame_rate: Frame rate of output video
        zoom_speed: Speed of zoom effect (0-100)
        audio_path: Path to the audio file (optional)
        srt_path: Path to the SRT or ASS subtitle file (optional)
        caption_properties: Caption styling properties (optional)
        match_length: Whether to match the output length to 'audio' or 'video'
        effect_type: Type of animation effect to apply ('zoom', 'pan', 'ken_burns')
        pan_direction: Direction of pan effect when effect_type is 'pan'
        ken_burns_keypoints: List of keypoints for Ken Burns effect when effect_type is 'ken_burns'
        
    Returns:
        Path to the final output video
    """
    try:
        # Verify input files exist
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Input image file not found: {image_path}")
            
        if audio_path and not os.path.exists(audio_path):
            raise FileNotFoundError(f"Input audio file not found: {audio_path}")
            
        if srt_path and not os.path.exists(srt_path):
            raise FileNotFoundError(f"Input subtitle file not found: {srt_path}")
        
        # Get image dimensions for optimal output settings
        from PIL import Image
        with Image.open(image_path) as img:
            width, height = img.size
        
        # Determine orientation and set dimensions
        if width > height:  # Landscape orientation
            scale_dims = "7680x4320"  # 8K landscape dimensions
            output_dims = "1920x1080"  # Full HD
        else:  # Portrait orientation
            scale_dims = "4320x7680"  # 8K portrait dimensions
            output_dims = "1080x1920"  # Full HD vertical video
        
        # First create video from image with effects
        video_path = await create_video_with_effects(
            image_path=image_path,
            video_length=video_length,
            frame_rate=frame_rate,
            zoom_speed=zoom_speed,
            output_dims=output_dims,
            scale_dims=scale_dims,
            effect_type=effect_type,
            pan_direction=pan_direction,
            ken_burns_keypoints=ken_burns_keypoints
        )
        
        # Then combine with audio and captions
        output_path = await combine_video_audio_captions(
            video_path=video_path,
            audio_path=audio_path,
            srt_path=srt_path,
            caption_properties=caption_properties,
            match_length=match_length,
            frame_rate=frame_rate
        )
        
        # Clean up intermediate video file
        if os.path.exists(video_path):
            try:
                os.remove(video_path)
            except Exception as e:
                logger.warning(f"Failed to remove temporary video file {video_path}: {e}")
        
        return output_path
        
    except Exception as e:
        logger.error(f"Error in create_video_with_audio_captions: {e}")
        raise 