<!-- last_verified: 2026-06-11 -->
# Feature: Dashboard

## Purpose
Give an at-a-glance overview of the sports-highlights pipeline — how many
videos were analyzed, how much action was found, and what's processing now.

## Used By
- UI: `/` page (dashboard home)
- API: `GET /videos/stats`, `GET /files/stats/activity`

## Core Functions
- `apps/web/src/components/dashboard/pipeline-stats-cards.tsx` — 4 pipeline metric cards
- `apps/web/src/components/dashboard/recent-analyses-table.tsx` — recent analyses with live status
- `apps/web/src/components/dashboard/upload-chart.tsx` — upload-activity bar chart (reused starter component)
- `apps/web/src/lib/queries.ts` — `usePipelineStats()`, `useUploadActivity()`
- `services/api/app/runtime/videos.py` — `GET /videos/stats` handler
- `services/api/app/service/stats.py` — `get_pipeline_stats()` aggregation
- `services/api/app/repo/video_store.py` — manifest scan (`list_video_ids` / `read_manifest`)

## Canonical Files
- Dashboard aggregation: `services/api/app/service/stats.py`
- Pipeline stats hook: `apps/web/src/lib/queries.ts` (`usePipelineStats`)

## Inputs
- None (dashboard loads data automatically)

## Outputs
- `GET /videos/stats` → `PipelineStats` (videos_analyzed, highlights_generated,
  moments_detected, footage_minutes, recent[])
- `GET /files/stats/activity?days=7` → `DailyUploadCount[]` for the chart

## Flow
- Page loads → `usePipelineStats()` scans every manifest under this app's prefix
- Stat cards show videos analyzed, highlights generated, moments detected, and
  footage minutes
- The recent-analyses table lists the latest videos with a live status badge;
  while any job is active the query polls every ~4s and stops at ready/failed
- The upload-activity chart shows server-aggregated daily counts (last 7 days)

## Edge Cases
- API unavailable → cards/table show an inline error with retry
- No videos yet → empty states on cards and table
- Many videos → manifest list paginates via `ContinuationToken`

## UX States
- Loading: skeleton placeholders
- Empty: "No analyses yet"
- Loaded: populated cards, chart, and table (with live status)

## Verification
- Test files: `services/api/tests/test_videos.py` (stats aggregation exercised
  via the service/store), `services/api/tests/test_upload_activity.py`
- Required cases: stats with videos, empty bucket, API error fallback
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
