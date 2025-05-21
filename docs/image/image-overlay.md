# Image Overlay API

This endpoint allows you to overlay one or more images on top of a base image with precise control over positioning, size, rotation, opacity, and z-index.

## Overview

The image overlay API provides a powerful way to composite multiple images together. Common use cases include:

- Adding logos or watermarks to images
- Creating composite marketing materials
- Generating dynamic image templates
- Adding decorative elements to images
- Creating collages from multiple images

## Endpoint Details

### Create Image Overlay Job

**URL**: `/v1/image/add-overlay-image`  
**Method**: `POST`  
**Authentication**: API Key (header: `X-API-Key`)

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `base_image_url` | string | Yes | URL of the base image on which overlays will be placed |
| `overlay_images` | array | Yes | List of overlay image objects with positioning information |
| `output_format` | string | No | Output image format (default: "png", options: "png", "jpg", "webp") |
| `output_quality` | integer | No | Quality for lossy formats like JPEG (1-100, default: 90) |
| `output_width` | integer | No | Width of the output image in pixels (if not specified, uses the base image width) |
| `output_height` | integer | No | Height of the output image in pixels (if not specified, uses the base image height) |
| `maintain_aspect_ratio` | boolean | No | Whether to maintain the aspect ratio when resizing (default: true) |

Each overlay image object in the `overlay_images` array has the following properties:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | Yes | URL of the overlay image to be placed on the base image |
| `x` | float | Yes | Horizontal position (0.0 to 1.0) where 0.0 is the left edge and 1.0 is the right edge |
| `y` | float | Yes | Vertical position (0.0 to 1.0) where 0.0 is the top edge and 1.0 is the bottom edge |
| `width` | float | No | Width of the overlay relative to the base image width (0.0 to 1.0) |
| `height` | float | No | Height of the overlay relative to the base image height (0.0 to 1.0) |
| `rotation` | float | No | Rotation angle in degrees (0 to 359.99, default: 0) |
| `opacity` | float | No | Opacity of the overlay (0.0 to 1.0, default: 1.0) |
| `z_index` | integer | No | Z-index for layering multiple overlays (higher values appear on top, default: 0) |

#### Response

```json
{
  "job_id": "unique-job-identifier"
}
```

### Check Image Overlay Job Status

**URL**: `/v1/image/add-overlay-image/{job_id}`  
**Method**: `GET`  
**Authentication**: API Key (header: `X-API-Key`)

#### Response

```json
{
  "job_id": "unique-job-identifier",
  "status": "pending|processing|completed|failed",
  "result": {
    "image_url": "https://your-bucket.s3.region.amazonaws.com/image-overlay-results/result.png",
    "width": 1200,
    "height": 800,
    "format": "png",
    "storage_path": "image-overlay-results/unique-id.png"
  },
  "error": "Error message if the job failed"
}
```

## Example Usage

### Basic Overlay Example

Adding a logo to the bottom right corner of an image:

```json
{
  "base_image_url": "https://example.com/background.jpg",
  "overlay_images": [
    {
      "url": "https://example.com/logo.png",
      "x": 0.9,
      "y": 0.9,
      "width": 0.2,
      "opacity": 0.8
    }
  ],
  "output_format": "png"
}
```

### Multiple Overlays Example

Adding multiple images with different positioning, rotation, and z-index:

```json
{
  "base_image_url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png",
  "overlay_images": [
    {
      "url": "https://python.org/static/community_logos/python-logo.png",
      "x": 0.5,
      "y": 0.8,
      "width": 0.3,
      "opacity": 0.9,
      "z_index": 1
    },
    {
      "url": "https://upload.wikimedia.org/wikipedia/commons/6/6a/JavaScript-logo.png",
      "x": 0.8,
      "y": 0.2,
      "width": 0.2,
      "rotation": 15,
      "opacity": 0.8,
      "z_index": 2
    }
  ],
  "output_format": "png",
  "output_quality": 95,
  "output_width": 1200,
  "maintain_aspect_ratio": true
}
```

## Implementation Details

The image overlay API leverages the following components:

1. **Image Download**: Securely downloads images from the provided URLs.
2. **Overlay Processing**: 
   - Applies precise positioning based on normalized coordinates (0.0 to 1.0)
   - Maintains aspect ratios when resizing overlay images
   - Handles rotation with transparent backgrounds to prevent clipping
   - Applies opacity/transparency as specified
   - Sorts overlays by z-index to control stacking order
3. **Output Formatting**:
   - Supports multiple output formats (PNG, JPEG, WebP)
   - Quality control for lossy formats
   - Customizable output dimensions with aspect ratio preservation
4. **Storage**: Uploads the resulting image to secure cloud storage

## Error Handling

The API follows standard HTTP status codes:

- 200: Successful operation
- 400: Bad request (invalid parameters)
- 401: Unauthorized (invalid API key)
- 404: Resource not found
- 500: Internal server error

Detailed error messages are provided in the response body.

## Performance Considerations

- **Image Size**: Very large images may require more processing time
- **Number of Overlays**: Each overlay adds processing overhead
- **Output Format**: PNG processing may take longer than JPEG due to compression
- **Rotation**: Rotating overlays requires additional processing

## Best Practices

1. **Efficient Image Sizes**: Use appropriately sized images for both base and overlays
2. **Use PNG for Transparency**: When overlays require transparency, use PNG format
3. **Z-Index Management**: Plan z-index values carefully for complex compositions
4. **URL Accessibility**: Ensure all image URLs are publicly accessible
5. **Error Handling**: Always check job status and handle potential errors 