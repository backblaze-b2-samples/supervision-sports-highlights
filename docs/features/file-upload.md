<!-- last_verified: 2026-06-11 -->
# Feature: Sports Video Upload

## Purpose
Upload a sports clip from the browser to Backblaze B2 and register it for the
CV pipeline.

## Used By
- UI: `/upload` page, upload form component
- API: `POST /videos`
- Job: kicks off `analyze.run_pipeline` via FastAPI `BackgroundTasks`

## Core Functions
- `apps/web/src/components/upload/upload-form.tsx` — orchestrates the dropzone + progress, calls `uploadVideo()`, redirects to the detail page
- `apps/web/src/components/upload/dropzone.tsx` — drag-and-drop via `react-dropzone`, configurable `accept`/`maxSize`/`multiple`
- `apps/web/src/lib/api-client.ts` — `uploadVideo()` (XHR for progress)
- `services/api/app/runtime/videos.py` — `POST /videos` handler, reads chunks, schedules the pipeline
- `services/api/app/service/videos.py` — `register_upload()` validates and writes source + initial manifest
- `services/api/app/repo/video_store.py` — `put_bytes()` / `write_manifest()` via boto3

## Canonical Files
- Upload handler pattern: `services/api/app/runtime/videos.py`
- Service orchestration pattern: `services/api/app/service/videos.py`
- Frontend upload flow: `apps/web/src/components/upload/upload-form.tsx`

## Inputs
- file: `File` (mp4 / mov / webm, multipart form data)
- content_type: string (validated against the video allowlist)

## Outputs
- `Video` (status `uploaded`, with `id` and `source_key`)
- Side effects: source stored at `…/videos/{id}/source.{ext}`, initial
  `manifest.json` written, pipeline scheduled as a background task

## Flow
- User drops or selects one video; the dropzone constrains to video types and ≤ 500MB
- XHR sends a multipart `POST /videos` with progress events
- API rejects oversized requests while streaming the body
- `register_upload()` validates the type, stores the source bytes on B2, writes the initial manifest, and returns the `Video`
- The handler schedules `run_pipeline(video.id)` as a background task
- Client toasts success and redirects to `/highlights/{id}`

## Edge Cases
- Unsupported type → API returns 415 (and the dropzone rejects client-side)
- File exceeds the limit → API returns 413
- Empty file → API returns 400
- B2 unreachable → API returns 500
- Upload aborted → XHR abort, error state in UI

## UX States
- Empty: dropzone with video-only instructions
- Loading: progress bar with spinner
- Error: red status icon + message
- Complete: green checkmark, redirect to analysis detail

## Verification
- Test files: `services/api/tests/test_videos.py`, `services/api/tests/test_error_handling.py`
- Required cases: register success, non-video rejection, empty file rejection, invalid id rejection
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Video Analysis](video-analysis.md)
- [App Workflows](../app-workflows.md)
