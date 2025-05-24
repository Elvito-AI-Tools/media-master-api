# Image Routes Documentation

This directory contains documentation for all image-related endpoints in the Media Master API.

## Available Endpoints

### Image to Video Conversion
- **Create Job**: `POST /v1/image/image-to-video`
- **Check Status**: `GET /v1/image/image-to-video/{job_id}`

### Image Overlay
- **Create Job**: `POST /v1/image/add-overlay-image`
- **Check Status**: `GET /v1/image/add-overlay-image/{job_id}`

### Video Overlay on Image
- **Create Job**: `POST /v1/image/add-video-overlay`
- **Check Status**: `GET /v1/image/add-video-overlay/{job_id}`

## Common Use Cases

### Image to Video Conversion
Convert static images into dynamic videos with customizable duration, effects, and audio integration. Perfect for creating social media content, presentations, and animated displays.

### Image Overlay
Create composite images by overlaying multiple images with precise positioning, sizing, and visual effects. Ideal for adding logos, watermarks, creating templates, and building complex visual compositions.

### Video Overlay on Image
Transform static images into dynamic video content by overlaying animated videos with precise timing and positioning control. Revolutionary for creating:
- Dynamic marketing materials with animated elements
- Interactive presentations with video demonstrations
- Social media content with motion graphics
- Educational materials with video explanations
- Digital signage with mixed static and dynamic content

## Advanced Audio Features

The image-to-video endpoint supports sophisticated audio integration:
- **Dual Audio Sources**: Combine background music with text-to-speech narration
- **Text-to-Speech Integration**: Convert text descriptions into natural-sounding speech
- **Volume Control**: Fine-tune audio levels for optimal balance
- **Audio Synchronization**: Automatically sync audio with video duration

## Error Handling

All image endpoints follow standard HTTP status codes:

- **200**: Successful operation
- **400**: Bad request (invalid parameters or malformed JSON)
- **401**: Unauthorized (missing or invalid API key)
- **404**: Resource not found (invalid job ID or endpoint)
- **500**: Internal server error (processing failure or system issues)

Detailed error messages are provided in the response body. 