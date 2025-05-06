# Video Routes Documentation

This section documents all video-related endpoints provided by the Media Master API.

## Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| [/v1/video/concatenate](./concatenate.md) | POST | Concatenate multiple videos into a single video |
| [/v1/video/concatenate/{job_id}](./concatenate.md#get-job-status) | GET | Get the status of a video concatenation job |

## Common Use Cases

### Video Concatenation

The video concatenation endpoint allows you to join multiple video files into a single continuous video. This is useful for:

- Combining multiple video clips into a single file
- Creating compilations from shorter video segments
- Merging different parts of a video that were recorded separately
- Creating sequential video content from separate scenes or shots

## Supported Video Formats

The Media Master API supports various video formats for both input and output:

- MP4 (.mp4)
- WebM (.webm)
- AVI (.avi)
- MOV (.mov)
- MKV (.mkv)

## Error Handling

All video endpoints follow standard HTTP status codes:
- 200: Successful operation
- 400: Bad request (invalid parameters)
- 401: Unauthorized (invalid API key)
- 404: Resource not found
- 500: Internal server error

Detailed error messages are provided in the response body. 