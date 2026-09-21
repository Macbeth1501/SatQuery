# SatQuery AI — Startup Guide and Demo Test Plan

How to start the stack, drive the demo in front of someone, and manually test it. Written against the state
recorded in `docs/PROGRESS_LOG.md` (Phases 0-8 done, dummy specialists; one live-model path for single-image
questions, section 3a).

## 1. What you are showing (say this first)

- The **pipeline is real end to end**: query interpretation, structural validation, routing, verification, overlays,
  confidence scoring, execution trace, SQLite persistence, JSON/HTML/PDF reports.
- The **specialists are deterministic dummies** (`ScenarioEngine`, five hardcoded scenarios). There is no model and
  no LLM behind the answers. This is deliberate (Development Plan section 2.5).
- The demo therefore shows the **architecture and its contracts** (validation before execution, evidence ledger,
  confidence tiers, first-class rejection), not a trained model's accuracy.
- **One path is real (section 3a):** single-image questions about five real BigEarthNet Sentinel-2 patches, answered
  by the trained LoRA adapter (`data/b5_run2/adapter_final` on Qwen2-VL-2B, 4-bit). Say plainly that the images
  were chosen because the adapter answers their questions correctly, and that on unseen tiles it scores about 33% on
  multiple choice (chance 25%) and 50% on yes/no. The panel on screen says the same.

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

## 3a. Live model demo (real adapter, real BigEarthNet image)

Needs the GPU machine with `.venv-ml` and `data/` (the adapter and the cached model; neither is in git). Three
terminals, all from the repo root except the frontend.

**Terminal 1, model server** (about a minute to load; binds to `127.0.0.1:8001`, offline):

```
.venv-ml/Scripts/python.exe ml/serve_vqa.py --adapter data/b5_run2/adapter_final --port 8001
```

Wait for `Uvicorn running on http://127.0.0.1:8001`. `http://127.0.0.1:8001/health` names the model, revision and adapter.

**Terminal 2, backend with the model switched on** (PowerShell):

```
$env:SATQUERY_VQA_MODEL_URL="http://127.0.0.1:8001"; uvicorn backend.app.main:app --port 8000
```

**Terminal 3, frontend:** `npm run dev` from `frontend/`, then open `http://localhost:5173/analyze`.

**Running it:** everything happens in the one studio.
1. The preset bar has a green row, **"Live model — real BigEarthNet Sentinel-2 images"**, with one card per image
   (thumbnail, country, month and number of questions). Click one. The real GeoTIFF loads into **Image 1**, and its
   card shows the file's own CRS, 10 m GSD and acquisition date.
2. Under the query box, the suggestion chips become that image's BigEarthNet questions, with the accuracy note.
3. Click one, then **Run Agentic Analysis**. The Results page checks the answer against BigEarthNet's reference.

Clicking a card in the grey "Demo engine" row brings back the scripted scenarios and their queries.

**Or upload an image yourself.** Click **Image 1** (or drag a file onto it) and pick one of the `.tif` files in
`D:\Projects\SatQuery\frontend\public\real\`. The studio recognises a sample by its file name, shows its facts and
preview, and offers its question chips. Your own file's bytes are sent. Your typed query is kept, so click a chip
before **Run Agentic Analysis**.
- The `.png` next to each `.tif` also works, with the same pixels and the same answers. A PNG has no georeference,
  so its card shows "No CRS" and "GSD unknown".
- A renamed copy is treated as an ordinary upload.

**Any other file** you upload is read by the backend (`POST /v1/inspect`) the moment you pick it. The card shows
"Reading file…", then what the file actually says (CRS, GSD, bands, date, modality). A TIFF gets a preview the
browser can display. If the backend is down, the fields stay "unknown"; nothing is guessed. The model will answer a
yes/no or a-d question about any optical image, but only these samples have reference answers, and the model was
trained only on 120×120 px Sentinel-2 patches.

**The five images** (all on Sentinel tiles never seen in training; measured in the browser 2026-09-21, 23 of 23 correct):

| Card | File | Questions | Model probabilities | Tiers |
|---|---|---|---|---|
| Ireland · Nov 2017 | `bigearthnet_T29UPU_55_58.tif` | 5 (4 yes/no, 1 a-d) | 78, 51, 50, 51, 34% | 1 Medium, 4 Low |
| Ireland · Apr 2018 | `bigearthnet_T29UPU_38_37.tif` | 5 (4 yes/no, 1 a-d) | 69, 59, 37, 87, 54% | 1 Medium, 4 Low |
| Lithuania · Apr 2018 | `bigearthnet_T34UEG_28_34.tif` | 6 (2 yes/no, 4 a-d) | 30, 46, 31, 31, 56, 58% | 6 Low |
| Serbia · Aug 2017 | `bigearthnet_T34TCR_36_25.tif` | 4 (3 yes/no, 1 a-d) | 50, 59, 50, 30% | 4 Low |
| Portugal · Nov 2017 | `bigearthnet_T29SND_42_38.tif` | 3 (2 yes/no, 1 a-d) | 55, 65, 33% | 3 Low |

For a four-option question, 30-46% is above the 25% a guess would get; for yes/no, 50-59% is close to a coin flip.
Examples of the first image's questions: "Does the satellite view capture inland waters?" gives No (78%, Medium), and
"How much of the scene do arable lands cover? a) 90 to 100%, b) 30 to 60%, c) 0 to 20%, d) 60 to 80%" gives
b) 30 to 60% (34%, Low).

All 23 are right, and the Results page shows the reference check under each answer. **Point at the
probabilities**: they are honest, and many of the yes/no answers are near coin flips. The tier is Medium at best on
purpose, because no model answer is rated High. What to show on the Results page:
- the trace step `VqaCaptionSpecialist` with the adapter ID, the answer distribution and the real latency
  (about 0.4 s on the GPU, 0.7-1 s for the step);
- the metadata read from the uploaded GeoTIFF (e.g. EPSG:32629, 10 m, 2017-11-12 for the first image);
- no bounding boxes, because the adapter does not ground.

**What to ask, and what not to (from the owner's live session, 2026-09-22):**
- **Good new questions:** yes/no or a-d questions about land cover, e.g. "Is there forest in this image?", "Is most of
  the image farmland?", "Is this image from Ireland?". Expect probabilities mostly between 50 and 70%.
- **Avoid "Describe the image"** and similar. The adapter did learn BigEarthNet's caption template, but it fills in
  country, season and climate from memory. It said "Finland, spring" for the Irish November patch and described a
  "large, complex building" on Serbian farmland. The note under such answers wrongly says the model was never trained on
  descriptions; that note is a known bug.
- **Avoid commands starting with "Do"** ("Do descriptive analysis"). A bug reads them as yes/no and answers "No".
- **Do not run change or fusion on the real patches.** Only single-image questions go to the model. Change, fusion and
  grounding still come from the demo engine, which returns scripted text rated High even for real images. The A-G
  scenarios are fine to show as scripted demos.

**If the model server is down**, the backend returns 503 and the page shows a red "No answer" box. On this path
there is no fallback to demo data. Without `SATQUERY_VQA_MODEL_URL` the backend answers the sample from the demo
engine, which would be wrong for these samples, so always set it for this demo.

To swap in a better adapter later, change `--adapter` only. `tools/make_real_sample.py` regenerates all five
samples from the raw BigEarthNet bands (edit its `PATCH_IDS` to change them).

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
  inference latency. The exception is the live-model path (section 3a), whose specialist step is real GPU time.
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
- [ ] `python -m pytest` gives 195 passed (set `PROJ_DATA` and `PROJ_LIB`, see section 9)
- [ ] From `frontend/`: `npm test` (72 passed), `npm run build`, `npm run lint` (two known warnings)

## 8. Known rough edges (avoid or pre-empt)

- **Silent fallback.** If the backend is down the UI serves a bundled scenario. Always check the badge.
- **Uploads are safe to demo since 2026-09-21.** A TIFF now gets a preview rendered by the backend
  (`POST /v1/inspect`), and the card shows the file's real metadata. That needs the backend running; without it the
  fields stay "unknown". For a live-model demo, upload one of the files in `frontend/public/real/` (section 3a).
- **Demo imagery is synthetic.** The GeoTIFFs carry real CRS, geotransform and timestamps, but the pictures are drawn,
  and each file says so in a `DEMO_NOTE` tag.
- **Scenario D** claims 42% cloud in its answer text while the raster measures about 5%. The tier is unaffected.
- **Cloud share** is an 8-bit brightness approximation, not a detector.
- **Two rejection codes have no demo** (`crs_mismatch_unresolvable`, `insufficient_footprint_overlap`); they are
  reachable only through the API.
- **Reopened sessions show no source imagery** (needs an `inputImages` field and a DB migration, logged).
- **Scenarios A-E's answers are hardcoded text.** Do not present them as model output or ask the audience to
  test their own imagery for correctness. Only the green live-model row (section 3a) is answered by a model.
- **After an ordinary upload, the previously selected scenario card still shows as selected**, and if the backend then
  fails, that scenario's mock answer is shown. The live-model samples never fall back like this.

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
