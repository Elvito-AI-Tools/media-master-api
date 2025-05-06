# Video Concatenation

The video concatenation endpoint allows you to join multiple video files into a single continuous video.

## Create Concatenation Job

Create a job to concatenate multiple videos into a single video file.

### Endpoint

```
POST /v1/video/concatenate
```

### Headers

| Name | Required | Description |
|------|----------|-------------|
| X-API-Key | Yes | Your API key for authentication |
| Content-Type | Yes | application/json |

### Request Body

```json
{
  "video_urls": [
    "https://example.com/video1.mp4",
    "https://example.com/video2.mp4",
    "https://example.com/video3.mp4"
  ],
  "output_format": "mp4"
}
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| video_urls | array | Yes | Array of URLs pointing to video files to be concatenated (in order) |
| output_format | string | No | Desired output format (default: "mp4") |

### Supported Output Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| MP4 | .mp4 | Widely supported video format suitable for most platforms |
| WebM | .webm | Open format optimized for web delivery |
| AVI | .avi | Microsoft's Audio Video Interleave format |
| MOV | .mov | Apple QuickTime movie format |
| MKV | .mkv | Matroska video container format |

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
  https://api.mediamaster.com/v1/video/concatenate \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-api-key' \
  -d '{
    "video_urls": [
      "https://example.com/intro.mp4",
      "https://example.com/main-content.mp4",
      "https://example.com/outro.mp4"
    ],
    "output_format": "mp4"
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

Check the status of a video concatenation job.

### Endpoint

```
GET /v1/video/concatenate/{job_id}
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
    "duration": 183.5,
    "size": 28500000,
    "format": "mp4",
    "resolution": "1920x1080"
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
  https://api.mediamaster.com/v1/video/concatenate/j-123e4567-e89b-12d3-a456-426614174000 \
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

- Maximum number of videos: 50
- Maximum combined duration: 12 hours
- Maximum file size per video: 2 GB
- Supported input formats: MP4, WebM, AVI, MOV, MKV
- Processing time depends on the number and size of videos
- Videos are concatenated in the order provided in the request
- No transitions are added between videos by default
- Output video will adopt properties (resolution, bitrate) from the first video
- If videos have different resolutions, aspect ratios, or codecs, they will be automatically adjusted to match 