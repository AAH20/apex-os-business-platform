# ComfyUI Integration

## 1. Architecture

```mermaid
%%{init: {'theme':'dark'}}%%
graph TD
    A[APEX-OS API Gateway] --> B[ComfyUI Server]
    B --> C[Workflow Engine]
    C --> D[Image Pipeline]
    C --> E[Video Pipeline]
    D --> F[Stable Diffusion / SDXL]
    D --> G[ControlNet / LoRA]
    E --> H[AnimateDiff / SVD]
    E --> I[Frame Interpolation]
    F --> J[Output Storage]
    G --> J
    H --> J
    I --> J
    J --> K[CDN / S3]
    K --> L[Client Delivery]
```

## 2. Workflow Templates

| Template | Use Case | Nodes |
|----------|----------|-------|
| `img_base` | Standard image gen | LoadCheckpoint → CLIPTextEncode → KSampler → VAEDecode → SaveImage |
| `img_upscale` | 4x upscaling | LoadImage → UpscaleModel → SaveImage |
| `img_inpaint` | Masked editing | LoadImage → VAEEncodeInpaint → KSampler → VAEDecode |
| `img2img` | Style transfer | LoadImage → VAEEncode → KSampler → VAEDecode |
| `vid_text2vid` | Text-to-video | LoadCheckpoint → CLIPTextEncode → KSampler → VAEDecode → SaveAnimation |
| `vid_img2vid` | Image-to-video | LoadImage → VAEEncode → AnimateDiff → KSampler → SaveAnimation |

## 3. Image Generation Pipeline

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart LR
    A[Prompt + Params] --> B[Validate]
    B --> C[Queue Job]
    C --> D[Load Model]
    D --> E[Encode Prompt]
    E --> F[Sample Latents]
    F --> G[VAE Decode]
    G --> H[Post-process]
    H --> I[Upload Storage]
    I --> J[Return URL]
```

**Key parameters:**
- `steps`: 20–50 (default 30)
- `cfg`: 5–9 (default 7)
- `sampler`: `dpmpp_2m`, `euler_a`, `ddim`
- `scheduler`: `karras`, `normal`, `exponential`
- `seed`: integer or `-1` for random

## 4. Video Generation Pipeline

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart LR
    A[Prompt + Motion] --> B[Validate]
    B --> C[Queue Job]
    C --> D[Load AnimateDiff]
    D --> E[Encode Prompt]
    E --> F[Sample Frames]
    F --> G[VAE Decode]
    G --> H[Interpolate]
    H --> I[Encode MP4/WebP]
    I --> J[Upload Storage]
    J --> K[Return URL]
```

**Key parameters:**
- `frame_count`: 16–48 (default 24)
- `fps`: 8–24 (default 12)
- `motion_scale`: 0.5–2.0 (default 1.0)
- `interpolation`: `rife`, `film`, `none`

## 5. API Integration

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/img/generate` | Submit image job |
| `POST` | `/api/v1/img/upscale` | Submit upscale job |
| `POST` | `/api/v1/vid/generate` | Submit video job |
| `GET` | `/api/v1/job/{id}` | Poll job status |
| `GET` | `/api/v1/job/{id}/result` | Fetch result URL |
| `DELETE` | `/api/v1/job/{id}` | Cancel job |

### Request Example

```json
{
  "template": "img_base",
  "prompt": "a futuristic city at sunset, cyberpunk",
  "negative_prompt": "blurry, low quality",
  "width": 1024,
  "height": 1024,
  "steps": 30,
  "cfg": 7.0,
  "sampler": "dpmpp_2m",
  "seed": -1,
  "callback_url": "https://client.example.com/webhook"
}
```

### Response Example

```json
{
  "job_id": "job_abc123",
  "status": "queued",
  "estimated_time": 12,
  "result_url": null
}
```

### WebSocket Events

```mermaid
%%{init: {'theme':'dark'}}%%
sequenceDiagram
    participant C as Client
    participant G as Gateway
    participant W as Worker
    C->>G: WS connect /ws/jobs/{id}
    G->>W: Subscribe
    W-->>G: progress 25%
    G-->>C: progress 25%
    W-->>G: progress 75%
    G-->>C: progress 75%
    W-->>G: complete
    G-->>C: result_url
```

### Error Handling

| Code | Meaning | Action |
|------|---------|--------|
| `400` | Invalid params | Fix request |
| `429` | Rate limited | Backoff + retry |
| `503` | GPU unavailable | Queue or retry |
| `500` | Internal error | Alert + retry |

### Authentication

All requests require `Authorization: Bearer <token>` header. Tokens are issued by the APEX-OS auth service and scoped to `comfyui:generate`, `comfyui:read`, or `comfyui:admin`.
