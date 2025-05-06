# Media Transcription

The transcription endpoint allows you to convert audio and video content into text and subtitles using the Whisper model.

## Create Transcription Job

Create a job to transcribe audio or video content.

### Endpoint

```
POST /v1/media/transcription
```

### Headers

| Name | Required | Description |
|------|----------|-------------|
| X-API-Key | Yes | Your API key for authentication |
| Content-Type | Yes | application/json |

### Request Body

```json
{
  "media_url": "https://example.com/media/recording.mp3",
  "include_text": true,
  "include_srt": true,
  "word_timestamps": false,
  "language": "en",
  "max_words_per_line": 10
}
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| media_url | string | Yes | URL of the media file to be transcribed |
| include_text | boolean | No | Include plain text transcription in the response (default: true) |
| include_srt | boolean | No | Include SRT format subtitles in the response (default: true) |
| word_timestamps | boolean | No | Include timestamps for individual words (default: false) |
| language | string | No | Source language code for transcription (optional, auto-detected if not provided) |
| max_words_per_line | integer | No | Maximum words per line in SRT (default: 10) |

### Supported Languages

The transcription service supports a wide range of languages, including but not limited to:

| Language Code | Language |
|---------------|----------|
| en | English |
| fr | French |
| de | German |
| es | Spanish |
| it | Italian |
| ja | Japanese |
| ko | Korean |
| zh | Chinese |
| ru | Russian |
| pt | Portuguese |

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
  https://api.mediamaster.com/v1/media/transcription \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-api-key' \
  -d '{
    "media_url": "https://example.com/media/interview.mp4",
    "include_text": true,
    "include_srt": true,
    "word_timestamps": true,
    "language": "en",
    "max_words_per_line": 8
  }'
```

#### Response

```json
{
  "job_id": "j-123e4567-e89b-12d3-a456-426614174000"
}
```

## Get Job Status

Check the status of a transcription job.

### Endpoint

```
GET /v1/media/transcription/{job_id}
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
    "text": "This is the full text transcription of the media file. It contains all the spoken content in plain text format without timestamps or formatting.",
    "srt_url": "https://cdn.mediamaster.com/output/j-123e4567.srt",
    "words": [
      {
        "word": "This",
        "start": 0.5,
        "end": 0.7,
        "confidence": 0.98
      },
      {
        "word": "is",
        "start": 0.8,
        "end": 0.9,
        "confidence": 0.99
      },
      // ...more words
    ]
  },
  "error": null
}
```

#### Result Fields

| Field | Description |
|-------|-------------|
| text | Full text transcription (included if include_text was true) |
| srt_url | URL to download the SRT subtitle file (included if include_srt was true) |
| words | Array of word objects with timestamps (included if word_timestamps was true) |

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
  https://api.mediamaster.com/v1/media/transcription/j-123e4567-e89b-12d3-a456-426614174000 \
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

## Technical Details

- Maximum media file size: 1 GB
- Maximum media duration: 4 hours
- Supported audio formats: MP3, WAV, M4A, AAC, FLAC
- Supported video formats: MP4, MOV, AVI, MKV, WebM
- Processing time depends on media length (typically 10-25% of the media duration)
- Accuracy varies based on audio quality, background noise, and accents 