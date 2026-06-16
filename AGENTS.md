<!-- last_verified: 2026-06-11 -->
# AGENTS.md

This is the authoritative control surface for all coding agents. Read this first.

## 1. Repository Map

```
apps/web/          Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  src/app/                /, /upload, /highlights, /highlights/[id], /files,
                          /settings, /design
  src/components/highlights/   Highlights Library, analysis detail, annotated
                          player, moment card, status badge
  src/components/dashboard/    Pipeline stats cards, recent-analyses table,
                          upload-activity chart
services/api/      FastAPI backend (layered: types/config/repo/service/runtime)
  app/repo/               b2_client, video_store (B2); media (ffmpeg),
                          detection (Roboflow Inference), annotate
                          (Supervision), video_pipeline (OpenCV loop),
                          llm (Anthropic) — ALL external SDKs live here
  app/service/            analyze (pipeline orchestrator), moments
                          (heuristic), summarize, videos, search, stats
  app/runtime/            videos, search, files, upload, health, metrics
packages/shared/   Shared TypeScript types (Video, Moment, PipelineStats, …)
docs/              System of record (features, workflows, security, reliability)
docs/exec-plans/   Execution plans and tech debt tracker
infra/railway/     Deployment config
```

The CV pipeline is async (FastAPI `BackgroundTasks`); status is persisted in
each video's `manifest.json` on B2 (the sole data store — no DB, no queue).
See [ARCHITECTURE.md](ARCHITECTURE.md) for the pipeline stages and B2 layout.

## 2. Building on This App

This app was scaffolded from the `vibe-coding-starter-kit`. The starter contract
below still holds — keep these pieces; the rest is this app's CV pipeline.

**Keep as-is (do not strip, rename, or replace)**
- **UI kit / design system.** `apps/web/src/components/ui/` (shadcn primitives), the design tokens in `apps/web/src/app/globals.css`, and the `/design` reference page. Build new screens with these primitives; never edit the generated `components/ui/` files directly. Restyling happens through tokens in `globals.css`.
- **File Explorer.** `/files` route, `apps/web/src/app/files/`, and `apps/web/src/components/files/` — the full-bucket browser. The Files sidebar entry stays.
- **Upload.** `/upload` route, `apps/web/src/app/upload/`, and `apps/web/src/components/upload/` — here it uploads a sports video and kicks off analysis.
- The sidebar nav (Dashboard, Upload, Highlights, Files, Settings, plus the Design System utility link).

**This app's surface**
- **Highlights Library** (`/highlights`) — scoped asset explorer over this app's `…/videos/` prefix (distinct from the full-bucket `/files`).
- **Analysis detail** (`/highlights/[id]`) — annotated player + moment timeline + per-moment search.
- **Dashboard** (`/`) — pipeline metrics (videos analyzed, highlights, moments, footage minutes) + recent-analyses table with live status. New aggregations flow `runtime -> service -> repo` and are exposed via TanStack Query hooks in `apps/web/src/lib/queries.ts` — no bare `useEffect + fetch`.

**Pipeline invariant**
- Every external CV/AI/media dependency is wrapped in a `repo/` adapter
  (`detection`, `annotate`, `video_pipeline`, `llm`, `media`). The service layer
  reasons over plain Pydantic/dataclass models, never imports `inference`,
  `supervision`, `anthropic`, or `cv2` directly. Keep it that way.
- The primary feature (detect → track → clip → annotate → summarize) must stay
  real — no mocked detections, no synthetic clips. Pre-trained models run with
  no key; AI summaries degrade gracefully without `ANTHROPIC_API_KEY`.

## 3. Architectural Invariants

**Backend layering**: `types` -> `config` -> `repo` -> `service` -> `runtime`

- No backward imports across layers
- No `boto3` outside `repo/`
- No business logic in route handlers (`runtime/`)
- All external APIs wrapped in `repo/` adapters
- All request/response data validated at boundary (Pydantic models)
- No shared mutable state across layers

**Frontend**: shadcn/ui components in `src/components/ui/` are generated — never modify them.

**Data fetching**: every API call flows through TanStack Query hooks in `apps/web/src/lib/queries.ts`. No bare `useEffect + fetch` patterns. New endpoints touch three files: `runtime/<router>.py`, `lib/api-client.ts`, `lib/queries.ts`.

## 4. Quality Expectations

- **DRY** — do not duplicate logic, types, or constants. Extract shared code only when used in 2+ places.
- Structured JSON logging only — no `print()` statements
- No raw SDK calls outside `repo/` layer
- Files stay under 300 lines
- Tests added or updated for every behavior change
- Docs updated in same PR as code changes
- Lint clean before merge
- Prefer boring, composable libraries over clever abstractions
- No implicit type assumptions — use typed models

## 5. Mechanical Enforcement

| Rule | Enforced by |
|------|-------------|
| No backward imports | `tests/test_structure.py::test_no_backward_imports` |
| No boto3 outside repo/ | `tests/test_structure.py::test_boto3_only_in_repo` |
| File size < 300 lines | `tests/test_structure.py::test_file_size_limits` |
| All layers exist | `tests/test_structure.py::test_all_layers_exist` |
| No bare print() | `ruff` rule T20 |
| Import ordering | `ruff` rule I001 |
| Frontend strict equality | `eslint` rule eqeqeq |
| No unused vars | `eslint` + `ruff` rules |

## 6. Commands

```bash
# Run
pnpm dev               # start both frontend and backend
pnpm dev:web           # frontend only
pnpm dev:api           # backend only

# Test & Lint
pnpm lint              # frontend lint (eslint)
pnpm build             # frontend type check + build
pnpm lint:api          # backend lint (ruff)
pnpm test:api          # backend tests (pytest)
pnpm check:structure   # structural boundary tests
pnpm test:e2e          # Playwright e2e tests
```

## 7. Agent Workflow

1. Read this file first.
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) before structural changes.
3. For non-trivial changes, create a plan in `docs/exec-plans/active/`.
4. Implement the smallest coherent change.
5. Run: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
6. Update docs in the same PR (see §9).
7. Move completed plans to `docs/exec-plans/completed/`.
8. Only change files relevant to the task. No drive-by improvements.

## 8. Frontend Conventions

See [docs/dev-workflows.md](docs/dev-workflows.md) for full details.

## 9. Doc Update Mapping

| Change Type | Update Location |
|-------------|-----------------|
| Feature logic, inputs, outputs, tests | `docs/features/<feature>.md` |
| User journeys | `docs/app-workflows.md` |
| System layout, deployments | `ARCHITECTURE.md` |
| Dev or testing process | `docs/dev-workflows.md` |
| Setup or scope changes | `README.md` |
| Security changes | `docs/SECURITY.md` |
| Reliability changes | `docs/RELIABILITY.md` |
| Active work plans | `docs/exec-plans/active/` |
| Known tech debt | `docs/exec-plans/tech-debt-tracker.md` |

If documentation and implementation conflict, update docs in the same PR. Documentation rot destroys agent reliability.

## 10. Doc Map

| Topic | Location |
|-------|----------|
| System layout, data flows, boundaries | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Feature docs | [docs/features/](docs/features/) |
| User journeys | [docs/app-workflows.md](docs/app-workflows.md) |
| Engineering workflows and testing | [docs/dev-workflows.md](docs/dev-workflows.md) |
| Security principles | [docs/SECURITY.md](docs/SECURITY.md) |
| Reliability expectations | [docs/RELIABILITY.md](docs/RELIABILITY.md) |
| Execution plans | [docs/exec-plans/](docs/exec-plans/) |
| Tech debt | [docs/exec-plans/tech-debt-tracker.md](docs/exec-plans/tech-debt-tracker.md) |

## 11. When Unsure

- Prefer boring, stable libraries
- Prefer small PRs over large changes
- Add tests with every change
- Never bypass lint rules without explicit instruction
- Ask before making destructive or irreversible changes
