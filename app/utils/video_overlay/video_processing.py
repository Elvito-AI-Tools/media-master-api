"""
Video processing utilities for the video overlay functionality.

This module contains functions for processing and manipulating videos
for overlay operations.
"""
import os
import logging
import json
import subprocess
import asyncio
from typing import Dict, Any, Tuple, Optional

from app.utils.media import download_media_file

# Configure logging
logger = logging.getLogger(__name__)

async def get_video_metadata(video_path: str) -> Dict[str, Any]:
    """
    Get metadata for a video file using FFprobe.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Dictionary containing video metadata
    """
    try:
        # Check if file exists and has content
        if not os.path.exists(video_path):
            logger.error(f"Video file does not exist: {video_path}")
            return {}
        
        file_size = os.path.getsize(video_path)
        if file_size == 0:
            logger.error(f"Video file is empty: {video_path}")
            return {}
        
        logger.info(f"Getting metadata for video: {video_path} (size: {file_size} bytes)")
        
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration,size,bit_rate:stream=width,height,codec_name,avg_frame_rate,codec_type",
            "-of", "json",
            video_path
        ]
        
        logger.debug(f"Running FFprobe command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFprobe failed with return code {result.returncode}")
            logger.error(f"FFprobe stderr: {result.stderr}")
            return {}
        
        if not result.stdout.strip():
            logger.error("FFprobe returned empty output")
            return {}
        
        logger.debug(f"FFprobe output: {result.stdout}")
        
        try:
            info = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse FFprobe JSON output: {e}")
            logger.error(f"Raw output: {result.stdout}")
            return {}
        
        metadata = {
            "duration": None,
            "size_bytes": None,
            "bit_rate": None,
            "width": None,
            "height": None,
            "codec": None,
            "frame_rate": None,
            "has_audio": False
        }
        
        # Extract format information
        if "format" in info:
            format_info = info["format"]
            if "duration" in format_info:
                try:
                    metadata["duration"] = float(format_info["duration"])
                except (ValueError, TypeError):
                    logger.warning(f"Could not parse duration: {format_info.get('duration')}")
            
            if "size" in format_info:
                try:
                    metadata["size_bytes"] = int(format_info["size"])
                except (ValueError, TypeError):
                    logger.warning(f"Could not parse size: {format_info.get('size')}")
            
            if "bit_rate" in format_info:
                try:
                    metadata["bit_rate"] = int(format_info["bit_rate"])
                except (ValueError, TypeError):
                    logger.warning(f"Could not parse bit_rate: {format_info.get('bit_rate')}")
        
        # Get video stream info if available
        if "streams" in info:
            video_stream_found = False
            audio_stream_found = False
            
            for stream in info["streams"]:
                if stream.get("codec_type") == "video":
                    video_stream_found = True
                    logger.debug(f"Found video stream: {stream}")
                    
                    # Extract width and height
                    if "width" in stream and "height" in stream:
                        try:
                            metadata["width"] = int(stream["width"])
                            metadata["height"] = int(stream["height"])
                        except (ValueError, TypeError):
                            logger.warning(f"Could not parse video dimensions: {stream.get('width')}x{stream.get('height')}")
                    
                    # Extract codec
                    if "codec_name" in stream:
                        metadata["codec"] = stream["codec_name"]
                    
                    # Parse frame rate
                    if "avg_frame_rate" in stream:
                        try:
                            frame_rate_str = stream["avg_frame_rate"]
                            if "/" in frame_rate_str:
                                num, den = frame_rate_str.split("/")
                                if float(den) != 0:
                                    metadata["frame_rate"] = round(float(num) / float(den), 2)
                            else:
                                metadata["frame_rate"] = round(float(frame_rate_str), 2)
                        except (ValueError, ZeroDivisionError, TypeError):
                            logger.warning(f"Could not parse frame rate: {stream.get('avg_frame_rate')}")
                
                elif stream.get("codec_type") == "audio":
                    audio_stream_found = True
                    logger.debug(f"Found audio stream: {stream}")
            
            metadata["has_audio"] = audio_stream_found
            
            if not video_stream_found:
                logger.error(f"No video stream found in file: {video_path}")
                logger.debug(f"Available streams: {info.get('streams', [])}")
        else:
            logger.error(f"No streams found in file: {video_path}")
        
        logger.info(f"Extracted metadata: {metadata}")
        
        # If we still don't have width/height, try a simpler approach
        if not metadata.get('width') or not metadata.get('height'):
            logger.warning("Primary metadata extraction failed to get dimensions, trying fallback method")
            try:
                # Try a simpler FFprobe command
                simple_cmd = [
                    "ffprobe",
                    "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=width,height",
                    "-of", "csv=s=x:p=0",
                    video_path
                ]
                
                logger.debug(f"Running fallback FFprobe command: {' '.join(simple_cmd)}")
                
                result = subprocess.run(simple_cmd, check=True, capture_output=True, text=True)
                
                if result.stdout.strip():
                    dimensions = result.stdout.strip()
                    if 'x' in dimensions:
                        width_str, height_str = dimensions.split('x')
                        try:
                            metadata["width"] = int(width_str)
                            metadata["height"] = int(height_str)
                            logger.info(f"Fallback method extracted dimensions: {metadata['width']}x{metadata['height']}")
                        except ValueError:
                            logger.error(f"Could not parse dimensions from fallback output: {dimensions}")
                
            except Exception as fallback_error:
                logger.error(f"Fallback metadata extraction also failed: {fallback_error}")
        
        return metadata
        
    except subprocess.CalledProcessError as e:
        logger.error(f"FFprobe command failed: {e}")
        logger.error(f"FFprobe stderr: {e.stderr}")
        return {}
    except Exception as e:
        logger.error(f"Error getting video metadata: {e}", exc_info=True)
        return {}

async def process_overlay_video(
    overlay_info: Dict[str, Any], 
    base_width: int, 
    base_height: int,
    temp_dir: str
) -> Dict[str, Any]:
    """
    Process a single overlay video and prepare it for composition.
    
    Args:
        overlay_info: Dictionary with overlay information including:
            - url: URL of the overlay video
            - x, y: Position (0-1) where to place the overlay
            - width, height: Optional size (0-1) relative to base image
            - start_time, end_time: Optional timing information
            - loop: Whether to loop the video
            - opacity: Optional opacity (0-1)
            - volume: Optional volume (0-1)
        base_width: Width of the base image/video
        base_height: Height of the base image/video
        temp_dir: Directory for temporary files
    
    Returns:
        Dictionary with processed overlay information
    """
    try:
        # Download the overlay video
        url = overlay_info['url']
        logger.info(f"Downloading overlay video from {url}")
        overlay_path, _ = await download_media_file(url, temp_dir=temp_dir)
        
        # Get video metadata
        metadata = await get_video_metadata(overlay_path)
        
        logger.debug(f"Video metadata for {url}: {metadata}")
        
        if not metadata:
            raise ValueError(f"Failed to extract any metadata from video: {url}. The file may be corrupted or in an unsupported format.")
        
        if not metadata.get('width') or not metadata.get('height'):
            available_info = {k: v for k, v in metadata.items() if v is not None}
            raise ValueError(f"Could not determine video dimensions for {url}. Available metadata: {available_info}. The video file may be corrupted or missing video streams.")
        
        # Calculate overlay sizing
        overlay_width, overlay_height = calculate_overlay_size(
            base_width, 
            base_height, 
            metadata['width'], 
            metadata['height'],
            overlay_info.get('width'),
            overlay_info.get('height')
        )
        
        # Calculate position in pixels
        x_pos = int(overlay_info['x'] * base_width)
        y_pos = int(overlay_info['y'] * base_height)
        
        # Adjust position to center the overlay at the specified point
        x_pos -= overlay_width // 2
        y_pos -= overlay_height // 2
        
        # Ensure overlay doesn't go outside bounds
        x_pos = max(0, min(x_pos, base_width - overlay_width))
        y_pos = max(0, min(y_pos, base_height - overlay_height))
        
        return {
            "path": overlay_path,
            "metadata": metadata,
            "x": x_pos,
            "y": y_pos,
            "width": overlay_width,
            "height": overlay_height,
            "start_time": overlay_info.get('start_time', 0.0),
            "end_time": overlay_info.get('end_time'),
            "loop": overlay_info.get('loop', False),
            "opacity": overlay_info.get('opacity', 1.0),
            "volume": overlay_info.get('volume', 0.0),
            "z_index": overlay_info.get('z_index', 0)
        }
    
    except Exception as e:
        logger.error(f"Error processing overlay video: {str(e)}", exc_info=True)
        raise

def calculate_overlay_size(
    base_width: int, 
    base_height: int, 
    overlay_width: int, 
    overlay_height: int,
    rel_width: Optional[float] = None,
    rel_height: Optional[float] = None
) -> Tuple[int, int]:
    """
    Calculate the size of the overlay video based on relative width/height.
    
    Args:
        base_width: Width of the base image
        base_height: Height of the base image
        overlay_width: Original width of the overlay video
        overlay_height: Original height of the overlay video
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

def build_ffmpeg_filter_complex(
    base_width: int,
    base_height: int,
    output_duration: float,
    frame_rate: int,
    overlay_videos: list,
    background_audio_path: Optional[str] = None,
    background_audio_volume: float = 0.2
) -> Tuple[str, list]:
    """
    Build the FFmpeg filter complex for video overlay composition.
    
    Args:
        base_width: Width of the base image
        base_height: Height of the base image
        output_duration: Duration of the output video
        frame_rate: Frame rate of the output video
        overlay_videos: List of processed overlay video information
        background_audio_path: Optional path to background audio
        background_audio_volume: Volume for background audio
    
    Returns:
        Tuple of (filter_complex_string, input_files_list)
    """
    # Sort overlays by z-index
    sorted_overlays = sorted(overlay_videos, key=lambda x: x.get('z_index', 0))
    
    # Build input files list
    input_files = []
    
    # Start with base image converted to video
    filter_parts = []
    
    # Create base video from image
    filter_parts.append(f"[0:v]scale={base_width}:{base_height},loop=loop=-1:size={int(frame_rate * output_duration)}:start=0[base]")
    
    # Process each overlay
    current_output = "base"
    for i, overlay in enumerate(sorted_overlays):
        input_files.append(overlay['path'])
        input_index = i + 1  # +1 because base image is input 0
        
        # Build timing filter
        timing_filter = ""
        if overlay['start_time'] > 0 or overlay['end_time'] is not None:
            end_time = overlay['end_time'] if overlay['end_time'] is not None else output_duration
            timing_filter = f"enable='between(t,{overlay['start_time']},{end_time})':"
        
        # Build scale and position filter
        scale_filter = f"scale={overlay['width']}:{overlay['height']}"
        
        # Add opacity if needed
        opacity_filter = ""
        if overlay['opacity'] < 1.0:
            opacity_filter = f",format=yuva420p,colorchannelmixer=aa={overlay['opacity']}"
        
        # Build overlay filter
        overlay_filter = f"[{input_index}:v]{scale_filter}{opacity_filter}[overlay{i}]"
        filter_parts.append(overlay_filter)
        
        # Combine with previous output
        next_output = f"out{i}" if i < len(sorted_overlays) - 1 else "vout"
        combine_filter = f"[{current_output}][overlay{i}]overlay={timing_filter}x={overlay['x']}:y={overlay['y']}[{next_output}]"
        filter_parts.append(combine_filter)
        
        current_output = next_output
    
    # Handle audio mixing
    audio_parts = []
    audio_inputs = []
    
    # Collect audio from overlay videos
    for i, overlay in enumerate(sorted_overlays):
        if overlay['volume'] > 0 and overlay['metadata'].get('has_audio', False):
            input_index = i + 1
            volume_filter = f"[{input_index}:a]volume={overlay['volume']}[aud{i}]"
            filter_parts.append(volume_filter)
            audio_inputs.append(f"aud{i}")
    
    # Add background audio if provided
    if background_audio_path:
        input_files.append(background_audio_path)
        bg_audio_index = len(input_files)  # This will be the last input
        bg_volume_filter = f"[{bg_audio_index}:a]volume={background_audio_volume}[bgaud]"
        filter_parts.append(bg_volume_filter)
        audio_inputs.append("bgaud")
    
    # Mix all audio inputs
    if audio_inputs:
        if len(audio_inputs) == 1:
            filter_parts.append(f"[{audio_inputs[0]}]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[aout]")
        else:
            mix_filter = f"[{''.join(f'[{inp}]' for inp in audio_inputs)}]amix=inputs={len(audio_inputs)}:duration=first:dropout_transition=2[aout]"
            filter_parts.append(mix_filter)
    
    filter_complex = ";".join(filter_parts)
    
    return filter_complex, input_files 