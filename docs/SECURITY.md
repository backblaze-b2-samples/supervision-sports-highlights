<!-- last_verified: 2026-04-22 -->
# Security

Security principles and implementation for supervision-sports-highlights.

## Trust Boundaries

- **Frontend -> API**: CORS-restricted to configured origins, scoped to `GET/POST/DELETE/OPTIONS`
- **API -> B2**: Authenticated via `B2_APPLICATION_KEY_ID` + `B2_APPLICATION_KEY`, region-aware, signature v4
- **Client -> B2**: Presigned GET URLs. Highlight media (annotated video, clips,
  thumbnails) is streamed *inline* (range-friendly, ~1h expiry) so the browser
  `<video>` tag can seek directly from B2; the `/files` download path uses a
  shorter expiry with `Content-Disposition: attachment`.

## Upload Validation

- Video upload (`/videos`): content-type allowlist (mp4/mov/webm), chunked
  streaming with size enforcement (500MB default), empty-file rejection
- `/files` upload retains the broader starter allowlist + filename sanitization
  (path traversal, null bytes, unsafe chars stripped) and MIME/extension checks
- Video ids are validated as 32-char hex; scoped deletes only ever touch a
  single video's `…/videos/{id}/` prefix (never other videos or apps)

## File Key Validation

- Empty keys rejected
- Path traversal patterns rejected (`../`, `%2e%2e`, backslashes, null bytes)
- The bucket is the only access boundary — add prefix scoping in
  `services/api/app/service/files.py::validate_key` if your deployment
  shares a bucket with other workloads

## Download Safety

- Presigned URLs force `Content-Disposition: attachment`
- Prevents inline rendering of user-uploaded content (XSS mitigation)

## Secrets Management

- All secrets loaded via environment variables (pydantic-settings)
- Never committed to source control
- `.env.example` documents required variables without values

## Agent Security Rules

- Never commit `.env`, credentials, or API keys
- Never weaken validation without explicit instruction
- Never bypass CORS, auth, or input sanitization
- Always validate at system boundaries
