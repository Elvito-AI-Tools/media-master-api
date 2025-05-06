# Image to Video Conversion

The image-to-video endpoint allows you to convert a static image into a dynamic video with optional audio and captions.

## Create Image to Video Job

Convert an image to a video with a Ken Burns zoom effect and optional audio and captions.

### Endpoint

```
POST /v1/image/to-video
```

### Headers

| Name | Required | Description |
|------|----------|-------------|
| X-API-Key | Yes | Your API key for authentication |
| Content-Type | Yes | application/json |

### Request Body

```json
{
  "image_url": "https://example.com/image.jpg",
  "video_length": 10,
  "frame_rate": 30,
  "zoom_speed": 1.0,
  "speech_text": "This is optional text that will be converted to speech",
  "voice": "en-US-Neural2-F",
  "audio_url": "https://example.com/audio.mp3",
  "audio_vol": 80,
  "should_add_captions": true,
  "caption_properties": {
    "max_words_per_line": 10,
    "font_size": 24,
    "font_family": "Arial",
    "color": "#FFFFFF",
    "position": "bottom"
  },
  "match_length": "audio"
}
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| image_url | string | Yes | URL of the image to convert to video |
| video_length | number | Yes | Length of the output video in seconds |
| frame_rate | number | No | Frame rate of the output video (default: 30) |
| zoom_speed | number | No | Speed of the Ken Burns effect (0.5-2.0, default: 1.0) |
| speech_text | string | No | Text to convert to speech (if provided, audio_url is ignored) |
| voice | string | No | Voice ID to use for speech synthesis |
| audio_url | string | No | URL of audio file to add (ignored if speech_text is provided) |
| audio_vol | number | No | Volume level for the audio track (0-100, default: 80) |
| should_add_captions | boolean | No | Whether to automatically add captions (default: false) |
| caption_properties | object | No | Styling properties for captions |
| caption_properties.max_words_per_line | number | No | Max words per caption line (1-20, default: 10) |
| caption_properties.font_size | number | No | Font size for captions (default: 24) |
| caption_properties.font_family | string | No | Font family for captions (default: Arial) |
| caption_properties.color | string | No | Caption text color (default: #FFFFFF) |
| caption_properties.position | string | No | Caption position (top, middle, bottom; default: bottom) |
| match_length | string | No | Whether to match output length to 'audio' or 'video' (default: video) |

### Response

```json
{
  "job_id": "j-123e4567-e89b-12d3-a456-426614174000"
}
```

### Example

#### Request

```bash
curl -X POST \
  https://api.mediamaster.com/v1/image/to-video \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-api-key' \
  -d '{
    "image_url": "https://example.com/mountain.jpg",
    "video_length": 15,
    "frame_rate": 30,
    "zoom_speed": 1.2,
    "speech_text": "Explore the breathtaking views of the mountain landscape",
    "voice": "en-US-Neural2-F",
    "audio_vol": 75,
    "should_add_captions": true,
    "match_length": "audio"
  }'
```

#### Response

```json
{
  "job_id": "j-123e4567-e89b-12d3-a456-426614174000"
}
```

## Get Job Status

Check the status of an image-to-video conversion job.

### Endpoint

```
GET /v1/image/to-video/{job_id}
```

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| job_id | string | Yes | ID of the job to get status for |

### Headers

| Name | Required | Description |
|------|----------|-------------|
| X-API-Key | Yes | Your API key for authentication |

### Response

```json
{
  "job_id": "j-123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "result": {
    "output_url": "https://cdn.mediamaster.com/output/j-123e4567.mp4",
    "duration": 15.5,
    "size": 12500000,
    "format": "mp4",
    "resolution": "1280x720"
  },
  "error": null
}
```

#### Status Values

| Status | Description |
|--------|-------------|
| queued | Job is in the queue waiting to be processed |
| processing | Job is currently being processed |
| completed | Job has completed successfully |
| failed | Job has failed with an error |

### Example

```bash
curl -X GET \
  https://api.mediamaster.com/v1/image/to-video/j-123e4567-e89b-12d3-a456-426614174000 \
  -H 'X-API-Key: your-api-key'
```

### Error Responses

#### 404 Not Found

```json
{
  "detail": "Job with ID j-123e4567-e89b-12d3-a456-426614174000 not found"
}
```

#### 401 Unauthorized

```json
{
  "detail": "Invalid API key"
}
``` 