"""
Main controller for the image-to-video pipeline.

This module orchestrates the entire image-to-video conversion process
by utilizing all the specialized utility modules.
"""
import logging
from typing import Dict, Any, List

from app.utils.image_to_video.image_processing import process_image
from app.utils.image_to_video.audio_processing import (
    process_narrator_audio,
    process_background_music,
    mix_audio_tracks
)
from app.utils.image_to_video.caption_processing import (
    process_captions_from_audio,
    process_captions_from_text
)
from app.utils.image_to_video.video_generation import (
    create_video_with_effects,
    combine_video_audio_captions
)
from app.utils.image_to_video.output_processing import (
    prepare_result,
    cleanup_temp_files
)

logger = logging.getLogger(__name__)

async def process_image_to_video(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process an image-to-video conversion with all steps.
    
    Args:
        params: Job parameters
            - image_url: URL of the image to convert
            - video_length: Length of the output video in seconds
            - frame_rate: Frame rate of the output video
            - zoom_speed: Speed of the zoom effect (0-100)
            - narrator_audio_url: URL of narrator audio file to add
            - narrator_speech_text: Text to convert to speech
            - voice: Voice to use for speech synthesis
            - narrator_vol: Volume level for narrator audio (0-100)
            - background_music_url: URL of background music to add
            - background_music_vol: Volume level for background music (0-100)
            - should_add_captions: Whether to add captions
            - caption_properties: Styling properties for captions
            - match_length: Whether to match output length to 'audio' or 'video'
            
    Returns:
        Dictionary with result information
    """
    # Track created files for cleanup
    temp_files = []
    
    try:
        # Extract basic parameters
        video_length = params.get("video_length", 10.0)
        frame_rate = params.get("frame_rate", 30)
        zoom_speed = params.get("zoom_speed", 10.0)
        match_length = params.get("match_length", "audio")

        print(f"zoom_speed: {zoom_speed}")

        logger.info(f"zoom_speed: {zoom_speed}")
        
        # Step 1: Process the image
        logger.info("Step 1: Processing image")
        image_result = await process_image(params["image_url"])
        image_path = image_result["image_path"]
        temp_files.append(image_path)
        
        # Step 2: Process narrator audio
        logger.info("Step 2: Processing narrator audio")
        narrator_result = await process_narrator_audio(params)
        narrator_audio_path = narrator_result.get("narrator_audio_path")
        speech_text = narrator_result.get("speech_text")
        
        if narrator_audio_path:
            temp_files.append(narrator_audio_path)
        
        # Step 3: Process background music
        logger.info("Step 3: Processing background music")
        background_result = await process_background_music(params)
        background_music_path = background_result.get("background_music_path")
        
        if background_music_path:
            temp_files.append(background_music_path)
        
        # Step 4: Mix audio if both narrator and background music are available
        audio_path = None
        audio_duration = None
        
        if narrator_audio_path and background_music_path:
            logger.info("Step 4: Mixing narrator audio and background music")
            mix_result = await mix_audio_tracks(
                narrator_audio_path,
                background_music_path,
                params
            )
            
            if mix_result.get("mixed_audio_path"):
                audio_path = mix_result["mixed_audio_path"]
                audio_duration = mix_result["audio_duration"]
                temp_files.append(audio_path)
            else:
                # Fallback to narrator audio only
                audio_path = narrator_audio_path
                audio_duration = narrator_result.get("audio_duration")
        elif narrator_audio_path:
            audio_path = narrator_audio_path
            audio_duration = narrator_result.get("audio_duration")
        elif background_music_path:
            audio_path = background_music_path
            audio_duration = background_result.get("background_music_duration")
        
        # Step 5: Process captions
        srt_path = None
        srt_url = None
        
        if params.get("should_add_captions", False) and audio_path:
            logger.info("Step 5: Processing captions")
            if narrator_audio_path:
                caption_result = await process_captions_from_audio(
                    narrator_audio_path,
                    speech_text,
                    params
                )
                srt_path = caption_result.get("srt_path")
                srt_url = caption_result.get("srt_url")
            elif speech_text and audio_duration:
                caption_result = await process_captions_from_text(
                    speech_text,
                    audio_duration,
                    params
                )
                srt_path = caption_result.get("srt_path")
            
            if srt_path:
                temp_files.append(srt_path)
        
        # Step 6: Generate video from image
        logger.info("Step 6: Generating video from image with effects")
        video_path = await create_video_with_effects(
            image_path=image_path,
            video_length=video_length,
            frame_rate=frame_rate,
            zoom_speed=zoom_speed,
            output_dims=image_result["output_dims"],
            scale_dims=image_result["scale_dims"],
            effect_type=params.get("effect_type", "zoom"),
            pan_direction=params.get("pan_direction"),
            ken_burns_keypoints=params.get("ken_burns_keypoints")
        )
        temp_files.append(video_path)
        
        # Step 7: Combine video with audio and captions
        logger.info("Step 7: Combining video with audio and captions")
        final_video_path = await combine_video_audio_captions(
            video_path=video_path,
            audio_path=audio_path,
            srt_path=srt_path,
            caption_properties=params.get("caption_properties"),
            match_length=match_length,
            frame_rate=frame_rate
        )
        temp_files.append(final_video_path)
        
        # Step 8: Prepare result
        logger.info("Step 8: Preparing result")
        result = await prepare_result(
            video_path=final_video_path,
            has_audio=audio_path is not None,
            has_captions=srt_path is not None,
            srt_url=srt_url
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error in process_image_to_video: {e}")
        raise
    
    finally:
        # Step 9: Cleanup
        logger.info("Step 9: Cleaning up temporary files")
        cleanup_temp_files(temp_files) 