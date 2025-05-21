"""
Media processor service to generate videos from images with audio and captions 
using a streamlined FFmpeg pipeline.

This service reduces S3 uploads/downloads by combining multiple operations into fewer FFmpeg commands.

## How the Image-to-Video Service Works (Step-by-Step)

1. **Image Processing**:
   - Downloads the input image from the provided URL
   - Analyzes image dimensions to determine appropriate video dimensions
   - Prepares the image for video conversion

2. **Audio Processing**:
   - Handles audio from two potential sources:
     a. Direct audio file input (narrator_audio_url)
     b. Text-to-speech generation (narrator_speech_text)
   - Processes background music if provided
   - Mixes narrator audio with background music if both are present
   - Adjusts volume levels based on user preferences

3. **Caption Generation**:
   - Creates captions from speech text or transcribes audio
   - Generates subtitle files (SRT or ASS) with appropriate styling
   - Applies word-level timestamps for advanced caption styles

4. **Video Generation**:
   - Converts the still image into a video with smooth zoom effects
   - Controls video parameters (length, frame rate, zoom speed)
   - Determines optimal video dimensions based on image orientation

5. **Media Integration**:
   - Combines the video, audio, and captions in a single FFmpeg pipeline
   - Applies subtitle styling according to user preferences
   - Synchronizes audio and video duration based on user settings

6. **Output Processing**:
   - Generates the final video file with all elements combined
   - Uploads the result to S3 storage
   - Returns URLs and metadata about the created video

7. **Cleanup**:
   - Removes all temporary files created during processing
"""
import logging
import asyncio
from typing import Dict, Any, Optional

from app.utils.image_to_video.controller import process_image_to_video


# Configure logging
logger = logging.getLogger(__name__)

class ImageToVideoService:
    """
    Service for generating videos from images with audio and captions in an optimized way.
    
    This service combines multiple operations (image to video, audio generation, 
    captioning) into fewer FFmpeg commands, reducing the need for S3 roundtrips.
    
    The implementation delegates to modular utility functions in the 
    app.utils.image_to_video package.
    """
    
    def __init__(self):
        """Initialize the optimized media processor service."""
        self.executor = asyncio.get_event_loop().run_in_executor
        logger.info("Optimized media processor service initialized")
    
    async def image_to_video(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an optimized image-to-video conversion with audio and captions in one pipeline.
        
        Args:
            params: Job parameters
                - image_url: URL of the image to convert
                - video_length: Length of the output video in seconds
                - frame_rate: Frame rate of the output video
                - zoom_speed: Speed of the zoom effect (0-100)
                - narrator_audio_url: URL of narrator audio file to add (prioritized over narrator_speech_text)
                - narrator_speech_text: Text to convert to speech (used only if narrator_audio_url is not provided)
                - voice: Voice to use for speech synthesis (when using narrator_speech_text)
                - narrator_vol: Volume level for the narrator audio track (0-100)
                - background_music_url: URL of background music to add (can be YouTube URL)
                - background_music_vol: Volume level for the background music track (0-100)
                - should_add_captions: Whether to add captions
                - caption_properties: Styling properties for captions (optional)
                - match_length: Whether to match output length to 'audio' or 'video'
                
        Returns:
            Dictionary with result information
        """
        # Delegate to the modular implementation
        return await process_image_to_video(params)

# Create a singleton instance
image_to_video_service = ImageToVideoService() 