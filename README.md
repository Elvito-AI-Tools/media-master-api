# Media Master API

A powerful API for generating media content. This project provides asynchronous operations for various media transformations, built with FastAPI and Docker.


## Why use this API?

1. It saves your time and money by using our API to generate long-form videos, audio and more, with few simple API calls you can generate high-quality media content.

2. Replace expensive services like JSON2Video, Creatomate, etc. with this API to generate high-quality media content.

## Features

- Image-to-video conversion with audio and captions
- Text-to-speech conversion using Kokoro TTS
- Media transcription using Whisper
- Videos concatenation
- Secure storage of generated media in AWS S3

## Prerequisites

- AWS S3 account and credentials
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

3. Add your API_KEY and AWS credentials to the .env file:

```bash
# Edit .env with your actual credentials
API_KEY=your_api_key
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=your_region
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
- **Audio Processing**:
  - [Audio Routes Overview](./docs/audio/README.md)
  - [Text to Speech Conversion](./docs/audio/text-to-speech.md)
- **Media Processing**:
  - [Media Routes Overview](./docs/media/README.md)
  - [Media Transcription](./docs/media/transcription.md)
- **Video Processing**:
  - [Video Routes Overview](./docs/video/README.md)
  - [Video Concatenation](./docs/video/concatenate.md)

### Image to Video Conversion

Convert an image to a video with audio and captions:

1. Create a job (POST /v1/image/to-video):

```json
{
  "image_url": "https://example.com/your-image.jpg",
  "audio_url": "https://example.com/your-audio.mp3",
  "should_add_captions": true,
  "captions_properties": {
    "font_size": 24,
    "font_color": "#ffffff",
    "background_color": "#000000",
    "position": "bottom"
  }
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
    "video_duration": 10.0
  },
  "error": null
}
```

### Text to Speech Conversion (Kokoro TTS)

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


### Media Transcription

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

### Videos Concatenation

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

