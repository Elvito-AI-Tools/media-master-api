# Media Master API

A powerful API for generating media content. This project provides asynchronous operations for various media transformations, built with FastAPI and Docker.


## Why use this API?

1. It saves your time and money by using our API to generate long-form videos, audio and more, with few simple API calls you can generate high-quality media content.

2. Replace expensive services like JSON2Video, Creatomate, Eleven Labs etc. with this API to generate high-quality media content.

## Features

- Image-to-video conversion with audio and captions
- Text-to-speech conversion using Kokoro TTS
- Media transcription using Whisper
- Videos concatenation
- Add audio to videos with volume control and length matching
- Secure storage of generated media in S3

## Prerequisites

- S3 account and credentials
- Docker Desktop installed, you can install it from here: https://www.docker.com/products/docker-desktop/

## Installation

1. Clone the repository:

```bash
git clone https://github.com/Elvito-AI-Tools/media-master-api.git
cd media-master-api
```

2. Copy the .env.example:

```bash
cp .env.example .env
```

3. Add your API_KEY and S3 credentials to the .env file:

```bash

API_KEY=your_secret_api_key_here

# S3 configuration
S3_ACCESS_KEY=your_s3_access_key_here
S3_SECRET_KEY=your_s3_secret_key_here
S3_BUCKET_NAME=your_s3_bucket_name_here
S3_REGION=your_s3_region_here
S3_ENDPOINT_URL=your_s3_endpoint_here

# IF you are using local hosted minio
MINIO_ROOT_USER=minio
MINIO_ROOT_PASSWORD=12345678
```

4. Run and build the docker compose:

```bash
docker-compose up --build
```


## API Documentation

Interactive API documentation is available at http://localhost:8000/docs

### Comprehensive Documentation

For detailed API documentation, we've created a comprehensive documentation set in the [docs](./docs) directory:

- **[API Overview](./docs/README.md)**: Complete overview of all API endpoints
- **Image Processing**:
  - [Image Routes Overview](./docs/image/README.md)
  - [Image to Video Conversion](./docs/image/image-to-video.md)
  - [Image Overlay](./docs/image/image-overlay.md)
  - [Video Overlay on Image](./docs/image/video-overlay.md)
- **Audio Processing**:
  - [Audio Routes Overview](./docs/audio/README.md)
  - [Text to Speech Conversion](./docs/audio/text-to-speech.md)
- **Media Processing**:
  - [Media Routes Overview](./docs/media/README.md)
  - [Media Transcription](./docs/media/transcription.md)
- **Video Processing**:
  - [Video Routes Overview](./docs/video/README.md)
  - [Video Concatenation](./docs/video/concatenate.md)
  - [Add Audio to Video](./docs/video/add_audio.md)

### API Examples

<details>
<summary><strong>Image to Video Conversion</strong></summary>

Convert an image to a video with audio and captions:

1. Create a job (POST /v1/image/to-video):

```json
{
  "image_url": "https://example.com/your-image.jpg",
  "video_length": 10.0,
  "frame_rate": 30,
  "zoom_speed": 10.0,
  "narrator_speech_text": "This is the narrator speaking over this beautiful image",
  "voice": "af_alloy",
  "narrator_vol": 100,
  "background_music_url": "https://example.com/background-music.mp3",
  "background_music_vol": 20,
  "should_add_captions": true,
  "caption_properties": {
    "max_words_per_line": 7,
    "font_size": 24,
    "color": "#ffffff",
    "background_color": "#00000080",
    "position": "bottom"
  },
  "match_length": "audio"
}
```

Response:

```json
{
  "job_id": "68d6fd45-5d30-4fcd-9588-c2c4ff4cce23"
}
```

2. Check job status (GET /v1/image/to-video/{job_id})

Response (when completed):

```json
{
  "job_id": "68d6fd45-5d30-4fcd-9588-c2c4ff4cce23",
  "status": "completed",
  "result": {
    "has_audio": true,
    "has_captions": true,
    "final_video_url": "https://your-bucket.s3.region.amazonaws.com/videos/68d6fd45-5d30-4fcd-9588-c2c4ff4cce23.mp4",
    "video_duration": 15.2,
    "srt_url": "https://your-bucket.s3.region.amazonaws.com/srt/68d6fd45-5d30-4fcd-9588-c2c4ff4cce23.srt"
  },
  "error": null
}
```

#### Audio Mixing Features

The image-to-video endpoint supports sophisticated audio mixing:

- **Dual Audio Sources**: Combine narrator audio (from TTS or direct file) with background music
- **YouTube Support**: Use YouTube URLs directly as background music sources
- **Volume Control**: Adjust volume levels independently for narrator and background music
- **Format Compatibility**: Automatic handling of different audio formats and sample rates
- **Fallback Mechanisms**: Multiple mixing methods ensure reliable audio processing
</details>

<details>
<summary><strong>Image Overlay</strong></summary>

Overlay multiple images on top of a base image with positioning and effects:

1. Create a job (POST /v1/image/add-overlay-image):

```json
{
  "base_image_url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png",
  "overlay_images": [
    {
      "url": "https://python.org/static/community_logos/python-logo.png",
      "x": 0.5,
      "y": 0.8,
      "width": 0.3,
      "opacity": 0.9,
      "z_index": 1
    },
    {
      "url": "https://upload.wikimedia.org/wikipedia/commons/6/6a/JavaScript-logo.png",
      "x": 0.8,
      "y": 0.2,
      "width": 0.2,
      "rotation": 15,
      "opacity": 0.8,
      "z_index": 2
    }
  ],
  "output_format": "png",
  "output_quality": 95,
  "output_width": 1200,
  "maintain_aspect_ratio": true
}
```

Response:

```json
{
  "job_id": "a1b2c3d4-5e6f-7g8h-9i0j-1k2l3m4n5o6p"
}
```

2. Check job status (GET /v1/image/add-overlay-image/{job_id})

Response (when completed):

```json
{
  "job_id": "a1b2c3d4-5e6f-7g8h-9i0j-1k2l3m4n5o6p",
  "status": "completed",
  "result": {
    "image_url": "https://your-bucket.s3.region.amazonaws.com/image-overlay-results/a1b2c3d4-5e6f-7g8h-9i0j-1k2l3m4n5o6p.png",
    "width": 1200,
    "height": 800,
    "format": "png",
    "storage_path": "image-overlay-results/a1b2c3d4-5e6f-7g8h-9i0j-1k2l3m4n5o6p.png"
  },
  "error": null
}
```

#### Image Overlay Features

The image overlay endpoint provides advanced image composition capabilities:

- **Multiple Overlays**: Add any number of images on top of a base image
- **Precise Positioning**: Position overlays using normalized coordinates (0.0 to 1.0)
- **Sizing Control**: Maintain aspect ratios or set specific dimensions relative to the base image
- **Visual Effects**: Apply rotation and opacity to overlays
- **Layering Control**: Use z-index to control which overlays appear on top of others
- **Format Options**: Output in PNG, JPEG, or WebP with quality control
</details>

<details>
<summary><strong>Text to Speech Conversion (Kokoro TTS)</strong></summary>

Convert text to speech using Kokoro TTS via an external service:

1. Create a job (POST /v1/audio/text-to-speech):

```json
{
  "text": "Hello, this is a test of the Kokoro text to speech system.",
  "model": "af_heart"
}
```

The `model` parameter is optional and defaults to "af_alloy". Available models include: "
                    "af_alloy, af_aoede, af_bella, af_heart, af_jadzia, af_jessica, af_kore, "
                    "af_nicole, af_nova, af_river, af_sarah, af_sky, af_v0, af_v0bella, af_v0irulan, "
                    "af_v0nicole, af_v0sarah, af_v0sky, am_adam, am_echo, am_eric, am_fenrir, am_liam, "
                    "am_michael, am_onyx, am_puck, am_santa, am_v0adam, am_v0gurney, am_v0michael, "
                    "bf_alice, bf_emma, bf_lily, bf_v0emma, bf_v0isabella, bm_daniel, bm_fable, "
                    "bm_george, bm_lewis, bm_v0george, bm_v0lewis, ef_dora, em_alex, em_santa, ff_siwis, "
                    "hf_alpha, hf_beta, hm_omega, hm_psi, if_sara, im_nicola, jf_alpha, jf_gongitsune, "
                    "jf_nezumi, jf_tebukuro, jm_kumo, pf_dora, pm_alex, pm_santa, zf_xiaobei, zf_xiaoni, "
                    "zf_xiaoxiao, zf_xiaoyi, zm_yunjian, zm_yunxi, zm_yunxia, zm_yunyang"

Response:

```json
{
  "job_id": "c3d5e7f9-1a2b-3c4d-5e6f-7a8b9c0d1e2f"
}
```

2. Check job status (GET /v1/audio/text-to-speech/{job_id})

Response (when completed):

```json
{
  "job_id": "c3d5e7f9-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
  "status": "completed",
  "result": {
    "audio_url": "https://your-bucket.s3.region.amazonaws.com/audio/c3d5e7f9-1a2b-3c4d-5e6f-7a8b9c0d1e2f.mp3",
    "tts_engine": "kokoro"
  },
  "error": null
}
``` 
</details>

<details>
<summary><strong>Media Transcription</strong></summary>

Transcribe an audio or video file:

1. Create a job (POST /v1/media/transcription):

```json
{
  "media_url": "https://example.com/your-media.mp3",
  "include_text": true,
  "include_srt": true,
  "word_timestamps": true,
  "language": "en"
}
```

Response:

```json
{
  "job_id": "c3d5e7f9-1a2b-3c4d-5e6f-7a8b9c0d1e2f"
}
```

2. Check job status (GET /v1/media/transcription/{job_id})

Response (when completed):

```json
{
  "job_id": "c3d5e7f9-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
  "status": "completed",
  "result": {
    "text": "Hello, this is a test of the media transcription system.",
    "srt_url": "https://your-bucket.s3.region.amazonaws.com/srt/c3d5e7f9-1a2b-3c4d-5e6f-7a8b9c0d1e2f.srt",
    "words": [
      {
        "word": "Hello",
        "start_time": 0.0,
        "end_time": 1.0
      },
      {
        "word": "this",
        "start_time": 1.0,
        "end_time": 2.0
      },
      {
        "word": "is",
        "start_time": 2.0,
        "end_time": 3.0
      },
      {
        "word": "a",
        "start_time": 3.0,
        "end_time": 4.0
      }
    ]
  },
  "error": null
}
```
</details>

<details>
<summary><strong>Videos Concatenation</strong></summary>

Concatenate multiple videos:

1. Create a job (POST /v1/video/concatenate):

```json
{
  "video_urls": ["https://example.com/video1.mp4", "https://example.com/video2.mp4"]
}
```

Response:

```json
{
  "job_id": "c3d5e7f9-1a2b-3c4d-5e6f-7a8b9c0d1e2f"
}
```

2. Check job status (GET /v1/video/concatenate/{job_id})

Response (when completed):

```json
{
  "job_id": "c3d5e7f9-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
  "status": "completed",
  "result": {
    "url": "https://your-bucket.s3.region.amazonaws.com/videos/c3d5e7f9-1a2b-3c4d-5e6f-7a8b9c0d1e2f.mp4"
  },
  "error": null
}
```
</details>

<details>
<summary><strong>Add Audio to Video</strong></summary>

Add audio to a video with volume control:

1. Create a job (POST /v1/video/add-audio):

```json
{
  "video_url": "https://example.com/your-video.mp4",
  "audio_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "video_volume": 20,
  "audio_volume": 80,
  "match_length": "video"
}
```

Response:

```json
{
  "job_id": "c3d5e7f9-1a2b-3c4d-5e6f-7a8b9c0d1e2f"
}
```

2. Check job status (GET /v1/video/add-audio/{job_id})

Response (when completed):

```json
{
  "job_id": "c3d5e7f9-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
  "status": "completed",
  "result": {
    "url": "https://your-bucket.s3.region.amazonaws.com/output/videos/mixed_video_c3d5e7f9-1a2b-3c4d-5e6f-7a8b9c0d1e2f.mp4",
    "path": "output/videos/mixed_video_c3d5e7f9-1a2b-3c4d-5e6f-7a8b9c0d1e2f.mp4",
    "duration": 120.5
  },
  "error": null
}
```
</details>

### Video Overlay on Image

Create dynamic video content by overlaying animated videos on static images:

```bash
# Create a video overlay job
curl -X POST "http://localhost:8000/v1/image/add-video-overlay" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "base_image_url": "https://example.com/background.jpg",
    "overlay_videos": [
      {
        "url": "https://example.com/animated-logo.mp4",
        "x": 0.85,
        "y": 0.85,
        "width": 0.2,
        "opacity": 0.9,
        "start_time": 0.0,
        "end_time": 10.0,
        "volume": 0.0
      }
    ],
    "output_duration": 10.0,
    "frame_rate": 30,
    "background_audio_url": "https://example.com/music.mp3",
    "background_audio_volume": 0.2
  }'

# Response
{
  "job_id": "video-overlay-12345"
}

# Check job status
curl -X GET "http://localhost:8000/v1/image/add-video-overlay/video-overlay-12345" \
  -H "X-API-Key: your-api-key"

# Response when completed
{
  "job_id": "video-overlay-12345",
  "status": "completed",
  "result": {
    "video_url": "https://your-bucket.s3.region.amazonaws.com/video-overlay-results/result.mp4",
    "width": 1920,
    "height": 1080,
    "duration": 10.0,
    "frame_rate": 30,
    "has_audio": true
  }
}
```

### Video Overlay Features

- **Multiple Video Overlays**: Layer multiple videos with precise timing control
- **Flexible Positioning**: Position overlays anywhere on the base image using relative coordinates
- **Visual Effects**: Control opacity, rotation, and layering with z-index
- **Audio Mixing**: Combine overlay video audio with background music
- **Timing Control**: Set start/end times for each overlay with looping support
- **Dynamic Compositions**: Create picture-in-picture effects and animated watermarks

