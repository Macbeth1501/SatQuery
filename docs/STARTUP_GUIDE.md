# SatQuery AI — Startup Guide and Demo Test Plan

How to start the stack, drive the demo in front of someone, and manually test it. Written against the state
recorded in `docs/PROGRESS_LOG.md` (Phases 0-8 done, dummy specialists, no model in the running system).

## 1. What you are showing (say this first)

- The **pipeline is real end to end**: query interpretation, structural validation, routing, verification, overlays,
  confidence scoring, execution trace, SQLite persistence, JSON/HTML/PDF reports.
- The **specialists are deterministic dummies** (`ScenarioEngine`, five hardcoded scenarios). There is no model and
  no LLM behind the answers. This is deliberate (Development Plan section 2.5).
- The demo therefore shows the **architecture and its contracts** (validation before execution, evidence ledger,
  confidence tiers, first-class rejection), not a trained model's accuracy. A trained adapter exists in `data/`
  but is not wired in, and it has not been shown to read imagery.

## 2. Prerequisites

| Need | Check |
|---|---|
| Python 3 | `python --version` |
| Node.js + npm | `node --version` |
| Backend deps | from the repo root: `pip install -r requirements.txt` |
| Frontend deps | from `frontend/`: `npm install` |

No GPU, no model download and no internet are needed. The stack runs offline (enforced by tests).

## 3. Route 1: dev stack (recommended for a demo)

Two terminals.

**Terminal 1, backend. It must run from the repo root** (imports are absolute):

```
uvicorn backend.app.main:app --reload --port 8000
```

**Terminal 2, frontend, from `frontend/`:**

```
npm run dev
```

Open `http://localhost:5173`.

**Before the audience arrives:**

1. Open `http://127.0.0.1:8000/v1/health`. It must return 200.
2. Run one scenario. The Results page must show the badge **"Live Backend"**. If it says
   **"Demo Data — Backend Unreachable"**, the backend is down and the UI is serving a bundled copy. The two look
   almost identical, so always check the badge.
3. Open `http://127.0.0.1:8000/docs` to confirm the API docs load.

## 4. Route 2: containers

```
docker compose up --build
```

Frontend on `http://localhost:8080`, API on `http://localhost:8000` (loopback only). CI proves both images build and
an analyze cycle works, but **nobody has yet clicked a demo through the nginx-served frontend** (a logged
verification gap). Do the full checklist in section 7 through `:8080` once, well before the audience. Do not
discover problems live.

## 5. Demo script

Routes: `/` home, `/analyze` upload and query, `/results` and `/results/:sessionId` results. Use the demo
scenario bar on `/analyze`; each scenario loads real georeferenced GeoTIFFs bundled in `frontend/public/demo/`
(B and F are PNGs).

| # | Scenario | Query (pre-filled) | Task | Expected result |
|---|---|---|---|---|
| A | Single scene understanding | Describe the land-cover and major objects visible in this image. | `single_caption` | 3 boxes, tier **High** |
| B | Ambiguous region grounding | Highlight the water body referred to in the query. | `single_grounding` | 2 candidate boxes, tier **Medium** (by design: several candidates) |
| C | Bi-temporal urban expansion | What changed between these two dates, and where did the change occur? | `change_vqa` | 2 boxes plus a change mask, tier **High** |
| D | Optical-SAR fusion | Use the optical and SAR images together to identify built-up and water-covered regions. | `fusion` | 3 boxes, tier **High** |
| E | Fusion, then change | Use the optical and SAR images together to identify built-up areas, then determine whether the built-up area increased. | `fusion_then_change` | 2 boxes, tier **High** |
| F | Optical + SAR asked for change | What changed between these two dates and did built-up area increase? | `change_vqa` | **Rejected**, `modality_mismatch`, tier Low |
| G | Scenario C reversed | (same as C) | `change_vqa` | **Rejected**, `temporal_ordering_invalid`, tier Low |

Suggested order: A, B, C, D, E, then F and G.

**The signature moment is F and G.** A rejection is a success path, not an error: the API returns **HTTP 200** with
`rejected: true`, a reason code, a full execution trace and a redirect toward a valid query. F shows that the system
refuses a physically meaningless request (optical vs SAR cannot show change) instead of hallucinating an answer.
G shows it reads acquisition times from inside the files and refuses a baseline that is newer than the current
image. Validation is structural, not conversational.

## 6. What to point at on screen

- The 8-step pipeline progress (mirrors the backend's seven steps plus the UI's own).
- The evidence ledger and the bounding boxes (normalized 0-100 percent).
- The confidence tier and its written rationale.
- The execution trace. Step timings are near zero because the dummies do no work; do not present them as
  inference latency.
- Report export: JSON, HTML and **PDF** (`/v1/session/{id}/report?format=pdf|json|html`).
- Reopen a finished session at `/results/<sessionId>` after restarting the backend to show SQLite persistence.

## 7. Manual test checklist

Tick each box; the expected result is beside it.

**Startup**
- [ ] `GET /v1/health` returns 200
- [ ] `/docs` loads the OpenAPI page
- [ ] `GET /v1/registry` returns JSON
- [ ] Home page loads with no console errors

**Scenarios** (badge must read "Live Backend" each time)
- [ ] A: `single_caption`, 3 boxes, High
- [ ] B: `single_grounding`, 2 boxes, Medium
- [ ] C: `change_vqa`, 2 boxes plus mask, High
- [ ] D: `fusion`, 3 boxes, High
- [ ] E: `fusion_then_change`, 2 boxes, High
- [ ] F: rejected, `modality_mismatch`; in the Network tab the `/v1/analyze` call is **200**, not 4xx
- [ ] G: rejected, `temporal_ordering_invalid`; also 200

**Results page**
- [ ] Boxes sit inside the image and match the ledger entries
- [ ] Each result shows a rationale and a trace
- [ ] A rejection renders the rejection panel with a redirect suggestion

**Persistence and export**
- [ ] Copy the `/results/<sessionId>` URL, stop and restart the backend, reload the URL: the session is still there
- [ ] Reopened sessions show **no source imagery** (known gap, see section 8)
- [ ] JSON, HTML and PDF exports all download; the PDF opens and is not empty

**Failure behaviour**
- [ ] Stop the backend, run a scenario: the badge changes to "Demo Data — Backend Unreachable" and the console logs
  `Live backend call unfulfilled, falling back to client-side scenario`

**Optional, from the repo root**
- [ ] `python -m pytest` gives 152 passed (set `PROJ_DATA` and `PROJ_LIB`, see section 9)
- [ ] From `frontend/`: `npm test` (58 passed), `npm run build`, `npm run lint` (two known warnings)

## 8. Known rough edges (avoid or pre-empt)

- **Silent fallback.** If the backend is down the UI serves a bundled scenario. Always check the badge.
- **Do not demo a live upload.** A user-uploaded GeoTIFF probably shows a broken preview, because browsers do not
  decode TIFF in an `<img>` (inferred from browser behaviour, not observed). The built-in scenarios are unaffected.
- **Demo imagery is synthetic.** The GeoTIFFs carry real CRS, geotransform and timestamps, but the pictures are drawn,
  and each file says so in a `DEMO_NOTE` tag.
- **Scenario D** claims 42% cloud in its answer text while the raster measures about 5%. The tier is unaffected.
- **Cloud share** is an 8-bit brightness approximation, not a detector.
- **Two rejection codes have no demo** (`crs_mismatch_unresolvable`, `insufficient_footprint_overlap`); they are
  reachable only through the API.
- **Reopened sessions show no source imagery** (needs an `inputImages` field and a DB migration, logged).
- **Scenarios A-E's answers are hardcoded text.** Do not present them as model output or ask the audience to
  test their own imagery for correctness.

## 9. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `ModuleNotFoundError: backend` | Backend was not started from the repo root. `cd` to the repo root and re-run uvicorn |
| Port 8000 or 5173 in use | Stop the other process, or pass `--port` and set `VITE_API_BASE_URL` to match |
| Browser shows CORS errors | The frontend origin is not in `SATQUERY_CORS_ORIGINS` (defaults cover `localhost:5173`, `127.0.0.1:5173`, `localhost:3000`) |
| UI shows the demo-fallback badge | Backend unreachable; check the URL in `VITE_API_BASE_URL` (default `http://127.0.0.1:8000`) |
| CRS tests fail with a `proj.db` error | A local PostgreSQL install sets `PROJ_LIB`. Point `PROJ_DATA` and `PROJ_LIB` at `<site-packages>/rasterio/proj_data`. The server itself is unaffected |
| PDF export fails | PDF uses pure-Python `xhtml2pdf`; reinstall `requirements.txt` |
| Stale sessions or a clean slate | Delete `backend/storage/` (gitignored). It is recreated on start |

Configuration lives in `SATQUERY_*` environment variables (`.env.example`); bad values fail at startup and name the
variable.
