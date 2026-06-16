<!-- last_verified: 2026-06-11 -->
# Feature: Video Analysis

## Purpose
Detect and track the action in a sports clip and reduce it to a ranked timeline
of key moments.

## Used By
- UI: `/highlights/[id]` (status + moment timeline)
- API: `POST /videos` (kicks off), `GET /videos/{id}` (status + moments)
- Job: `service/analyze.run_pipeline` (FastAPI BackgroundTask)

## Core Functions
- `services/api/app/service/analyze.py` — pipeline orchestrator
- `services/api/app/repo/video_pipeline.py` — OpenCV frame loop: decode → detect+track → annotate
- `services/api/app/repo/detection.py` — **Roboflow Inference** `get_model` + `infer()` (the only place the model runs)
- `services/api/app/repo/annotate.py` — **Supervision** `ByteTrack` + annotators
- `services/api/app/service/moments.py` — sport-agnostic moment-detection heuristic

## Canonical Files
- Orchestrator: `services/api/app/service/analyze.py`
- Detection adapter: `services/api/app/repo/detection.py`
- Moment heuristic: `services/api/app/service/moments.py`

## Inputs
- video_id: str (a registered video's id)
- knobs: `DETECTION_MODEL` (default `rfdetr-base`), `ANALYZE_STRIDE` (default 3), `MAX_MOMENTS` (default 8)
- class mapping: `DETECTION_PERSON_CLASSES` (default `person`), `DETECTION_BALL_CLASSES` (default `sports ball`) — comma-separated, case-insensitive class names that map a model's labels onto the heuristic's person/ball roles

## Outputs
- Per-frame stats (person count, ball presence, motion, track ids)
- `Moment[]` written to the manifest (start/end, score, track/detection stats, peak thumbnail timestamp)
- Status transitions persisted to `manifest.json` at each stage

## Flow
- Probe the source (ffprobe) for duration/fps/dimensions
- Decode frames (OpenCV); every `ANALYZE_STRIDE`th frame, run Roboflow detection and update ByteTrack
- Reduce each analyzed frame to plain stats (no CV types leak to the service)
- Compute an intensity score per frame (people + ball + motion); a moment is a contiguous run above a rolling threshold; merge near-adjacent runs; rank and cap to top-N

## Edge Cases
- No action found → zero moments, status still reaches `ready`
- Pre-trained model needs no key; `ROBOFLOW_API_KEY` optional for Universe / hosted
- Universe models emit custom labels (e.g. `player`/`basketball`); set `DETECTION_PERSON_CLASSES` / `DETECTION_BALL_CLASSES` to map them, or the heuristic silently collapses to motion-only. The keyless COCO default needs no override.
- Any exception → status `failed`, error recorded on the manifest (worker never crashes)
- Heavy/slow on CPU → use short clips (documented in README)

## UX States
- Active: live status badge + "Analyzing…" (page polls ~4s)
- Ready: moment timeline appears
- Failed: error alert with re-analyze action

## Verification
- Test files: `services/api/tests/test_moments.py`, `services/api/tests/test_videos.py`
- Required cases: empty input, single burst detected, top-N cap + ranking, invalid id
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Highlights & Annotation](highlights-and-annotation.md)
- [App Workflows](../app-workflows.md)
