# Text to Speech Conversion

The text-to-speech endpoint allows you to convert text into natural-sounding speech using Kokoro TTS.

## Create Text to Speech Job

Convert text to speech using the specified voice.

### Endpoint

```
POST /v1/audio/text-to-speech
```

### Headers

| Name | Required | Description |
|------|----------|-------------|
| X-API-Key | Yes | Your API key for authentication |
| Content-Type | Yes | application/json |

### Request Body

```json
{
  "text": "This is the text that will be converted to speech.",
  "voice": "en_alloy"
}
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | Text to convert to speech (max 5000 characters) |
| voice | string | No | Voice ID to use for speech synthesis (default: "af_alloy") |

### Available Voices

| Voice ID | Language | Description |
|----------|----------|-------------|
| af_alloy | English (Neutral) | Alloy voice - neutral speaking style |
| en_echo | English (US) | Echo voice - conversational speaking style |
| en_fable | English (British) | Fable voice - clear and articulate speaking style |
| en_onyx | English (US) | Onyx voice - deeper tone speaking style |
| fr_alloy | French | Alloy French voice |
| de_alloy | German | Alloy German voice |
| es_alloy | Spanish | Alloy Spanish voice |
| it_alloy | Italian | Alloy Italian voice |
| ja_alloy | Japanese | Alloy Japanese voice |

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
  https://api.mediamaster.com/v1/audio/text-to-speech \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-api-key' \
  -d '{
    "text": "Welcome to Media Master API. This text will be converted into speech that sounds natural and engaging.",
    "voice": "en_echo"
  }'
```

#### Response

```json
{
  "job_id": "j-123e4567-e89b-12d3-a456-426614174000"
}
```

## Get Job Status

Check the status of a text-to-speech conversion job.

### Endpoint

```
GET /v1/audio/text-to-speech/{job_id}
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
    "audio_url": "https://cdn.mediamaster.com/output/j-123e4567.mp3",
    "duration": 12.5,
    "format": "mp3",
    "voice": "en_echo"
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
  https://api.mediamaster.com/v1/audio/text-to-speech/j-123e4567-e89b-12d3-a456-426614174000 \
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

- Maximum text length: 5000 characters
- Output audio format: MP3
- Audio quality: 128 kbps
- Sample rate: 24 kHz
- Supported language/voice combinations are listed in the Available Voices section
- Processing time depends on text length (typically 1-3 seconds per 100 characters) 