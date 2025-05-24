# Video Overlay API

This endpoint allows you to overlay one or more videos on top of a base image with precise control over positioning, timing, size, opacity, and audio mixing.

## Overview

The video overlay API provides a revolutionary way to create dynamic video compositions by combining static images with animated video elements. This opens up incredible possibilities for:

- **Dynamic Marketing Content**: Overlay animated logos, product demos, or promotional videos on static backgrounds
- **Interactive Presentations**: Add video explanations or demonstrations over infographic backgrounds  
- **Social Media Content**: Create engaging posts with animated elements over static designs
- **Educational Materials**: Overlay instructional videos on diagrams or charts
- **Digital Signage**: Combine static branding with dynamic video content
- **Creative Compositions**: Mix static and dynamic elements for artistic projects

## Endpoint Details

### Create Video Overlay Job

**URL**: `/v1/image/add-video-overlay`  
**Method**: `POST`  
**Authentication**: API Key (header: `X-API-Key`)

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `base_image_url` | string | Yes | URL of the base image on which video overlays will be placed |
| `overlay_videos` | array | Yes | List of overlay video objects with positioning and timing information |
| `output_duration` | number | No | Duration of the output video in seconds (if not specified, uses the longest overlay video duration) |
| `frame_rate` | integer | No | Frame rate of the output video (default: 30, range: 15-60) |
| `output_width` | integer | No | Width of the output video in pixels (if not specified, uses the base image width) |
| `output_height` | integer | No | Height of the output video in pixels (if not specified, uses the base image height) |
| `maintain_aspect_ratio` | boolean | No | Whether to maintain the aspect ratio when resizing (default: true) |
| `background_audio_url` | string | No | URL of background audio to add to the video (can be a direct audio file or YouTube URL) |
| `background_audio_volume` | number | No | Volume level for the background audio track (0.0 to 1.0, default: 0.2) |

Each overlay video object in the `overlay_videos` array has the following properties:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | Yes | URL of the overlay video to be placed on the base image |
| `x` | float | Yes | Horizontal position (0.0 to 1.0) where 0.0 is the left edge and 1.0 is the right edge |
| `y` | float | Yes | Vertical position (0.0 to 1.0) where 0.0 is the top edge and 1.0 is the bottom edge |
| `width` | float | No | Width of the overlay relative to the base image width (0.0 to 1.0) |
| `height` | float | No | Height of the overlay relative to the base image height (0.0 to 1.0) |
| `start_time` | float | No | Start time in seconds when the overlay video should begin playing (default: 0.0) |
| `end_time` | float | No | End time in seconds when the overlay video should stop playing |
| `loop` | boolean | No | Whether to loop the overlay video if it's shorter than the base video duration (default: false) |
| `opacity` | float | No | Opacity of the overlay video (0.0 to 1.0, default: 1.0) |
| `z_index` | integer | No | Z-index for layering multiple overlays (higher values appear on top, default: 0) |
| `volume` | float | No | Volume level of the overlay video audio (0.0 to 1.0, default: 0.0 - muted) |

#### Response

```json
{
  "job_id": "unique-job-identifier"
}
```

### Check Video Overlay Job Status

**URL**: `/v1/image/add-video-overlay/{job_id}`  
**Method**: `GET`  
**Authentication**: API Key (header: `X-API-Key`)

#### Response

```json
{
  "job_id": "unique-job-identifier",
  "status": "pending|processing|completed|failed",
  "result": {
    "video_url": "https://your-bucket.s3.region.amazonaws.com/video-overlay-results/result.mp4",
    "width": 1920,
    "height": 1080,
    "duration": 15.5,
    "frame_rate": 30,
    "has_audio": true,
    "storage_path": "video-overlay-results/unique-id.mp4"
  },
  "error": "Error message if the job failed"
}
```

## Example Usage

### Basic Video Overlay Example

Adding a small animated logo to the bottom right corner of an image:

```json
{
  "base_image_url": "https://example.com/background.jpg",
  "overlay_videos": [
    {
      "url": "https://example.com/animated-logo.mp4",
      "x": 0.85,
      "y": 0.85,
      "width": 0.2,
      "opacity": 0.9,
      "volume": 0.0
    }
  ],
  "output_duration": 10.0,
  "frame_rate": 30
}
```

### Advanced Multi-Video Overlay Example

Creating a dynamic composition with multiple timed video overlays and background audio:

```json
{
  "base_image_url": "https://example.com/presentation-slide.jpg",
  "overlay_videos": [
    {
      "url": "https://example.com/intro-animation.mp4",
      "x": 0.5,
      "y": 0.3,
      "width": 0.6,
      "start_time": 0.0,
      "end_time": 3.0,
      "opacity": 1.0,
      "z_index": 1,
      "volume": 0.3
    },
    {
      "url": "https://example.com/product-demo.mp4",
      "x": 0.7,
      "y": 0.6,
      "width": 0.4,
      "start_time": 2.5,
      "end_time": 12.0,
      "opacity": 0.95,
      "z_index": 2,
      "volume": 0.5
    },
    {
      "url": "https://example.com/call-to-action.mp4",
      "x": 0.5,
      "y": 0.8,
      "width": 0.8,
      "start_time": 10.0,
      "loop": true,
      "opacity": 0.9,
      "z_index": 3,
      "volume": 0.2
    }
  ],
  "output_duration": 15.0,
  "frame_rate": 30,
  "output_width": 1920,
  "output_height": 1080,
  "background_audio_url": "https://example.com/background-music.mp3",
  "background_audio_volume": 0.15
}
```

### Creative Use Cases

#### Picture-in-Picture Effect
```json
{
  "base_image_url": "https://example.com/main-content.jpg",
  "overlay_videos": [
    {
      "url": "https://example.com/speaker-video.mp4",
      "x": 0.8,
      "y": 0.2,
      "width": 0.3,
      "height": 0.3,
      "opacity": 1.0,
      "volume": 0.8
    }
  ]
}
```

#### Animated Watermark
```json
{
  "base_image_url": "https://example.com/content.jpg",
  "overlay_videos": [
    {
      "url": "https://example.com/animated-watermark.mp4",
      "x": 0.95,
      "y": 0.05,
      "width": 0.15,
      "opacity": 0.7,
      "loop": true,
      "volume": 0.0
    }
  ]
}
```

## Implementation Details

The video overlay API leverages advanced FFmpeg processing to create seamless compositions:

1. **Image Processing**: Downloads and processes the base image, determining optimal dimensions
2. **Video Download & Analysis**: Downloads overlay videos and extracts metadata (duration, dimensions, etc.)
3. **Timing Calculation**: Automatically calculates output duration based on overlay timings
4. **Filter Complex Generation**: Builds sophisticated FFmpeg filter chains for:
   - Video scaling and positioning
   - Opacity and transparency effects
   - Timing and synchronization
   - Audio mixing and volume control
5. **Composition**: Combines all elements using hardware-accelerated video processing
6. **Audio Processing**: Mixes overlay video audio with optional background music
7. **Output Optimization**: Generates web-optimized MP4 files with proper encoding

## Performance Considerations

- **Video Size**: Larger overlay videos require more processing time and memory
- **Number of Overlays**: Each overlay adds computational overhead
- **Duration**: Longer output videos take more time to process
- **Frame Rate**: Higher frame rates increase processing requirements
- **Audio Mixing**: Multiple audio sources add processing complexity

## Best Practices

1. **Optimize Video Sizes**: Use appropriately sized overlay videos for your target output
2. **Plan Z-Index Values**: Organize overlay layers logically for complex compositions
3. **Audio Management**: Keep overlay video audio volumes low to avoid conflicts
4. **Timing Coordination**: Plan start/end times to create smooth transitions
5. **URL Accessibility**: Ensure all video and audio URLs are publicly accessible
6. **Test Compositions**: Start with simple overlays before creating complex multi-layer compositions
7. **Duration Planning**: Consider the natural duration of overlay videos when setting output duration

## Error Handling

The API follows standard HTTP status codes:

- 200: Successful operation
- 400: Bad request (invalid parameters)
- 401: Unauthorized (invalid API key)
- 404: Resource not found
- 500: Internal server error

Common error scenarios:
- Invalid video URLs or inaccessible content
- Unsupported video formats
- Timing conflicts (end_time before start_time)
- Invalid positioning values (outside 0.0-1.0 range)
- Insufficient system resources for complex compositions

## Technical Specifications

- **Supported Video Formats**: MP4, WebM, MOV, AVI, MKV
- **Supported Audio Formats**: MP3, WAV, AAC, M4A, OGG
- **Output Format**: MP4 with H.264 video and AAC audio
- **Maximum Duration**: 300 seconds (5 minutes)
- **Frame Rate Range**: 15-60 fps
- **Position Precision**: Floating-point coordinates with sub-pixel accuracy 