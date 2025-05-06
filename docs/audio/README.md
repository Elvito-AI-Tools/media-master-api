# Audio Routes Documentation

This section documents all audio-related endpoints provided by the Media Master API.

## Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| [/v1/audio/text-to-speech](./text-to-speech.md) | POST | Convert text to speech using Kokoro TTS |
| [/v1/audio/text-to-speech/{job_id}](./text-to-speech.md#get-job-status) | GET | Get the status of a text-to-speech job |

## Common Use Cases

### Text-to-Speech Generation

The text-to-speech endpoint lets you convert any text into natural-sounding speech with various voices. This is useful for:

- Adding narration to videos
- Creating audio content for podcasts
- Generating voice-overs for presentations
- Creating accessible content for users with reading difficulties

## Error Handling

All audio endpoints follow standard HTTP status codes:
- 200: Successful operation
- 400: Bad request (invalid parameters)
- 401: Unauthorized (invalid API key)
- 404: Resource not found
- 500: Internal server error

Detailed error messages are provided in the response body. 