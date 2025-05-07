# Add Audio to Video

The add audio endpoint allows you to add background music or other audio to videos with control over volume levels and length matching.

## Create Add Audio Job

Create a job to add audio to a video with options for volume control and length matching.

### Endpoint

```
POST /v1/video/add-audio
```

### Headers

| Name | Required | Description |
|------|----------|-------------|
| X-API-Key | Yes | Your API key for authentication |
| Content-Type | Yes | application/json |

### Request Body

```json
{
  "video_url": "https://example.com/video.mp4",
  "audio_url": "https://example.com/audio.mp3",
  "video_volume": 100,
  "audio_volume": 50,
  "match_length": "video"
}
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| video_url | string | Yes | URL pointing to the video file |
| audio_url | string | Yes | URL pointing to the audio file (can be a direct file URL or YouTube URL) |
| video_volume | integer | No | Volume level for the video's original audio track (0-100, default: 100) |
| audio_volume | integer | No | Volume level for the added audio track (0-100, default: 50) |
| match_length | string | No | Whether to match the output length to "video" or "audio" (default: "video") |

### Length Matching Options

| Option | Description |
|--------|-------------|
| video | The output video length will match the original video's length. If the audio is shorter, it will be looped to fill the video duration. |
| audio | The output video length will match the audio's length. If the video is shorter, it will be looped to fill the audio duration. |

### Response

```json
{
  "job_id": "j-123e4567-e89b-12d3-a456-426614174000",
  "status": "processing"
}
```

### Example

#### Request

```bash
curl -X POST \
  https://api.mediamaster.com/v1/video/add-audio \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-api-key' \
  -d '{
    "video_url": "https://example.com/my-video.mp4",
    "audio_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "video_volume": 20,
    "audio_volume": 80,
    "match_length": "video"
  }'
```

#### Response

```json
{
  "job_id": "j-123e4567-e89b-12d3-a456-426614174000",
  "status": "processing"
}
```

## Get Job Status

Check the status of an add audio job.

### Endpoint

```
GET /v1/video/add-audio/{job_id}
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
    "url": "https://cdn.mediamaster.com/output/videos/mixed_video_j-123e4567.mp4",
    "path": "output/videos/mixed_video_j-123e4567.mp4",
    "duration": 183.5
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
  https://api.mediamaster.com/v1/video/add-audio/j-123e4567-e89b-12d3-a456-426614174000 \
  -H 'X-API-Key: your-api-key'
```

### Error Responses

#### 404 Not Found

```json
{
  "detail": "Job not found: j-123e4567-e89b-12d3-a456-426614174000"
}
```

#### 401 Unauthorized

```json
{
  "detail": "Invalid API key"
}
```

## Technical Details

- **YouTube Support**: The service can extract audio directly from YouTube URLs
- **Volume Control**: Both the video's original audio and the added audio can have their volumes adjusted independently
- **Length Matching**: The service can match the output length to either the video or audio duration
- **Audio Looping**: Shorter audio tracks can be automatically looped to fill longer videos
- **Video Looping**: Shorter videos can be automatically looped to match longer audio tracks
- **Supported video formats**: MP4, WebM, AVI, MOV, MKV
- **Supported audio formats**: MP3, WAV, AAC, FLAC, OGG
- **Maximum video duration**: 2 hours
- **Maximum audio duration**: 3 hours
- **Processing time**: Depends on the length and size of the media files 