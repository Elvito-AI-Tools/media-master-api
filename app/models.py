from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, AnyUrl


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(str, Enum):
    """Job type enumeration."""
    IMAGE_TO_VIDEO = "image_to_video"
    TEXT_TO_SPEECH = "text_to_speech"
    MEDIA_TRANSCRIPTION = "media_transcription"
    VIDEO_CONCATENATION = "video_concatenation"
    VIDEO_ADD_AUDIO = "video_add_audio"
    VIDEO_ADD_CAPTIONS = "video_add_captions"


class Job(BaseModel):
    """Job model."""
    id: str
    status: JobStatus = JobStatus.PENDING
    operation: str
    params: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str


class JobResponse(BaseModel):
    """Job response model."""
    job_id: str


class JobStatusResponse(BaseModel):
    """Job status response model."""
    job_id: str
    status: JobStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None





class TextToSpeechRequest(BaseModel):
    """
    Text to speech request model using Kokoro TTS.
    
    The text will be converted to an audio file using the specified Kokoro voice.
    """
    text: str = Field(
        description="The text that will be converted to speech."
    )
    voice: str = Field(
        default="af_alloy",
        description="The Kokoro voice to use for speech synthesis. Available voices include: "
                    "af_alloy, af_aoede, af_bella, af_heart, af_jadzia, af_jessica, af_kore, "
                    "af_nicole, af_nova, af_river, af_sarah, af_sky, af_v0, af_v0bella, af_v0irulan, "
                    "af_v0nicole, af_v0sarah, af_v0sky, am_adam, am_echo, am_eric, am_fenrir, am_liam, "
                    "am_michael, am_onyx, am_puck, am_santa, am_v0adam, am_v0gurney, am_v0michael, "
                    "bf_alice, bf_emma, bf_lily, bf_v0emma, bf_v0isabella, bm_daniel, bm_fable, "
                    "bm_george, bm_lewis, bm_v0george, bm_v0lewis, ef_dora, em_alex, em_santa, ff_siwis, "
                    "hf_alpha, hf_beta, hm_omega, hm_psi, if_sara, im_nicola, jf_alpha, jf_gongitsune, "
                    "jf_nezumi, jf_tebukuro, jm_kumo, pf_dora, pm_alex, pm_santa, zf_xiaobei, zf_xiaoni, "
                    "zf_xiaoxiao, zf_xiaoyi, zm_yunjian, zm_yunxi, zm_yunxia, zm_yunyang"
    )


class TextToSpeechResult(BaseModel):
    """Text to speech result model."""
    audio_url: AnyUrl 


class MediaTranscriptionRequest(BaseModel):
    """
    Media transcription request model.
    
    This model represents a request to transcribe a media file (audio or video)
    using the Whisper model.
    """
    media_url: AnyUrl = Field(
        description="URL of the media file to be transcribed. Supports S3 URLs and most public media URLs."
    )
    include_text: bool = Field(
        default=True,
        description="Include plain text transcription in the response."
    )
    include_srt: bool = Field(
        default=True,
        description="Include SRT format subtitles in the response and save to S3."
    )
    word_timestamps: bool = Field(
        default=False,
        description="Include timestamps for individual words. This enables more precise timing information."
    )
    language: Optional[str] = Field(
        default=None,
        description="Source language code for transcription (e.g., 'en', 'fr', 'es'). "
                   "If not provided, Whisper will auto-detect the language."
    )
    max_words_per_line: Optional[int] = Field(
        default=10,
        ge=1,
        le=20,
        description="Maximum number of words per line in the generated SRT file. "
                   "Controls how caption text is split across lines for better readability."
    )


class MediaTranscriptionResult(BaseModel):
    """Media transcription result model."""
    text: Optional[str] = Field(
        None,
        description="Plain text transcription of the media."
    )
    srt_url: Optional[AnyUrl] = Field(
        None, 
        description="URL to the SRT subtitle file stored in S3."
    )
    words: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Word-level timestamps with start and end times for each word."
    )



class VideoCaptionProperties(BaseModel):
    """
    Properties for customizing the appearance and style of video captions.
    """
    line_color: Optional[str] = Field(
        default=None,
        description="Color of the text line (e.g., 'white', '#FFFFFF')."
    )
    word_color: Optional[str] = Field(
        default=None,
        description="Color of individual words when highlighted (e.g., 'yellow', '#FFFF00')."
    )
    outline_color: Optional[str] = Field(
        default=None,
        description="Color of text outline/stroke (e.g., 'black', '#000000')."
    )
    all_caps: Optional[bool] = Field(
        default=None,
        description="Whether to convert all text to uppercase."
    )
    max_words_per_line: Optional[int] = Field(
        default=None,
        ge=1,
        le=20,
        description="Maximum number of words to display per line in generated captions. Controls how caption text is split across lines for better readability. Valid range is 1-20, defaults to 10 if not specified."
    )
    x: Optional[int] = Field(
        default=None,
        description="X coordinate for caption positioning (manual positioning)."
    )
    y: Optional[int] = Field(
        default=None,
        description="Y coordinate for caption positioning (manual positioning)."
    )
    position: Optional[str] = Field(
        default=None,
        description="Predefined position for captions (e.g., 'bottom_center', 'top_left')."
    )
    alignment: Optional[str] = Field(
        default=None,
        description="Text alignment within caption area ('left', 'center', 'right')."
    )
    font_family: Optional[str] = Field(
        default=None,
        description="Font family to use for captions."
    )
    font_size: Optional[int] = Field(
        default=None,
        description="Font size for captions in pixels."
    )
    bold: Optional[bool] = Field(
        default=None,
        description="Whether to apply bold formatting to text."
    )
    italic: Optional[bool] = Field(
        default=None,
        description="Whether to apply italic formatting to text."
    )
    underline: Optional[bool] = Field(
        default=None,
        description="Whether to apply underline formatting to text."
    )
    strikeout: Optional[bool] = Field(
        default=None,
        description="Whether to apply strikeout formatting to text."
    )
    style: Optional[str] = Field(
        default=None,
        description="Caption display style ('highlight', 'word_by_word')."
    )
    outline_width: Optional[int] = Field(
        default=None,
        description="Width of text outline/stroke in pixels."
    )
    spacing: Optional[int] = Field(
        default=None,
        description="Spacing between lines in pixels."
    )
    angle: Optional[int] = Field(
        default=None,
        description="Rotation angle of text in degrees."
    )
    shadow_offset: Optional[int] = Field(
        default=None,
        description="Shadow offset distance in pixels."
    )
    # Background properties
    background_color: Optional[str] = Field(
        default=None,
        description="Background color for captions (e.g., 'black', '#000000')."
    )
    background_opacity: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Opacity of background from 0.0 (transparent) to 1.0 (opaque)."
    )
    background_padding: Optional[int] = Field(
        default=None,
        description="Padding around text within background in pixels."
    )
    background_radius: Optional[int] = Field(
        default=None,
        description="Corner radius for background in pixels for rounded corners."
    )


class ImageToVideoRequest(BaseModel):
    """
    Comprehensive request model for creating a video from an image with audio and captions.
    
    This combines the functionality of image-to-video conversion, text-to-speech,
    audio mixing, and video captioning in a single request.
    
    For best results:
    - For standard quality: frame_rate=30, zoom_speed=10, video_length=10
    - For high quality: frame_rate=60, zoom_speed=10, video_length=15 
    """
    # Image to video parameters
    image_url: AnyUrl = Field(
        description="URL of the image to convert to video."
    )
    video_length: float = Field(
        default=10.0, 
        gt=0, 
        le=30,
        description="Length of output video in seconds. Longer videos will have smoother zoom effects."
    )
    frame_rate: int = Field(
        default=30, 
        gt=0, 
        le=60,
        description="Frame rate of output video. Use 30 for standard quality or 60 for smoother results."
    )
    zoom_speed: float = Field(
        default=10.0, 
        ge=0, 
        le=100,
        description="Speed of zoom effect (0-100). Values between 5-20 produce the smoothest results."
    )
    effect_type: str = Field(
        default="none",
        description="Type of animation effect to apply. Options: 'none', 'zoom', 'pan', 'ken_burns'. Use 'none' for a static video with no motion effects."
    )
    pan_direction: Optional[str] = Field(
        default=None,
        description="Direction of pan effect when effect_type is 'pan'. Options: 'left_to_right', 'right_to_left', 'top_to_bottom', 'bottom_to_top', 'diagonal_top_left', 'diagonal_top_right', 'diagonal_bottom_left', 'diagonal_bottom_right'."
    )
    ken_burns_keypoints: Optional[List[Dict[str, float]]] = Field(
        default=None,
        description="List of keypoints for Ken Burns effect when effect_type is 'ken_burns'. Each keypoint is a dictionary with 'time' (in seconds), 'x' (0-1), 'y' (0-1), and 'zoom' (scale factor) values. At least 2 keypoints should be provided."
    )
    
    # Narrator audio parameters (optional)
    narrator_speech_text: Optional[str] = Field(
        default=None,
        description="Text to convert to speech. If provided, a TTS audio will be added to the video."
    )
    voice: Optional[str] = Field(
        default="af_alloy",
        description="The Kokoro voice to use for speech synthesis if narrator_speech_text is provided."
    )
    narrator_audio_url: Optional[AnyUrl] = Field(
        default=None,
        description="URL of an existing audio file to add to the video as narration. Ignored if narrator_speech_text is provided."
    )
    narrator_vol: int = Field(
        default=100,
        ge=0,
        le=100,
        description="Volume level for the narrator audio track (0-100)."
    )
    
    # Background music parameters (optional)
    background_music_url: Optional[AnyUrl] = Field(
        default=None,
        description="URL of background music to add to the video. Can be a direct audio file or YouTube URL."
    )
    background_music_vol: int = Field(
        default=20,
        ge=0,
        le=100,
        description="Volume level for the background music track (0-100)."
    )
    
    # Caption parameters (optional)
    should_add_captions: bool = Field(
        default=False,
        description="Whether to automatically add captions by transcribing the audio. If enabled, captions will be generated from either the narrator_speech_text or the narrator audio content."
    )
    caption_properties: Optional[VideoCaptionProperties] = Field(
        default=None,
        description="Styling properties for captions, if should_add_captions is true."
    )
    
    # Video and audio synchronization
    match_length: str = Field(
        default="audio",
        description="Whether to match the output video length to the 'audio' or 'video'. If 'audio', the video will loop if necessary."
    )


class ImageToVideoResult(BaseModel):
    """
    Result model for the comprehensive image to video with audio and captions operation.
    """
    final_video_url: AnyUrl = Field(
        description="URL to the final video with audio and captions."
    )
    video_duration: float = Field(
        description="Duration of the output video in seconds."
    )
    has_audio: bool = Field(
        description="Whether the video has audio."
    )
    has_captions: bool = Field(
        description="Whether the video has captions."
    )
    audio_url: Optional[AnyUrl] = Field(
        default=None,
        description="URL to the audio file used (if applicable)."
    )
    srt_url: Optional[AnyUrl] = Field(
        default=None,
        description="URL to the SRT subtitle file (if applicable)."
    )


class VideoConcatenateRequest(BaseModel):
    """
    Request model for concatenating multiple videos.
    
    This model represents a request to concatenate multiple videos into a single video.
    """
    video_urls: List[str] = Field(
        ..., 
        description="List of video URLs to concatenate. Supports S3 URLs and other video URLs."
    )
    output_format: str = Field(
        "mp4", 
        description="Output video format (e.g., 'mp4', 'webm', 'mov')"
    )


class VideoConcatenateResult(BaseModel):
    """
    Result model for video concatenation operation.
    """
    url: AnyUrl = Field(
        description="URL to the concatenated video file stored in S3."
    )
    path: str = Field(
        description="Storage path of the concatenated video in S3."
    )


class VideoAddAudioRequest(BaseModel):
    """
    Request model for adding audio to a video.
    
    This model represents a request to add background music or other audio to a video,
    with control over volume levels and length matching.
    """
    video_url: str = Field(
        ..., 
        description="URL of the video to add audio to. Supports S3 URLs and other video URLs."
    )
    audio_url: str = Field(
        ..., 
        description="URL of the audio to add to the video. Supports S3 URLs and other audio URLs."
    )
    video_volume: int = Field(
        default=100,
        ge=0,
        le=100,
        description="Volume level for the video track (0-100)."
    )
    audio_volume: int = Field(
        default=20,
        ge=0,
        le=100,
        description="Volume level for the audio track (0-100)."
    )
    match_length: str = Field(
        default="video",
        description="Whether to match the output length to the 'audio' or 'video'. Default is 'video'."
    )


class VideoAddAudioResult(BaseModel):
    """
    Result model for video add audio operation.
    """
    url: AnyUrl = Field(
        description="URL to the video with added audio stored in S3."
    )
    path: str = Field(
        description="Storage path of the video with added audio in S3."
    )
    duration: float = Field(
        description="Duration of the output video in seconds."
    ) 


class VideoAddCaptionsRequest(BaseModel):
    """
    Request model for adding captions to a video.
    
    This model represents a request to add captions to a video, with options for
    customizing their appearance and using different caption sources.
    """
    video_url: str = Field(
        ...,
        description="URL of the video to add captions to. Supports S3 URLs and other video URLs."
    )
    captions: Optional[str] = Field(
        default=None,
        description="Caption content, which can be raw text, URL to an SRT/ASS subtitle file, or None to use audio from the video."
    )
    caption_properties: Optional[VideoCaptionProperties] = Field(
        default=None,
        description="Styling properties for captions, allowing customization of appearance and behavior."
    )


class VideoAddCaptionsResult(BaseModel):
    """
    Result model for video add captions operation.
    """
    url: AnyUrl = Field(
        description="URL to the video with added captions stored in S3."
    )
    path: str = Field(
        description="Storage path of the video with added captions in S3."
    )
    duration: float = Field(
        description="Duration of the output video in seconds."
    )
    width: int = Field(
        description="Width of the output video in pixels."
    )
    height: int = Field(
        description="Height of the output video in pixels."
    )
    srt_url: Optional[AnyUrl] = Field(
        default=None,
        description="URL to the SRT subtitle file used (if applicable)."
    ) 