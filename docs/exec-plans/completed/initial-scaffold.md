# Plan — `supervision-sports-highlights`

A new B2 sample scaffolded from `vibe-coding-starter-kit`. Source of truth:
`.claude/scratch/vcsk-2d661321-5543-47eb-a108-92eeefc494d4/` (fresh clone).
Built to match the established sibling video-pipeline house style (closest
sibling: `personal-video-ai-search`).

---

## 1. Purpose

`supervision-sports-highlights` turns a raw sports video into a searchable
library of highlights. Upload a clip to Backblaze B2; the backend runs a
**Roboflow** computer-vision pipeline — **Roboflow Inference** for object
detection + **Roboflow Supervision** for multi-object tracking and annotation —
to find the action, cuts **highlight clips** at each key
moment, renders a **Supervision-annotated** version of the video, and uses
**Claude** to write a short natural-language summary and searchable description
for every moment. Every artifact — source footage, clips, annotated video,
per-moment analysis JSON, summaries, and the search index — is stored on and
streamed back from **B2 over the S3 API**. It's for developers exploring
computer vision, sports analytics, and video-AI workflows who want a concrete,
end-to-end example of B2 as the storage layer for a media-processing pipeline.

**Reality note (honest scoping):** this is a real CV pipeline. Roboflow
Inference runs the model locally on CPU/GPU, so a full demo run is **minutes,
not seconds**, and the Python install is heavy (the `inference` runtime pulls
opencv/onnxruntime). Demo videos should be **short (≤ ~2 min)**. These
constraints are documented in the README, not hidden.

---

## 2. Architecture delta from `vibe-coding-starter-kit`

The starter is a pnpm monorepo: Next.js 16 web + FastAPI (layered
`types → config → repo → service → runtime`) backend, B2 as the sole data store
(no DB). The CV/AI work is all Python, so it lives in the existing backend — no
new service type needed.

### KEEP (as-is — starter contract)
- **UI kit / design system**: `apps/web/src/components/ui/*`, design tokens in
  `globals.css`, `/design` page. (Never edit generated `ui/` files.)
- **Bucket explorer — `/files`** (full-bucket browse): `apps/web/src/app/files/`,
  `apps/web/src/components/files/`, `lib/file-tree.ts`. **Non-negotiable keep.**
- **Upload — `/upload`**: `apps/web/src/app/upload/`, `components/upload/`.
  Reused to upload the source sports video to B2 (accept constrained to video).
- **Sidebar nav** (`layout/app-sidebar.tsx`), header, theme, command palette,
  health banner, error/empty-state patterns.
- **Backend layered architecture + structural tests** (`tests/test_structure.py`:
  no backward imports, boto3 only in `repo/`, ≤300 lines/file, all layers exist).
  boto3 stays confined to `repo/`; **Supervision/Ultralytics/ffmpeg/Anthropic are
  likewise wrapped in `repo/` adapters** (the "all external APIs wrapped in repo/"
  invariant).
- **Cross-cutting backend**: `health.py`, `metrics.py`, structured JSON logging,
  request tracing, `/health` (B2 connectivity), `/metrics`.
- **Single-`.env` config, TanStack Query data layer** (`lib/queries.ts`,
  `lib/api-client.ts`), `pnpm dev` + `scripts/doctor.mjs` preflight, Railway config.

### TRIM (remove — this app doesn't need it)
- **Image/PDF metadata extraction**: drop `Pillow` + `PyPDF2`; reduce
  `service/metadata.py` to size/content-type (no EXIF/image-dimension/PDF
  parsing); delete `docs/features/metadata-extraction.md`; remove/adjust the
  EXIF/PDF-specific assertions in the upload tests. Keep `/upload` working — it
  just stores the video and registers it for analysis. *(A sports-video app has
  no use for image EXIF/PDF parsing; this is "strip what it doesn't need.")*
- **Default dashboard widgets** (generic upload stats/chart/recent-uploads) —
  replaced, not kept (see ADD → Dashboard). Upload-activity chart may be reused.

### ADD (new for this sample)
**Frontend routes**
- **`/highlights` — Highlights Library (the required sample-specific asset
  explorer, scoped to the sample's own `…/videos/` prefix).** Lists analyzed
  videos with thumbnail, live pipeline status, moment count, footage duration.
  This is distinct from `/files` (full bucket): it shows only this app's assets.
- **`/highlights/[id]` — Analysis detail**: Supervision-**annotated video player**
  (streamed from B2 via presigned GET + HTTP range), a **moment timeline** of
  cards — each with its **highlight clip** (streamed from B2), the **Claude
  summary + tags**, and detection/track stats — plus a **search box** that
  filters moments by description/tags.
- Sidebar gets a **Highlights** entry (Dashboard · Upload · **Highlights** ·
  Files · Settings · + Design utility link).

**Frontend — adapted**
- **Dashboard (`/`)**: replace generic stats with pipeline metrics — *Videos
  analyzed*, *Highlights generated*, *Moments detected*, *Footage processed
  (min)*, and a recent-analyses table showing live status for in-flight jobs.
  New aggregations flow through `runtime → service → repo` and TanStack Query
  hooks (no bare `useEffect + fetch`).

**Backend — new files (mirroring sibling house style)**
- `types/`: `video.py` (`VideoStatus` enum `uploaded → probing → detecting →
  clipping → annotating → summarizing → ready | failed`; `Video`/job model),
  `moment.py` (`Moment`: id, start_s, end_s, score, track/detection stats,
  thumb_key, clip_key, summary, description, tags), `stats.py` (dashboard stats).
- `config/settings.py` (extend): add `b2_region`, `b2_application_key_id`
  (rename from `b2_key_id`), `anthropic_api_key`, `video_prefix`, and knobs
  (`detection_model`, `analyze_stride`, `max_moments`, `summary_model`).
- `repo/`: `video_store.py` (B2 key builders + manifest read/write + scoped
  list; boto3 lives here / in `b2_client.py`), `media.py` (ffmpeg/ffprobe
  **subprocess** wrappers: probe, cut clip, encode annotated mp4),
  `detection.py` (**Roboflow Inference** `get_model` load + per-frame
  `model.infer()` — the only place the detection model runs),
  `annotate.py` (**Supervision** `ByteTrack` +
  `BoxAnnotator`/`LabelAnnotator`/`TraceAnnotator`), `llm.py` (**Anthropic**
  client for moment summaries).
- `service/`: `analyze.py` (the `run_pipeline(video_id)` orchestrator —
  probe → detect+track → moment-detection → cut clips → annotate → summarize →
  write manifest, updating status to B2 at each stage; graceful-degrades if the
  LLM key is absent), `videos.py` (register upload, load/list, **delete video +
  its derived assets scoped to that video's prefix**), `search.py` (scan
  manifests, return matching moments), `stats.py` (dashboard aggregation).
- `runtime/`: `videos.py` (POST register/complete upload → kick off
  `analyze.run_pipeline` via FastAPI **BackgroundTasks**; GET list; GET
  one/status; GET playback presigned URL; POST reanalyze; DELETE), `search.py`
  (GET `/search?q=`).

**Heavy dependencies** (`services/api/requirements.txt`): `inference` (Roboflow
Inference runtime — pulls opencv/onnxruntime/numpy), `supervision` (Roboflow),
`anthropic`. **No PyTorch/Ultralytics** — the Roboflow runtime is the model
engine. **ffmpeg/ffprobe** are system binaries (documented install, not pip).
Flag in README: heavy install, first-run model weight auto-download, CPU-bound
runtime.

**Tooling**: extend `scripts/doctor.mjs` — rename B2 vars
(`B2_KEY_ID`→`B2_APPLICATION_KEY_ID`, add `B2_REGION`), add an **ffmpeg-on-PATH**
check, and a **warn** (not fail) if `ANTHROPIC_API_KEY` is missing/placeholder
(pipeline degrades gracefully). Keep `main.py` `REQUIRED_B2_SETTINGS` /
`PLACEHOLDER_VALUES` in sync.

### Processing model & CV approach (house style + honest constraints)
- **Async jobs**: FastAPI `BackgroundTasks`; status persisted as JSON in B2
  (`manifest.json`); frontend polls with TanStack `refetchInterval` (~4 s) while
  any job is processing, stops at `ready`/`failed`. No database, no job queue.
- **Detection source — Roboflow Inference, local, no key required**:
  `from inference import get_model; model = get_model(model_id="rfdetr-base")`
  runs a COCO-pretrained model **locally** (default `rfdetr-base`, configurable
  via `DETECTION_MODEL`; a smaller/faster id is fine for CPU). COCO includes
  `person` + `sports ball`, so it works on any ball sport with **zero
  training**. **Pre-trained models need no key**; `ROBOFLOW_API_KEY` is
  **optional** and unlocks sport-specific **Roboflow Universe** models + hosted
  serverless inference (a documented upgrade path).
- **Supervision is the showcase**: detections arrive via
  `sv.Detections.from_inference(results)`, then `sv.ByteTrack` for persistent
  IDs and the annotators (`Box`/`Label`/`Trace`) that draw the annotated video.
- **Tractability**: analyze on a configurable frame **stride** (default every
  3rd frame); ByteTrack carries IDs; the annotated video is rendered with
  carry-forward of the latest detections so output looks full-FPS. Raw clips cut
  with `ffmpeg -c copy` (fast, no re-encode); only the annotated video is
  re-encoded.
- **Moment detection (generic, sport-agnostic heuristic)**: per analyzed frame,
  an intensity score from tracked-person count + sports-ball presence/speed +
  motion; a *moment* = a contiguous run above a rolling threshold; merge
  near-adjacent runs; rank and cap to top-N (`MAX_MOMENTS`, default ~8–10). Each
  moment → {start/end, peak score, track stats, representative thumbnail}.

---

## 3. B2 surface (S3 operations)

All via the S3-compatible API (boto3). **No b2-native API.** Single S3 client
factory carries the custom user agent (`b2ai-supervision-sports-highlights`).

| Op | S3 call | Used for |
|----|---------|----------|
| PUT | `put_object` | source video, highlight clips, annotated video, per-moment JSON, summaries, manifest/search index, thumbnails |
| GET | `get_object` / `generate_presigned_url` | **stream** annotated video & clips to the `<video>` tag (presigned GET, HTTP **range** requests served directly by B2); read manifest/index |
| LIST | `list_objects_v2` | render the scoped Highlights Library + full-bucket `/files` explorer |
| HEAD | `head_object` | object metadata |
| DELETE | `delete_object` | scoped cleanup of a video + its derived assets (never wipes other prefixes) |

**Bucket prefix layout** (scoped under `settings.video_prefix`, default
`supervision-sports-highlights/`):
```
supervision-sports-highlights/videos/{video_id}/
  source.{ext}              # uploaded source footage
  manifest.json             # pipeline status + moment index (= search index)
  annotated.mp4             # Supervision-annotated full video
  clips/moment-{n}.mp4      # highlight clips
  moments/moment-{n}.json   # per-moment detection/track analysis
  summaries/moment-{n}.txt  # Claude summary
  thumbs/moment-{n}.jpg      # representative keyframe
```
**Highlight: B2 serves media directly** — the browser streams/seeks the
annotated video and clips straight from presigned B2 GET URLs (range-friendly),
no proxying through the API.

---

## 4. Key features (→ README list + `docs/features/*.md`)

1. **Sports video upload** → stored on B2 (reuses the starter uploader). →
   `docs/features/file-upload.md` (kept, lightly retargeted to video).
2. **Supervision CV analysis & moment detection** — YOLO detection + ByteTrack
   tracking → key-moment timeline. → `docs/features/video-analysis.md` (new).
3. **Highlight clips & annotated video** — ffmpeg cuts per moment + a
   Supervision-annotated render, both stored on B2. →
   `docs/features/highlights-and-annotation.md` (new).
4. **AI moment summaries & search** — Claude writes a summary + searchable
   description/tags per moment; a search index over all moments. →
   `docs/features/ai-summaries-and-search.md` (new).
5. **Highlights Library** — scoped asset explorer streaming every generated
   asset from B2. → `docs/features/highlights-library.md` (new).
6. **File Browser (full bucket)** — unchanged starter explorer. →
   `docs/features/file-browser.md` (kept).

### External API providers (per `api-provider-selection.md`)
| Capability | Provider / model | Key (env var) | Core? | Est. cost / full demo run |
|---|---|---|---|---|
| Detection + tracking + annotation | **Roboflow Inference** (`inference`, local) + **Roboflow Supervision** | none for pre-trained models | core | **$0** (local, CPU/GPU) |
| Moment summaries + searchable descriptions | **Anthropic Claude Haiku 4.5** (`claude-haiku-4-5`) | `ANTHROPIC_API_KEY` | core | **~$0.03–0.05** (text-only, ~10 moments × short prompt+output) |
| *(optional)* sport-specific detection | Roboflow **Universe** model / hosted serverless | `ROBOFLOW_API_KEY` (free tier) | optional | ~$0 on free tier |

- Only **one required external key** beyond B2: `ANTHROPIC_API_KEY`. The
  Roboflow CV core runs locally with **no key** for pre-trained models;
  `ROBOFLOW_API_KEY` is optional (Universe / hosted). Both core capabilities are
  really wired (no simulation). Total well **under $1/run** → recorded, no
  approval gate needed.
- Summaries are **text-only from detection/track metadata** by default (keeps
  cost trivial and avoids requiring vision). Attaching a keyframe for richer
  multimodal descriptions is noted as an optional enhancement, off by default.
- **Graceful degradation**: if `ANTHROPIC_API_KEY` is absent, the pipeline still
  detects, clips, and annotates; moments get a templated fallback description and
  the UI shows a "configure `ANTHROPIC_API_KEY` for AI summaries" note.

---

## 5. Doc transforms

| Doc | Action |
|-----|--------|
| `README.md` | **Rewrite** — purpose, features, tech stack (Supervision/YOLO/ffmpeg/Claude), setup (ffmpeg install + `ANTHROPIC_API_KEY` + first-run weights + heavy install note + short-video guidance), demo flow, B2's role. |
| `ARCHITECTURE.md` | **Rewrite** — pipeline stages, async-job/manifest model, B2 prefix layout, new data flows, presigned-streaming. |
| `AGENTS.md` | **Update** — §1 repo map (new routes/modules), §2 building-on note. Keep invariants. |
| `docs/features/dashboard.md` | **Rewrite** — new sports metrics. |
| `docs/features/file-upload.md`, `file-browser.md` | **Keep** (light retarget of upload to video). |
| `docs/features/metadata-extraction.md` | **Delete** (trimmed feature). |
| `docs/features/video-analysis.md`, `highlights-and-annotation.md`, `ai-summaries-and-search.md`, `highlights-library.md` | **New** (use `docs/features/_template.md`). |
| `docs/app-workflows.md` | **Rewrite** — the upload→analyze→browse/search journey. |
| `docs/dev-workflows.md`, `docs/SECURITY.md`, `docs/RELIABILITY.md`, `docs/design-system.md` | **Keep** (light touch: ffmpeg dep, large media, presigned-URL expiry already covered). |
| `docs/exec-plans/completed/*` (starter's history) | **Delete** (not this app's history). This plan lands at `docs/exec-plans/completed/initial-scaffold.md` in Phase 5. |
| `CODE_REVIEW.md`, `CLAUDE.md` (→ `@AGENTS.md` pointer), `LICENSE` | **Keep**. |

---

## 6. Rename table (`vibe-coding-starter-kit` → `supervision-sports-highlights`)

| Scope | From | To |
|-------|------|----|
| Repo / kebab slug | `vibe-coding-starter-kit` | `supervision-sports-highlights` |
| Title Case (README H1, doc titles) | `Vibe Coding Starter Kit` | `Supervision Sports Highlights` |
| Root `package.json` `name` | `vibe-coding-starter-kit` | `supervision-sports-highlights` |
| Web package | `@vibe-coding-starter-kit/web` | `@supervision-sports-highlights/web` |
| Shared package | `@vibe-coding-starter-kit/shared` | `@supervision-sports-highlights/shared` |
| `pnpm --filter` refs in `package.json` scripts + README | `@vibe-coding-starter-kit/web` | `@supervision-sports-highlights/web` |
| S3 client `user_agent_extra` | `b2ai-oss-start` | `b2ai-supervision-sports-highlights` |
| UTM `utm_content=` (all README/doc B2 links) | `b2ai-oss-start` | `b2ai-supervision-sports-highlights` |
| Railway/infra service refs | `vibe-coding-starter-kit` | `supervision-sports-highlights` |
| Env var (rename) | `B2_KEY_ID` | `B2_APPLICATION_KEY_ID` |
| Env var (add) | — | `B2_REGION` (default `us-west-004`) |
| Settings field | `b2_key_id` | `b2_application_key_id` (+ add `b2_region`, wire `region_name=` into the boto3 client) |
| Python package | `app/*` modules | **unchanged** (generic names) |

Notes: no `.github/workflows` exist in the starter → no CI workflow slugs to
rename. `pyproject.toml` has no `name` field → nothing to rename there.

---

## 7. B2 standards compliance (audited by `/b2-doctor`)
1. **S3 API default** — ✓ boto3 S3 client only; no b2-native API anywhere.
2. **Custom user agent on every S3 client** — ✓ single `get_s3_client()` factory
   sets `user_agent_extra="b2ai-supervision-sports-highlights"`.
3. **Standardized `B2_*` env vars** — ✓ `B2_APPLICATION_KEY_ID`,
   `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, `B2_REGION`, `B2_ENDPOINT` (fixes the
   starter kit's `B2_KEY_ID`/no-`B2_REGION` deviation).

---

## 8. Decisions worth confirming before build
1. **Detection = Roboflow Inference running locally** (free, no key for
   pre-trained COCO models; `ROBOFLOW_API_KEY` optional for Universe
   sport-specific models). CPU-bound runtime, heavy install. *(Updated per your
   steer — Roboflow Inference + Supervision are now the core CV engine; dropped
   Ultralytics/PyTorch.)*
2. **Trim image/PDF metadata extraction** (drop Pillow/PyPDF2, delete its feature
   doc + tests). Plan says **trim**.
3. **Claude Haiku 4.5** for summaries, text-only from detection metadata
   (~$0.05/run). Plan defaults to **Haiku, text-only**.
