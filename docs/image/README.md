# Image Routes Documentation

This section documents all image-related endpoints provided by the Media Master API.

## Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| [/v1/image/to-video](./image-to-video.md) | POST | Convert an image to a video with optional audio and captions |
| [/v1/image/to-video/{job_id}](./image-to-video.md#get-job-status) | GET | Get the status of an image-to-video job |

## Common Use Cases

### Converting a Static Image to an Animated Video

You can use the image-to-video endpoint to create engaging content from static images by adding:
- Ken Burns zoom effect
- Background audio (either from a URL or text-to-speech)
- Automatic captions

This is particularly useful for:
- Social media content
- Presentations
- Digital signage
- Educational content

### Advanced Audio Features

The image-to-video endpoint includes sophisticated audio processing capabilities:

- **Dual Audio Sources**: Combine narrator audio with background music
- **Text-to-Speech Integration**: Generate narrator audio directly from text
- **YouTube Support**: Use YouTube links as background music sources
- **Volume Control**: Adjust volume levels independently for narrator and background music
- **Format Compatibility**: Automatic handling of different audio formats and sample rates
- **Fallback Mechanisms**: Multiple mixing methods ensure reliable audio processing

These features allow you to create professional-quality videos with rich audio experiences without needing specialized editing software.

## Error Handling

All image endpoints follow standard HTTP status codes:
- 200: Successful operation
- 400: Bad request (invalid parameters)
- 401: Unauthorized (invalid API key)
- 404: Resource not found
- 500: Internal server error

Detailed error messages are provided in the response body. 