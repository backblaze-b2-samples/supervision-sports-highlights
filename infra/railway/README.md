# Railway Deployment

Deploy both services (web + api) on Railway.

## Setup

1. Create a new Railway project
2. Add two services from the same repo:

### Web Service (Next.js)
- **Root Directory**: `apps/web`
- **Build Command**: `pnpm install && pnpm build`
- **Start Command**: `pnpm start`
- **Port**: `3000`

### API Service (FastAPI)
- **Root Directory**: `services/api`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **System dependency**: the CV pipeline shells out to `ffmpeg`/`ffprobe` and
  the `inference` runtime is heavy. Use a build with `ffmpeg` available (e.g. an
  apt/nixpacks step installing `ffmpeg`) and enough CPU/RAM for local inference.

## Environment Variables

Set these on the API service:

| Variable | Value |
|----------|-------|
| `B2_APPLICATION_KEY_ID` | Your B2 key ID |
| `B2_APPLICATION_KEY` | Your B2 key |
| `B2_BUCKET_NAME` | Your bucket name |
| `B2_REGION` | Your B2 region slug (e.g. `us-west-004`; not a full endpoint URL) |
| `ANTHROPIC_API_KEY` | *(recommended)* AI moment summaries; omit to degrade gracefully |
| `ROBOFLOW_API_KEY` | *(optional)* only for Roboflow Universe / hosted inference |
| `API_CORS_ORIGINS` | Your web service URL (e.g., `https://web-production-xxx.up.railway.app`) |

Optional for the API service:

| Variable | Value |
|----------|-------|
| `B2_PUBLIC_URL_BASE` | HTTPS public bucket/CDN base; set only for intentionally public buckets |

Set this on the Web service:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | Your API service URL (e.g., `https://api-production-xxx.up.railway.app`) |
