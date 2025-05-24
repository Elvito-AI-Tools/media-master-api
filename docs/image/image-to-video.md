# Image to Video Conversion

The image-to-video endpoint allows you to convert a static image into a dynamic video with various animation effects, optional audio and captions.

## Create Image to Video Job

Convert an image to a video with customizable animation effects and optional audio and captions.

### Endpoint

```
POST /v1/image/to-video
```

### Headers

| Name | Required | Description |
|------|----------|-------------|
| X-API-Key | Yes | Your API key for authentication |
| Content-Type | Yes | application/json |

### Request Body

```json
{
  "image_url": "https://example.com/image.jpg",
  "video_length": 10.0,
  "frame_rate": 30,
  "zoom_speed": 10.0,
  "effect_type": "zoom",
  "narrator_speech_text": "This is optional text that will be converted to speech",
  "voice": "af_alloy",
  "narrator_audio_url": "https://example.com/audio.mp3",
  "narrator_vol": 100,
  "should_add_captions": true,
  "caption_properties": {
    "max_words_per_line": 10,
    "font_size": 24,
    "font_family": "Arial",
    "line_color": "#FFFFFF",
    "position": "bottom_center"
  },
  "match_length": "audio"
}
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| image_url | string | Yes | URL of the image to convert to video |
| video_length | number | No | Length of output video in seconds (0-30, default: 10.0) |
| frame_rate | number | No | Frame rate of the output video (1-60, default: 30) |
| zoom_speed | number | No | Speed of zoom effect when effect_type is 'zoom' (0-100, default: 10.0) |
| effect_type | string | No | Type of animation effect ('none', 'zoom', 'pan', 'ken_burns', default: 'none') |
| pan_direction | string | No | Direction for pan effect when effect_type is 'pan' |
| ken_burns_keypoints | array | No | Keypoints for Ken Burns effect when effect_type is 'ken_burns' |
| narrator_speech_text | string | No | Text to convert to speech (if provided, narrator_audio_url is ignored) |
| voice | string | No | Voice ID to use for speech synthesis (default: "af_alloy") |
| narrator_audio_url | string | No | URL of narrator audio file (ignored if narrator_speech_text is provided) |
| narrator_vol | number | No | Volume level for the narrator audio track (0-100, default: 100) |
| background_music_url | string | No | URL of background music to add (can be a direct audio file URL or YouTube URL) |
| background_music_vol | number | No | Volume level for the background music track (0-100, default: 20) |
| should_add_captions | boolean | No | Whether to automatically add captions (default: false) |
| caption_properties | object | No | Styling properties for captions |
| match_length | string | No | Whether to match output length to 'audio' or 'video' (default: audio) |

### Animation Effects

The API supports four different animation effects:

#### 1. None Effect (`effect_type: "none"`)
Creates a static video with no motion effects. The image remains stationary throughout the video duration.

#### 2. Zoom Effect (`effect_type: "zoom"`)
Applies a smooth zoom-in or zoom-out effect to the image. The `zoom_speed` parameter controls the intensity of the zoom.

#### 3. Pan Effect (`effect_type: "pan"`)
Creates a panning motion across the image. Requires the `pan_direction` parameter.

**Pan Direction Options:**
- `left_to_right`: Pans from left side to right side
- `right_to_left`: Pans from right side to left side  
- `top_to_bottom`: Pans from top to bottom
- `bottom_to_top`: Pans from bottom to top
- `diagonal_top_left`: Pans diagonally from top-left to bottom-right
- `diagonal_top_right`: Pans diagonally from top-right to bottom-left
- `diagonal_bottom_left`: Pans diagonally from bottom-left to top-right
- `diagonal_bottom_right`: Pans diagonally from bottom-right to top-left

#### 4. Ken Burns Effect (`effect_type: "ken_burns"`)
Creates a sophisticated cinematic effect with multiple keypoints defining position and zoom changes over time. Requires the `ken_burns_keypoints` parameter.

**Ken Burns Keypoints Structure:**
Each keypoint is an object with the following properties:
- `time`: Time in seconds when this keypoint occurs
- `x`: Horizontal position (0.0 to 1.0, where 0.0 is left edge, 1.0 is right edge)
- `y`: Vertical position (0.0 to 1.0, where 0.0 is top edge, 1.0 is bottom edge)
- `zoom`: Scale factor for zoom level (e.g., 1.0 = original size, 1.5 = 150% zoom)

**Requirements:**
- At least 2 keypoints must be provided
- Keypoints should be ordered by time
- Time values should be within the video duration

### Caption Properties

| Property | Type | Description |
|----------|------|-------------|
| line_color | string | Color of the text line (e.g., 'white', '#FFFFFF') |
| word_color | string | Color of individual words when highlighted |
| outline_color | string | Color of text outline/stroke |
| all_caps | boolean | Whether to convert all text to uppercase |
| max_words_per_line | number | Max words per caption line (1-20, default: 10) |
| x | number | X coordinate for manual positioning |
| y | number | Y coordinate for manual positioning |
| position | string | Predefined position ('bottom_center', 'top_left', etc.) |
| alignment | string | Text alignment ('left', 'center', 'right') |
| font_family | string | Font family for captions |
| font_size | number | Font size in pixels |
| bold | boolean | Apply bold formatting |
| italic | boolean | Apply italic formatting |
| underline | boolean | Apply underline formatting |
| strikeout | boolean | Apply strikeout formatting |
| style | string | Caption style ('highlight', 'word_by_word') |
| outline_width | number | Width of text outline in pixels |
| spacing | number | Line spacing in pixels |
| angle | number | Text rotation angle in degrees |
| shadow_offset | number | Shadow offset distance in pixels |
| background_color | string | Background color for captions |
| background_opacity | number | Background opacity (0.0-1.0) |
| background_padding | number | Background padding in pixels |
| background_radius | number | Background corner radius in pixels |

### Audio Mixing Features

The API supports sophisticated audio mixing capabilities:

1. **Narrator Audio**: Can be provided directly via URL or generated from text using text-to-speech
2. **Background Music**: Can be added from a direct URL or YouTube link
3. **Volume Control**: Independent volume levels for narrator and background music
4. **Format Compatibility**: Automatic handling of different audio formats and sample rates
5. **Fallback Mechanisms**: Multiple mixing methods are attempted if the primary method fails

When both narrator audio and background music are provided, they will be mixed with the specified volume levels. If mixing fails for any reason, the system will fall back to using only the narrator audio.

### Response

```json
{
  "job_id": "j-123e4567-e89b-12d3-a456-426614174000"
}
```

## Examples

### Example 1: Static Video (No Effect)

```bash
curl -X POST \
  https://api.mediamaster.com/v1/image/to-video \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-api-key' \
  -d '{
    "image_url": "https://example.com/portrait.jpg",
    "video_length": 8,
    "frame_rate": 30,
    "effect_type": "none",
    "narrator_speech_text": "This is a static presentation of our product",
    "voice": "af_alloy",
    "should_add_captions": true
  }'
```

### Example 2: Zoom Effect

```bash
curl -X POST \
  https://api.mediamaster.com/v1/image/to-video \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-api-key' \
  -d '{
    "image_url": "https://example.com/landscape.jpg",
    "video_length": 12,
    "frame_rate": 30,
    "effect_type": "zoom",
    "zoom_speed": 15,
    "narrator_speech_text": "Watch as we zoom into this beautiful landscape",
    "voice": "af_bella",
    "background_music_url": "https://example.com/ambient.mp3",
    "background_music_vol": 25,
    "should_add_captions": true,
    "caption_properties": {
      "position": "bottom_center",
      "font_size": 28,
      "line_color": "#FFFFFF",
      "outline_color": "#000000",
      "outline_width": 2
    }
  }'
```

### Example 3: Pan Effect

```bash
curl -X POST \
  https://api.mediamaster.com/v1/image/to-video \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-api-key' \
  -d '{
    "image_url": "https://example.com/cityscape.jpg",
    "video_length": 10,
    "frame_rate": 30,
    "effect_type": "pan",
    "pan_direction": "left_to_right",
    "narrator_speech_text": "Explore the city skyline from left to right",
    "voice": "am_michael",
    "should_add_captions": true,
    "caption_properties": {
      "style": "word_by_word",
      "max_words_per_line": 8,
      "font_family": "Arial",
      "bold": true
    }
  }'
```

### Example 4: Diagonal Pan Effect

```bash
curl -X POST \
  https://api.mediamaster.com/v1/image/to-video \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-api-key' \
  -d '{
    "image_url": "https://example.com/nature.jpg",
    "video_length": 14,
    "frame_rate": 30,
    "effect_type": "pan",
    "pan_direction": "diagonal_top_left",
    "narrator_speech_text": "Journey through nature with a dynamic diagonal movement",
    "voice": "af_nova",
    "background_music_url": "https://www.youtube.com/watch?v=example",
    "background_music_vol": 20,
    "narrator_vol": 85
  }'
```

### Example 5: Ken Burns Effect

```bash
curl -X POST \
  https://api.mediamaster.com/v1/image/to-video \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-api-key' \
  -d '{
    "image_url": "https://example.com/artwork.jpg",
    "video_length": 20,
    "frame_rate": 30,
    "effect_type": "ken_burns",
    "ken_burns_keypoints": [
      {
        "time": 0,
        "x": 0.2,
        "y": 0.3,
        "zoom": 1.2
      },
      {
        "time": 8,
        "x": 0.7,
        "y": 0.4,
        "zoom": 1.8
      },
      {
        "time": 15,
        "x": 0.5,
        "y": 0.6,
        "zoom": 1.0
      },
      {
        "time": 20,
        "x": 0.3,
        "y": 0.2,
        "zoom": 2.0
      }
    ],
    "narrator_speech_text": "Experience this masterpiece through a cinematic Ken Burns effect that reveals different details over time",
    "voice": "af_sarah",
    "should_add_captions": true,
    "caption_properties": {
      "position": "bottom_center",
      "background_color": "#000000",
      "background_opacity": 0.7,
      "background_padding": 10,
      "background_radius": 5,
      "line_color": "#FFFFFF",
      "font_size": 24
    },
    "match_length": "audio"
  }'
```

### Example 6: Complex Ken Burns with Multiple Transitions

```bash
curl -X POST \
  https://api.mediamaster.com/v1/image/to-video \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-api-key' \
  -d '{
    "image_url": "https://example.com/detailed-map.jpg",
    "video_length": 25,
    "frame_rate": 60,
    "effect_type": "ken_burns",
    "ken_burns_keypoints": [
      {
        "time": 0,
        "x": 0.1,
        "y": 0.1,
        "zoom": 1.0
      },
      {
        "time": 5,
        "x": 0.3,
        "y": 0.2,
        "zoom": 1.5
      },
      {
        "time": 10,
        "x": 0.7,
        "y": 0.3,
        "zoom": 2.2
      },
      {
        "time": 15,
        "x": 0.8,
        "y": 0.7,
        "zoom": 1.8
      },
      {
        "time": 20,
        "x": 0.4,
        "y": 0.8,
        "zoom": 2.5
      },
      {
        "time": 25,
        "x": 0.5,
        "y": 0.5,
        "zoom": 1.0
      }
    ],
    "narrator_audio_url": "https://example.com/detailed-narration.mp3",
    "background_music_url": "https://example.com/documentary-music.mp3",
    "background_music_vol": 15,
    "narrator_vol": 95,
    "should_add_captions": true,
    "caption_properties": {
      "style": "highlight",
      "max_words_per_line": 12,
      "line_color": "#FFFF00",
      "word_color": "#FF6600",
      "outline_color": "#000000",
      "outline_width": 3,
      "font_size": 26,
      "bold": true,
      "position": "bottom_center"
    }
  }'
```

## Get Job Status

Check the status of an image-to-video conversion job.

### Endpoint

```
GET /v1/image/to-video/{job_id}
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
    "final_video_url": "https://cdn.mediamaster.com/videos/j-123e4567.mp4",
    "video_duration": 15.5,
    "has_audio": true,
    "has_captions": true,
    "audio_url": "https://cdn.mediamaster.com/audio/j-123e4567.mp3",
    "srt_url": "https://cdn.mediamaster.com/srt/j-123e4567.srt"
  },
  "error": null
}
```

#### Status Values

| Status | Description |
|--------|-------------|
| pending | Job is in the queue waiting to be processed |
| processing | Job is currently being processed |
| completed | Job has completed successfully |
| failed | Job has failed with an error |

### Example

```bash
curl -X GET \
  https://api.mediamaster.com/v1/image/to-video/j-123e4567-e89b-12d3-a456-426614174000 \
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
