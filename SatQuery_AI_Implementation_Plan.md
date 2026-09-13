# SatQuery AI (SIH26167) — Implementation & Action Plan

**Source documents:** `Problem_Statement.md`, `SatQuery_AI_Final_Synthesized_Solution.md` (Proposal), `SatQuery_AI_SPDD.md` (SPDD — engineering ground truth).
**Status of this document:** Planning only. No code, scaffolding, or execution is contained here — this is a module/step/sub-step breakdown for a team to execute against.

---

## 0. How to Use This Plan

- The project is split into three **domains**: `Frontend`, `Backend`, `AI/ML`.
- Each domain is split into **independent modules**, numbered `F0, F1, …` (Frontend), `B0, B1, …` (Backend), `M0, M1, …` (AI/ML), designed so different people on different machines can work on them with minimal merge conflicts.
- Every module states its **Dependencies** explicitly, including cross-domain dependencies (e.g., a Frontend module depending on a Backend API contract, or a Backend module depending on an AI/ML model-serving contract). Modules with no dependency on unfinished work can start on day 1 in parallel.
- The very first module in each domain (`F0`, `B0`, `M0`) is full setup-from-scratch (repo/folder structure, environment, base configs) and MUST be completed (or at least have its output artifacts — folder skeletons and config stubs — committed) before any other module in that domain begins.
- **⚠️ FLAGGED AMBIGUITY** call-out boxes mark places where the PS, Proposal, and SPDD conflict, are silent, or leave an implementation choice unresolved. These are not resolved here — they are surfaced for the team to decide and document, per the SPDD's own instruction (§17) that unresolved items must be explicitly resolved or explicitly accepted as risk before submission.
- File paths quoted below follow the repository layout specified in SPDD §18. Where this plan introduces a path not explicit in the SPDD, it is marked `(plan-introduced path)`.

### 0.1 Master Dependency Overview (cross-domain)

```
B0 (repo/env setup) ──────────────┬─────────────────────────────┐
                                   │                              │
M0 (data pipeline setup) ─────────┼──> M1 (model serving infra)  │
                                   │        │                     │
F0 (frontend setup) ───────────────────────┼─────────────────────┤
                                            │                     │
B1 (data contracts/schemas) ───────────────┼──> B2 (API gateway) │
                                            │        │            │
                              M2 (query interpreter model)        │
                                       │                          │
                        B5 (query interpreter integration) <──────┘
                                       │
                        B6 (compatibility validator) <── M9 (modality heuristic)
                                       │
                        B7 (specialist router)
                                       │
        M3/M4/M5 (adapters) ──> B8 (specialist invocation layer)
                                       │
        M7/M8 (fusion) ──> B9 (fusion orchestration)
                                       │
                        B10 (verifier) ──> B11 (confidence) ──> B12 (trace) ──> B13 (response composer)
                                       │
                        B14 (report service)      F2..F8 (frontend pages, consume B1 contract + B2 endpoints)
                                       │
                        B17 (deployment wiring) <── F-all, B-all, M1
```

---

## FRONTEND

### Module F0 — Project Setup & Scaffolding

**Domain:** Frontend
**Purpose:** Establish the frontend repository skeleton, build tooling, and shared conventions before any UI feature work begins.
**Rationale:** SPDD §18 fixes the target directory layout (`frontend/src/pages`, `frontend/src/components`). All later frontend modules assume this skeleton exists, plus a working build/dev-server loop and a typed API client shell.
**Dependencies:** None (can start immediately, in parallel with `B0` and `M0`).

#### Step F0.1 — Initialize the frontend package
1. From the repository root (created in `B0`, or, if working in parallel before `B0` lands, in a temporary local folder to be merged later), run:
   ```
   npm create vite@latest frontend -- --template react-ts
   ```
2. `cd frontend && npm install`.
3. Add required dependencies:
   ```
   npm install axios leaflet react-leaflet
   npm install -D @types/leaflet
   ```
   ⚠️ **FLAGGED AMBIGUITY:** The Proposal (§6, §7) and SPDD (§12.3) both say "Leaflet (or deck.gl)" without a final decision. This plan assumes **Leaflet** for concreteness (lighter weight, simpler React bindings). The team must confirm this choice explicitly before `F7` starts, since deck.gl has a materially different component API.
4. Confirm `npm run dev` serves the default Vite app on `localhost:5173` before proceeding.

#### Step F0.2 — Establish folder structure
Create the following empty directories/files exactly matching SPDD §18:
```
frontend/src/pages/UploadQuery.tsx
frontend/src/pages/Results.tsx
frontend/src/components/EvidenceOverlay.tsx
frontend/src/components/ExecutionTracePanel.tsx
frontend/src/components/ConfidenceBadge.tsx
```
##### Sub-step F0.2.1
Also create (plan-introduced paths, not explicit in SPDD but required by later modules):
```
frontend/src/components/RejectionCard.tsx
frontend/src/api/client.ts
frontend/src/api/types.ts
frontend/src/App.tsx  (routes between UploadQuery and Results)
```
##### Sub-step F0.2.2
Add a router: `npm install react-router-dom`. In `App.tsx`, define two routes: `/` → `UploadQuery`, `/results/:sessionId` → `Results`.

#### Step F0.3 — Environment configuration
1. Create `frontend/.env.development` with:
   ```
   VITE_API_BASE_URL=http://localhost:8000/v1
   ```
2. In `frontend/src/api/client.ts`, create an `axios` instance with `baseURL: import.meta.env.VITE_API_BASE_URL`.
3. Confirm this env var is documented in the root `config/config.yaml` conventions established by `B0` so both frontend and backend agree on the port (default backend port: `8000`, per FastAPI convention; confirm against `B2`'s actual chosen port before merging).

#### Step F0.4 — Linting/formatting baseline
1. `npm install -D eslint prettier eslint-config-prettier`.
2. Add `.eslintrc.cjs` and `.prettierrc` with a standard React/TS ruleset (2-space indent, single quotes, no unused vars as error).
3. Add an `npm run lint` script to `package.json`.

---

### Module F1 — Shared API Types & Client Layer

**Domain:** Frontend
**Purpose:** Define TypeScript types mirroring the backend's data contracts, and a single typed API client module used by every page/component.
**Rationale:** SPDD §8 defines `TaskSpec`, `ImageMetadata`, `EvidenceLedger`, `ExecutionTrace`, `AnalyzeRequest`/`AnalyzeResponse` as the **authoritative contracts**. Duplicating these as hand-typed interfaces in the frontend (rather than inventing ad hoc shapes) is required so the frontend and `B1` never drift.
**Dependencies:** `F0` (folder/build must exist). Logically depends on `B1` (Backend Module — Data Contracts) being finalized; until `B1` is merged, this module proceeds against the schemas as literally written in SPDD §8, and MUST be revisited if `B1`'s implementation changes any field name/type.

#### Step F1.1 — Transcribe data contracts into TypeScript
In `frontend/src/api/types.ts`, define (types transcribed directly from SPDD §8, camelCase preserved exactly):
1. `TaskSpec` — fields: `taskType` (union of the 8 literal strings from SPDD §8.1), `status: 'resolved' | 'ambiguous'`, `targetObject: string | null`, `questionText: string | null`, `requiredImageCount: number`, `requiredModalities: ('optical'|'multispectral'|'sar')[]`, `requiresTemporalPairing: boolean`, `requestedParameters: { iouThreshold?: number; topK?: number }`, `intentConfidence: number`, `clarifyingQuestion: string | null`.
2. `ImageMetadata` — fields per SPDD §8.2 exactly (`imageId`, `format`, `crs`, `bandCount`, `detectedModality`, `gsdMeters`, `footprintPolygon`, `acquisitionTimestamp`, `nodataPercent`, `cloudMaskPercent`).
3. `EvidenceItem` and `EvidenceLedger` per SPDD §8.3.
4. `ExecutionTrace` and its nested `TraceStep` per SPDD §8.4.
5. `AnalyzeResponse` per SPDD §8.5, including nested `evidence`, `confidence`, `executionTrace`, `reportUrl`, `rejected`, `rejectionReason`.

##### Sub-step F1.1.1
Export all as named interfaces from a single `types.ts` file (not scattered per-component) so a single source-of-truth diff is easy to review against SPDD updates.

#### Step F1.2 — Build the API client functions
In `frontend/src/api/client.ts`, implement one function per SPDD §9 endpoint:
1. `analyzeQuery(images: File[], query: string, sessionOptions?: {returnReport: boolean}): Promise<AnalyzeResponse>` — POST `/v1/analyze` as `multipart/form-data`; `images[]` field per image, `query` field, `sessionOptions` JSON-stringified into its own form field per SPDD §9.1.
2. `getSession(sessionId: string): Promise<AnalyzeResponse>` — GET `/v1/session/{sessionId}`.
3. `getReportUrl(sessionId: string, format: 'pdf'|'json'): string` — returns the constructed URL for `GET /v1/session/{sessionId}/report?format=...` (used as an `<a href>` target, not fetched via JS, so the browser handles the file stream).
4. `getHealth(): Promise<{status: string}>` — GET `/v1/health`.
5. `getRegistry(): Promise<RegistryResponse>` — GET `/v1/registry` (define `RegistryResponse` type reflecting adapter IDs/versions/precondition blocks per SPDD §4.2/§9.5 — exact shape TBD by `B15`; stub with `{ specialists: { name: string; preconditions: Record<string, unknown> }[] }` until `B15` publishes the real shape).

##### Sub-step F1.2.1
Add a 30-second `axios` timeout on `analyzeQuery` matching the P95+P99 latency budget ceiling in SPDD §13.1 (worst case: fusion + compound ≈ 8s + change-VQA 6s + 0.5s = ~14.5s P95; set client timeout to 30s to comfortably clear P99).

#### Step F1.3 — Error handling contract
1. Define a discriminated union `ApiResult<T> = { ok: true; data: T } | { ok: false; kind: 'network'|'server_error'|'validation_400'; message: string }`.
2. Wrap every client function's `try/catch` to normalize axios errors into `ApiResult`, distinguishing HTTP `400` (malformed request per SPDD §9.1) from `503` (model_serving unreachable, SPDD §14.2) from network failures — each renders a different UI state in later modules.

---

### Module F2 — Upload & Query Page

**Domain:** Frontend
**Purpose:** Build the page where the user uploads 1–2 images and types a natural-language query.
**Rationale:** SPDD §12.1 item 1. This is the system's entry point and must mirror (not replace) server-side validation client-side.
**Dependencies:** `F0`, `F1`.

#### Step F2.1 — Build the drag-and-drop uploader
1. In `UploadQuery.tsx`, implement a drop-zone component accepting 1–2 files.
2. Client-side validation before enabling submission:
   - File extension MUST be one of `.tif`, `.tiff`, `.png`, `.jpg`, `.jpeg` (mirrors SPDD §4.2 format constraints; the server remains the authority — this is a UX pre-check only, per SPDD §12.1).
   - File count MUST be 1 or 2 — show inline error text if 3+ files are dropped, rather than silently truncating.
3. Store selected files in local component state (`useState<File[]>`).

#### Step F2.2 — Build the query text box
1. A `<textarea>` bound to `query: string` state, placeholder text drawn from the PS's own representative queries (e.g., *"Describe the land-cover and major objects visible in this image."*) rotated as placeholder examples.
2. Disable the "Analyze" submit button while `query.trim() === '' || files.length === 0`.

#### Step F2.3 — Capability hint panel
1. On page mount, call `getRegistry()` (from `F1`).
2. Render a collapsible panel listing supported task types and, for each, the precondition summary (image count, modality) returned by `/v1/registry` — this lets the user self-check before submitting, per SPDD §12.1.
3. If `getRegistry()` fails (network/server error), hide the panel silently rather than blocking the page — it is a hint, not a hard gate.

#### Step F2.4 — Submit handler
1. On submit, call `analyzeQuery(files, query)`.
2. Show a loading spinner with the elapsed time counter (useful given SPDD §13.1's multi-second latency budgets — a static spinner with no time context degrades perceived responsiveness).
3. On success (`ok: true`): `navigate('/results/' + data.sessionId)`, passing the full `AnalyzeResponse` via router state (or re-fetch via `getSession` on the Results page — pick one; this plan recommends passing via router state to avoid a redundant round-trip, and falling back to `getSession(sessionId)` only if the Results page is opened directly via URL, e.g., from a bookmark).
4. On failure: render an inline error banner on the same page (do not navigate away) with the `message` field from `ApiResult`.

---

### Module F3 — Results Page Core (Answer + Confidence Badge)

**Domain:** Frontend
**Purpose:** Render the core answer text and confidence badge on the Results page.
**Rationale:** SPDD §12.1 item 2 (first two sub-bullets).
**Dependencies:** `F0`, `F1`, `F2` (for navigation into this page). Does not depend on `F4`–`F6` (those render additional panels on the same page independently).

#### Step F3.1 — Page shell and data loading
1. In `Results.tsx`, read `sessionId` from route params.
2. If `AnalyzeResponse` was passed via router state, use it directly; otherwise call `getSession(sessionId)` on mount and show a loading state until it resolves.
3. If `rejected === true`, delegate entirely to the Rejection UI (`F6`) and do not render the rest of this module's components (early return).

#### Step F3.2 — Answer text panel
1. Render `answerText` in a prominent, readable panel (e.g., a card with generous line-height — this is the primary output the user came for).
2. If `answerText === null` (should only occur alongside `rejected: true`, per SPDD §8.5), render nothing here (guarded by the early return in F3.1).

#### Step F3.3 — Confidence badge component
Implement `ConfidenceBadge.tsx` (already stubbed in `F0`):
1. Props: `tier: 'High'|'Medium'|'Low'`, `rationale: string`.
2. Render a colored chip: green for `High`, amber for `Medium`, red for `Low`.
3. On hover/focus, show `rationale` in a tooltip — this MUST be visible, not buried, since SPDD §7.2/§7.3 treats confidence rationale as a first-class, judge-facing artifact.
4. Import and render this component in `Results.tsx`, passing `confidence.tier` and `confidence.rationale`.

---

### Module F4 — Evidence Overlay Renderer

**Domain:** Frontend
**Purpose:** Draw bounding boxes and change masks over the displayed image(s).
**Rationale:** SPDD §12.2 — evidence overlays are a mandatory rubric item ("Evidence & Visual Output").
**Dependencies:** `F0`, `F1`, `F3` (renders inside the Results page, but as a logically separate component so it can be built/tested independently against a fixture `AnalyzeResponse`).

#### Step F4.1 — Build `EvidenceOverlay.tsx`
1. Props: `imageUrl: string`, `boxes: {xLeft, yTop, xRight, yBottom, theta}[]`, `regionTags?: {region, tag, score}[]`.
2. Render the base image in an `<img>` or `<canvas>`, then an absolutely-positioned SVG overlay sized to the image's rendered dimensions.
3. Convert each box's normalized `[0,100]` coordinates (per SPDD §12.2) to pixel coordinates: `pixelX = (normalizedX / 100) * renderedImageWidth`. Handle `theta` (oriented box angle) via an SVG `transform="rotate(theta, cx, cy)"` on each box's `<rect>`.

#### Step F4.2 — Multi-candidate grounding rendering
1. When more than one box is present for a single grounding result (SPDD §5.2's ambiguity behavior — the specialist returns all plausible boxes, never a silent top-1), render every box simultaneously.
2. Vary box opacity/stroke-width by each box's `score` field so the highest-confidence candidate is visually distinguishable without hiding the others (per SPDD §12.2's "distinguishable styling" requirement).

#### Step F4.3 — Toggle controls
1. Add a checkbox/toggle per evidence item ("Show grounding boxes", "Show change mask") allowing the user to hide/show each overlay layer independently, per SPDD §12.1's "toggle-able per evidence item."
2. Store toggle state in `Results.tsx` component state, passed down as props.

#### Step F4.4 — Change-mask rendering
1. If `evidence.masks` is non-empty, fetch the mask image (served from `object_store` per SPDD §10.1 path convention `/{sessionId}/evidence/{stepIndex}_overlay.png`) and render it as a semi-transparent PNG layer above the base image.
2. Do not attempt to vectorize the mask client-side — the backend renders the overlay PNG server-side (SPDD §9.6 note that overlays are pre-rendered); the frontend only positions and layers the already-rendered image.

---

### Module F5 — Execution Trace Panel

**Domain:** Frontend
**Purpose:** Render the collapsible, expanded-by-default execution trace.
**Rationale:** SPDD §12.1 item 2, third sub-bullet; this is the PS's mandatory "auditable execution summary" made visible.
**Dependencies:** `F0`, `F1`. Independent of `F3`/`F4` (reads only `executionTrace` from the same `AnalyzeResponse`, can be built/tested in isolation with a fixture trace object).

#### Step F5.1 — Build `ExecutionTracePanel.tsx`
1. Props: `trace: ExecutionTrace`.
2. Render a collapsible `<details>`-style panel, `open` by default per the Proposal's presentation strategy (SPDD §12.1) — this is a deliberate demo choice, not incidental.
3. Render `trace.selectedTaskType` as a header line.

#### Step F5.2 — Step table
1. Render `trace.steps` as an ordered table with columns: Step #, Component, Adapter/Version, Parameters Used, Wall-Clock (ms), Output Summary.
2. Format `parametersUsed` (an arbitrary object) as a compact `key: value` inline list rather than a raw JSON dump, for readability.

#### Step F5.3 — Confidence + rejection trace states
1. Below the step table, render `trace.confidenceTier` and `trace.confidenceRationale` (duplicated from the badge for a self-contained trace panel a judge can screenshot independently).
2. If `trace.rejection` is present (non-null), render its `reasonCode` and `humanReadableReason` in place of the step table (per SPDD §20.3 — a trace is emitted even on rejection, and this panel MUST handle that case, not assume steps is always non-empty).

---

### Module F6 — Rejection State UI

**Domain:** Frontend
**Purpose:** A distinct, polished UI state for a validated-but-rejected query.
**Rationale:** SPDD §12.1 item 3 explicitly calls this a "first-class, polished UI state, not an afterthought" and the demo's "differentiating moment."
**Dependencies:** `F0`, `F1`. Independent build/test surface (renders from `rejected`/`rejectionReason`/`executionTrace.rejection` fields only).

#### Step F6.1 — Build `RejectionCard.tsx`
1. Props: `rejectionReason: string`, `trace: ExecutionTrace`.
2. Design as a visually distinct card (not a generic red error toast) — use a neutral/informative color scheme (e.g., blue-grey, not alarm-red) since a rejection here is a correct, expected system behavior, not a failure.
3. Display `rejectionReason` verbatim (per SPDD §12.1 — never paraphrased or truncated client-side).

#### Step F6.2 — Wire into Results page
1. In `Results.tsx` (from `F3`), when `rejected === true`, render `RejectionCard` instead of the answer/confidence/evidence components, but still render `ExecutionTracePanel` below it (a rejection still has a trace, per SPDD §7.3/§20.3).

#### Step F6.3 — Clarifying-question sub-state
⚠️ **FLAGGED AMBIGUITY:** SPDD §4.1 describes an `ambiguous_intent` "rejection" that is actually not a rejection at all — it returns `TaskSpec.clarifyingQuestion` and expects a round-trip, not a terminal rejection card. SPDD §8.5 (`AnalyzeResponse`) does not include a `clarifyingQuestion` field, and §14.1's table lists `ambiguous_intent` as a `reasonCode` alongside true rejections, but its "Example human-readable text" column is empty and just says "(returns `TaskSpec.clarifyingQuestion` instead of a rejection — see §4.1)." **This is a genuine contract gap between §4.1, §8.5, and §14.1 that must be resolved by the Backend team (`B1`/`B6`) before this sub-step can be implemented** — specifically, whether `AnalyzeResponse` needs a new `clarifyingQuestion: string | null` field, and whether the frontend should re-render the Upload & Query page pre-filled with the original query plus the clarifying question, or show a distinct inline prompt on the Results page. Implement as a placeholder that logs a console warning ("ambiguous_intent path not yet contract-defined") until this is resolved, rather than guessing at a UX flow the backend contract doesn't yet support.

---

### Module F7 — Map Integration

**Domain:** Frontend
**Purpose:** Render a georeferenced map layer (Leaflet) when valid CRS/footprint metadata is present; fall back to a plain image viewer otherwise.
**Rationale:** SPDD §12.3.
**Dependencies:** `F0`, `F1`, `F4` (the map layer is a container around the same evidence overlays `F4` produces — this module wraps `F4`'s output, it does not duplicate it).

#### Step F7.1 — Conditional map/plain-image branch
1. In `Results.tsx`, inspect whether the session's original `ImageMetadata` (obtained via `getSession` or passed through router state — confirm this is actually included in `AnalyzeResponse` or fetched separately; ⚠️ **FLAGGED AMBIGUITY**: SPDD §8.5's `AnalyzeResponse` does not include `ImageMetadata` or CRS/footprint fields directly — only `evidence.overlayImageUrls`. The frontend cannot determine "valid CRS/footprint present" from the documented `AnalyzeResponse` alone. This must be clarified with the backend team: either `AnalyzeResponse` needs an added `hasGeoreference: boolean` field, or the frontend infers it from the presence/format of `overlayImageUrls` metadata. Flag and confirm before building this step's conditional logic.)
2. If georeferencing is confirmed present: render a `react-leaflet` `<MapContainer>` with the base image as an `ImageOverlay` bounded by the reprojected footprint.
3. Otherwise: render the plain `EvidenceOverlay` component from `F4` directly (no map chrome, no basemap tiles).

#### Step F7.2 — Leaflet configuration
1. Set `MapContainer` `crs` prop appropriately for a simple image-overlay use case (`L.CRS.Simple` when no real-world basemap tiles are used, since no third-party tile server is assumed in an offline-capable deployment per SPDD §13.5 — do not silently pull tiles from a public tile server, which would violate the "no runtime external network calls" NFR).
2. Layer the `EvidenceOverlay`'s SVG boxes as a Leaflet `SVGOverlay` on top of the `ImageOverlay`, reusing the same coordinate-conversion logic from `F4.1` rather than duplicating it — extract that conversion into a small shared utility function first if not already done.

---

### Module F8 — Report Download & Session Reopen

**Domain:** Frontend
**Purpose:** "Download Report" button and re-opening a previously computed session.
**Rationale:** SPDD §9.2, §9.3, §12.1 item 2 last sub-bullet, §12.4.
**Dependencies:** `F0`, `F1`.

#### Step F8.1 — Download button
1. In `Results.tsx`, render a "Download Report" button with a dropdown/toggle for `PDF` vs `JSON`.
2. On click, set `<a href={getReportUrl(sessionId, format)} download>` — let the browser handle the file stream directly rather than fetching via `axios` and manually creating a blob URL, since SPDD §9.3 says this endpoint "streams the rendered report file."
3. Handle `404` (session doesn't exist) and `409` (original request was rejected, nothing to report) by disabling/hiding the button appropriately: hide entirely if `rejected === true` (there is nothing to report per SPDD §9.3), since offering a button that will 409 is worse UX than not showing it.

#### Step F8.2 — Direct-URL session reopen
1. Support navigating directly to `/results/:sessionId` (e.g., a bookmarked or shared link) by having `Results.tsx`'s mount effect call `getSession(sessionId)` whenever router state is absent (this was stubbed as a fallback in `F3.1` — this step completes it).
2. Show a distinct "session not found" state if `getSession` 404s, rather than a blank page.

---

### Module F9 — Frontend Testing

**Domain:** Frontend
**Purpose:** Automated tests for the components/pages above.
**Rationale:** No frontend-specific test plan is given in the SPDD (§16 covers backend/model testing only) — this module fills that gap using standard practice, and is flagged as such.
**Dependencies:** `F0`–`F8` (tests are written against each module as it completes; this module's steps can run incrementally, one per completed module, rather than strictly last).

⚠️ **FLAGGED GAP:** Neither the Proposal nor the SPDD specifies a frontend testing strategy, coverage target, or tooling choice. This plan adopts Vitest + React Testing Library as a reasonable default; the team should confirm or override this choice explicitly.

#### Step F9.1 — Test tooling setup
1. `npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom`.
2. Add a `vitest.config.ts` with `environment: 'jsdom'`.
3. Add `npm run test` script.

#### Step F9.2 — Component-level tests
1. `ConfidenceBadge.test.tsx`: assert correct color class for each of `High`/`Medium`/`Low`, and that the rationale appears in the DOM (accessible via tooltip or `aria-describedby`).
2. `EvidenceOverlay.test.tsx`: given a fixture with 3 boxes of varying `score`, assert 3 `<rect>` elements render with distinguishable opacity/stroke values.
3. `ExecutionTracePanel.test.tsx`: given a fixture trace with a `rejection` field populated, assert the step table is NOT rendered and the rejection reason IS rendered (covers the branch from `F5.3`).
4. `RejectionCard.test.tsx`: assert `rejectionReason` renders verbatim, unmodified.

#### Step F9.3 — Page-level integration tests (mocked API)
1. Mock `client.ts` functions using Vitest's `vi.mock`.
2. `UploadQuery` test: assert the submit button is disabled with 0 files or empty query, and enabled otherwise; assert a rejected file-count (3 files) shows the inline error.
3. `Results` test (three fixture `AnalyzeResponse` variants: success, rejection, and — once `F6.3`'s ambiguity is resolved — clarifying-question): assert each renders the correct top-level branch (answer panel vs. rejection card vs. clarifying-question UI).

---

## BACKEND

### Module B0 — Repository, Environment & Docker Compose Skeleton

**Domain:** Backend
**Purpose:** Establish the monorepo layout, base configuration, and container skeleton before any service logic is written.
**Rationale:** SPDD §18 defines the exact repository layout; SPDD §15 defines the container topology. Every other backend (and AI/ML) module writes into paths this module creates.
**Dependencies:** None — this is the first module across the whole project and should be completed (or at minimum have its directory skeleton committed) before `B1`+ begin.

#### Step B0.1 — Initialize the monorepo
1. `mkdir satquery-ai && cd satquery-ai && git init`.
2. Create the top-level structure exactly per SPDD §18:
   ```
   satquery-ai/
   ├── docker-compose.yml
   ├── config/
   │   └── config.yaml
   ├── frontend/            (populated by F0)
   ├── services/
   │   ├── api_gateway/
   │   ├── orchestrator/
   │   ├── fusion_pipeline/
   │   ├── report_service/
   │   └── model_serving/
   │       └── adapters/
   ├── training/
   │   └── data_prep/
   ├── eval/
   ├── tests/
   │   ├── unit/
   │   └── integration/
   └── docs/
   ```
3. Copy the three source documents (`Problem_Statement.md`, `SatQuery_AI_Final_Synthesized_Solution.md`, `SatQuery_AI_SPDD.md`) into `docs/`.

#### Step B0.2 — Python environment baseline
1. Create `services/requirements.txt` (shared base) with pinned versions for: `fastapi`, `uvicorn`, `pydantic` (v2), `rasterio`, `pyproj`, `shapely`, `sqlalchemy`, `psycopg2-binary`, `weasyprint`, `pytest`, `httpx` (for FastAPI TestClient).
   ⚠️ **FLAGGED AMBIGUITY:** Neither the Proposal nor SPDD pins a Python version or exact library versions. This plan assumes Python 3.11 as a reasonable, current LTS-adjacent choice; confirm against actual available GPU-host base images before locking `M1`'s Dockerfile.
2. Create a `services/pyproject.toml` or per-service `requirements.txt` files (decide one convention team-wide — this plan recommends one shared `requirements.txt` plus per-service `requirements-extra.txt` for model-serving-only deps like `vllm`/`transformers`/`peft`, to avoid installing GPU-heavy packages into the lightweight `api_gateway` container).

#### Step B0.3 — `config.yaml` skeleton
1. Create `config/config.yaml` with placeholder sections for every externalized value SPDD §15.2 requires:
   ```yaml
   service_urls:
     model_serving: "http://model_serving:8001"
     metadata_db: "postgresql://..."
   adapter_versions:
     vqa_caption: "v1"
     grounding: "v1"
     change_vqa: "v1"
   confidence_thresholds:
     quantity_discrepancy_tolerance_pct: 15
   validation_thresholds:
     footprint_overlap_min_pct: 70
     nodata_percent_max: 40
   routing_table: "see specialist_router.py for authoritative table; this section reserved for future externalization"
   ```
2. Create `.env.example` mirroring any secrets/URLs that should NOT live in `config.yaml` (e.g., DB password), with real `.env` gitignored.

#### Step B0.4 — Docker Compose skeleton
1. Create `docker-compose.yml` with **stub** service definitions (empty `command: ["true"]` placeholders acceptable at this stage) for the six services in SPDD §15.1: `frontend`, `api_gateway` (co-located with `orchestrator_service`), `model_serving`, `metadata_db`, `object_store`, and note `report_service` is co-located inside `api_gateway` (no separate compose entry).
2. Do not attempt to wire real health-check dependencies yet — that is `B17`'s job once individual services exist. This step only reserves the file and service names so no one duplicates them independently.

#### Step B0.5 — CI skeleton
1. Add `.github/workflows/ci.yml` (or equivalent) that, at minimum, runs `pytest tests/unit` and the frontend's `npm run lint` on every push — even with zero tests written yet, this establishes the pipeline other modules' tests will plug into.
2. Add the router/schema consistency check placeholder mentioned in SPDD §4.3 ("this invariant MUST be enforced by a schema/table consistency test in CI") as a TODO test file `tests/unit/test_router_schema_consistency.py` (empty stub, implemented fully in `B16`).

---

### Module B1 — Shared Data Contracts (Pydantic Schemas)

**Domain:** Backend
**Purpose:** Implement the authoritative Pydantic models for every schema in SPDD §8.
**Rationale:** Every other backend module, plus the frontend's `F1`, depends on these being fixed early and not duplicated ad hoc.
**Dependencies:** `B0`.

#### Step B1.1 — Create `services/api_gateway/schemas.py`
1. Implement `TaskSpec` exactly per SPDD §8.1, using a Pydantic `Literal` type for `taskType` restricted to the 8 enum values (`single_vqa`, `single_caption`, `single_grounding`, `change_vqa`, `change_description`, `change_and_grounding`, `fusion`, `fusion_then_change`), and `Literal['resolved', 'ambiguous']` for `status`.
2. Implement `ImageMetadata` per SPDD §8.2, using `Literal['optical','multispectral','sar']` for `detectedModality` and `Literal['geotiff','tiff','png','jpeg']` for `format`.
3. Implement `EvidenceItem`, `EvidenceLedger` per SPDD §8.3 (nested `Box` and `RegionTag` sub-models).
4. Implement `TraceStep`, `ExecutionTrace`, `Rejection` per SPDD §8.4.
5. Implement `AnalyzeRequest` (multipart body's JSON-carrying fields only — `query`, `sessionOptions`) and `AnalyzeResponse` per SPDD §8.5.

##### Sub-step B1.1.1
Use Pydantic's `alias_generator` (camelCase alias, snake_case Python attribute) so internal Python code uses `snake_case` while the JSON wire format stays `camelCase`, per SPDD §1.3's stated convention. Set `model_config = ConfigDict(populate_by_name=True)` on every model.

#### Step B1.2 — `TaskSpec.clarifyingQuestion` resolution
Per the ambiguity flagged in Frontend `F6.3`, this module is the place to formally resolve it: add `clarifyingQuestion: str | None` directly to `AnalyzeResponse` (not just `TaskSpec`) so the API-facing contract can actually surface it to the frontend without requiring the frontend to inspect `TaskSpec` internals it never receives. Document this addition explicitly as a deviation-with-reason from the SPDD's literal §8.5 schema (the SPDD's own §4.1/§14.1 text implies this field must exist somewhere in the response; this module is where that implication is made concrete).

#### Step B1.3 — Schema tests
1. Write `tests/unit/test_schemas.py`: for each schema, one test constructing a valid instance and one test asserting an invalid `taskType`/`status`/`format`/`detectedModality` value raises `pydantic.ValidationError`.
2. Confirm round-trip JSON serialization (`model_dump(by_alias=True)` → camelCase) matches the exact field names in SPDD §8's code blocks, field-for-field.

---

### Module B2 — API Gateway Core

**Domain:** Backend
**Purpose:** Stand up the FastAPI app skeleton with the five endpoints from SPDD §9, initially returning stub/mock responses.
**Rationale:** This is the single HTTP surface the frontend talks to; building it early (with mocked internals) unblocks frontend integration work before the orchestrator internals (`B5`–`B13`) are complete.
**Dependencies:** `B0`, `B1`.

#### Step B2.1 — FastAPI app scaffold
1. Create `services/api_gateway/main.py`:
   ```python
   from fastapi import FastAPI
   app = FastAPI(title="SatQuery AI API Gateway", version="0.1.0")
   ```
2. Mount CORS middleware permitting the frontend's dev origin (`http://localhost:5173`) — required since frontend and backend run on different ports in local dev.

#### Step B2.2 — Implement `POST /v1/analyze` (stubbed)
1. Define the route accepting `images: list[UploadFile] = File(...)`, `query: str = Form(...)`, `sessionOptions: str | None = Form(None)` (JSON string, parsed manually).
2. Validate: `1 <= len(images) <= 2`, else return HTTP `400` with a clear message (per SPDD §9.1's "malformed requests... DO return 400").
3. Validate `query` is non-empty, else `400`.
4. For this module only: generate a `session_id` (UUID4), and return a **hand-built mock `AnalyzeResponse`** (hardcoded `answerText`, a fixed `Medium` confidence, an empty evidence list, a minimal one-step trace) — this lets `F2`/`F3` integrate against a real, running endpoint immediately, before the orchestrator (`B5`+) exists. Mark this response generation clearly with a `# TODO(B5-B13): replace with real orchestrator call` comment.

#### Step B2.3 — Implement `GET /v1/health`
1. For this module, return `{"status": "ok"}` unconditionally with HTTP `200`. Real dependency checks (`model_serving` reachability, DB connectivity per SPDD §9.4) are added once `B3`/`B4`/`M1` exist — mark with a TODO.

#### Step B2.4 — Implement `GET /v1/session/{sessionId}` and `GET /v1/registry` (stubbed)
1. `GET /v1/session/{sessionId}`: for now, return `404` unconditionally (no persistence exists yet — real implementation lands in `B4`).
2. `GET /v1/registry`: return a hardcoded JSON object listing the four specialists and their precondition blocks, transcribed directly from the SPDD §4.2 precondition table (this table's content does not depend on any other module being built — it is static data) — this endpoint can be fully correct from day one.

#### Step B2.5 — Implement `GET /v1/session/{sessionId}/report` (stubbed)
1. Return `404` unconditionally for now (real implementation depends on `B14`).

#### Step B2.6 — Local run instructions
1. Document in `services/api_gateway/README.md`: `uvicorn services.api_gateway.main:app --reload --port 8000`.
2. Confirm this matches the port assumed in Frontend `F0.3`.

---

### Module B3 — Object Store Service

**Domain:** Backend
**Purpose:** Implement image/artifact storage per SPDD §10.1.
**Rationale:** Needed by `B2`'s real `/v1/analyze` implementation (once `B5`+ exists) to persist uploads, normalized tiles, evidence overlays, and reports.
**Dependencies:** `B0`. Independent of `B1`/`B2` internals — this is a pure storage utility module, testable in isolation.

#### Step B3.1 — Storage abstraction interface
1. Create `services/api_gateway/object_store.py` with an abstract interface: `save(session_id, subpath, bytes) -> str (path/url)`, `load(session_id, subpath) -> bytes`, `exists(session_id, subpath) -> bool`.
2. Implement a `LocalFilesystemObjectStore` concrete class writing under a configurable root directory (default `./data/object_store/`), following the exact path convention from SPDD §10.1:
   ```
   /{sessionId}/inputs/{imageId}.{ext}
   /{sessionId}/derived/{imageId}_normalized.tif
   /{sessionId}/evidence/{stepIndex}_overlay.png
   /{sessionId}/report.pdf
   /{sessionId}/report.json
   ```
3. ⚠️ **FLAGGED AMBIGUITY:** SPDD §10.1 says "S3-compatible bucket (if available)" without committing to which for the demo. Implement `LocalFilesystemObjectStore` first (sufficient per SPDD §15.1's "or bind-mounted volume" note); implement an `S3ObjectStore`/MinIO variant only if the team confirms cloud deployment is actually needed — do not build both speculatively.

#### Step B3.2 — Content-addressed hashing for caching
1. Implement `compute_content_hash(image_bytes) -> str` (SHA-256 hex digest) per SPDD §10.1/§13.3.
2. Use this hash as the cache key for the vision-encoder embedding cache described in SPDD §13.3 — store a mapping `{content_hash: cached_embedding_ref}` (this mapping itself can live in `metadata_db`, built in `B4`, or a simple local key-value file for the hackathon scope; decide and document which).

#### Step B3.3 — Unit tests
1. `tests/unit/test_object_store.py`: save then load round-trip; `exists()` correctness; two identical byte-strings produce the same content hash; two different byte-strings produce different hashes.

---

### Module B4 — Metadata DB Service

**Domain:** Backend
**Purpose:** Implement the three-table relational schema from SPDD §10.2.
**Rationale:** Persists sessions, evidence ledgers, and execution traces so `GET /v1/session/{id}` and report regeneration work without recomputation.
**Dependencies:** `B0`, `B1` (needs the Pydantic schemas to know what JSON blobs it's storing).

#### Step B4.1 — Define the schema
1. Using SQLAlchemy (or the team's preferred ORM — this plan assumes SQLAlchemy per the `psycopg2-binary` dependency pinned in `B0.2`), create `services/api_gateway/db_models.py` with three tables exactly per SPDD §10.2:
   - `sessions(session_id PK, created_at, query_text, task_type, rejected BOOLEAN, confidence_tier)`
   - `evidence_ledgers(session_id FK, ledger_json JSONB)`
   - `execution_traces(session_id FK, trace_json JSONB)`
2. Use SQLite for local dev (`sqlite:///./data/satquery.db`) and Postgres for shared deployment, switched via `config.yaml`'s `service_urls.metadata_db` — confirm SQLAlchemy's engine URL scheme handles both without code branching (it does, via the URL prefix).

#### Step B4.2 — Migration setup
1. Add Alembic (`pip install alembic`), initialize with `alembic init migrations`.
2. Generate the initial migration for the three tables above.
3. Document the idempotent migration-on-startup requirement from SPDD §15.3 step 3 — implement as a startup hook that runs `alembic upgrade head` before `api_gateway` accepts traffic (wired fully in `B17`; this module only needs the migration files to exist).

#### Step B4.3 — Repository functions
1. `save_session(session: SessionRecord) -> None`.
2. `get_session(session_id: str) -> AnalyzeResponse | None` — reconstructs the full `AnalyzeResponse` by joining all three tables (this is what `B2`'s real `GET /v1/session/{sessionId}` will call).
3. `session_exists(session_id: str) -> bool`.

#### Step B4.4 — Wire into `B2`'s stubbed endpoints
1. Replace `B2.4`'s hardcoded `404` for `GET /v1/session/{sessionId}` with a real call to `get_session`.
2. This step has a hard dependency on `B13` (Response Composer) actually producing real `AnalyzeResponse` objects to persist — until then, this module's `save_session` call site remains a TODO in `B2`'s `/v1/analyze` handler.

#### Step B4.5 — Unit tests
1. `tests/unit/test_metadata_db.py` against an in-memory SQLite DB: save + retrieve round-trip for a session including nested JSON ledger/trace; `session_exists` correctness for present/absent IDs.

---

### Module B5 — Query Interpreter Integration

**Domain:** Backend
**Purpose:** The backend-side wrapper that calls the AI/ML query-interpreter model (built in `M2`) and enforces the schema/repair-prompt logic from SPDD §4.1.
**Rationale:** This is the first orchestrator stage; separated from `M2` itself so the backend team can build the calling/validation/retry logic against a mocked model response while the AI/ML team finalizes the actual model.
**Dependencies:** `B1` (schemas), `B0`. Cross-domain dependency: needs `M2`'s inference API contract (endpoint shape, expected latency) defined — even before `M2`'s model is fully trained/tuned, `M2` must publish its call signature early so this module isn't blocked.

#### Step B5.1 — Define the calling contract with `M2`
1. Agree and document (in `docs/interfaces/query_interpreter.md`, plan-introduced path) the exact request/response shape between `orchestrator_service` and the query-interpreter model endpoint, e.g.:
   ```
   POST {model_serving_url}/interpret
   body: { "query": str, "imageContext": ImageContextSummary }
   response: { "taskType": str, "status": str, ..., "intentConfidence": float }
   ```
2. This contract MUST be finalized (even if the underlying model is a stub returning canned responses) before this module's retry logic can be tested end-to-end.

#### Step B5.2 — Implement `services/orchestrator/query_interpreter.py`
1. Function `interpret(query: str, image_context: ImageContextSummary) -> TaskSpec`.
2. Call the `M2` endpoint per the contract in `B5.1`.
3. Validate the raw JSON response against the `TaskSpec` Pydantic model.
4. On `pydantic.ValidationError` (invalid JSON shape or an out-of-enum `taskType`): retry once with a repair prompt appended (per SPDD §4.1's failure-mode spec) — implement the repair prompt construction here (backend responsibility), even though the actual re-inference call goes back through the same `M2` endpoint.
5. On a second failure: raise a typed `InterpretationFailedError`, caught by `B2`'s route handler and surfaced as the `interpretation_failed` error path (SPDD §4.1) — this specific error is NOT in the SPDD §14.1 rejection-reason-code table (that table is `compatibility_validator`-specific); confirm with the team whether `interpretation_failed` needs its own top-level HTTP error response or should be folded into `AnalyzeResponse.rejected` for contract consistency. ⚠️ **FLAGGED AMBIGUITY:** SPDD §4.1 mentions this "hard error" but §14 (Error Taxonomy) never explicitly places it in either the validation-rejection table (§14.1, which is `compatibility_validator`-specific) or the runtime-failure section (§14.2, which covers post-validation failures) — `query_interpreter` failures happen *before* validation. Resolve explicitly: this plan recommends treating it as a `ValidationRejection`-shaped response with a new reason code `interpretation_failed` added to the §14.1 enum, for contract consistency with the frontend's existing rejection-rendering path (`F6`), rather than inventing a third response shape.

#### Step B5.3 — Ambiguous-intent handling
1. When the returned `TaskSpec.status == "ambiguous"`, this module returns the `TaskSpec` as-is (with `clarifyingQuestion` populated) up to `B2`'s route handler, which — per the resolution in `B1.2` — populates `AnalyzeResponse.clarifyingQuestion` and does NOT proceed to `B6`/`B7`.

#### Step B5.4 — Unit tests
1. Mock the `M2` endpoint call. Test: valid response → correct `TaskSpec`; invalid JSON on first call, valid on retry → success after one retry; invalid JSON on both calls → `InterpretationFailedError` raised; `intentConfidence < 0.55` → `status == "ambiguous"` and `clarifyingQuestion` populated (per SPDD §4.1's explicit `0.55` threshold).

---

### Module B6 — Compatibility Validator

**Domain:** Backend
**Purpose:** Implement the deterministic, non-LLM precondition-checking logic from SPDD §4.2.
**Rationale:** This is the PS's "Input Validation" rubric row and the Proposal's headline differentiator (the "rejecting" validator). It is pure, deterministic business logic — ideal for isolated, thorough unit testing independent of any model.
**Dependencies:** `B1`, `B0`. Cross-domain dependency: `M9` (Modality/Format Detection Heuristic) for the "ambiguous cases fall back to a lightweight heuristic classifier" behavior in SPDD §4.2 step 2 — this module can be built and fully tested against known/explicit metadata first, then wired to `M9`'s heuristic only for the ambiguous-modality fallback path.

#### Step B6.1 — Metadata extraction helper
1. Implement `services/orchestrator/metadata_extraction.py`: `extract_metadata(image_bytes, filename) -> ImageMetadata`, using `rasterio`/`GDAL` to read CRS, band count, resolution, and any embedded acquisition-date tags.
2. Compute `nodataPercent` and, where feasible, `cloudMaskPercent` (note: cloud masking from raw bytes without a dedicated cloud-detection model is nontrivial — ⚠️ **FLAGGED GAP**: neither the Proposal nor SPDD specifies how `cloudMaskPercent` is actually computed; this plan recommends a placeholder heuristic (e.g., a simple brightness/whiteness threshold on optical imagery) documented explicitly as an approximation, not a validated cloud-detection model, unless/until the AI/ML team provides one).

#### Step B6.2 — Implement the precondition table
1. Transcribe SPDD §4.2's precondition table into a static Python data structure (`PRECONDITIONS: dict[str, PreconditionBlock]`), one entry per specialist (`vqa_caption_specialist`, `grounding_specialist`, `change_vqa_specialist`, `fusion_pipeline`), fields matching the table's columns exactly (required image count, modality, temporal relationship, spatial relationship, format constraints).
2. This table MUST be exposed (or a serialized copy of it) via `GET /v1/registry` (`B2.4`) — implement as a single shared source, imported by both the validator and the registry endpoint, so they cannot drift.

#### Step B6.3 — Implement the six validation steps, in order
1. **Format sniff:** use GDAL's driver detection; reject with `unsupported_format` if not in `{GeoTIFF, TIFF, PNG, JPEG}`.
2. **Modality detection:** primary path uses explicit sensor metadata tags/band count heuristics (e.g., band count + wavelength tags indicate SAR vs. optical vs. multispectral); ambiguous cases call `M9`'s heuristic classifier endpoint.
3. **Count check:** compare `len(images)` against the selected task's `PRECONDITIONS[...].required_image_count`; reject with `insufficient_image_count` if short.
4. **Pair checks (only when 2 images):**
   - CRS compatibility: attempt `pyproj`-based reprojection if CRSs differ but are both resolvable; reject `crs_mismatch_unresolvable` if not.
   - Footprint overlap: compute IoU via `shapely`; reject `insufficient_footprint_overlap` if below the configurable threshold (default 70%, from `config.yaml`, `B0.3`).
   - Temporal ordering (change tasks only): reject `temporal_ordering_invalid` if both images share the same acquisition date.
5. **Radiometric sanity:** if `nodataPercent`/`cloudMaskPercent` exceeds the configurable threshold (default 40%), do NOT reject — attach a `warnings[]` entry (this list must be added to `ValidationPass`'s shape if not already covered by `B1`'s schema; confirm and add if missing).
6. **Rejection construction:** on any hard failure, build `ValidationRejection{reasonCode, humanReadableReason, missingRequirement}` using the exact templated strings from SPDD §14.1's table — never leak a raw Python exception message to the response.

#### Step B6.4 — Compound-task validation nuance
1. For `fusion_then_change` and `change_and_grounding` task types, apply the precondition check for **each** specialist in the sequence (per `B7`'s routing table), not just the first — a compound plan is only valid if every step in its sequence is individually satisfiable given the supplied images.
2. Handle the specific 3-image edge case documented in SPDD §20.2 (a `fusion_then_change`-flavored query that actually implies 3 images): when only 2 images are supplied but the query's phrasing implies a third (temporal) reference, this module MUST downgrade the `taskType` to what IS answerable (e.g., `fusion` only) and pass a note through to `B13`'s Response Composer stating the unaddressable clause — implement this as a `TaskSpec.requestedParameters` annotation (e.g., `{"unsatisfiedClause": "temporal comparison — no prior-date reference supplied"}`) rather than inventing a new top-level field, to keep the schema change minimal. Add an integration test for this exact scenario in `B16`.

#### Step B6.5 — Unit tests
1. One test per precondition-table row × one test per rejection reason code in SPDD §14.1 (both pass and fail paths), per SPDD §16.1's explicit test-plan requirement.
2. A specific test reproducing the SPDD §20.3 sequence (footprint overlap = 12%, threshold 70% → `insufficient_footprint_overlap`).
3. A specific test reproducing the SPDD §20.2 three-image-implied-but-two-supplied scenario from `B6.4.2`.

---

### Module B7 — Specialist Router

**Domain:** Backend
**Purpose:** Implement the fixed, deterministic routing table from SPDD §4.3.
**Rationale:** Pure, non-LLM lookup logic — table-driven and fully unit-testable without any model dependency, per SPDD §4.3's explicit design intent.
**Dependencies:** `B1` (needs the `TaskSpec.taskType` enum). Does not depend on `B6` functionally (it consumes a `ValidationPass`, but the routing table itself can be written and tested against a bare `taskType` string without a real validator existing yet) — can be built in parallel with `B6`.

#### Step B7.1 — Transcribe the routing table
1. Implement `services/orchestrator/specialist_router.py` with a `ROUTING_TABLE: dict[str, list[SpecialistCallSpec]]` transcribed exactly from SPDD §4.3's table (8 `taskType` entries, including the two sequential/compound ones: `change_and_grounding` → `[change_vqa_specialist, grounding_specialist]`, `fusion_then_change` → `[fusion_pipeline, change_vqa_specialist]`).
2. Define `SpecialistCallSpec` as a small dataclass: `{specialist_name: str, sequence_index: int, depends_on_prior_output: bool}`.

#### Step B7.2 — CI consistency invariant
1. Implement the specific test required by SPDD §4.3's "Failure modes" note and SPDD §16.1: assert `set(ROUTING_TABLE.keys()) == set(TaskSpec's taskType Literal values)` — this catches drift between `B1`'s schema and this module's table automatically. Wire this into the CI stub reserved in `B0.5`.

#### Step B7.3 — Route resolution function
1. `route(task_spec: TaskSpec) -> list[SpecialistCallSpec]` — pure function, no I/O, no LLM call.
2. Raise an internal assertion error (not a user-facing error) if `task_spec.taskType` is missing from the table — per SPDD §4.3, this should be "impossible by construction" given `B7.2`'s CI check, so a runtime hit here indicates a CI gap, not a normal error path.

#### Step B7.4 — Unit tests
1. Table-driven test: for every one of the 8 `taskType` values, assert the exact expected specialist sequence, per SPDD §16.1.

---

### Module B8 — Specialist Invocation Layer

**Domain:** Backend
**Purpose:** The orchestrator-side code that actually calls each specialist's `model_serving` endpoint and collects results into an `EvidenceLedger`.
**Rationale:** Bridges `B7`'s routing decision to real model inference. Kept as its own module because its internals (HTTP/RPC calls to `model_serving`, timeout handling) are backend infrastructure concerns distinct from the routing logic (`B7`) or the model implementations themselves (`M3`–`M5`).
**Dependencies:** `B1`, `B7`. Cross-domain: needs `M1`'s inference-endpoint contract (adapter hot-swap API) published, and functional (even stubbed) `M3`/`M4`/`M5` endpoints to call against.

#### Step B8.1 — Define the specialist-call contract with `M1`
1. Document (in `docs/interfaces/model_serving.md`, plan-introduced path) the single parameterized inference endpoint `M1` exposes, per SPDD §5.4: `POST {model_serving_url}/infer` with body `{adapterId: str, taskToken: str, image(s): ..., prompt: str}` → returns the specialist-specific output contract (SPDD §5.1–§5.3's per-specialist output shapes).
2. This contract must be agreed before this module's real HTTP-calling code is written; until then, build against a documented mock.

#### Step B8.2 — Implement per-specialist call wrappers
1. `call_vqa_caption(image, mode, question=None) -> EvidenceItem` — maps to SPDD §5.1's input/output contract, sets `adapterId="adapter_vqa_caption"`.
2. `call_grounding(image, referring_expression) -> EvidenceItem` — SPDD §5.2's contract; MUST preserve the multi-box, no-silent-top-1 behavior end-to-end (this module must not itself collapse multiple boxes — pass all of them through).
3. `call_change_vqa(image_t1, image_t2, question=None) -> EvidenceItem` — SPDD §5.3's contract, including passing through `quantityFlag`/`deterministicPixelCount` untouched for the verifier to consume later.
4. Each wrapper sets a per-call timeout aligned with SPDD §13.1's latency budgets (e.g., grounding's HTTP call timeout ≥ 4s target + buffer, not an arbitrary global timeout).

#### Step B8.3 — Sequential compound execution
1. For a compound `SpecialistCallSpec` list (from `B7`) with `depends_on_prior_output = True` (e.g., `change_and_grounding`, where grounding runs "over the change-difference map region" per SPDD §4.3), implement the data hand-off: extract the relevant region/mask from the first specialist's `EvidenceItem` and pass it as additional input to the second call.
2. Execute calls in strict sequence for dependent compound plans (not parallel) — sequencing correctness is a routing/orchestration hard requirement (SPDD §4.3), not a performance optimization opportunity to parallelize casually.

#### Step B8.4 — Failure handling (SPDD §14.2)
1. Wrap each specialist call in a try/except catching timeout and inference-error exceptions.
2. On failure mid-compound-plan: mark that step `failed` in the (in-progress) trace, and continue only if partial results are meaningful — per SPDD §14.2, return partial results with confidence forced to `Low` rather than a raw 500.
3. If `model_serving` itself is unreachable (connection refused), propagate a distinct exception type that `B2`'s route handler translates into the `503` response described in SPDD §14.2 — do not conflate "specialist model errored" with "model_serving is down," since they need different HTTP-level responses.

#### Step B8.5 — Assemble the `EvidenceLedger`
1. Collect every `EvidenceItem` produced (in order) into a single `EvidenceLedger{sessionId, items, agreementFlag: "n/a" (set later by B10)}`.

#### Step B8.6 — Unit/integration tests
1. Unit tests with a mocked `model_serving` HTTP client: single-specialist happy path; compound sequential hand-off; timeout → partial-result path; connection-refused → `503`-triggering exception.

---

### Module B9 — Fusion Pipeline Orchestration (Backend Composition Layer)

**Domain:** Backend
**Purpose:** The backend-side composition of the fusion pipeline's three sub-steps, as specified in SPDD §6 — this module orchestrates calls, it does not implement the ML models themselves (those are `M7`/`M8`).
**Rationale:** SPDD §6 explicitly frames the fusion pipeline as "a single logical specialist with three internal sub-steps," reusing the VQA specialist (sub-step 1) and a separate complementarity-detector model (sub-step 2), composed here.
**Dependencies:** `B8` (reuses `call_vqa_caption`), `B1`. Cross-domain: `M7` (complementarity detector endpoint contract) and `M8` (the fusion input contract / domain-gap preprocessing hook).

#### Step B9.1 — Sub-step 1: independent per-modality evidence extraction
1. Implement `services/fusion_pipeline/evidence_extraction.py`: calls `B8.2`'s `call_vqa_caption` **twice** — once on the optical/multispectral image, once on the SAR image — each requesting **structured** output (LULC class presence list + confidence, approximate area share, grounded regions relevant to the query) rather than free text.
2. ⚠️ **FLAGGED GAP:** SPDD §5.1's `vqa_caption_specialist` output contract (`{answerText, answerType, boundingBoxesIfAny, rawTokenConfidence}`) as literally specified does NOT include a structured LULC-class-presence-list field that §6 sub-step 1 says it must produce for fusion. Either (a) the `vqa_caption_specialist` output contract needs an additional structured-mode output field for fusion's internal use (not exposed in the plain single-image VQA API response), or (b) a separate structured-extraction prompt/parsing step is needed on top of the specialist's free-text answer. This must be resolved between the Backend and AI/ML teams before `B9.1`/`M8` can be implemented — do not silently invent a structured schema without cross-team agreement, since `M3`'s training/prompting must also support producing it.

#### Step B9.2 — Sub-step 2: complementarity detector call
1. Implement `services/fusion_pipeline/complementarity_detector.py`: calls `M7`'s dedicated lightweight endpoint (not the LLM decoder — a "dense-feature encoder pair" per SPDD §6) with the two structured evidence sets from `B9.1`.
2. Implement the **config-flag fallback switch** required by SPDD §6/§17 item 2: read `config.yaml`'s `fusion.complementarity_detector_mode: "trained" | "rule_based"`. When `"rule_based"`, call a locally-implemented rule-based fallback (class-presence-set intersection/difference between the two modalities' structured evidence) instead of `M7`'s endpoint — implement this switch as a single `if` at the call site, not scattered through the pipeline, per SPDD §6's explicit instruction.
3. Output: per-LULC-region tags (`agreement`/`optical_only`/`sar_only`) with numeric scores, per SPDD §6 output contract.

#### Step B9.3 — Sub-step 3: verbalization
1. Implement `services/fusion_pipeline/verbalizer.py`: calls the same controller LLM used by `B13`'s Response Composer, passing **only** the tagged structured comparison (never raw pixels, per SPDD §6's explicit "MUST NOT be given raw pixels" requirement) and produces the natural-language answer citing which modality supplied which claim.

#### Step B9.4 — Domain-gap preprocessing hook
1. Before `B9.1` runs, call the domain-gap normalization preprocessing (GSD-normalization tiling, radiometric normalization) built in `M6`, applied to both input images uniformly. This step is pipeline-level (per SPDD §6's explicit note that it's "not something either sub-step implements itself") — implement as a preprocessing call in `services/fusion_pipeline/__init__.py`'s top-level `run_fusion_pipeline()` entry point, invoked before sub-step 1, for every specialist call, not fusion alone (confirm with `B8` whether this preprocessing hook should actually live upstream of ALL specialist calls, not just fusion, since SPDD §6's note implies it "applies uniformly to every specialist" — if so, relocate this call into `B8`'s common entry point rather than duplicating it here).

#### Step B9.5 — Assemble fusion `EvidenceItem`
1. Package sub-steps 1–3's outputs into a single `EvidenceItem` matching the fusion output contract in SPDD §6 (`answerText, regionTags, opticalEvidenceRef, sarEvidenceRef`).

#### Step B9.6 — Unit/integration tests
1. Test the config-flag switch: with `complementarity_detector_mode="rule_based"`, assert `M7`'s endpoint is never called and the rule-based path produces valid region tags on a fixture pair.
2. Test the "MUST NOT be given raw pixels" constraint at the verbalizer call site — assert the payload sent to the LLM contains only structured tags, never image bytes.

---

### Module B10 — Verifier Node

**Domain:** Backend
**Purpose:** Implement the three mandatory check classes from SPDD §7.1.
**Rationale:** Deterministic, rule-based logic operating purely on the `EvidenceLedger` — no model calls, ideal for isolated, thorough testing.
**Dependencies:** `B1`, `B8` (consumes the `EvidenceLedger` `B8` produces), `B9` (for fusion-specific cross-tool checks).

#### Step B10.1 — Geometric sanity checks
1. For every `EvidenceItem.boxes`, assert each coordinate lies within `[0,100]`; assert `theta ∈ [-90°, 90°]`.
2. For change-mask items, assert the mask's spatial extent does not exceed the co-registered overlap region computed during `B6`'s validation (pass this overlap region through the pipeline as part of `TaskSpec`/validation context so the verifier has access to it without recomputing).
3. On any violation, set `EvidenceItem.geometryValid = false` and log the specific violation verbatim (which field, which value, which bound was exceeded) into the in-progress trace object.

#### Step B10.2 — Cross-tool agreement checks
1. When the ledger contains two independently-derived answers to the same underlying question (e.g., fusion's `regionTags` vs. a direct VQA call on the same region — this scenario mainly arises in compound plans), compare them.
2. Define "disagreement above threshold" concretely: e.g., if fusion tags a region `optical_only` but a direct VQA call on the same region reports high-confidence presence of the same class in both modalities, flag disagreement. ⚠️ **FLAGGED GAP:** SPDD §7.1 item 2 describes this check narratively but does not give an exact comparison algorithm or threshold value. This plan recommends implementing a minimal, documented heuristic (e.g., a configurable Jaccard-similarity threshold between the two evidence sources' claimed LULC classes) and treating it as v1, subject to revision — do not block the module on finding a "correct" algorithm the source documents don't specify.
3. Set `EvidenceLedger.agreementFlag = "low"` on disagreement above threshold, else `"high"`.

#### Step B10.3 — Deterministic quantity cross-check
1. Only runs when `EvidenceItem.quantityFlag == true` (set upstream by `M5`'s change-VQA adapter output per SPDD §5.3).
2. Extract a numeric claim from `answerText` via a small regex/NLI parse (e.g., regex for explicit numbers/percentages first; fall back to a lightweight NLI-style comparison only if no explicit number is present — document which library/approach is used, e.g., a simple regex pass is sufficient for MVP per the SPDD's own framing of this as "a small regex/NLI parse").
3. Compare against `deterministicPixelCount`; if divergence exceeds the configurable tolerance (default ±15%, from `config.yaml`), set `EvidenceItem.quantityDiscrepancy = true`.

#### Step B10.4 — Non-mutating contract
1. Confirm (via tests) that `verifier_node` never rewrites `answerText` — it only annotates the ledger, per SPDD §7.1's explicit "the verifier does not rewrite the answer text" requirement. This is a behavioral invariant worth its own dedicated test, not just incidental coverage.

#### Step B10.5 — Unit tests
1. Per SPDD §16.1: synthetic `EvidenceLedger` fixtures for each of the three check classes, asserting correct flag-setting — one fixture per check class, both a passing and a failing case each (6 fixtures minimum).

---

### Module B11 — Confidence Scorer

**Domain:** Backend
**Purpose:** Implement the priority-ordered rule list from SPDD §7.2.
**Rationale:** A simple, auditable decision list (explicitly not a learned scorer, per the SPDD's own stated rationale) — pure business logic.
**Dependencies:** `B1`, `B10` (consumes the annotated `EvidenceLedger`).

#### Step B11.1 — Implement the 5-rule priority list, in exact order
1. Rule 1: any consumed evidence item has `geometryValid == false` → `Low`, rationale = `"a geometric consistency check failed."`
2. Rule 2: `quantityDiscrepancy == true` → `Low`, rationale = `"the model's stated count/ratio disagrees with a deterministic pixel-based count."`
3. Rule 3: query type matches the documented weak-point list (counting, ratio, smallest-change, non-unique-referent grounding — this list must be sourced from `TaskSpec.requestedParameters`/`questionText` classification; confirm with `B5`/`M2` how "query type" is actually tagged on the `TaskSpec` so this rule has something concrete to check against, since SPDD §7.2 assumes this tagging exists but does not specify which upstream component sets it — ⚠️ **FLAGGED GAP**: this plan recommends the Query Interpreter (`M2`/`B5`) add a `queryWeakPointCategory: string | null` field to `TaskSpec.requestedParameters` at classification time, since it already has the full query text and task type in hand) → apply a one-tier discount to whatever rules 4–5 would otherwise produce.
4. Rule 4: decoupled perception/reasoning confidence tokens (stretch goal, `M11`) both present and both above calibration threshold → `High`.
5. Rule 5 (default): `Medium`.

##### Sub-step B11.1.1
Implement as a literal ordered `if/elif` chain (first match wins) per SPDD §7.2's explicit "first applicable rule wins" instruction — do not implement as a scoring/summation system, which would violate the documented design intent.

#### Step B11.2 — MVP vs. stretch-goal path switch
1. Implement Rule 4 defensively: if `M11`'s decoupled confidence tokens are not available (feature not yet implemented, or the specialist didn't emit them), Rule 4 simply never matches and the chain falls through to Rule 5 — confirm this fallback requires zero special-casing beyond "Rule 4's precondition check returns false," per SPDD §7.2.1's explicit fallback design.

#### Step B11.3 — Unit tests
1. Per SPDD §16.1: table-driven tests covering the full priority-ordered rule list, **including the interaction case** explicitly called out: a query that would otherwise be `High` (Rule 4 satisfied) but matches a weak-point category (Rule 3) — assert the result is the one-tier-discounted `Medium`, not `High`, and that Rule 3 is checked before Rule 4's discount is applied (confirm the exact interaction order: does Rule 3's discount apply to what Rule 4 *would have* produced, requiring look-ahead, or does the discount apply post-hoc after determining Medium/High from 4-5? SPDD §7.2 rule 3's phrasing — "apply a fixed one-tier discount to whatever tier steps 4–5 would otherwise produce" — implies look-ahead: evaluate 4/5 first, then discount. Implement accordingly, and write a test explicitly asserting this evaluation order.)

---

### Module B12 — Trace Emitter

**Domain:** Backend
**Purpose:** Serialize the `ExecutionTrace` object per SPDD §7.3.
**Rationale:** The PS's mandatory auditable execution summary — must be present on every response, success or rejection.
**Dependencies:** `B1`. Logically sits downstream of every other orchestrator component (it collects their per-step outputs), so in practice it is threaded through `B5`–`B11` as a shared accumulator object rather than called once at the end — but its schema/serialization logic is independently implementable and testable against synthetic step data before the rest of the orchestrator is wired together.

#### Step B12.1 — `ExecutionTrace` accumulator
1. Implement a `TraceBuilder` class instantiated once per request (in `B2`'s `/v1/analyze` handler once `B5`–`B13` are wired), with an `add_step(component, adapter_id_or_version, parameters_used, wall_clock_ms, output_summary)` method appended by each orchestrator component as it runs.
2. Each of `B5` (query interpreter), `B6` (validator — even on rejection), `B8` (each specialist call), `B9` (each fusion sub-step), `B10` (verifier), `B11` (confidence scorer) MUST call `add_step(...)` — this is a cross-cutting integration responsibility; document it explicitly in each of those modules' code as a required call, not an optional nicety.

#### Step B12.2 — Rejection trace path
1. When `B6` (or `B5`'s ambiguous-intent path) short-circuits the pipeline, the `TraceBuilder` still finalizes an `ExecutionTrace` with `rejection: {reasonCode, humanReadableReason}` populated in place of a normal step-by-step body — per SPDD §7.3's explicit "trace still emitted, even on rejection" and the sequence example in SPDD §20.3.

#### Step B12.3 — Finalization
1. `TraceBuilder.finalize(confidence_tier, confidence_rationale) -> ExecutionTrace` — called once by `B13` after `B11` has produced the final confidence tier.

#### Step B12.4 — Unit tests
1. Assert a trace built from a mocked sequence of `add_step` calls serializes exactly per SPDD §8.4's schema.
2. Assert the rejection path produces a trace with `rejection` populated and `steps` either empty or containing only the steps that ran before the short-circuit (confirm which — this plan recommends including the steps that DID run, e.g., `query_interpreter` ran successfully even if `compatibility_validator` then rejected, so the trace should show that step, not hide it).

---

### Module B13 — Response Composer

**Domain:** Backend
**Purpose:** Convert the finalized `EvidenceLedger` + `ExecutionTrace` + confidence tier into the final `AnalyzeResponse`.
**Rationale:** The last orchestrator stage before the API gateway returns to the frontend.
**Dependencies:** `B1`, `B10`, `B11`, `B12`.

#### Step B13.1 — Natural-language composition
1. For non-fusion single-specialist responses, `answerText` is largely the specialist's own `answerText` (from `B8`), possibly lightly post-processed (e.g., appending a caveat sentence if `B6.4.2`'s "unsatisfied clause" annotation is present on the `TaskSpec`).
2. For fusion responses, `answerText` comes from `B9.3`'s verbalizer output directly.
3. For compound plans, compose a combined answer citing both specialists' contributions (e.g., per SPDD §20.2's example: state the fusion result AND explicitly state the unaddressable temporal clause, rather than silently dropping it).

#### Step B13.2 — Assemble `AnalyzeResponse`
1. Populate every field per SPDD §8.5: `sessionId`, `answerText`, `evidence` (boxes/masks/overlay URLs — overlay URLs point to `object_store` paths rendered by a to-be-specified overlay-rendering step; see `B13.3`), `confidence`, `executionTrace`, `reportUrl` (null until `B14` generates one, or populated eagerly if `sessionOptions.returnReport == true`), `rejected`, `rejectionReason`, and (per `B1.2`'s resolution) `clarifyingQuestion`.

#### Step B13.3 — Evidence overlay rendering (server-side)
1. ⚠️ **FLAGGED GAP:** SPDD §9.6 and §12.2 both assume overlay PNGs are pre-rendered server-side and simply layered by the frontend, but no SPDD section explicitly assigns "render boxes/masks onto the base image as a PNG" to a named component. This plan assigns it here, as a `B13` sub-responsibility (`services/orchestrator/overlay_renderer.py`), using a Python imaging library (e.g., `Pillow` + `rasterio` for georeferenced draws) to draw `EvidenceItem.boxes`/masks onto a copy of the base image, saved to `object_store` at `/{sessionId}/evidence/{stepIndex}_overlay.png` per the path convention in `B3.1`. Confirm this assignment with the team since it could equally be split into its own module — this plan keeps it inside `B13` because it operates on the same finalized evidence the Response Composer already has in hand.

#### Step B13.4 — Persist and return
1. Call `B4`'s `save_session(...)` with the finalized `AnalyzeResponse`'s constituent parts.
2. Return the `AnalyzeResponse` to `B2`'s route handler.

#### Step B13.5 — Unit/integration tests
1. Test the compound-plan answer composition explicitly reproduces the SPDD §20.2 example text pattern (stating what was answered and what could not be, given only 2 of the implied 3 images).

---

### Module B14 — Report Service

**Domain:** Backend
**Purpose:** Render a persisted session's trace/ledger/images into a downloadable PDF and JSON, per SPDD §9.6.
**Rationale:** Explicit PS deliverable ("Downloadable Reports").
**Dependencies:** `B1`, `B4` (reads persisted sessions), `B13` (consumes the same `AnalyzeResponse` shape).

#### Step B14.1 — JSON export
1. `GET /v1/session/{sessionId}/report?format=json` returns the raw persisted `AnalyzeResponse` + `ExecutionTrace` + `EvidenceLedger` as a single JSON document — this direction requires no new rendering logic, just a DB fetch and a `json.dumps`.

#### Step B14.2 — PDF export via HTML template
1. Create `services/report_service/template.html` (Jinja2), including: query text, answer, confidence badge + rationale, evidence images with overlays (embedded as `<img>` tags pointing to the `object_store` overlay PNGs from `B13.3`), and the full step-by-step execution trace table — per SPDD §9.6's explicit content-parity requirement.
2. Implement `services/report_service/render.py`: render the Jinja2 template with the session's data, then convert to PDF via `weasyprint.HTML(string=rendered_html).write_pdf(...)`.
3. Save the rendered PDF to `object_store` at `/{sessionId}/report.pdf` (per `B3.1`'s path convention) so repeat requests for the same session's report don't re-render from scratch — check `object_store.exists(...)` first.

#### Step B14.3 — Endpoint error handling
1. `404` if `session_exists(sessionId) == False` (per SPDD §9.3).
2. `409` if the session's `rejected == True` ("nothing to report," per SPDD §9.3) — do not attempt to render a report for a rejected session.

#### Step B14.4 — Content-parity test
1. Per SPDD §12.4/§16.4's manual checklist item ("the downloadable report matches the on-screen Results page exactly"): write an automated test that extracts the set of data fields rendered into the PDF template context and asserts it is a superset of (or exactly equal to) the fields the frontend's `Results.tsx` renders — this can be a simple field-name-list comparison test, not full visual diffing, to keep it maintainable.

---

### Module B15 — Registry Endpoint Finalization

**Domain:** Backend
**Purpose:** Replace `B2.4`'s hardcoded `GET /v1/registry` stub with the real, live precondition table from `B6.2`, plus actual adapter version strings from `M1`.
**Rationale:** SPDD §9.5 — used by both the frontend's capability-hint panel (`F2.3`) and integration tests asserting router/validator table sync.
**Dependencies:** `B6` (precondition table), `M1` (adapter version strings), `B2`.

#### Step B15.1 — Wire real data
1. Import `B6.2`'s `PRECONDITIONS` table directly (not a re-transcribed copy) into the registry route handler.
2. Fetch current adapter version strings from `M1`'s model-serving startup metadata (e.g., an `/adapters` introspection endpoint `M1` exposes, or a static read of `config.yaml`'s `adapter_versions` section, `B0.3`) — confirm with `M1` which source is authoritative and use only that one, to avoid two endpoints reporting inconsistent versions.

#### Step B15.2 — Integration test
1. Assert `GET /v1/registry`'s returned precondition blocks exactly match `B6.2`'s `PRECONDITIONS` table (this test would fail immediately if someone edits one copy without the other, catching the exact drift risk `B6.2` warns about).

---

### Module B16 — Backend Testing (Consolidated Unit & Integration Suite)

**Domain:** Backend
**Purpose:** Bring together the per-module unit tests into the full suite specified in SPDD §16.1–§16.2, plus the CI-enforced consistency checks.
**Rationale:** While individual modules write their own unit tests incrementally, SPDD §16.2's integration tests exercise the **whole** `/v1/analyze` pipeline end-to-end and can only be written once `B5`–`B13` are all wired together.
**Dependencies:** `B5`–`B15` all substantially complete.

#### Step B16.1 — Consolidate unit tests
1. Confirm every unit test enumerated in `B4.5`, `B6.5`, `B7.4`, `B8.6`, `B9.6`, `B10.5`, `B11.3`, `B12.4` is present under `tests/unit/`, organized one file per module (e.g., `tests/unit/test_compatibility_validator.py`).
2. Run `pytest tests/unit --cov=services` and confirm coverage is reported (no specific coverage percentage target is given in the source documents — ⚠️ **FLAGGED GAP**: the team should agree an explicit minimum, e.g., 80% for pure-logic modules like `B6`/`B7`/`B10`/`B11`, since none of the three source documents specifies one).

#### Step B16.2 — Integration test suite (per SPDD §16.2, verbatim scope)
Implement `tests/integration/test_analyze_e2e.py` with exactly these five scenarios, each as a full HTTP call against a running (or `TestClient`-mounted) `api_gateway`:
1. A clean single-image VQA pass — asserts `200`, `rejected: false`, non-null `answerText`, a 1-step trace.
2. A deliberately malformed pair — parametrized to trigger **each** rejection code in SPDD §14.1 at least once (mismatched format, missing modality, insufficient count, CRS mismatch, insufficient overlap, same-date temporal) — six sub-cases minimum.
3. An ambiguous-referent grounding case — asserts the response's evidence contains **multiple** boxes, not a top-1 collapse.
4. A quantity-type change-VQA case with an injected discrepancy (mock the change-VQA specialist to return a stated answer that contradicts `deterministicPixelCount`) — asserts final `confidence.tier == "Low"`.
5. A compound `fusion_then_change` request — asserts correct sequential specialist invocation order and that the trace contains exactly the expected step count for a 2-specialist sequential plan.

#### Step B16.3 — Router/schema consistency test
1. Complete the stub reserved in `B0.5`/`B7.2`: assert `TaskSpec.taskType`'s Pydantic `Literal` values exactly equal `ROUTING_TABLE`'s key set — run in CI on every push, failing the build on any drift.

#### Step B16.4 — Wire into CI
1. Update `.github/workflows/ci.yml` (from `B0.5`) to run `pytest tests/unit tests/integration` on every push, and fail the build on any failure — integration tests may need a lightweight `model_serving` mock/stub server spun up in the CI job rather than the real GPU-backed service (document this CI-only mock explicitly so it's never mistaken for real model behavior).

---

### Module B17 — Deployment Orchestration

**Domain:** Backend
**Purpose:** Finalize the real `docker-compose.yml` wiring, health-check dependencies, and startup sequencing per SPDD §15.
**Rationale:** This is the last backend module — it depends on every service actually existing and being independently runnable first.
**Dependencies:** All of `B2`–`B16`, plus `M1` (model_serving container), `F0`–`F9` (frontend container), `M0`/training artifacts (adapter weights must exist to be mounted).

#### Step B17.1 — Finalize container definitions
1. Replace `B0.4`'s stub `docker-compose.yml` entries with real build contexts/images per SPDD §15.1's table:
   - `frontend`: builds `frontend/`, serves via nginx or `vite preview`.
   - `api_gateway`: builds `services/api_gateway` + `services/orchestrator` co-located in one container/process (per SPDD §15.1's explicit hackathon-topology note).
   - `model_serving`: GPU-attached, builds `services/model_serving`, mounts `services/model_serving/adapters/` as a volume containing the trained LoRA weights from `M3`/`M4`/`M5`.
   - `metadata_db`: official `postgres` image (or bind-mounted SQLite path for the simplest local dev path, per SPDD §15.1).
   - `object_store`: bind-mounted local volume (or MinIO container if the team decided cloud-style storage is needed per `B3.1`'s flagged choice).
2. Confirm `report_service` remains a function call inside `api_gateway`'s process (no separate compose entry), per SPDD §15.1.

#### Step B17.2 — Environment/config wiring
1. Mount `config/config.yaml` and `.env` into every container that needs them; confirm no service hardcodes a URL that should come from `config.yaml` (audit every `B*` module's code for this before finalizing).

#! Sub-step B17.2.1
Specifically re-verify SPDD §15.2's explicit requirement: "All service URLs, adapter version pins, confidence thresholds, and validation thresholds MUST be externalized... not hard-coded" — grep the codebase for hardcoded values matching the thresholds named in `B0.3`'s config skeleton (e.g., `70`, `40`, `15`, `0.55`) outside of `config.yaml` and its loader, and refactor any hits.

#### Step B17.3 — Startup sequencing
1. Implement the exact three-step sequence from SPDD §15.3:
   1. `model_serving` loads the frozen backbone, then all three adapters + complementarity detector, exposing a readiness signal only once fully loaded.
   2. `api_gateway` waits on `model_serving`'s health check (poll `/v1/health`'s `model_serving`-reachability sub-check, wired into `B2.3`'s real implementation) before accepting traffic — implement via `docker-compose`'s `depends_on: condition: service_healthy` plus a Dockerfile `HEALTHCHECK`, not just container start-order.
   3. `metadata_db` schema migration (`alembic upgrade head`, from `B4.2`) runs idempotently before `api_gateway` starts accepting requests — implement as an entrypoint script step, not a manual pre-deploy action.

#### Step B17.4 — Full-stack smoke test
1. Run `docker compose up` from a clean checkout with no prior state; confirm no runtime external network dependency is triggered (per SPDD §13.5's offline-capability NFR) — monitor outbound connections during a full `/v1/analyze` request cycle and confirm none occur, aside from the explicitly-labeled, opt-in hosted-LLM fallback path (`M2`'s optional config) if and only if that flag is deliberately enabled.
2. Run through the full manual demo-readiness checklist from SPDD §16.4 against this running stack (all 6 checklist items) before considering `B17` — and the project's backend/deployment surface — complete.

---

## AI/ML

### Module M0 — Data Pipeline Setup

**Domain:** AI/ML
**Purpose:** Ingest and prepare BigEarthNet.txt (via reBEN) and the quality-filtering step, producing the single filtered training pool every adapter subsamples from.
**Rationale:** SPDD §11.1 — this MUST run once, upstream of all three adapters (`M3`, `M4`, `M5`).
**Dependencies:** None (can start in parallel with `B0`/`F0` — pure data-engineering work, no dependency on backend/frontend code). ⚠️ Note: needs actual GPU/compute + storage provisioning confirmed before large-scale runs (SPDD §17 item 1 — "actual available GPU compute... is not yet confirmed").

#### Step M0.1 — Environment setup
1. Create `training/requirements.txt` (separate from the backend's, per `B0.2`'s note about not bloating lightweight containers): `torch`, `transformers`, `peft`, `datasets`, `rasterio`, `rico-hdl` (or the equivalent reBEN conversion tool), `lmdb`, `safetensors`.
2. Provision a GPU-enabled dev environment (exact spec TBD per the flagged compute-availability risk — document whatever is actually available, e.g., "1x A100 40GB" or "1x consumer RTX-class GPU," since the training recipe's feasibility in SPDD §11.6 assumes "a single modern multi-GPU node" as a planning figure, not a guarantee).

#### Step M0.2 — Ingest BigEarthNet.txt via reBEN
1. Download/access BigEarthNet.txt per its arXiv-linked release (arXiv:2603.29630) and reBEN's practical download/storage layer (arXiv:2407.03653), per Proposal §8's dataset table.
2. Run `training/data_prep/reben_ingest.py` (SPDD §18's named file): converts raw BigEarthNet.txt pairs into an LMDB/safetensors store for high-throughput random-batch reads, per SPDD §11.1 step 1.
3. Respect the **official geographic (not naive grid) train/val/test split** explicitly, per SPDD §11.1 step 3 and Proposal §8's reBEN row — implement the split assignment as an explicit, logged step (which regions/tiles went to which split), not an implicit default, since this is called out as correcting a documented leakage bug in the original BigEarthNet split.

#### Step M0.3 — Quality-scoring filter (§11.1.1)
1. Implement `training/data_prep/score_rs_filter.py`.
2. **Preferred path:** train a small learned scorer on a manually-labeled sample of ~1–2K pairs (in the spirit of ScoreRS, arXiv:2503.00743).
3. **Fallback path (if scorer-training time is unavailable):** a heuristic proxy combining caption length + LULC-label count + no-data percentage threshold, exactly as SPDD §11.1.1 specifies as the fallback.
4. Whichever path is used, drop the bottom quartile of the (filtered pool's) quality ranking before any fine-tuning run.
5. **Mandatory logging:** log `pairs_in` and `pairs_kept` counts to a committed, versioned log file (e.g., `training/data_prep/logs/quality_filter_run_{date}.json`) — per SPDD §11.1.1's explicit "MUST be logged... so its effect is auditable in the technical write-up" requirement. Do not treat this as an optional nicety.

#### Step M0.4 — Fusion-bridging data acquisition
1. Acquire MM-OVSeg's CMU-Data (25,087 RGB-SAR pairs, SpaceNet6+DFC2023) per Proposal §8.
2. Acquire SOMA-1M (arXiv:2602.05480) per Proposal §8, weighted toward higher-resolution regimes for the Sentinel-vs-Cartosat/RISAT gap.
3. Store both under a clearly separate `training/data_prep/fusion_bridging/` directory (plan-introduced path) so they are never accidentally mixed into the primary BigEarthNet.txt-derived training pool used for the single-image adapters.

#### Step M0.5 — Domain-shift stress-test proxy sourcing
1. Attempt to source a small set of openly-licensed, Cartosat-2S/RISAT-*like* public samples (sub-metre optical + X/C-band SAR proxies), via NRSC/Bhoonidhi open data portals where accessible, per Proposal §8's table.
2. ⚠️ **FLAGGED RISK (carried forward verbatim from SPDD §17 item 4):** if no suitable public proxy data can be sourced in time, this MUST become a documented limitation in the technical write-up, not a silently-dropped feature. Track this explicitly as an open item with a hard go/no-go decision date, not left indefinitely open.

#### Step M0.6 — Data pipeline validation
1. Write a small validation script (`training/data_prep/validate_pipeline.py`, plan-introduced path) that loads a sample batch from the LMDB store and confirms: correct image/text pairing, correct modality labeling (S1 vs. S2), and correct train/val/test split assignment per `M0.2`'s geographic split — run this before any adapter training begins, since a silent data-pipeline bug here would invalidate every downstream adapter's results.

---

### Module M1 — Model Serving Infrastructure

**Domain:** AI/ML
**Purpose:** Build the shared-backbone + hot-swappable-LoRA-adapter serving engine that every specialist (and the query interpreter) runs on top of.
**Rationale:** SPDD §5.4 (adapter hot-swap contract) and §3.1 (the `model_serving` service). This is infrastructure that must exist (even with dummy/randomly-initialized adapters) before `B8`'s real specialist-invocation calls can be integration-tested against something real rather than a mock.
**Dependencies:** `M0` (for the eventual real adapters, though the serving *engine* itself can be built and tested with placeholder/untrained adapter weights first — do not block engine development on training completing).

#### Step M1.1 — Choose and pin the backbone
1. Select a compact open-weight VLM in the 1–4B range per Proposal §5.1 (e.g., InternVL3-1B-class or a small Qwen-VL variant) — ⚠️ **FLAGGED AMBIGUITY:** the Proposal explicitly gives examples ("e.g.") rather than a final pinned choice; the SPDD does not name a specific model either. **This must be finalized as a concrete decision (exact model name + revision/commit hash) before `M2`–`M5` can begin real training**, since the training recipe (frozen encoder + frozen decoder + LoRA on attention projections) is backbone-specific in its exact module names.
2. Document the final choice and rationale (non-monotonic-scaling finding from Proposal §5.1 — an 8B variant underperforming a 4B variant under fixed-rank LoRA — is the cited justification for staying small) in `docs/model_choice_rationale.md` (plan-introduced path).

#### Step M1.2 — Serving engine skeleton
1. Implement `services/model_serving/serve.py` using `vLLM` or HF `transformers` (per SPDD §18's file comment "`vLLM`/HF endpoint, adapter hot-swap") — expose a single parameterized inference endpoint per the contract agreed with `B8.1`: `POST /infer {adapterId, taskToken, images, prompt}`.
2. Implement adapter hot-swapping: load the frozen backbone once at startup; keep all LoRA deltas resident in memory simultaneously (target <50MB per adapter at rank 8–16, per SPDD §5.4); merge/apply only the requested adapter's delta per forward pass — this is a **hard NFR**, not an optimization, because compound sequential queries call two specialists per request and cannot tolerate a full reload between them (SPDD §5.4).
3. Implement a `/health` sub-endpoint the `api_gateway`'s `GET /v1/health` (`B2.3`) polls, reporting `ready: true` only once the backbone + all adapters + complementarity detector are loaded (per SPDD §15.3 step 1).
4. Implement an `/adapters` introspection endpoint returning currently-loaded adapter IDs/versions (consumed by `B15.1`).

#### Step M1.3 — Task-token conditioning
1. Implement the shared task-conditioning convention from SPDD §11.5: prepend the explicit task token (`[vqa]`, `[caption]`, `[ground]`, `[change]`, `[fusion]`) to every instruction, in addition to the adapter selection — implement this as a shared utility function called by every specialist's inference-request construction, so the convention can't drift per-specialist.
2. Expose this pairing (adapter ID + task token) as a structural cross-check hook for `B10`'s verifier (per SPDD §11.5's note that this is "two redundant, cross-checkable signals... the verifier_node can use to detect an adapter/prompt mismatch") — document the exposed field name/location so `B10` can actually consume it.

#### Step M1.4 — Governance/offline default
1. Implement `M2`'s query interpreter's LLM call path to run fully self-hosted by default (per SPDD §13.4/Proposal §4.2's governance table row) — the hosted-LLM-API fallback (if implemented at all) MUST be a separate, explicitly-labeled, opt-in code path that NEVER applies to any component touching image bytes, and MUST default to off.

#### Step M1.5 — Testing
1. Load-test the hot-swap mechanism with a synthetic sequential two-adapter call sequence (simulating a `fusion_then_change` compound plan) and confirm no full-backbone reload occurs between calls (verify via timing — a reload would show a large latency spike on the second call).
2. Confirm the `/infer` endpoint's request/response shape exactly matches the contract documented in `docs/interfaces/model_serving.md` (from `B8.1`) — a contract-conformance test, run in CI if feasible without requiring a GPU (e.g., against a CPU-mode stub model for CI purposes only).

---

### Module M2 — Query Interpreter Model

**Domain:** AI/ML
**Purpose:** The small, text-only instruct LLM that converts natural-language queries into structured `TaskSpec` JSON.
**Rationale:** SPDD §4.1 — orchestration entry point.
**Dependencies:** `M1` (serving infrastructure, text-only endpoint variant). Does not depend on `M0`'s vision-training pipeline (this is a text-only model, potentially usable off-the-shelf with prompting alone rather than fine-tuning — confirm this design choice explicitly, see flag below).

#### Step M2.1 — Model selection
1. ⚠️ **FLAGGED AMBIGUITY:** SPDD §4.1 says "a small, text-only instruct LLM... called in structured function-calling / JSON-mode" but does not specify whether this model is fine-tuned at all, or used purely via few-shot prompting of an off-the-shelf small instruct model. Proposal §5.4 step 1 similarly just says "a small, text-only instruct LLM." **Resolve explicitly**: this plan recommends starting with pure few-shot prompting of an off-the-shelf small instruct model (e.g., a 1–3B instruct model, served via `vLLM`/Ollama per Proposal §6's pipeline table) and only considering fine-tuning it if few-shot accuracy on the representative-query taxonomy proves insufficient during `M2.4`'s evaluation — since neither source document mandates fine-tuning this specific component (the PS's mandatory-adaptation requirement is about the *vision-language* components, not the text-only router).

#### Step M2.2 — JSON-mode / function-calling constraint
1. Configure the serving call to constrain output to the `TaskSpec` JSON Schema (`B1.1`'s Pydantic schema, exported as JSON Schema via `TaskSpec.model_json_schema()`) using the serving engine's structured-output/JSON-mode feature (e.g., vLLM's guided decoding, or a grammar-constrained decoding library) — this is what makes emitting an out-of-enum `taskType` structurally impossible, per SPDD §4.1's stated design rationale, rather than relying on the model simply "trying to" follow instructions.

#### Step M2.3 — Few-shot exemplar set
1. Compose the few-shot prompt using, verbatim, the PS's own 5 "Representative Queries" examples (exact `taskType` labels assigned by the team, matching them to the 8-value enum).
2. Add 10–15 additional hand-written exemplars covering ambiguous phrasing (per SPDD §4.1) — specifically include at least one example each for: a compound query (`fusion_then_change`, `change_and_grounding`), a genuinely ambiguous query that SHOULD trigger `status: "ambiguous"` (intentionally low-confidence-worthy phrasing), and the counting/ratio-type queries relevant to `B11`'s Rule 3 weak-point tagging (`queryWeakPointCategory`, per the gap flagged in `B11.1`).
3. Include the `intentConfidence` self-reporting instruction explicitly in the prompt template, and the `0.55` threshold logic (SPDD §4.1) — note the threshold *check* itself lives in backend code (`B5.2`), but the model must be prompted to actually emit a meaningful, calibrated `intentConfidence` value in the first place for that check to be worth anything.

#### Step M2.4 — Evaluation
1. Build a small held-out test set (30–50 hand-written queries spanning all 8 `taskType` values plus a few genuinely ambiguous ones) and measure `taskType` classification accuracy + calibration of `intentConfidence` (does a query the team judges "clearly ambiguous" actually score below 0.55?).
2. If accuracy is materially poor (no numeric target given in source documents — ⚠️ **FLAGGED GAP**: team must set one, e.g., ">90% taskType accuracy on the held-out set" as a working bar), revisit `M2.1`'s decision and consider light fine-tuning (e.g., LoRA on this same small model, using a larger synthetically-generated query→TaskSpec dataset) as a fallback.

---

### Module M3 — VQA + Captioning Adapter (`adapter_vqa_caption`)

**Domain:** AI/ML
**Purpose:** Train the jointly-trained LoRA adapter for single-image VQA and captioning.
**Rationale:** SPDD §11.2, Proposal §5.1 — mandatory PS baseline requirement.
**Dependencies:** `M0` (filtered training data), `M1` (backbone chosen and serving skeleton exists to load the trained checkpoint into).

#### Step M3.1 — Data preparation
1. Extract BigEarthNet.txt's captioning + binary/MCQ VQA annotations from `M0`'s filtered, split training pool.
2. Confirm the structured-output requirement flagged in `B9.1`/`B9.2` (LULC class-presence list needed for fusion's sub-step 1) is factored into this adapter's training data/prompting — i.e., decide and implement whether this adapter is trained to *also* emit a structured side-channel output (e.g., a parseable `[LULC: water(0.9), built-up(0.4)...]` tag appended to its free-text answer) or whether fusion's structured extraction is a separate downstream parsing step over this adapter's plain free-text answer. This decision directly resolves the gap flagged in `B9.1` and MUST be made by this module (or jointly with `B9`) before fusion pipeline integration testing can proceed.

#### Step M3.2 — Model architecture
1. Freeze the vision encoder and base LLM (per `M1.1`'s chosen backbone).
2. Add small modality-specific linear projection layers for S1 (SAR) and S2 (multispectral) tokens, per Proposal §5.1/SPDD §11.2 — implement as a thin projection module inserted between the frozen encoder's output and the frozen decoder's input, trainable.
3. Apply LoRA (rank 8–16) only to the LLM's attention Q/K/V/O projections, per SPDD §11.2 — do not apply LoRA to the vision encoder (kept fully frozen).

#### Step M3.3 — Training run
1. Loss: autoregressive cross-entropy over the answer/caption token sequence, per SPDD §11.2.
2. Task conditioning: prepend `[vqa]` or `[caption]` task tokens per `M1.3`'s shared convention.
3. Closed-set constraint: for questions matching RSVQA's known question types, implement decoding-time vocabulary constraint (yes/no, land-cover class names) when tagged closed-set by the interpreter (SPDD §5.1's notes) — this is a decode-time behavior of the served model, so coordinate with `M1.2`'s serving code for how this constraint is actually applied (e.g., vLLM guided-decoding grammar restricted to the closed vocabulary).
4. Budget: ~1–2 GPU-days per adapter (planning figure, SPDD §11.6) — log actual wall-clock time and revise the plan if materially different, per the `M0`/SPDD §17 item 1 flagged compute risk.

#### Step M3.4 — Evaluation
1. Evaluate on VRSBench (captioning/grounding/VQA — grounding portion not applicable to this adapter, handled by `M4`) and RSVQA (closed-set VQA cross-check), held out and never trained on, per SPDD §11.2/§16.3.
2. Run the fine-tuning delta ablation (un-adapted backbone vs. this LoRA-adapted version) required by SPDD §16.3 — this is "the single most judge-legible proof that the mandatory adaptation requirement is genuinely met" and MUST be reproducible via a committed script (`eval/run_finetune_delta_ablation.py`, SPDD §18), not a one-off notebook run.
3. Apply the quality-filtering effect logged in `M0.3` — confirm the filtered-data model's accuracy is reported alongside (not instead of) an unfiltered-baseline comparison if time allows, to substantiate the ScoreRS-motivated claim in Proposal §5.1.

---

### Module M4 — Grounding Adapter (`adapter_grounding`)

**Domain:** AI/ML
**Purpose:** Train the separately-tuned LoRA adapter for text-guided region grounding.
**Rationale:** SPDD §11.2, Proposal §5.1's explicit task-interference rationale for NOT joint-training this with VQA/captioning.
**Dependencies:** `M0`, `M1`. Independent of `M3` (separate adapter, separate training run — can run in parallel on a second GPU if available).

#### Step M4.1 — Data preparation
1. Extract BigEarthNet.txt's referring-expression annotations from `M0`'s filtered pool, applying the same quality filter (§11.1.1) as `M3`.

#### Step M4.2 — Output format
1. Cast bounding-box regression as sequence generation: tokenize boxes as `{xLeft,yTop,xRight,yBottom|theta}` strings, per SPDD §11.2 — this keeps the output head identical in kind to the other specialists (text generation), avoiding a separate detection head, per the explicit design rationale.

#### Step M4.3 — Training run
1. Same frozen-backbone + LoRA (rank 8–16, attention projections only) recipe as `M3`, but as a fully separate adapter (`adapter_grounding`), trained independently — never merged or jointly optimized with `adapter_vqa_caption`, per the explicit task-interference avoidance rationale (Proposal §5.1, citing RS-LLaVA's documented multi-task collapse).
2. Task token: `[ground]`.
3. Loss: cross-entropy over the tokenized box-string sequence, per SPDD §11.2.

#### Step M4.4 — Multi-candidate / ambiguity behavior
1. Implement the mandatory multi-box output behavior from SPDD §5.2: when the model's decoding produces multiple above-threshold candidate regions for a referring expression, the specialist's serving wrapper (in `M1`/serve.py, or a thin post-processing layer specific to this adapter) MUST return **all** plausible boxes with per-box scores, never silently collapsing to top-1. Define the "above-threshold" cutoff explicitly (e.g., a fixed score threshold or top-K with K configurable) and document the choice — this behavior is described in the SPDD as a hard requirement but the exact threshold value is left to implementation; document whatever value is chosen in `config.yaml` (`grounding.candidate_score_threshold`) so it is externalized per `B17.2`'s NFR, not hardcoded in model code.

#### Step M4.5 — Evaluation
1. Evaluate on VRSBench's grounding split. Report Acc@0.5 and, per Proposal §5.1's cited literature (best-in-class fine-tuned GeoChat reaches ~49.8% Acc@0.5, non-unique referents ~44.5%), do NOT present this as a uniformly reliable capability in the technical write-up or demo — always pair a grounding result with its confidence badge in any demo material, per Proposal §10's explicit risk note ("Grounding is the hardest single-image task... it must be shown alongside its confidence score, never presented as uniformly reliable").
2. Run the fine-tuning delta ablation, same as `M3.4` step 2.

---

### Module M5 — Change-VQA Adapter (`adapter_change_vqa`)

**Domain:** AI/ML
**Purpose:** Train the third, separately-tuned adapter for bi-temporal change reasoning, including the Change-Enhancing Module (CEM).
**Rationale:** SPDD §11.3, Proposal §5.2 — mandatory multitemporal change-analysis requirement.
**Dependencies:** `M0` (this adapter trains on CDVQA, a **separate** dataset from BigEarthNet.txt — confirm CDVQA ingestion is added to `M0`'s data pipeline, or handled as this module's own ingestion step if `M0` scoped only BigEarthNet.txt proper), `M1`.

#### Step M5.1 — CDVQA data ingestion
1. If not already handled by `M0`, implement ingestion of CDVQA (from SECOND, arXiv:2112.06343) here: official train/val/test1/test2 splits, per SPDD §11.3 — 2,968 pairs, >122K QA pairs per Proposal §8.
2. Retain `test2` (the harder, distribution-shifted split) as the **honest reporting split** — do not cherry-pick `test1` for headline numbers, per SPDD §11.3's explicit instruction.

#### Step M5.2 — Change-Enhancing Module architecture
1. Implement Siamese-encoded T1/T2 feature extraction (shared frozen vision encoder run twice, once per timestamp).
2. Implement difference-attention combination of the two feature sets (NOT naive subtraction) — per SPDD §11.3 and CDVQA's own ablation showing this lifts average accuracy (0.5766→0.6008, per Proposal §5.2).
3. Optimize the CEM jointly, end-to-end, with the LoRA-adapted decoder — no separate auxiliary loss term, per SPDD §11.3.

#### Step M5.3 — Training run
1. Loss: cross-entropy over the answer sequence, per SPDD §11.3.
2. Task token: `[change]`.
3. LoRA rank 8–16 on attention projections, same recipe family as `M3`/`M4`, applied on top of the CEM-augmented architecture.

#### Step M5.4 — Deterministic quantity output (mandatory, not optional)
1. Whenever the query is tagged quantity/ratio-type (by `M2`'s interpreter, surfaced via `TaskSpec`), this adapter's inference wrapper MUST also compute a deterministic pixel/instance count from its internal change-attention map (when a mask is produced) and populate `deterministicPixelCount` + `quantityFlag = true` in its output — per SPDD §5.3's explicit "mandatory, not optional" instruction. Implement this as a post-processing step on the CEM's attention map (e.g., thresholding + connected-component counting), separate from the free-text answer generation, so the two signals are genuinely independent (this independence is what makes the downstream `B10.3` cross-check meaningful — if the count were derived FROM the text answer, the check would be circular).

#### Step M5.5 — Evaluation
1. Evaluate on CDVQA's official metrics: per-question-type accuracy + Average/Overall Accuracy, per SPDD §11.3 — **report split by question category** (not averaged away) specifically to expose the known counting/ratio weak point, per SPDD §11.3's explicit instruction. This is a reporting requirement, not just a training nicety — ensure the eval script (`eval/run_cdvqa_eval.py`, SPDD §18) outputs a per-category breakdown table, not a single scalar.
2. Cross-reference against the field-wide documented weak point (30–60% accuracy on counting/ratio/smallest-change vs. 80–85% on binary/directional, per Proposal §5.2/§10) — confirm this adapter's own numbers are reported honestly against this expectation, not silently omitted if they land in the expected weak range.
3. Run the fine-tuning delta ablation, same pattern as `M3.4`/`M4.5`.

---

### Module M6 — Domain-Gap Mitigation Pipeline

**Domain:** AI/ML
**Purpose:** Implement the Sentinel→Cartosat/RISAT domain-gap augmentation and normalization pipeline, applied uniformly across all specialists as a preprocessing stage.
**Rationale:** Proposal §5.3/§4.2's central engineering concern — the single largest, most PS-specific technical risk. SPDD §11.4.
**Dependencies:** `M0` (needs training data statistics — Sentinel-2's response curve — to compute what to normalize toward/from), independent of `M3`/`M4`/`M5`'s training runs themselves (this module produces a *preprocessing function*, callable both at training time for the stress-test ablation and at inference time via `B9.4`'s hook).

#### Step M6.1 — GSD-normalization tiling
1. Implement `training/domain_gap_augmentation.py`'s tiling function: given an input image's actual GSD (meters/pixel, from `ImageMetadata.gsdMeters`) and a target reference GSD (Sentinel-2's, since that's the training distribution), resample tiles to a consistent effective resolution before specialist inference — this directly addresses the documented 5–30× resolution jump between Sentinel-2 (10–60m) and Cartosat-2S (0.65–2m), per Proposal §5.3/§3.

#### Step M6.2 — Radiometric-jitter augmentation
1. Implement histogram matching toward Cartosat-2S's response curve (for optical/multispectral inputs) and speckle-noise injection matching RISAT's SAR characteristics — per SPDD §11.4. Requires having representative response-curve/speckle statistics for Cartosat-2S/RISAT; source these from public sensor specification documents (not the withheld ISRO/SAC evaluation data itself) — document exactly which public source is used for these statistics, since this is a load-bearing technical detail for the write-up's honesty about the mitigation's basis.

#### Step M6.3 — Held-out stress-test application
1. Apply `M6.1`+`M6.2` to a held-out training slice, used **purely for a robustness stress-test ablation**, never mixed into headline-accuracy training/eval data, per SPDD §11.4's explicit instruction.
2. Run each of `M3`/`M4`/`M5`'s trained adapters against this stress-test slice (before vs. after normalization) and report the delta honestly in a dedicated ablation report — this is Proposal §9's "realistic stretch goal" item ("a documented, honestly-reported domain-shift stress test... showing before/after the normalization stage").

#### Step M6.4 — Inference-time hook
1. Expose `M6.1`+`M6.2` as a single callable preprocessing function (`normalize_for_domain_gap(image, source_gsd, source_sensor_type) -> normalized_image`) that `B9.4` (and, per that module's flagged question, potentially all of `B8`'s specialist calls) invokes before every real inference call — not just for the domain-shift stress test, but as an always-on inference-time normalization step, since Cartosat/RISAT-class imagery is exactly what the real ISRO/SAC evaluation set contains.

##### Sub-step M6.4.1
Confirm with the Backend team (resolving `B9.4`'s flagged question) whether this hook is invoked once centrally in `B8`'s common specialist-call entry point, or per-pipeline (fusion only) — this is a joint Backend/AI-ML decision; document the resolution in `docs/interfaces/domain_gap_hook.md` (plan-introduced path).

#### Step M6.5 — Domain-shift proxy stress test using `M0.5`'s sourced data
1. If `M0.5` successfully sourced Cartosat-2S/RISAT-*like* public proxy samples, run the same before/after comparison from `M6.3` against these more realistic proxies (rather than only a held-out Sentinel slice) — this is the more convincing version of the ablation, if the data-sourcing risk (flagged in `M0.5`) resolves favorably.

---

### Module M7 — Complementarity Detector

**Domain:** AI/ML
**Purpose:** Train the small classifier that tags per-LULC-region agreement/disagreement between optical and SAR structured evidence, using MM-OVSeg's InfoNCE alignment recipe.
**Rationale:** SPDD §6 sub-step 2, Proposal §5.3 — this is flagged (SPDD §17 item 2) as "the single highest-risk deliverable" in the entire system.
**Dependencies:** `M0.4` (fusion-bridging data: MM-OVSeg's CMU-Data + SOMA-1M), `M1` (serving infra for the lightweight endpoint).

#### Step M7.1 — Architecture
1. Implement a dense-feature encoder pair — SAR-DINO and RGB-DINO encoders — per MM-OVSeg's CMU (Cross-Modal Unification) recipe, per Proposal §2.1/§5.3. This is explicitly NOT the LLM decoder; it is a separate, small model served as its own endpoint (SPDD §6).
2. Train using an InfoNCE contrastive alignment objective between the two encoders' dense features, on BigEarthNet.txt's paired S1/S2 labels **plus** the CMU-Data (25,087 pairs) and SOMA-1M pools from `M0.4` — per SPDD §6/Proposal §5.3, weighting SOMA-1M toward higher-resolution regimes to better match the Sentinel-vs-Cartosat/RISAT gap.

#### Step M7.2 — Output contract
1. Given two structured evidence sets (from `B9.1`, resolved per that module's flagged structured-output-format question — this module's output tagging logic depends on that format being finalized first), produce per-LULC-region tags (`agreement`/`optical_only`/`sar_only`) with numeric agreement scores, per SPDD §6's output contract.

#### Step M7.3 — Serving
1. Expose as its own lightweight endpoint in `services/model_serving` (per SPDD §18's directory note and §6's "served as its own lightweight endpoint" instruction) — separate from the main `/infer` LLM endpoint, since this is a dense-feature classifier, not a generative decoder call.

#### Step M7.4 — Risk mitigation: config-flag fallback readiness
1. Per SPDD §17 item 2's explicit instruction: if this detector's contrastive-alignment training is not ready in time, the rule-based fallback (already specified in `B9.2`) MUST be used and **clearly labeled as such** in the demo and write-up — never silently presented as the trained version. This module's team should communicate a go/no-go status to the Backend team early (not at the last minute) so `B9.2`'s config flag is flipped deliberately, with time to verify the fallback path end-to-end, rather than discovered as broken during demo prep.

#### Step M7.5 — Evaluation
1. Report mIoU (or an equivalent agreement-tagging accuracy metric) against MM-OVSeg's own published ablation numbers as a sanity check (MM-OVSeg's own ablation: 73.1% mIoU for InfoNCE vs. 67.7%/69.0% for MSE/L1 alternatives, per Proposal §4.2's table) — this module's own trained detector's numbers should be reported as "self-reported... not directly comparable to a published baseline" per Proposal §10's explicit honesty framing (no existing baseline exists for this exact structured-fusion formulation), not overstated as matching MM-OVSeg's segmentation-task numbers directly (different task).

---

### Module M8 — Fusion Pipeline Model Composition

**Domain:** AI/ML
**Purpose:** The AI/ML-side responsibilities within the fusion pipeline: ensuring `adapter_vqa_caption` (from `M3`) can genuinely serve sub-step 1's structured-extraction need, and providing/tuning the verbalizer prompt template for sub-step 3.
**Rationale:** Complements `B9`'s backend orchestration — this module owns the model-facing prompt engineering and output-format guarantees the fusion pipeline depends on.
**Dependencies:** `M3` (must resolve the structured-output question raised there), `M7` (complementarity detector's tag output format).

#### Step M8.1 — Resolve structured-extraction format (joint with `M3.1`/`B9.1`)
1. Finalize whether `adapter_vqa_caption` emits a structured side-channel (e.g., an appended, parseable tag block) or whether a separate lightweight parsing step extracts structure from its free-text answer — implement whichever was decided in `M3.1`, and validate it end-to-end here specifically for the fusion use case (structured LULC class presence + area share + grounded regions).
2. Write a small conformance test: given a known optical image with known ground-truth LULC composition, assert the structured extraction produces a class-presence list matching expectations within a reasonable tolerance.

#### Step M8.2 — Verbalizer prompt template
1. Design the prompt template used by `B9.3`'s verbalizer call: given the tagged, structured comparison (region → tag → score list) and the original user query, produce natural language that explicitly cites which modality supplied which claim — per SPDD §6 sub-step 3's explicit requirement and the worked example ("SAR imagery reveals a water body in the north-east quadrant not visible in the optical scene, consistent with cloud cover there").
2. Explicitly enforce (via the prompt, and spot-checked manually) that the template never asks the model to reason over raw pixels — it must only ever see the structured, already-tagged evidence, per SPDD §6's "MUST NOT be given raw pixels" requirement (this is a prompt-engineering and integration-testing responsibility shared with `B9.3`'s payload-construction code — confirm both sides enforce the same constraint).

#### Step M8.3 — Fusion-pipeline end-to-end evaluation
1. Since no existing benchmark directly tests this exact structured-fusion formulation (Proposal §10's explicit acknowledgment), construct a small internal evaluation set: a handful of manually-curated optical-SAR pairs with hand-labeled "what should the fusion answer say" reference text, and score the pipeline's actual output against it via a simple rubric (does it correctly identify agreement/disagreement regions; does it correctly attribute claims to the right modality) — document this as a self-constructed, non-standard eval, per the Proposal's own honesty framing, not presented as a standard benchmark score.

---

### Module M9 — Modality/Format Detection Heuristic

**Domain:** AI/ML
**Purpose:** The lightweight heuristic classifier `B6.3`'s validator falls back on for ambiguous optical-vs-multispectral-vs-SAR classification.
**Rationale:** SPDD §4.2 step 2 explicitly calls for "a lightweight heuristic classifier (not a full specialist model) trained on BigEarthNet.txt's own modality labels."
**Dependencies:** `M0` (BigEarthNet.txt's modality labels). Small, independent module — can be built quickly in parallel with the larger adapter-training modules.

#### Step M9.1 — Feature engineering
1. Extract simple, fast features from raw image bytes/headers: band count, band wavelength metadata (if present), pixel-value distribution statistics (SAR imagery typically has a distinctive speckle/backscatter statistical signature vs. optical reflectance) — this is deliberately NOT a deep-learning model, per the SPDD's explicit "not a full specialist model" instruction.

#### Step M9.2 — Train a simple classifier
1. Train a small, fast classifier (e.g., logistic regression or a shallow gradient-boosted tree, not a neural network) on BigEarthNet.txt's own labeled modality ground truth (S1=SAR, S2=optical/multispectral), using the features from `M9.1`.
2. Confirm inference latency is negligible (sub-100ms) since this runs synchronously inside `B6.3`'s validation step, which must stay well within its share of the overall latency budget (SPDD §13.1).

#### Step M9.3 — Serving
1. Expose as a lightweight, CPU-only endpoint (does not need GPU-attached `model_serving` — could run directly inside `api_gateway`'s process, or as a tiny separate service; confirm with Backend team which is simpler for the hackathon topology) — this is explicitly a cheap heuristic, not warranting the same infrastructure as the LLM specialists.

#### Step M9.4 — Evaluation
1. Report classification accuracy on a held-out BigEarthNet.txt modality-labeled sample; this does not need to be perfect (it is a fallback for genuinely ambiguous cases only, per SPDD §4.2 — most cases are resolved by explicit metadata tags before this heuristic is ever invoked).

---

### Module M10 — Model Evaluation Harness & Fine-Tune Delta Ablation

**Domain:** AI/ML
**Purpose:** Consolidate the individual adapters' evaluation scripts (`M3.4`, `M4.5`, `M5.5`) into the single, scheduled, reproducible offline harness specified in SPDD §16.3.
**Rationale:** SPDD §16.3 explicitly requires this to be "run as a scheduled offline script, with results logged... not just eyeballed" and calls the fine-tuning delta ablation "the single most judge-legible proof" of meeting the mandatory adaptation requirement.
**Dependencies:** `M3`, `M4`, `M5` (adapters must exist to be evaluated), `M0` (benchmark data: VRSBench, RSVQA, CDVQA — held out, never trained on).

#### Step M10.1 — Consolidate per-adapter eval scripts
1. Ensure `eval/run_vrsbench_eval.py`, `eval/run_rsvqa_eval.py`, `eval/run_cdvqa_eval.py` (SPDD §18's named files) each wrap the evaluation logic already built incrementally in `M3.4`, `M4.5`, `M5.5` respectively, callable independently or via a single top-level harness runner.

#### Step M10.2 — Fine-tuning delta ablation script
1. Implement `eval/run_finetune_delta_ablation.py` (SPDD §18) to run each benchmark twice per adapter — once against the frozen, un-adapted backbone (LoRA disabled) and once with the trained adapter applied — and produce a single delta table (metric before vs. after, per benchmark, per adapter).
2. This script MUST be committed and re-runnable on demand (per SPDD §16.3's explicit "reproducible from a committed script, not a one-off notebook run" requirement) — do not hand-produce this table once and hardcode it into a report.

#### Step M10.3 — Results logging
1. Persist every harness run's output (not just console-printed) to a versioned results directory (e.g., `eval/results/{run_date}/`, plan-introduced path) as structured JSON/CSV, so the technical write-up's numbers can always be traced back to a specific committed run.

#### Step M10.4 — Cross-check against literature-cited baselines
1. Where the Proposal cites specific comparable numbers (e.g., GeoChat's Acc@0.5 for grounding, CDVQA's naive-subtraction-vs-CEM delta), include those cited numbers alongside this project's own results in the same table for direct, honest comparison — per the Proposal §2.1's emphasis on verified, not asserted, technical claims.

---

### Module M11 — Decoupled Perception/Reasoning Confidence (Stretch Goal)

**Domain:** AI/ML
**Purpose:** Implement the VL-Calibration-style decoupled confidence tokens, if time allows after the MVP path (SPDD §7.2's rules 1–3, 5) is working and demo-ready.
**Rationale:** SPDD §7.2.1 — explicitly a stretch goal; the MVP confidence path MUST work standalone regardless of whether this lands (per SPDD §17 item 3).
**Dependencies:** `M3`, `M4`, `M5` (this is an additional training/calibration pass on top of already-trained adapters, not a prerequisite for them), `B11` (must confirm the exact field names/shape this module's output needs to populate for Rule 4 to consume it).

#### Step M11.1 — Confirm this is being attempted
1. This module is explicitly conditional per SPDD §9's feasibility tiering ("attempt if the core MVP lands early"). Before starting any work here, confirm with the team that `M0`–`M10` and the corresponding Backend/Frontend modules are demo-ready first — do not begin `M11` at the expense of MVP-path completeness or testing time.

#### Step M11.2 — Implement decoupled confidence-token prompting
1. Prompt each specialist to emit two separate confidence signals: one for "did I correctly perceive the relevant visual evidence" (perception confidence) and one for "did I correctly reason from that evidence to the answer" (reasoning confidence), per the VL-Calibration pattern (Proposal §2.1/§5.5).

#### Step M11.3 — Calibration
1. Fit a simple isotonic or Platt-scaling calibration model per confidence signal, using a held-out validation slice (explicitly NOT the test split, per SPDD §7.2.1) — this calibration model maps the raw emitted confidence token to a calibrated probability the downstream threshold check (`B11`'s Rule 4) can meaningfully compare against a threshold.

#### Step M11.4 — Integration with `B11`
1. Publish the exact output field names/shape (e.g., `perceptionConfidence: float`, `reasoningConfidence: float`, plus the calibration thresholds themselves) to the Backend team so `B11.2`'s Rule 4 precondition check has something concrete to test against — this must be documented in `docs/interfaces/confidence_tokens.md` (plan-introduced path) before `B11`'s Rule 4 can move from its documented fallback-only behavior to an actually-functioning high-confidence path.

#### Step M11.5 — Evaluation
1. Reproduce (at whatever scale is feasible) the calibration-error reduction check from the VL-Calibration paper (Proposal §2.1 cites a ~4× ECE reduction, 0.421→0.098) — report this project's own measured ECE before/after decoupling, honestly, without assuming the published paper's exact numbers transfer to this project's smaller/different backbone.

---

## Appendix — Consolidated List of Flagged Ambiguities & Gaps

For quick reference, every ⚠️ flag raised above, in one place, so the team can triage and resolve them as a batch before/during the build rather than discovering them piecemeal:

1. **Leaflet vs. deck.gl** — undecided in source docs; this plan assumes Leaflet (`F0.1`).
2. **`clarifyingQuestion` contract gap** — `TaskSpec.clarifyingQuestion` exists but `AnalyzeResponse` doesn't expose it in the SPDD's literal schema; this plan adds it to `AnalyzeResponse` (`B1.2`, surfaced in `F6.3`).
3. **`AnalyzeResponse` lacks georeference/CRS info** the frontend needs to decide map-vs-plain-image rendering (`F7.1`).
4. **Python version / exact library versions** unpinned in source docs (`B0.2`).
5. **`interpretation_failed` error's place in the error taxonomy** is unclear — not in §14.1's rejection table nor cleanly in §14.2's runtime-failure section (`B5.2`).
6. **Object store backend** (local filesystem vs. S3/MinIO) left conditional on availability (`B3.1`).
7. **`cloudMaskPercent` computation method** unspecified (`B6.1`).
8. **Cross-tool agreement-check algorithm/threshold** (SPDD §7.1 item 2) described narratively, no exact formula given (`B10.2`).
9. **`queryWeakPointCategory` tagging** — SPDD §7.2 Rule 3 assumes query-type tagging exists but never assigns which component sets it (`B11.1`, resolved by adding a field on `M2`'s `TaskSpec` output).
10. **Rule 3 vs. Rule 4 evaluation order** (look-ahead discount vs. post-hoc) needs an explicit test to lock down the intended semantics (`B11.3`).
11. **Server-side overlay-rendering component ownership** not explicitly assigned in the SPDD; this plan assigns it to `B13.3`.
12. **Structured-output format for fusion sub-step 1** — `vqa_caption_specialist`'s documented output contract doesn't include the LULC-class-presence structure fusion needs; must be resolved jointly by `M3.1`/`M8.1`/`B9.1` before fusion integration testing.
13. **Domain-gap normalization hook scope** — fusion-only vs. all-specialists; SPDD §6 implies "uniform," `B9.4`/`M6.4.1` must confirm the actual call-site placement.
14. **Frontend test tooling/coverage target** — not specified in any source document; this plan assumes Vitest + RTL (`F9`).
15. **Backend unit-test coverage target** — no percentage specified in source docs (`B16.1`).
16. **Backbone model exact choice** — Proposal gives examples only, not a final pin; must be locked before `M2`–`M5` training starts (`M1.1`).
17. **Query Interpreter fine-tuned vs. prompted-only** — not specified; this plan recommends starting prompted-only (`M2.1`).
18. **`M2` accuracy target** — no numeric bar given; team must set one (`M2.4`).
19. **Domain-shift proxy data availability** — genuinely uncertain; carried forward from SPDD §17 item 4 as an open risk (`M0.5`).
20. **Compute budget (GPU-days/hardware)** — unconfirmed planning assumption; carried forward from SPDD §17 item 1 (`M0.1`, `M3.3`).
21. **Modality-heuristic (`M9`) serving location** — CPU-inline vs. separate service, left to team convenience (`M9.3`).
22. **Complementarity detector (`M7`) readiness** — the single highest-risk deliverable per SPDD §17 item 2; needs an explicit go/no-go communicated early to `B9.2`'s fallback switch (`M7.4`).
23. **Concurrency target (3 simultaneous requests)** — stated as untested in SPDD §17 item 6; must be load-tested against real hardware before the live demo (`B17.4`).
24. **Auth/session model** — intentionally minimal per SPDD §17 item 5; full RBAC explicitly deferred, noted here so no module accidentally over-builds it.
