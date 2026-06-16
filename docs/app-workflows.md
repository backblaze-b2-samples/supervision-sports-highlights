<!-- last_verified: 2026-06-11 -->
# App Workflows

User journeys inside the application.

## Upload and analyze a clip

- User navigates to `/upload`.
- Drops or selects a single sports video (mp4/mov/webm; client constrains the
  dropzone to video and ≤ 500MB).
- Progress bar shows the upload to B2.
- On success the clip is registered, the CV pipeline starts on the server, and
  the user is redirected to the analysis detail page.
- See: [Sports Video Upload](features/file-upload.md),
  [Video Analysis](features/video-analysis.md).

## Watch the pipeline run (analysis detail)

- `/highlights/[id]` loads the video's manifest and shows a live status badge
  (Queued → Probing → Detecting → Cutting clips → Annotating → Summarizing →
  Ready).
- While any stage is active the page polls every ~4s and shows an "Analyzing…"
  state; it stops polling at `ready`/`failed`.
- When ready: the **Supervision-annotated video** streams from a presigned B2
  URL, and the **moment timeline** appears — each card has its highlight clip
  (also streamed from B2), the Claude summary + tags, and detection/track stats.
- A **search box** filters the moments client-side by description or tag.
- If `ANTHROPIC_API_KEY` is absent, a note explains summaries are templated and
  invites the user to configure it and re-analyze.
- Actions: **Re-analyze** (re-runs the pipeline) and **Delete** (removes the
  video and all its derived assets, scoped to its prefix).
- See: [Highlights & Annotation](features/highlights-and-annotation.md),
  [AI Summaries & Search](features/ai-summaries-and-search.md).

## Browse the Highlights Library

- `/highlights` lists every analyzed video as a card: thumbnail, live status,
  moment count, and footage duration — scoped to this app's `…/videos/` prefix.
- Clicking a card opens its analysis detail.
- Empty state prompts the user to upload a clip.
- See: [Highlights Library](features/highlights-library.md).

## Search highlights

- The detail page filters one video's moments inline.
- The API also exposes `GET /search?q=` which scans every video's manifest and
  returns matching moments across the whole library (used for cross-video
  search and available to agents).
- See: [AI Summaries & Search](features/ai-summaries-and-search.md).

## Browse the full bucket (Files)

- `/files` is the unchanged starter explorer over the entire bucket — tree
  view with preview, download, and delete.
- Useful for inspecting raw pipeline artifacts (manifests, clips, thumbs).
- See: [File Browser](features/file-browser.md).

## View the dashboard

- `/` shows pipeline headline metrics — Videos Analyzed, Highlights Generated,
  Moments Detected, Footage Processed (min) — plus an upload-activity chart and
  a recent-analyses table with live status for in-flight jobs.
- See: [Dashboard](features/dashboard.md).
