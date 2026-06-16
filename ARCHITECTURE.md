<!-- last_verified: 2026-06-11 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Dashboard with pipeline metrics + live analysis status
  - Sports-video upload with drag-and-drop, progress tracking
  - **Highlights Library** (`/highlights`) — scoped asset explorer
  - **Analysis detail** (`/highlights/[id]`) — annotated player, moment
    timeline, per-moment search
  - File browser (`/files`) — full-bucket explorer (unchanged starter feature)
- **services/api/** — FastAPI backend (layered architecture)
  - REST API for upload, analysis status, playback, moments, search
  - The CV pipeline: Roboflow Inference + Supervision + ffmpeg + Claude
  - B2 S3 integration via boto3; presigned URLs for direct media streaming
  - Health check, structured JSON logging, Prometheus-format metrics
- **packages/shared/** — TypeScript type definitions mirroring the Pydantic
  models (Video, Moment, PipelineStats, etc.)

## The pipeline

A single async job per video, run via FastAPI `BackgroundTasks`. There is **no
database and no job queue** — status lives in the video's `manifest.json` on
B2, which the frontend polls (TanStack `refetchInterval`, ~4s) while any job is
active and stops once everything is `ready`/`failed`.

```
uploaded → probing → detecting → clipping → annotating → summarizing → ready
                                                                       ↘ failed
```

1. **probe** (`repo/media.py`, ffprobe) — duration, fps, dimensions, codec.
2. **detect + track + annotate** (`repo/video_pipeline.py`) — decode frames
   with OpenCV, run **Roboflow Inference** every Nth frame
   (`ANALYZE_STRIDE`), feed detections through **Supervision ByteTrack** for
   persistent IDs, and render an annotated frame for *every* frame (carrying
   forward the latest tracked detections so output looks full-FPS). The
   annotated mp4 is encoded and uploaded to B2.
3. **moment detection** (`service/moments.py`) — a sport-agnostic intensity
   heuristic over per-frame stats (tracked-person count + sports-ball presence
   + motion). A *moment* is a contiguous run above a rolling threshold;
   near-adjacent runs merge, then rank and cap to top-N (`MAX_MOMENTS`).
4. **cut clips + thumbnails** (`repo/media.py`, ffmpeg) — raw clips use
   `-c copy` (fast, no re-encode); a keyframe at peak intensity is the thumb.
5. **summarize** (`repo/llm.py`, Claude) — text-only prompt from detection/track
   metadata → summary + description + tags. Degrades to a templated description
   when `ANTHROPIC_API_KEY` is absent.

Each stage writes the manifest back to B2 so progress is observable live.

## Backend Layering

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access + ALL external SDKs (boto3, inference, supervision,
  |        anthropic, opencv, ffmpeg subprocess) — no business logic
service/   Business logic — orchestration, heuristics, prompts
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules (enforced by `tests/test_structure.py`)

1. Dependencies flow downward only.
2. No backward imports.
3. `boto3` only in `repo/`.
4. **All external APIs wrapped in `repo/` adapters** — the service layer never
   imports `inference`, `supervision`, `anthropic`, or `cv2` directly; it talks
   to `repo/detection.py`, `repo/annotate.py`, `repo/llm.py`, `repo/media.py`,
   and `repo/video_pipeline.py`.
5. All boundary data uses Pydantic models.
6. Each file stays under 300 lines.

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 video.py, moment.py, stats.py, files.py, upload.py
    config/                settings.py (B2 + pipeline knobs)
    repo/                  b2_client.py, video_store.py, media.py,
                           detection.py, annotate.py, video_pipeline.py, llm.py
    service/               analyze.py (orchestrator), moments.py, summarize.py,
                           videos.py, search.py, stats.py, files.py, upload.py
    runtime/               videos.py, search.py, files.py, upload.py,
                           health.py, metrics.py
  tests/                   pytest tests (structural + unit + integration)
```

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API), the **sole** data
  store. No application database.
- Per-app prefix layout (scoped under `settings.video_prefix`, default
  `supervision-sports-highlights/`):

```
supervision-sports-highlights/videos/{video_id}/
  source.{ext}              # uploaded source footage
  manifest.json             # pipeline status + moment index (= search index)
  annotated.mp4             # Supervision-annotated full video
  clips/moment-{n}.mp4      # highlight clips
  moments/moment-{n}.json   # per-moment detection/track analysis
  summaries/moment-{n}.txt  # Claude (or templated) summary
  thumbs/moment-{n}.jpg      # representative keyframe
```

## External Services

- **Backblaze B2 S3 API** — storage, retrieval, presigned URLs, scoped delete.
- **Roboflow Inference** — local model runtime (no key for pre-trained COCO
  models; optional `ROBOFLOW_API_KEY` for Universe / hosted inference).
- **Anthropic Claude** — moment summaries (optional; graceful degradation).
- **ffmpeg/ffprobe** — local subprocesses (system binaries).

## B2 Operations

| Op | S3 call | Used for |
|----|---------|----------|
| PUT | `put_object` | source, clips, annotated video, per-moment JSON, summaries, manifest, thumbnails |
| GET | `get_object` / `generate_presigned_url` | **stream** annotated video & clips (presigned GET, HTTP range served by B2); read manifests |
| LIST | `list_objects_v2` | scoped Highlights Library + full-bucket `/files` |
| HEAD | `head_object` | object metadata (`/files`) |
| DELETE | `delete_objects` | scoped cleanup of a video + its derived assets |

**No b2-native API.** Deletes are always scoped to a single video's prefix —
they never touch other videos or other apps' data.

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md).

- **Frontend → API** — CORS-restricted to configured origins.
- **API → B2** — authenticated via application keys, signature v4, region-aware.
- **Client → B2** — presigned GET URLs for direct media streaming (range-
  friendly; ~1h expiry).

## Observability

- Structured JSON logging on all requests with `request_id`.
- Pipeline stages logged with `video=<id> status=<stage>`.
- `/metrics` (Prometheus format), `/health` (B2 connectivity).

## Canonical Files

- Pipeline orchestrator: `services/api/app/service/analyze.py`
- Moment heuristic: `services/api/app/service/moments.py`
- B2 data access (repo): `services/api/app/repo/video_store.py`, `b2_client.py`
- CV adapters: `services/api/app/repo/detection.py`, `annotate.py`,
  `video_pipeline.py`
- Pydantic models: `services/api/app/types/video.py`, `moment.py`, `stats.py`
- Structural tests: `services/api/tests/test_structure.py`
- Frontend API client: `apps/web/src/lib/api-client.ts`
- Data layer hooks: `apps/web/src/lib/queries.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently`.
- **Railway** — two services from the same repo; see `infra/railway/README.md`.
  Note the CV runtime needs a build with ffmpeg available and enough CPU/RAM.

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
