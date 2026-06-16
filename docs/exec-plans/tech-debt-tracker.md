<!-- last_verified: 2026-06-11 -->
# Tech Debt Tracker

Known tech debt items. Agents update this when they discover or create tech debt.

| Description | Impact | Proposed Resolution | Priority | Status |
|---|---|---|---|---|
| Annotated render writes every frame as a JPEG to disk before encoding | Disk + time overhead on long clips | Pipe frames to ffmpeg via stdin (rawvideo) instead of intermediate JPEGs | Medium | Open |
| Search is a linear scan of every manifest | Fine for a demo; O(videos×moments) per query | Add a per-prefix index object or a vector index if the corpus grows | Low | Open |
| No automated test exercises the full CV pipeline end-to-end | Pipeline regressions only caught manually | Add a fixture with a tiny synthetic video + a stubbed `repo/detection` to drive `analyze.run_pipeline` (without mocking the real model in production paths) | Medium | Open |
| `humanizeBytes` / `formatDate` duplicated patterns in TS | DRY | Already centralized in `lib/utils.ts`; keep new code importing from there | Low | Resolved |
