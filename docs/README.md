# Media Master API Documentation

This directory contains documentation for all routes available in the Media Master API.

## API Overview

The Media Master API is a powerful service for generating and transforming media content without coding. It provides endpoints for:

- **Image Processing**: Convert images to videos with effects
- **Audio Processing**: Text-to-speech generation
- **Video Processing**: Video manipulation and concatenation
- **Media Processing**: Transcription and other media operations

## Documentation Structure

The documentation is organized by resource type:

- [Image Routes](./image/README.md): Documentation for all image-related endpoints
- [Audio Routes](./audio/README.md): Documentation for all audio-related endpoints
- [Video Routes](./video/README.md): Documentation for all video-related endpoints
- [Media Routes](./media/README.md): Documentation for all media-related endpoints

## Authentication

All API endpoints require authentication using an API key. Include your API key in the `X-API-Key` header for all requests.

## Getting Started

1. Obtain an API key
2. Make requests to the desired endpoints with your API key in the headers
3. Check job status using the provided job ID

## Common Response Formats

### Job Creation Response

```json
{
  "job_id": "unique-job-identifier"
}
```

### Job Status Response

```json
{
  "job_id": "unique-job-identifier",
  "status": "processing|completed|failed",
  "result": {
    "output_url": "https://example.com/output.mp4",
    "additional_metadata": {}
  },
  "error": "Error message if job failed"
}
``` 