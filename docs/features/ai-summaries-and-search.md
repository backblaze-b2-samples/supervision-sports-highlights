<!-- last_verified: 2026-06-11 -->
# Feature: AI Summaries & Search

## Purpose
Write a short natural-language summary + searchable description and tags for
each moment with Claude, and let users find moments across the library.

## Used By
- UI: `/highlights/[id]` (summaries, tags, inline filter)
- API: `GET /search?q=`
- Job: `service/analyze.run_pipeline` (summarize stage)

## Core Functions
- `services/api/app/repo/llm.py` — Anthropic Claude adapter (`is_available`, `summarize_moment`)
- `services/api/app/service/summarize.py` — text-only prompt builder + templated `fallback`
- `services/api/app/service/search.py` — substring/token match across all manifests
- `services/api/app/runtime/search.py` — `GET /search` handler

## Canonical Files
- LLM adapter: `services/api/app/repo/llm.py`
- Search: `services/api/app/service/search.py`

## Inputs
- Per moment: detection/track metadata (people, tracks, ball, score, duration)
- `q`: search query string

## Outputs
- Per moment: `summary`, `description`, `tags[]` (written to the manifest and to `…/summaries/moment-{n}.txt` + `…/moments/moment-{n}.json`)
- `GET /search` → `SearchHit[]` (video id + filename + matching moment)

## Flow
- For each moment, build a text-only prompt from its stats (no vision required)
- Call Claude (`SUMMARY_MODEL`, default `claude-haiku-4-5`); parse JSON into summary/description/tags
- If `ANTHROPIC_API_KEY` is absent OR the call fails, use a templated fallback that names the action and invites the user to configure the key
- Search scans every video's manifest (the manifest doubles as the index) and ranks moments by phrase/token match then intensity

## Edge Cases
- No key → graceful degradation; `video.ai_summaries=false`; UI shows a note
- LLM error mid-run → that moment falls back; the pipeline still completes
- Malformed model JSON → best-effort parse, then raw-text fallback
- Empty query → empty result list

## UX States
- Moment card shows summary + description + tag badges
- Detail page has a client-side filter box; the `/search` API enables cross-video search

## Verification
- Test files: `services/api/tests/test_summarize.py`, `services/api/tests/test_videos.py`
- Required cases: prompt includes stats, fallback is self-describing + tagged, search matches tags/description, empty query
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Video Analysis](video-analysis.md)
- [App Workflows](../app-workflows.md)
