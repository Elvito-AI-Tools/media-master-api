# Media Routes Documentation

This section documents all media-related endpoints provided by the Media Master API.

## Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| [/v1/media/transcription](./transcription.md) | POST | Create a media transcription job |
| [/v1/media/transcription/{job_id}](./transcription.md#get-job-status) | GET | Get the status of a transcription job |

## Common Use Cases

### Media Transcription

The transcription endpoint allows you to convert audio and video content into text. This is useful for:

- Creating subtitles for videos
- Generating searchable text from audio content
- Creating accessible content for users with hearing impairments
- Extracting information from recorded meetings or interviews

## Supported Media Types

The Media Master API supports transcription for various media types, including:

- Audio files (MP3, WAV, M4A, AAC, FLAC)
- Video files (MP4, MOV, AVI, MKV, WebM)

## Error Handling

All media endpoints follow standard HTTP status codes:
- 200: Successful operation
- 400: Bad request (invalid parameters)
- 401: Unauthorized (invalid API key)
- 404: Resource not found
- 500: Internal server error

Detailed error messages are provided in the response body. 