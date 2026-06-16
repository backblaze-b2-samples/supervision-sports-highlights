<!-- last_verified: 2026-06-11 -->
# Feature: Highlights Library

## Purpose
A scoped asset explorer for this app's analyzed videos — distinct from the
full-bucket `/files` browser — streaming every generated asset from B2.

## Used By
- UI: `/highlights` (library grid), `/highlights/[id]` (detail)
- API: `GET /videos`, `GET /videos/{id}`, `GET /videos/{id}/moments`, `GET /videos/{id}/playback`, `POST /videos/{id}/reanalyze`, `DELETE /videos/{id}`

## Core Functions
- `apps/web/src/components/highlights/highlights-library.tsx` — card grid
- `apps/web/src/components/highlights/analysis-detail.tsx` — detail orchestrator
- `apps/web/src/components/highlights/{annotated-player,moment-card,status-badge}.tsx`
- `apps/web/src/lib/queries.ts` — `useVideos`, `useVideo`, `useVideoMoments`, `useVideoPlayback`, `useDeleteVideo`, `useReanalyzeVideo`
- `services/api/app/service/videos.py` — `list_videos`, `get_video`, `moments_with_media`, `delete_video` (scoped)
- `services/api/app/repo/video_store.py` — `list_video_ids` (scoped), `delete_video_prefix` (scoped)

## Canonical Files
- Library list: `apps/web/src/components/highlights/highlights-library.tsx`
- Scoped listing/delete: `services/api/app/repo/video_store.py`

## Inputs
- None for the list; `id` for the detail view

## Outputs
- `VideoSummary[]` (id, filename, status, moment_count, duration, thumb_url)
- Detail: `Video` + `MomentPlayback[]` (presigned clip/thumb URLs) + annotated playback URL

## Flow
- `/highlights` lists every manifest under `…/videos/` (scoped — never the whole bucket); cards show a live status badge and poll while any job is active
- Clicking a card opens the detail view (see Highlights & Annotation, AI Summaries & Search)
- Delete is scoped to a single video's prefix via `delete_video_prefix` — it lists then `delete_objects` only under `…/videos/{id}/`, so it can never wipe other videos or other apps' data
- Re-analyze resets the manifest to `uploaded` and re-schedules the pipeline

## Edge Cases
- Empty library → empty state prompting an upload
- Corrupt/missing manifest → skipped in the list
- Invalid id → 400; unknown id → 404
- Thumbnails/clips stream via presigned B2 GET (range-friendly), expiring ~1h

## UX States
- Loading: skeleton cards
- Empty: "No analyzed videos yet"
- Error: inline error with retry
- Loaded: card grid with thumbnails + status

## Verification
- Test files: `services/api/tests/test_videos.py`
- Required cases: scoped delete passes only the target id, delete missing → 404, invalid id rejected
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [File Browser](file-browser.md)
- [App Workflows](../app-workflows.md)
