<!-- last_verified: 2026-06-11 -->
# Feature: Highlights & Annotation

## Purpose
Produce the playable artifacts of an analysis: a highlight clip per moment and
a Supervision-annotated render of the whole video, all stored on B2.

## Used By
- UI: `/highlights/[id]` (annotated player + per-moment clips)
- API: `GET /videos/{id}/playback`, `GET /videos/{id}/moments`
- Job: `service/analyze.run_pipeline`

## Core Functions
- `services/api/app/repo/media.py` — ffmpeg wrappers: `cut_clip` (`-c copy`), `extract_frame`, `encode_from_frames`
- `services/api/app/repo/video_pipeline.py` — renders an annotated frame for every frame and encodes the annotated mp4
- `services/api/app/repo/annotate.py` — Box/Label/Trace annotators over ByteTrack output
- `services/api/app/repo/video_store.py` — uploads clips/annotated/thumbs, presigned GET URLs
- `apps/web/src/components/highlights/annotated-player.tsx`, `moment-card.tsx`

## Canonical Files
- Media wrappers: `services/api/app/repo/media.py`
- Annotation: `services/api/app/repo/annotate.py`

## Inputs
- Source video (local temp copy downloaded from B2)
- Detected moments (start/end + peak timestamp)

## Outputs
- `…/annotated.mp4` — Supervision-annotated full video (re-encoded, faststart)
- `…/clips/moment-{n}.mp4` — highlight clips (stream copy, fast)
- `…/thumbs/moment-{n}.jpg` — representative keyframe
- Presigned, range-friendly B2 GET URLs for direct browser streaming

## Flow
- During the detect loop, every frame is annotated with the latest tracked detections (carry-forward) so output looks full-FPS
- The annotated frames are encoded to mp4 and uploaded to B2
- For each moment, ffmpeg cuts a clip with `-c copy` and extracts a keyframe thumbnail; both are uploaded
- The browser streams the annotated video and clips straight from presigned B2 URLs (HTTP range served by B2 — no API proxying)

## Edge Cases
- A clip or thumb failing → logged, that moment keeps null keys; the rest proceed
- ffmpeg/ffprobe missing → `MediaError` surfaced; `pnpm doctor` checks PATH up front
- Annotated render only re-encodes once; raw clips never re-encode (keeps cost/time down)

## UX States
- Annotated player: skeleton while presigning, then `<video controls>`
- Moment card: `<video>` with thumbnail poster; "Clip unavailable" if missing

## Verification
- Test files: `services/api/tests/test_videos.py` (moments + playback URL surface)
- Required cases: moments-with-media mapping, playback URL when annotated exists / 404 when not
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Video Analysis](video-analysis.md)
- [Highlights Library](highlights-library.md)
