"""
Service for overlaying videos on top of a base image.

This service handles the process of overlaying one or more videos onto a base image
with control over positioning, timing, size, and audio mixing.
"""
import logging
import asyncio
from typing import Dict, Any

from app.utils.video_overlay import process_video_overlay

# Configure logging
logger = logging.getLogger(__name__)

class VideoOverlayService:
    """
    Service for overlaying videos on top of a base image.
    
    This service processes requests to overlay one or more videos onto a base image,
    creating dynamic video compositions with control over position, size, timing, and audio.
    """
    
    def __init__(self):
        """Initialize the video overlay service."""
        self.executor = asyncio.get_event_loop().run_in_executor
        logger.info("Video overlay service initialized")
    
    async def overlay_videos(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a video overlay request.
        
        Args:
            params: Job parameters including:
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
            Dictionary with result information
        """
        # Delegate to the modular implementation
        return await process_video_overlay(params)

# Create a singleton instance
video_overlay_service = VideoOverlayService() 