# SatQuery AI — Progress Log

Live status of the SatQuery AI build (ISRO SIH26167). This file is the single
source of truth for where the project stands. If this log and the code disagree,
the log is wrong and must be corrected.

---

## Current status

**Phase: prototype complete and verified, Phases 0-8 all closed. The full pipeline
runs end to end on deterministic dummy specialists, with one exception added 2026-09-21: with
`SATQUERY_VQA_MODEL_URL` set, single-image questions are answered by the trained run-2 LoRA adapter served by
`ml/serve_vqa.py`, and the website offers five real BigEarthNet patches with 23 reference-graded questions as
live-model presets (C0 and C2 PARTIAL). Uploads are read by `POST /v1/inspect`; nothing is invented on screen.
Grounding, change and fusion are still dummies. Track A (hardening) is done except A6 (see "Next step").**

The system is a high-fidelity facade, and deliberately so — the Development Plan
(§2.5) requires that dummy specialists expose exactly the interface the real ones
will use, so the frontend never learns which is active.
Every architectural contract in the SPDD is implemented and exercised; only the
inference layer is stubbed.

### What works today

| Area | State |
|---|---|
| FastAPI backend, 6 endpoints | Complete, verified |
| 7-step orchestration pipeline | Complete, verified |
| All 8 `TaskType` classifications | Complete, all reachable |
| Compatibility validator, 7 rejection codes | Complete, all reachable |
| Verifier node (geometry + quantity cross-check) | Complete |
| Confidence scorer (High/Medium/Low + rationale) | Complete |
| Execution trace + JSON / HTML / PDF report export | Complete |
| Pillow bounding-box and change-mask overlays | Complete |
| Session persistence | Complete — SQLite (see the datastore row below); legacy `response.json` files are imported on first read |
| React frontend, 3 routes, 15 components | Complete, verified in-browser |
| Test suite: 207 pytest + 73 Vitest tests | All passing (26 in `tests/test_ml.py`, some of which skip when scikit-learn, scipy or torch are missing; `tests/test_real_model.py` and `tests/test_inspect.py` need no GPU) |
| Demo inputs | Seven georeferenced GeoTIFFs in `frontend/public/demo/` (scenarios A, C, D, E, and G which reuses C's pair reversed); B and F stay plain PNGs on purpose. Georeferencing is real, the pictures are synthetic |
| ML training side (`ml/`) | B1 thin slice built and verified; B5 LoRA train/eval/notebook written; baseline evaluated; **run 1 (old leaky slice, `data/b5_run1/adapter_final`) showed no evidence of image reading; run 2 (leak-neutral `data/b1_v2`, 300 steps in 1 h 43 min, `data/b5_run2/adapter_final`) passes the pre-registered test on `bench_hard` main (+6.1 binary, +8.6 mcq over text-only) but its binary lead is gone on held-out tiles (held-out mcq keeps +8.6)**. Not wired into the backend. `tests/test_ml.py` (26 tests) covers the CPU-side pieces (option parser, text-only baseline, raking, sampler, McNemar, answer parser, change rate, resumable training state on a toy model); training, extraction and GPU evaluation have no automated tests |
| **Specialist inference** | **Dummy — `ScenarioEngine` lookup — except single-image VQA/captioning when `SATQUERY_VQA_MODEL_URL` is set: real adapter over HTTP (`ml/serve_vqa.py`), verified live 2026-09-21** |
| Live-model demo | Green row of the preset bar on `/analyze`: five real BigEarthNet Sentinel-2 patches (Ireland ×2, Lithuania, Serbia, Portugal; tiles never seen in training), 23 questions, 23 of 23 correct in the browser, 2 rated Medium and 21 Low. A card, or uploading the file by hand, loads the GeoTIFF into Image 1 and the query chips become its questions. Free-form questions are answered by the base model with the adapter off (2026-09-22). Grounding, change and fusion on non-demo images are refused as `no_trained_model` while the live model is on |
| **Optical/SAR fusion** | **Dummy — hardcoded region tags** |
| Raster metadata extraction | Read from the file (CRS, bands, GSD, footprint, NoData, timestamp). Also exposed before analysis as `POST /v1/inspect`, which fills the upload card and renders a PNG preview (TIFFs included) |
| Externalized configuration | `SATQUERY_*` env vars and `VITE_API_BASE_URL` |
| Persistent datastore | SQLite (`sessions`, `evidence_ledgers`, `execution_traces`); survives restart |
| Containers, Compose, CI workflow | Complete (Track D) — both images build and the stack runs an analyze cycle in CI |
| Offline requirement | Enforced by tests: no outbound connection in a full analyze cycle, no CDN in the frontend |

### Verified behaviour

All five canonical SIH demo scenarios return their intended confidence tier with
unique, correctly-bounded evidence boxes:

| Scenario | Resolved task | Boxes | Confidence |
|---|---|---|---|
| 1 — Land-cover description | `single_caption` | 3 | High |
| 2 — Water body grounding | `single_grounding` | 2 | Medium (multi-candidate, by design) |
| 3 — Bi-temporal change | `change_vqa` | 2 + mask | High |
| 4 — Optical + SAR fusion | `fusion` | 3 | High |
| 5 — Compound fusion then change | `fusion_then_change` | 2 | High |

The signature rejection rule is verified: an optical + SAR pair submitted for
bi-temporal change is rejected with `modality_mismatch` and redirected to a
fusion query, returning HTTP 200 with a full trace rather than an error.

---

## Next step

**Newest (2026-09-22): run 3 (full epoch, captions without country/season/climate) is training.** The owner approved
removing those facts from the caption targets first, and restarted the PC to free the GPU (468 MiB used before launch).
Data: `data/b1_v3` (built by `ml/b1_v3.py`, see History). Command, from the repo root:
`.venv-ml/Scripts/python.exe ml/b5_train_lora.py --data data/b1_v3 --out data/b5_run3 --size 448 --epochs 1.0
--grad-accum 16 --eval-every 200 --eval-n 100 --save-every 100` (log `data/b5_run3_train.log`), 1,218 steps, expected
about 7 h at run 2's 20.6 s/step. **The GPU is busy until it ends, so the live demo cannot run.** If it dies, rerun the
same command with `--resume data/b5_run3` (never exercised on the real model). **Then:** score run 3 on `bench_hard` main
and held-out in the six-run matrix and judge it only by its paired lead over the text-only model (`b5_compare.py`),
against run 2's +6.1/+8.6 main and -0.5/+8.6 held-out; check the 23 sample answers with `--adapter
data/b5_run3/adapter_final`; and re-run `ml/b5_freeform_compare.py` with the new adapter to see whether it describes
without invented facts. After that: security items 1.1-1.3, then B6, B7, B3/C1 and fusion.

**Earlier (2026-09-21): five live-model samples; upload metadata read from the file.** Demo-ready: follow
`docs/STARTUP_GUIDE.md` §3a.

**Earlier (2026-09-21): live-model website demo built and verified over HTTP.**
Run it with `docs/STARTUP_GUIDE.md` §3a. **Verified in a real browser** (headless Chromium, all 5 questions and the
model-down case). **Open:** (1) nothing in the demo. (2) The owner raised retraining for
a full epoch (run 2 saw about a quarter of `data/b1_v2`; about 7 h on the RTX 3050) to raise accuracy. It has not
been started. A better adapter is a `--adapter` swap. (3) The rest of C0 (fusion modules) and C2 (other specialists).

**Standing (2026-09-21, Phase 2 under way, owner said "go" for steps 1-5):** steps 1-3 are done (see the History
entries: run 1 misses the primary bar, +4.1 binary and +1.7 mcq over text-only). **Phase 2 (steps 1-5) is complete.** Run 2 (`data/b5_run2/adapter_final`) passes the pre-registered primary and secondary
tests on `bench_hard` main (+6.1 binary, +8.6 mcq over text-only) but its binary lead vanishes on held-out tiles; held-out mcq
keeps +8.6. See the newest History entry. **Owner decision needed on what comes next** (B6 grounding, C0, more bench patches to
fill the thin categories, or a repeat seed); nothing further has been started.
`docs/STARTUP_GUIDE.md` §3a (live model) has been walked through in a browser (2026-09-21); the A-G demo scenarios in §5 have not.

**Decision taken 2026-09-20 (owner): train the first B5 adapter locally, not on Kaggle.** This rests on the
measured dry runs recorded in the Development Plan under D2 (QLoRA fit on the RTX 3050); it amends D2's
"training goes to the cloud" for this first run. The Kaggle notebook stays as the scale-up path.

1. **Done:** baseline (`data/b5_eval/base.json`), local thin training (300 steps, 13,060 s = 3 h 38 min
   against a 2.3 h estimate), and scoring (`data/b5_eval/tuned.json`, 776 s). Results and caveats in the
   2026-09-20 "first thin adapter" History entry. Nothing holds the GPU now.
2. **The blind baseline, the loss-masking check and the text-only baseline are done.** Tuned with no image
   scores 60.5% binary / 36.5% multiple choice against 65.0% / 41.5% with the image, and a text-only model
   with no image scores 62.3% / 40.2%, so there is no evidence yet that the adapter reads imagery. The
   masking is correct. The generator is not shipped, but the data show why the text leaks (correct options
   follow the dataset's label frequencies while wrong options look evenly drawn; "Autumn" is never correct).
   **Owner decision needed on what comes next** (nothing further has been started): (a) change the training
   data so the answer cannot be guessed from the text (see the History entry; the recommended route is to
   keep only training examples the text-only model gets wrong or is unsure about, and drop the "Autumn"
   leak, which shrinks the slice), then retrain and judge by the lead over the text-only model; (b) a real
   held-out-tile test built from the raw bench archive; (c) B6 (grounding boxes) or C0. Scaling the current
   recipe is not recommended. See the History entries.
3. **Decision taken 2026-09-20 (owner): route (a), with the filter replaced by leak-neutral resampling. Done.**
   Phase 1 (CPU) built `data/b1_v2/` (19,489 training and 1,197 validation examples on 17,121 and 1,017 patches, 6
   Sentinel tiles reserved) and `data/b1_v2/bench_hard.jsonl` (3,000 examples), on which the text-only baseline scores at
   chance. Phase 2 (2026-09-21) ran the control (run 1 misses the primary bar), the retrain (`data/b5_run2`) and the six-run
   scoring; results in the two newest History entries. **Open: what to do with run 2.** Options, none started: fill the
   thin bench categories with more extracted patches (not approved so far), a repeat seed to see whether the held-out mcq
   lead is stable, B6 (grounding boxes), or C0 before any wiring.
4. Nothing may be wired into `backend/` before C0.

Independent and still open: **A6** (map layer, unblocked), **C0** (must precede wiring any adapter into the
pipeline), two API-only rejections without demos (`crs_mismatch_unresolvable`,
`insufficient_footprint_overlap`), and the A8 follow-up (`inputImages`, DB migration 2).

Development Plan §10.5 has the full breakdown.

---

## Deployed addresses

| Environment | Address | State |
|---|---|---|
| Backend (local) | `http://127.0.0.1:8000` | Run manually |
| API docs (local) | `http://127.0.0.1:8000/docs` | Run manually |
| Frontend (local) | `http://localhost:5173` | Run manually |
| Source repository | `https://github.com/Macbeth1501/SatQuery` | Fresh single-commit history created by the owner 2026-09-20; earlier commit hashes quoted in this log no longer exist there |
| Staging | — | Not deployed |
| Production | — | Not deployed |

Nothing is deployed to a hosted environment. The frontend reads the backend URL from
`VITE_API_BASE_URL` (default `http://127.0.0.1:8000`), and the backend is configured
through `SATQUERY_*` environment variables — see `.env.example` and
`frontend/.env.example`.

### Running it

Backend, from the repo root (imports are absolute, so the root is required):

```
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --port 8000
python -m pytest
```

Frontend, from `frontend/`:

```
npm install
npm run dev
npm run build
npm run lint
npm test
```

The backend suite uses FastAPI's `TestClient`, so no server needs to be running.

---

## Open items

Real, known, not yet fixed (as opposed to "Known limitations", which are accepted):

0. **Found in the owner's live session 2026-09-22: all four fixed the same day** (History has the details).
   - (a) "Do ..." imperatives read as yes/no: fixed in `question_kind`, checked against all 22,158 binary and a-d questions in `data/b1_v2`.
   - (b) Free-form descriptions invent facts: the adapter still does; free-form questions now go to the base model. The
     base model names no country or season but can still describe things that are not there. **Still open: a description
     that is faithful and useful needs a caption target without country, season and climate, then a retrain.**
   - (c) The wrong "trained only on yes/no and a-d" note: corrected in `vqa_caption.py` and `confidence_scorer.py`.
   - (d) Change/fusion/grounding on real images: refused as `no_trained_model` while `SATQUERY_VQA_MODEL_URL` is set.
     With the URL unset the scripted demo still answers real uploads (accepted; the facade is deliberate).
   - Two sessions from my own verification script (`sq-96a332b6`, `sq-29d39d3b`, 2026-09-21 19:58 UTC, "What changed
     between these two dates?" and "Highlight the water bodies...") are in `backend/storage/satquery.db` beside the
     owner's; I did not delete them (a delete was blocked). They are harmless and the owner may remove them.

1. **The scorer (demo path) and both fusion modules still call `ScenarioEngine` directly.** The live-model path
   (single-image, `SATQUERY_VQA_MODEL_URL` set) no longer does, since 2026-09-21. The remainder of the original item:
   (`confidence_scorer.py`, `complementarity_detector.py`, `verbalizer.py`, plus the specialists).
   Harmless now; it must be removed before real inference lands (Plan step C0), or the scorer will
   override real model confidence with canned rationales.
2. **Demo mock traces are a copy, not generated.** `frontend/src/data/mockTraces.ts` will drift if
   the backend pipeline's steps change. Regenerate it from a live `/v1/analyze` response. One known difference from live: its
   `input_images` parameters name `opt_s2.png` / `sar_s1.png`, not the demo's file names.
3. **Two lint warnings** (`react/only-export-components` in `SatQueryContext.tsx`, currently lines 89 and 386).
   Non-blocking; fix by moving the shared constants to their own file.
4. **Started, not finished.** **D1 and D2 are both closed** (backbone `Qwen/Qwen2-VL-2B-Instruct`;
   RTX 3050 with 4 GB usable VRAM). **D2's "training goes to the cloud" was amended by measurement and then
   by the owner: QLoRA does fit on this card, and the first adapter was trained locally** (300 steps,
   3 h 38 min, peak 2,913 MiB). So training code and one adapter now exist — `ml/b1_slice.py`,
   `ml/b5_common.py`, `ml/b5_train_lora.py`, `ml/b5_eval.py`, `ml/b1_v2.py`, `ml/b5_deleak.py`, `ml/b5_text_only.py`, `ml/b5_compare.py`, `ml/b5_change_rate.py`, and the adapters `data/b5_run1/adapter_final` and
   `data/b5_run2/adapter_final` — and the dataset work is the B1 thin slice, the leak-neutral `data/b1_v2` and the
   extracted `bench` subset of BigEarthNet.txt (see History).
   What is *not* built: evidence that the adapter reads imagery on unseen tiles for binary questions (run 2 shows it only for
   mcq), and any link to `backend/`.
   The revision is pinned: `895c3a49bc3fa70a340399125c650a463535e71c`, downloaded to
   `data/hf_cache/` (4.2 GB, gitignored). **A6 (map layer)** is unblocked by Open item 5 but not started. A8 has one known gap: reopened
   sessions show no source imagery (needs an `inputImages` field and DB migration 2).
5. **Demo rasters are georeferenced but synthetic, and two demos have no georeference at all.**
   Scenarios A, C, D and E upload real GeoTIFFs (`frontend/public/demo/`, regenerated by
   `tools/make_demo_rasters.py`), so the A1 metadata work now fires in a demo. The pictures are still
   drawn, not acquired, and each file says so in a `DEMO_NOTE` tag. B and F remain PNGs. Scenario G
   shows `temporal_ordering_invalid` in the UI. `crs_mismatch_unresolvable` and
   `insufficient_footprint_overlap` are still reachable only through the API (see "Next step"). Real Sentinel patches are the
   later replacement, once the ML track needs real evaluation inputs.

## Verification gaps

Things that were changed but not confirmed the way a user would meet them:


- **Nobody has clicked through the containerised frontend in a browser.** CI proves both images build, that the
  stack comes up healthy, that an analyze cycle works through it and that a session survives a restart,
  but its frontend check is only that nginx serves `index.html` for `/` and for a client route. Locally,
  both images have been built and started, the backend reports healthy with `/v1/health` returning 200, and
  the nginx container is running (reported by the user, not re-verified here). The nginx-served bundle has
  still not been driven through a demo. Opening `http://localhost:8080` would close this.
- **This Windows machine has a PostgreSQL install that sets `PROJ_LIB` and `GDAL_DATA`.** With current
  rasterio (1.5) that makes the CRS tests fail locally with "PROJ: ... proj.db ... another PROJ
  installation". It is an environment clash, not a code fault: in a clean venv the full suite passes
  with `PROJ_DATA` and `PROJ_LIB` pointed at `rasterio/proj_data`. Linux CI is unaffected.
- ~~A user-uploaded GeoTIFF probably shows a broken preview.~~ **Resolved 2026-09-21:** the card now shows a PNG
  rendered by `POST /v1/inspect`. Verified in Chromium by uploading `Sentinel1_SAR_Assam_C_Band.tif`: the preview
  rendered, with EPSG:32646 and 10 m read from the file.
- **After an ordinary upload the previously selected demo scenario stays selected** (seen in a screenshot
  2026-09-21). If the backend then fails, that scenario's mock answer is shown for the user's image (audit 3.6b). This
  existed before; the live-model samples are not affected.
- **Answers and labels describe more than the rasters measure.** The scenario D picture and answer claim
  42% cloud, while the 8-bit brightness approximation reads 5.06% from the file. The cloud share stays
  under the warning threshold, so no tier changes, and the answer text is pinned by the parity snapshot,
  so it was left alone.
- **The 4-bit result covers inference only.** Peak memory was measured for `generate()`, not for training
  (still expected to overrun 4 GB; cloud training stands, unmeasured here). It is `torch` peak *allocated*
  memory, not the card's total use, and it ran with 3,303 MiB free because the Windows desktop already held
  about 800 MiB. It says nothing about a LoRA adapter's added memory or about adapter switching latency.
- **Only the CPU-side `ml/` code has automated tests** (`tests/test_ml.py`, 26 tests); B1's guarantees (disjoint patches, buffer distance) were checked by an
  ad-hoc script, not a committed test. The 300-step local run (bfloat16) completed with no non-finite loss,
  and the saved adapter reloads and changes outputs (checked 2026-09-20). Training loss did NOT visibly fall
  (single-step readings stay in about 0.19-0.50 from step 196 to 300); only validation loss fell (0.633,
  0.518, 0.500 at steps 100/200/300). The answer-only loss masking is still not checked directly. Nothing has
  compared this with the Kaggle T4 float16 path, and the notebook's pinned `transformers 5.17` and pip
  installs were never run on Kaggle.
- **The evaluation's answer parsing is strict and only spot-checked.** Twelve baseline samples were read by
  eye. It requires the reply to START with yes/no or a letter, so phrasings like "There is no instance of..."
  count as unreadable (wrong). Plain accuracy therefore mixes format and skill; use `acc_among_readable`.
- **Graph token cost** in `GRAPH_REPORT.md` reads 0 because the extraction subagents' usage was not
  recorded. The graph itself was verified to contain nodes from every changed file.
- **`SPDD.md` was not re-read against the code.** It carries an implementation note pointing at
  Appendix B for known deviations, but it may contain further undocumented ones.

---

## Known limitations

Accepted for the prototype, not defects to fix now:

- **No model.** Every specialist resolves to a hardcoded scenario bank. Adapter
  IDs such as `vqa_caption_adapter_v1.0` are strings, not weights.
- **Cloud share is an approximation**, not a detector: an 8-bit brightness threshold
  that flags snow, sand and bright roofs and misses thin cloud. It is `None` for
  non-8-bit rasters. Pair overlap is a lon/lat bounding-box IoU, exact only for
  axis-aligned scenes.
- **Demo pictures are synthetic.** The seven GeoTIFFs carry valid CRS, geotransform, GSD and
  platform/acquisition tags, and each says `DEMO_NOTE` in its own metadata, but none was acquired by the
  platform it names. Bands are 3 (optical) and 1 (SAR): Pillow cannot decode a 2-band TIFF and the overlay
  renderer needs it to, so the mocks no longer claim 4 and 2. Scenario E's two images carry no timestamp,
  on purpose, to show an unknown staying `None`.
- **The demo fallback still exists**, by design — if the backend is unreachable the
  UI serves a bundled scenario so a live presentation survives. It is no longer
  silent: the Results page labels it "Demo Data — Backend Unreachable".
- **Two scenario banks.** The backend `ScenarioEngine` and
  `frontend/src/data/mockScenarios.ts` still encode overlapping demo content that is
  authored in two places, so changing a demo means editing both. They can no longer drift
  silently: `tests/test_demo_parity.py` and `mockScenarios.test.ts` compare them through
  `frontend/src/data/demoParity.json` (see History). Masks are not compared.

---

## History

### 2026-09-22 — `data/b1_v3`: caption targets without country, season or climate; run 3 started

The owner asked to drop country, season and climate from the caption targets and then train a full epoch.
`ml/b1_v3.py` copies `data/b1_v2` and rewrites only the 1,528 captioning rows (1,431 train, 97 validation):
- the 32 caption prompts, which asked for "the geographic region and season" and similar, are mapped by hand to prompts
  that ask only for land cover (`QUESTION_MAP`);
- the answer's first sentence loses "captured during the <season> season in <country>" and "within the "<climate>"
  climate zone"; any later sentence that still names a country, nationality, season or climate is dropped (213
  sentences, 1 of which carried an area figure; no caption lost its first sentence or became empty). "fall" as a verb
  ("fall under the broader category") is kept;
- the build refuses to write if any caption or caption prompt still names one of them.

The 18,058 binary and mcq rows are byte-identical apart from the image path, which points into `data/b1_v2/images`
(nothing copied). **Kept on purpose:** the mcq/country, mcq/season and mcq/climate-zone questions (balanced by
`b5_deleak`, so not guessable from text; the owner asked about captions only). `bench_hard` stays in `data/b1_v2`, so
run 3 is scored on the same rows as run 2. Tests: 4 new in `tests/test_ml.py` (26 there, 207 pytest overall).
Run 3 was launched with the command in "Next step".

### 2026-09-22 — Three fixes from the live session: yes/no detector, honest free-form model, no scripted change on real images

The owner chose the three fixes first and the full-epoch retrain in the next prompt, (b) as a rejection, limited to
live-model mode, and let me restart the servers.

- **(a) Yes/no detector** (`ml/serve_vqa.py` `question_kind`). "Do"/"Did" openers count as yes/no only when the sentence
  ends with "?"; a description request ("Can you describe...", any sentence containing "analysis") is free-form. Checked
  against every labelled question in `data/b1_v2` (11,870 binary, 10,288 mcq): none changed kind. "Is there a river
  passing through" (no "?") stays binary. The wrong "trained only on yes/no and a-d" text in `vqa_caption.py` and
  `confidence_scorer.py` now says the adapter also saw a small share of BigEarthNet captions and that descriptions are
  unevaluated.
- **(b) `no_trained_model` rejection.** New `RejectionReasonCode`, mirrored in `satquery.ts`, the registry and
  `RejectionState.tsx` ("No Trained Model for This Task Yet"). `CompatibilityValidator` step 8 rejects grounding, change
  and fusion when `SATQUERY_VQA_MODEL_URL` is set and any input is not a demo input. `ImageMetadata.demo_input` (never
  serialised) is set from the ten demo file names (`metadata_service.DEMO_INPUT_NAMES`, tested against
  `mockScenarios.ts`) or the `DEMO_NOTE` tag. It runs after the structural checks, so `modality_mismatch` and overlap
  still win. With the URL unset nothing changes, so the parity tests and snapshot are untouched.
- **(c) Base model against the adapter** (`ml/b5_freeform_compare.py`, `data/b5_eval/freeform_compare.json`; 5 patches
  x 3 prompts x 2 models, all 30 replies read by hand). The adapter named a country in 7 of 15 replies, and every one was
  wrong ("Finland" for Ireland, Lithuania and Portugal; "Serbia" for Portugal), a season in 7 (6 wrong), and called
  Serbian farmland "a large, complex building". The base model named no country or season in 15 replies. It gives generic
  but plausible descriptions ("rural landscape, green and brown patches"), and also invents: buildings on a farmland
  patch, "a mountainous region ... night" for the Portuguese patch. The 64-token limit cut 13 of the base model's 15 replies and 12 of the
  adapter's 15 mid-sentence, so the limit is now 128 (the live check's description ended cleanly; longer ones may still
  be cut). **Decision:** free-form goes to the base model by default
  (`--free-form base`; `--free-form adapter` restores the old behaviour), labelled as such in the answer, trace and
  `source_specialist`. Five patches are a spot check, not an evaluation.
- **Tests:** 203 pytest (8 new), 73 Vitest (1 new), `tsc` and the build clean, lint shows the 2 known warnings.
- **Browser (Chromium, real stack):** "Do change anaylisis" on a real patch in both slots shows the rejection card, no
  scripted report; the first sample question still answers "No, 78%" and matches the BigEarthNet reference; "Do
  Descriptive analysis" returns a base-model description with the note. No console errors.
- **Housekeeping:** the three `*.aux.xml` sidecars were deleted. My check posted two sessions into the owner's database
  (see Open item 0). All servers I started were stopped; the GPU shows only the desktop's ~1 GB.
- Files (uncommitted): `ml/serve_vqa.py`, `ml/b5_freeform_compare.py`, `backend/app/{api/routes_system.py,
  orchestrator/{compatibility_validator,confidence_scorer,specialist_router}.py,schemas/{image_metadata,validation}.py,
  services/metadata_service.py,specialists/vqa_caption.py}`, `frontend/src/{types/satquery.ts,components/
  RejectionState.tsx,components/RejectionState.test.tsx}`, `tests/{test_ml,test_real_model}.py`,
  `docs/{PROGRESS_LOG,STARTUP_GUIDE,HANDOFF_PROMPT}.md`, `CLAUDE.md`.
- Log corrections: the test counts for `tests/test_ml.py` (21/18/12) are now 22 everywhere, the stale single-sample
  sentence in the live-model row is gone, and the handoff's last-commit reference was wrong (`f7eed5e`, not `7b08e79`).

### 2026-09-22 — Owner's live session reviewed; wrong training claim corrected; handover written (no code changed)

The owner asked new questions in the live demo and asked whether they can. They can: every single-image question went to
the real model. The backend's session records (`backend/storage/satquery.db`, read-only) show:

| Query | Image | Answer | Assessment |
|---|---|---|---|
| Is this image from ireland | T29UPU_38_37 (Ireland) | Yes, 61% | correct |
| Is this a dessert | T34UEG_28_34 | No, 61% | plausible |
| Is there a river passing through | T29UPU_55_58 | No, 60% | plausible |
| Describe the image / Give the descriptive study of scenery | T29UPU_55_58 (Ireland, Nov) | "...spring season in Finland..." | wrong country and season |
| Describe the scenery | T34TCR_36_25 (Serbia, farmland) | "a large, complex building..." | invented |
| Do Descriptive analysis | T29SND_42_38 | No, 92% | bug: "Do" read as a yes/no opener |
| Do change anaylisis | two real patches | scripted change report, High | demo engine answered real images |

**Correction.** The free-form note and earlier replies to the owner said the adapter was trained only on yes/no and a-d
questions. `data/b1_v2/train.jsonl` holds 9,470 binary, 8,588 mcq and **1,431 captioning** examples. The captions follow
BigEarthNet's template (country, season, climate zone, dominant class with area), which a 120 px patch cannot support,
so the adapter fills the template from memory. Run 1's captions named the right country 61.7% of the time on seen
tiles only; run 2's were never scored. The code text is not yet corrected (next step 1a).

**Answer given to the owner on "train further first?":** no. More of the same training teaches the caption template more
fluently, not more truthfully, and it holds the GPU so the demo cannot run. Fix first, then retrain for a full epoch
(which should help yes/no and a-d), preferably after removing image-unsupported facts from the caption targets.

Also: `docs/HANDOFF_PROMPT.md` was rewritten as the complete handover (state, bugs with file/line, ordered next steps,
facts, rules). `CLAUDE.md`, `docs/STARTUP_GUIDE.md` (presenter warnings), the Development Plan (B5 note) and
`docs/AUDIT_REPORT.md` (pointer to the new findings) were updated. `.gitignore` now ignores `*.aux.xml`: three GDAL
statistics sidecars appeared in `frontend/public/real/` at 01:05 on 2026-09-22, written when a GIS tool opened the files.
The Claude memory note on the GPU was corrected: it had said local fine-tuning cannot fit, which the two local runs
disproved.

### 2026-09-21 — Upload metadata read from the file, four more real images, interpreter narrowed, all docs refreshed

The owner asked for four things: fix the upload metadata bug, add more images and questions if feasible, update every
markdown file, and give a commit message.

- **Metadata bug (audit 3.1) fixed.**
  - New `POST /v1/inspect` (`routes_analyze.py`, `InspectResponse` in `api_models.py`). It runs the existing
    `metadata_service.inspect_file` on one upload and adds `render_preview`: a PNG data URI, longest side ≤ 512, via
    Pillow for 8-bit images and a 2-98 percentile rasterio stretch otherwise.
  - The bytes go to a temporary directory under a fixed name, and the client's filename is only a label.
  - `ImageUploader.tsx` no longer invents CRS, GSD, bands or dates. It shows "Reading file…", then fills the card from
    the reply. If the backend is unreachable the fields stay unknown (`metadataStatus`, frontend-only).
  - `ImagePreview` labels unknowns "No CRS", "GSD unknown" and "Date unknown". The old "Unprojected" and "Current"
    were claims.
  - This also resolves the TIFF-preview verification gap.
- **Audit items fixed on the way:**
  - 3.2: removing an image clears its file, and `resolveFile` checks the image first.
  - 3.3: drag-and-drop is implemented.
  - 3.4: the same file can be picked again.
  - 3.5: blob URLs are revoked once the backend preview arrives.
- **Four more real images.**
  - Candidates were unseen-tile patches with at least 3 `bench_hard` questions and at least 80% correct in the stored
    run-2 evaluation. All 8 candidates, re-asked through `ml/serve_vqa.py` with the float32 answer reading, were 100%
    correct.
  - Four were added for variety of country and season: T29UPU_38_37 (Ireland, Apr 2018, 5 questions),
    T34UEG_28_34 (Lithuania, Apr 2018, 6), T34TCR_36_25 (Serbia, Aug 2017, 4) and T29SND_42_38 (Portugal, Nov 2017,
    3). That makes five images and 23 questions.
  - `tools/make_real_sample.py` now builds a list (`PATCH_IDS`). It re-checks that no tile appears in training, checks
    pixels against the evaluation PNGs, and writes `frontend/src/data/realSamples.json` (replacing `realSample.json`).
  - The UI has one green "Live model" row in `DemoScenarioBar` with a card per image (thumbnail, country, month,
    question count), above a "Demo engine" row. The context tracks the sample by id (`activeRealSample`).
- **Interpreter narrowed (audit 2.3, partly).** Three of the new questions were misrouted: "between" (a range or an
  adjacency) went to change, and a choice question saying "where is" went to grounding. Bare "between" is no longer a
  change cue, and a question listing a)–d) options is never grounding or captioning. Regression tests are in
  `tests/test_orchestration.py`, and `tests/test_real_model.py` checks every sample question routes to `single_vqa`.
  The demo parity tests are unchanged and passing.
- **Tests**: 195 pytest (new `tests/test_inspect.py`, 7 tests), 72 Vitest (`LiveModelSample.test.tsx` covers one card
  per image, per-image chips, hand upload, inspect "reading" to "read", backend down leaving "unknown", and a removed
  image never being sent). `tsc` and the build are clean, and lint shows the 2 known warnings.
- **Browser (Chromium)**: all 23 questions go card, chip, Run, Results. Each is answered live (200), matches the
  reference, and the console is clean. The ordinary-upload check (demo SAR GeoTIFF) shows EPSG:32646, 10 m, the SAR
  modality and a rendered preview. The invented EPSG:32643 / 0.65 m are gone.
- **Docs refreshed**: `CLAUDE.md` (routes, live-model paragraph, upload rule), `docs/STARTUP_GUIDE.md` (§3a rewritten:
  five-image table, hand and ordinary uploads; checklist counts; rough edges), `docs/SatQuery_AI_SPDD.md` (§9.1 note,
  new §9.7, §12.1), `docs/SatQuery_AI_Development_Plan.md` (F2, C2 note), `docs/AUDIT_REPORT.md` (status block),
  `docs/HANDOFF_PROMPT.md` (rewritten), this log. `docs/Problem_Statement.md` and
  `docs/SatQuery_AI_Final_Synthesized_Solution.md` describe the problem and the design principles, so they needed no
  change.

### 2026-09-21 — The live-model sample can be uploaded by hand

The owner wants to upload the image themselves during the demo. Before this change, a hand upload of
`frontend/public/real/bigearthnet_T29UPU_55_58.tif` went through `ImageUploader`'s placeholder metadata:
- it showed EPSG:32643 and 0.65 m, which are wrong (the audit's 3.1);
- the preview was broken, because browsers cannot display a TIFF;
- the question chips, the reference check and the no-fallback rule did not apply.

The change:
- `ImageUploader` now recognises the sample's GeoTIFF or PNG by file name in slot 1 and calls
  `loadRealSample(undefined, file)`. That sends the uploaded bytes and shows the true facts with the PNG preview.
- For the PNG, CRS, GSD and time are left null rather than borrowed, since the PNG has no georeference.
- A hand upload keeps the typed query.
- `realSampleActive` now accepts either file name.
- Other uploads are unchanged, so the placeholder-metadata defect remains for them.
- Tests: `LiveModelSample.test.tsx` +2 (GeoTIFF: true CRS, PNG preview, the file itself sent, no fetch; PNG: no
  invented CRS). Vitest has 68, all passing; `tsc` is clean and lint shows the 2 known warnings.
- **Browser check** (Chromium, real file through the file input): the card shows EPSG:32629, 10 m and 2017-11-12,
  the chips appear, the multiple-choice question is answered live (200) and matches the reference, and there are no
  console errors.
- Docs: `STARTUP_GUIDE.md` §3a gives the upload path.

### 2026-09-21 — Live-model sample moved into the studio: one place to pick an image and a question

The owner found two input areas confusing. The separate panel had its own image and question list above the studio's
uploader and query box. The owner chose the studio as the single place. The change:
- `RealSamplePanel.tsx` was deleted.
- The sample is now the first card in `DemoScenarioBar.tsx` ("Live Model · Real Data — BigEarthNet Sentinel-2
  (Trained LoRA)", green border; the bar's badge now reads "Demo Engine + 1 Live Model"). Clicking it calls the
  existing `loadRealSample()`, so the real GeoTIFF fills Image 1.
- While the sample is active, `QueryInput.tsx` swaps its suggestion chips for the sample's 5 BigEarthNet questions
  and shows the accuracy note. Any other scenario brings the ISRO queries back.
- The first card's contrast was checked in screenshots and raised (light background, dark green text).
- The test file became `LiveModelSample.test.tsx`: 7 tests driving the preset bar and the query box, including that
  the chips switch back.
- Vitest has 66 tests, all passing. Build and `tsc` are clean, and lint shows the 2 known warnings.
- **Verified in the browser again** (headless Chromium): all 5 questions go preset card, chip, Run, Results. Each is
  answered live (200), matches the reference, and the console is clean.
- Docs: `STARTUP_GUIDE.md` §3a steps and `CLAUDE.md`.

### 2026-09-21 — Live-model demo verified in a browser; one bug found and fixed

The owner asked for a browser check. Playwright and Chromium were installed in a throwaway venv in the session
scratchpad; nothing was added to the project or to `requirements.txt`. With the model server, the backend (URL set)
and Vite running, a script opened `/analyze`, clicked each of the 5 panel questions, ran the analysis and read the
Results page.
- **All 5 pass in the browser.** Each run is one `POST /v1/analyze` returning 200, the badge reads "Live Backend",
  the reference check says "the model matches it", the trace shows the `b5_run2_lora` step with its distribution and
  latency, no boxes are drawn, and the console is clean.
- **Model server stopped:** the page stays on `/analyze` with the red "No answer" box naming the start command, after
  one 503. No mock result is shown.
- **Bug found only in the browser, fixed.** The Results page's Visual Evidence Canvas showed a broken image.
  `resolveAssetUrl` (`frontend/src/services/api.ts`) prefixed every relative path with the API base, so the
  frontend's own `/real/...png` was requested from `:8000` and returned 404. It now prefixes only backend paths
  (`/storage/`, `/v1/`) and leaves other same-origin assets alone. A regression test was added in `api.test.ts`.
  The existing demos were unaffected because their previews are data URIs. After the fix the canvas shows the patch.
- Vitest now has 65 tests, all passing; `tsc -b` is clean. Files (uncommitted): `frontend/src/services/api.ts`,
  `frontend/src/services/api.test.ts`, this log.

### 2026-09-21 — Live-model website demo: the run-2 adapter answers a real BigEarthNet image through the full pipeline

The owner asked for a simple walkthrough in the website where a real trained model answers questions about a real
satellite image, with no demo model or demo data on that path. The plan was approved first. What was built:

- **`ml/serve_vqa.py`** (new, `.venv-ml`). A FastAPI server on `127.0.0.1:8001` that loads Qwen2-VL-2B 4-bit and
  `data/b5_run2/adapter_final` once. `POST /vqa {image_path, question}` returns the answer, its probability over the
  candidate answers (yes/no or the offered a-d), the greedy reply, the latency and the model, revision and adapter.
  - Two measured pitfalls are handled in the code. A separate forward pass after `generate` reads stale Qwen2-VL
    rotary state, so the distribution comes from the first `generate` step.
  - The model's bfloat16 logits tie yes and no exactly on 3 of the 5 sample questions (0.5 / 0.5). Greedy decoding
    then broke the tie by token order, so the candidate logits are recomputed in float32 from the hidden state
    entering `lm_head`, which is not quantised.
  - Questions outside the trained format get a free-form reply, flagged as such.
- **Backend**:
  - `config.py`: `VQA_MODEL_URL` (unset by default, so behaviour is unchanged), `VQA_MODEL_TIMEOUT_SECONDS` and
    `MODEL_MEDIUM_PROBABILITY` (0.75).
  - `services/model_client.py` (httpx; `ModelUnavailableError` becomes 503, `ModelError` becomes 502, both in
    `routes_analyze.py`).
  - `VqaCaptionSpecialist.answer_with_model` sends the uploaded file itself.
  - The router's single-image branch skips the demo grounding call and records a trace step with the adapter, the
    answer distribution, the raw reply and the latency.
  - `ConfidenceScorer` takes the tier from the model probability: Medium at or above 0.75, otherwise Low, never
    High. The rationale states the held-out accuracy. The scenario engine is not called on this path (C0 partial).
  - The wire schema is unchanged, so `satquery.ts` needed no edit.
- **Real sample**: `tools/make_real_sample.py` renders patch `S2B_MSIL2A_20171112T114339_N9999_R123_T29UPU_55_58`
  (Ireland, 12 Nov 2017) from its raw B04/B03/B02 bands with `b1_slice.render()`.
  - The script refuses to write unless the pixels equal the evaluation PNG.
  - It writes a 3-band GeoTIFF keeping the patch's own CRS (EPSG:32629) and 10 m transform, a PNG preview
    (`frontend/public/real/`), and `frontend/src/data/realSample.json` with the patch's 5 `bench_hard` questions and
    reference answers.
  - Tile T29UPU appears in neither `train.jsonl` nor `validation.jsonl`.
  - The patch was chosen because run 2 got all 5 right in the stored evaluation (a grey image got 3, text-only 2).
    It is a sample, not an accuracy figure, and the panel says so.
- **Frontend**:
  - `RealSamplePanel.tsx` on `/analyze`: the image, facts, the 5 questions as buttons and the accuracy caveat.
  - `SatQueryContext`: `loadRealSample`, `realSampleActive`, `analysisError`. While the sample is loaded, a failed
    call shows a red "No answer" box instead of falling back to a mock result.
  - `ReferenceCheck.tsx` on Results grades the answer against the BigEarthNet reference.
  - The sample's JSON lives in `src/data/` because Vite cannot import from `public/`.
- **Tests**:
  - `tests/test_real_model.py` (15, fake model server). It checks that the model receives the uploaded bytes, that
    the scenario engine is never called (booby-trapped), that there are no boxes or grounding step, the trace
    fields, the tier thresholds, the free-form label, the 503/502 paths, that other tasks and the switch-off path
    stay on the demo engine, and that the interpreter routes all 5 sample questions to `single_vqa`.
  - `tests/test_ml.py` +3: question kind, candidates, option text.
  - `RealSamplePanel.test.tsx` (6).
  - Totals: 176 pytest, 64 Vitest. `tsc -b && vite build` is clean, and lint shows the 2 known warnings.
- **Live result** (model server, backend with the URL set, and Vite running; driven over HTTP as the browser would):

  | Question | Answer, probability | Tier | Reference |
  |---|---|---|---|
  | inland waters? | No, 78% | Medium | no |
  | pastures at least 90%? | No, 51% | Low | no |
  | complex cultivation bordering urban fabric? | No, 50% | Low | no |
  | exactly two arable areas? | No, 51% | Low | no |
  | arable share (a-d) | b) 30 to 60%, 34% | Low | b |

  - All 5 are correct. The specialist step takes 650-1,000 ms, of which about 400 ms is model time.
  - The metadata read from the uploaded file: EPSG:32629, 10 m, 2017-11-12.
  - With the server stopped, the call returns 503.

**Caution.** The answers are right but mostly unconfident. Three yes/no answers are within 1 point of a coin flip,
consistent with run 2's held-out result (no binary lead on unseen tiles). The demo shows the pipeline running a
real model honestly, not a strong model. **Docs**: `STARTUP_GUIDE.md` §3a (three-terminal run and expected
answers), `CLAUDE.md`, Development Plan C0/C2 marked PARTIAL, `.env.example`. **Not verified**: a click-through in a
browser (see Verification gaps). Files (uncommitted): `ml/serve_vqa.py`, `tools/make_real_sample.py`,
`backend/app/{config.py,services/model_client.py,specialists/vqa_caption.py,orchestrator/specialist_router.py,
orchestrator/confidence_scorer.py,orchestrator/orchestrator_service.py,api/routes_analyze.py}`,
`frontend/public/real/*`, `frontend/src/data/realSample.{ts,json}`,
`frontend/src/components/{RealSamplePanel,ReferenceCheck}.tsx`, `RealSamplePanel.test.tsx`, `SatQueryContext.tsx`,
`UploadQuery.tsx`, `Results.tsx`, `tests/test_real_model.py`, `tests/test_ml.py`, and the docs above.

### 2026-09-21 — Whole-project audit written to `docs/AUDIT_REPORT.md` (no code changed)

Read-only audit of backend, frontend, tests, `ml/` and all markdown, with the main claims reproduced against the running code.
Baseline confirmed: 158 pytest and 58 Vitest pass, `tsc` clean, lint shows the two known warnings. Headline findings: the session
database is downloadable at `/storage/satquery.db`; upload filenames are unsanitized (files written outside the storage root); the
optical+SAR `modality_mismatch` rule misses `multispectral` files; `requiredModalities` is never enforced; the confidence scorer's
own rules are unreachable behind `ScenarioEngine`; the frontend fabricates upload metadata and a High-confidence result on API
failure; several plan items marked DONE (B2, B7, B10, B11, B14, F2) are only partly implemented. Nothing is fixed yet; the report
proposes a seven-step order. Files (uncommitted): `docs/AUDIT_REPORT.md`, `docs/PROGRESS_LOG.md`.

### 2026-09-21 — Phase 2 step 5: run 2 scored (six runs); passes on tiles seen in training, does not generalise on binary

Sources: `data/b5_eval/run2_hard_{main,heldout}{,_blind,_mismatch}.json` and `textonly_run2_hard.json` (text-only model fitted
on `data/b1_v2/train.jsonl`). Unreadable replies: 0 everywhere except 1 binary reply in each of heldout blind and mismatch.

| | main binary | main mcq | heldout binary | heldout mcq |
|---|---|---|---|---|
| Real image | 55.3% | 34.5% | 50.1% | 32.9% |
| Grey image | 48.1% | 27.3% | 51.2% | 28.5% |
| Mismatched image | 48.8% | 28.5% | 49.1% | 28.0% |
| **Lead over text-only** (paired, 95% CI, McNemar p) | **+6.1** (2.1 to 10.0), p = 0.003 | **+8.6** (3.8 to 13.2), p = 0.0006 | **-0.5** (-6.0 to 5.0), p = 0.91 | **+8.6** (3.3 to 13.6), p = 0.002 |
| **Real minus grey** | **+7.2** (4.1 to 10.0), p < 0.0001 | **+7.3** (3.5 to 10.7), p = 0.0002 | **-1.2** (-5.1 to 2.9), p = 0.63 | **+4.4** (0.1 to 8.4), p = 0.052 |
| Answer change, real vs mismatched | 23.7% | 43.8% | 17.2% | 44.8% |
| Answer change, real vs grey | 28.8% | 42.1% | 26.2% | 44.1% |

Overall answer change, real vs mismatched: 30.9% main, 30.3% heldout. Text-only scores 49.7% binary and 25.2% mcq over all
3,000 rows, i.e. chance, which is why the leads are larger than run 1's.

**Against the pre-registered test.** *Primary (main):* **PASS**, 6.1 on binary and 8.6 on mcq, same sign, both p < 0.05.
*Secondary (main):* **PASS**, 7.2 and 7.3 points, both p < 0.05. *Tertiary:* overall change against a mismatched image 30.9%
(above 25%), but binary alone is 23.7%, just below it. *Generalisation:* **binary does not generalise.** On the held-out
tiles binary has no lead over text-only (-0.5, p = 0.91) and real is not better than grey, so the main binary result is stated
as "on tiles seen in training". Held-out mcq keeps a lead over text-only (+8.6, p = 0.002) and real beats grey by 4.4 (p = 0.052,
just short of significance).

**By category** (only groups with n of at least 100). Main, real vs grey: binary/adjacency 55.0 vs 50.1, binary/presence 55.4
vs 45.0, mcq/adjacency 38.6 vs 35.8, mcq/area 29.6 vs 22.4. Held-out: binary adjacency 47.5 vs 50.7 and presence 50.0 vs 50.0
(no image effect), mcq/adjacency 32.2 vs 34.5 (none), mcq/area 30.6 vs 21.3 (image effect). **Unreadable, not passes:** climate
zone, country, count, presence (mcq), relative position and season have too few rows (under 100, most under 25).

**Cautions.** The lead is measured against a text-only model that is at chance on the new set, so the leads are not comparable to
run 1's, and run 2's absolute mcq accuracy (34.5% main) is lower than run 1's (36.7%). The evidence for image reading is
concentrated in mcq/area on held-out tiles and in main binary presence; adjacency questions show none on held-out tiles.
One training run, one seed, no repeat. `--resume` remains unexercised on the real model. No `backend/` or `frontend/` change.
Nothing is wired into the pipeline (C0 must come first).

**Docs refreshed the same day:** this log (status row, Next step, Open item 4), `CLAUDE.md` (ML paragraph), `docs/STARTUP_GUIDE.md`
(158 tests), `docs/SatQuery_AI_Development_Plan.md` (B5 status) and `docs/HANDOFF_PROMPT.md` (rewritten: Phase 2 is done, the next
session asks for the follow-up decision). Files (uncommitted): `ml/b5_train_lora.py`, `ml/b5_change_rate.py`, `tests/test_ml.py`
and the docs above.

### 2026-09-21 — Phase 2 step 4: run 2 trained on `data/b1_v2` (`data/b5_run2`)

`ml/b5_train_lora.py --data data/b1_v2 --out data/b5_run2 --size 448 --max-steps 300 --grad-accum 16 --eval-every 100
--eval-n 100 --save-every 100`, all other hyperparameters at the run-1 defaults. **300 steps in 6,192 s (1 h 43 min),
against the ~3 h 40 estimate and run 1's 3 h 38; the reason for the speed-up was not investigated.** 0 non-finite steps,
peak 2,934 MiB. Validation (92 choice questions each time, too few to read a trend): loss 0.590 / 0.545 / 0.541 and choice
accuracy 40.2% / 41.3% / 42.4% at steps 100 / 200 / 300. Outputs: `adapter_step{100,200,300}`, `adapter_final`,
`state_step{100,200,300}.pt`, `train_log.jsonl`. **`--resume` was not exercised** (the run did not die), so it remains
tested only on a toy model. Validation numbers say nothing about image reading; step 5 (six-run scoring) decides that.

### 2026-09-21 — Phase 2 step 3: run 1 re-scored on `bench_hard` main; it does not clear the primary bar, so the retrain goes ahead

Run 1 (`data/b5_run1/adapter_final`, trained on the old leaky slice) on `bench_hard` **main** (1,186 binary, 660 mcq, no
unreadable replies in any condition). Sources: `data/b5_eval/run1_hard_main{,_blind,_mismatch}.json`,
`textonly_run1_hard.json` (text-only model fitted on `data/b1_slice/train.jsonl`, scored on the same rows).

| Measure | Binary | MCQ |
|---|---|---|
| Real image | 54.2% | 36.7% |
| Grey image | 47.8% | 30.3% |
| Mismatched image | 49.2% | 31.8% |
| Text-only | 50.1% | 35.0% |
| **Lead over text-only** (paired) | **+4.1 pts, p = 0.012** | **+1.7 pts, p = 0.53** |
| **Real minus grey** (paired) | **+6.4 pts, p = 1e-5** | **+6.4 pts, p = 0.004** |
| Answer change, matched vs mismatched | 20.5% | 40.9% (all: 27.8%, CI 25.8-29.9%) |
| Answer change, matched vs grey | 25.0% | 49.1% (all: 33.6%) |

**Against the pre-registered test.** Primary (lead over text-only): needs 5+ on both types; binary is 4.1 and mcq 1.7 with
p = 0.53, so it is **not a pass**, nor a weak pass (no type reaches 5). Secondary (real minus grey): **passes** on both
types. Tertiary: the overall change rate is above 25%, binary alone is below it. Because the primary bar is missed, the
rule says retrain. **Reading:** unlike on the old bench, run 1 does show some dependence on the image (grey and mismatched
pictures both hurt it), but its edge over a model with no image is small on binary and absent on mcq. This is run 1 only;
it is not evidence about run 2. Only the `main` part was scored, so tile memorisation is not separated out here.

### 2026-09-20 — Phase 2 steps 1-2: VRAM gate passed; resumable training and `b5_change_rate.py` written (CPU only)

**Step 1.** After a restart `nvidia-smi` read **362 MiB used, 3,603 MiB free of 4,096** (the owner saw 384 MiB idle a
moment earlier; the difference is normal drift). That clears the ~3,100 MiB bar, so the retrain uses `--size 448` as in
run 1. The processes still on the GPU are Windows shell components, Edge WebView2, Armoury Crate and VS Code; re-check
right before step 4.

**Step 2a, `ml/b5_train_lora.py`.** New pure functions `save_state`, `load_state` and `newest_state`. At each
`--save-every` and at the end it now writes `state_step{N}.pt` beside the adapter (optimiser and GradScaler state, step,
data cursor and shuffle order, skipped-step count, the total step count, and the Python, torch and CUDA RNG states).
`--resume DIR` reloads the newest state, restores the adapter weights from `adapter_step{N}` (or `adapter_final`) with
`set_peft_model_state_dict`, and restarts the loop at the saved step. It refuses a state saved for a run of a different
length, because the cosine schedule would not match. **The resume path is tested only on a toy model on CPU; it has not
been run against the real 4-bit Qwen model**, so the first real resume is still unproven.

**Step 2b, `ml/b5_change_rate.py`.** Pairs two `b5_eval.py` results on `(type, id)` and reports the changed share overall,
per type and per `type/category`, with a Wilson 95% interval; a pair where either side has `parsed is None` goes in its
own bucket and counts neither as change nor agreement. It raises `SystemExit` on a file with no `replies`.

**Tests: 158 pytest passing** (152 before). Six were added to `tests/test_ml.py`, not the four the handoff expected: four
for the change rate, two for training state (identical continuation of optimiser, batch order, parameters and RNG after a
restore; refusal on a length mismatch). No `backend/` or `frontend/` change, no GPU use. Files (uncommitted):
`ml/b5_train_lora.py`, `ml/b5_change_rate.py`, `tests/test_ml.py`, `docs/PROGRESS_LOG.md`.

### 2026-09-20 — Phase 2 planned (owner-approved); startup guide written; six stale statements corrected

Read-only orientation, then a plan the owner approved. **Measured:** 152 pytest passing; free VRAM **2,902 MiB** (1,194
of 4,096 in use by Chrome, Edge WebView2, VS Code and others), below the ~3,100 MiB bar, so the retrain needs those
apps closed or `--size 392`; `data/b1_v2/` matches this log (19,489 / 1,197 / 3,000, all bench rows carry `pair_image`).
**Owner decisions:** full six-run scoring matrix (Phase 2 is ~7 h, not ~5); optimiser state saved **and** a `--resume`
flag; more bench-side patches proposed but **not** run in Phase 2.

**Corrections to this log:** "`ml/` has no automated tests" (twice; `tests/test_ml.py` has 12); the control estimate
(about 40 min, now about 80 min for three conditions); the Phase 2 total (5 h, now ~7 h); "point `b5_train_lora.py` at
the new data" (`--data` already does it); Open item 4 omitted four `ml/` files. **`CLAUDE.md`** described `ml/` as it was
before Phase 1; its ML paragraph is corrected.

**New:** `docs/STARTUP_GUIDE.md` (start the stack, seven-scenario demo script, tickable manual checklist, known rough
edges, troubleshooting). Its scenario table is taken from `frontend/src/data/demoParity.json`; the box counts come from
this log's earlier verified table. **It has not been walked through in a browser this session.** No code, GPU or
`backend/`/`frontend/` change. Files (uncommitted): `docs/STARTUP_GUIDE.md`, `docs/PROGRESS_LOG.md`.

### 2026-09-20 — Handoff written for a plan-mode Phase 2; knowledge graph partly refreshed

`docs/HANDOFF_PROMPT.md` was rewritten: the next session starts in plan mode, orients read-only, and plans Phase 2
(control run, two missing pieces of code, retrain, judging) before any GPU use. The owner created
`https://github.com/Macbeth1501/SatQuery` with a fresh single-commit history.

**Graph.** `graphify update .` (code) rebuilt the code graph: 1,031 nodes, 2,240 edges, 58 communities, current
for all `ml/` and `tests/` files. An attempted `/graphify . --update` for the nine changed documents was **not
applied**: the extraction agent skimmed `PROGRESS_LOG.md`, `HANDOFF_PROMPT.md` and the Development Plan and used
placeholders for `frontend/index.html`, and the merge would have shrunk the graph to 997 nodes (-34) because a
shallow re-extraction replaced 432 richer nodes; graphify's shrink guard refused to overwrite, and it was not
forced. **`graph.json` is unchanged (1,031 nodes) and does not contain the new documents' concepts.** The nine
files were stamped in the manifest and cached, so a later `--update` will not re-extract them; run
`/graphify . --force` or a full `/graphify .` to rebuild the document layer properly.

### 2026-09-20 — Phase 1 done: leak-neutral training set and `bench_hard` built (CPU only, no GPU)

**Method changed from the plan, and why.** The plan said rebuild wrong options where ground truth is held. It is
not held: captions are lossy prose, so the options cannot be rebuilt exactly. Instead `ml/b5_deleak.py` keeps
every published question verbatim and chooses WHICH questions to keep by **raking**: per (type, category) each
example gets a weight, iterated until every multiple-choice option text is correct 1 time in 4 when offered
(and each answer letter 1 in 4), and every binary word or word pair is answered "yes" half the time; examples
are then drawn in proportion to weight, never topped up with zero-weight ones. The only text edit is
"Autumn" -> "Fall" in season options. This is the owner-approved departure from the published dataset in a
narrower form: no question or option was rewritten, so nothing was invented. Two first attempts failed the
gate and were fixed: summing per-feature corrections overshot (weights collapsed onto one answer; mean per
example fixed it), and topping a category up to its quota pulled leaky questions back in (`mcq/count` and
`mcq/presence` scored about 30% text-only; the sampler now returns fewer examples instead).

**Two errors in my earlier numbers, corrected.** Leave-one-out multiple-choice scoring is anti-predictive once
the signal is near zero (it scored a balanced set at 0.0%), so `out_of_fold` now uses patch-grouped 5-fold
cross-validation. And the plan estimated ~10,000 extra patches; questions come first and patches follow, so
**19,159 patches were extracted** (57,477 band files, 441 MB of PNG for 17,121 kept; one streaming pass).

**Gate results (text-only baseline, patch-grouped cross-validation, tolerance 3 points).**
- Training set (`data/b1_v2/train.jsonl`, 9,470 binary, 8,588 multiple choice, 1,431 captions): **49.5% binary,
  23.9% multiple choice. PASS.** Per category 47-51% binary and 22-28% multiple choice.
- `bench_hard` (from the local `bench_subset`, no new download), text-only fit on the NEW slice: main 49.2% binary
  (n=1,186) and 25.9% multiple choice (n=660); heldout (reserved tiles) 50.6% (n=607) and 24.3% (n=547). **PASS.**
- The same test with the text-only model fit on the OLD slice: main 50.1% binary, **35.0% multiple choice**;
  heldout 53.2% and 36.2%. So `bench_hard` is genuinely harder for text-only than the old bench (62.3% / 42.5%)
  even for a model trained on leaky data, and the rest of the leak is only closed by training on the new slice.

**Limits found, not fixed.** (1) The bench pool is small (1,082 patches), so raking leaves almost nothing in
`mcq/climate zone` (6 main, 4 heldout), `mcq/country` (4, 4), `mcq/count` (9, 5), `mcq/presence` (84, 8) and
`mcq/relative pos` (21, 10). **The multiple-choice test is effectively adjacency, area and season** (about 85%
of it); the pass/fail test cannot say anything about the other categories, and heldout multiple choice (547)
is under the planned 600. Raising it means extracting more bench-side patches, which the raw archive allows,
and has not been done. (2) Raking removes only single-option and single-word leaks; passing the gate is the
evidence, not the method, and a stronger text model could find interactions. (3) Nothing has been run on the
GPU, so no claim about the adapter follows from this step.

**Also built.** `ml/b5_text_only.py` (the baseline as a script: reproduces 62.3% bench binary exactly; its
multiple-choice figure is 42.5% against the logged 40.2%, a parser and smoothing difference in the earlier
inline version), `ml/b5_compare.py` (paired McNemar, exact, checked against a hand-worked table),
`ml/b1_v2.py` (select / extract / build / bench, tile reservation and buffer as in B1), `b5_eval.py` now stores
every reply and has `--bench-file`, `--part` and `--mismatch-image`. Tests: 12 new in `tests/test_ml.py`
(option parser, baselines, raking, sampler, Autumn edit, McNemar, strict answer parser). **152 pytest passing;
Vitest unchanged (58).** The old `b5_eval.py` results have no per-example replies, so they cannot be paired.

**Reserved tiles:** T29UPU (Ireland), T29SND (Portugal), T34TCR (Serbia), T34WFS (Finland), T32TMT
(Switzerland), T34UEG (Lithuania). 53,214 more official train patches fall on them and were excluded.

**Files (uncommitted).** New: `ml/b5_text_only.py`, `ml/b5_deleak.py`, `ml/b5_compare.py`, `ml/b1_v2.py`,
`ml/b1_v2_report.json`, `ml/b1_v2_bench_report.json`, `tests/test_ml.py`. Changed: `ml/b5_eval.py`,
`docs/PROGRESS_LOG.md`. Data is in gitignored `data/b1_v2/`. No commit, pull or push.

### 2026-09-20 — The de-leak plan, and why "keep what the text model gets wrong" was replaced

**Measured first, CPU only, nothing trained.** Refitting the text-only baselines from scratch reproduces
**62.3% on bench binary exactly**; the multiple-choice reproduction gives **42.5% against the logged 40.2%**,
a difference in the option parser and smoothing, which is one reason the baseline is now being committed as
a script rather than run inline. Out-of-fold on the *training* questions the same models score **70.1%
binary and 58.5% multiple choice**, so **the leak is markedly stronger inside the training set than on
bench** and training rewards text priors more than the bench score suggests. Counted precisely: **840 of the
919 training `mcq/season` questions carry an "Autumn" option** (never correct), and 40 of 45 on bench.

**The owner's proposed filter, measured.** Keeping only the examples the text-only model gets wrong or is
unsure about (binary |p−0.5| < 0.05, multiple choice top1−top2 < 0.02) leaves **3,136 of 7,980 binary and
3,584 of 7,980 multiple choice**, plus the 1,995 captions: 8,715 of 17,955, on the same 1,995 images. Per
category the survivors are binary adjacency 843, area 919, count 607, presence 767; mcq adjacency 392, area
630, climate zone 529, **count 213** (the most leaked), country 634, presence 595, relative pos 164, season
427. That is enough data for 300 steps, so the filter does not starve the run.

**But it was rejected as the primary route.** The filter selects on the label: an example survives *because*
the text prior points the wrong way, so the surviving set carries an **inverted** prior of about the same
strength as the one removed, and a model trained on it learns to answer against the wording — a different
text shortcut, not the absence of one. The same objection breaks the metric: on a bench filtered this way
the text-only model scores near zero by construction, making "lead over the text-only model" meaningless.

**A label-independent filter (keep only what the text model cannot call, ignoring the answer) was measured
as the alternative and is sufficient for binary only:** binary |p−0.5| < 0.10 keeps 2,619 of 7,980 at
**54.8%** text-only accuracy (chance 50%), but multiple choice top1−top2 < 0.05 keeps 1,296 at **40.1%**
(chance 25%) — still 15 points of leak, because a near-tie at the top of four options is itself informative.
**Filtering alone cannot de-leak four-option questions.**

**Two costs were re-measured and one assumption overturned.** `data/BigEarthNet/extract_bench.log` shows a
full streaming pass over the 63 GB `BigEarthNet-S2.tar.zst` takes about **370 s**, and 212 GB are free on
D:, so the 1,995-patch ceiling is **one ~6-minute CPU pass away from ~10,000 patches** — it was treated as
an expensive constraint and is not one. Separately, `BigEarthNet.txt.parquet` was checked and carries
`country`, `season`, `climate_zone`, `latitude`, `longitude` but **no land-cover label column**, and no
BigEarthNet label metadata exists under `data/`; so options can be rebuilt exactly for country / season /
climate zone, and for presence / count / area only by recovering each patch's class-and-area list from its
own caption text.

**The approved plan.** Rebuild the wrong options from the empirical label distribution where ground truth is
held, margin-filter where it is not, drop the Autumn/Fall leak, reserve whole Sentinel tiles at extraction
time so a real held-out-tile test becomes possible, build a `bench_hard` evaluation set of n ≥ 600 per type
with the text-only model gated to within 3 points of chance, store per-example replies so a paired McNemar
test exists, and only then retrain once. The pass bar is fixed before the run: **≥ 5 points over the
text-only model on both binary and multiple choice, paired, with p < 0.05 on at least one**, plus a
real-minus-grey gap and a matched/mismatched pair test that holds the text identical and changes only the
pixels. A fail stops the VQA line and moves to B6 (grounding boxes), where no text prior can supply a
coordinate.

**Also corrected in this log:** Open item 4 still said training runs on a cloud GPU and that no training code
or adapter existed. Both were false — QLoRA fits on this card and `data/b5_run1/adapter_final` exists.

**Nothing under `ml/`, `backend/` or `frontend/` changed in this step; only this log.** No GPU was used.

### 2026-09-20 — Why the questions leak their answers (inferred from the data; the generator is not shipped)

The BigEarthNet.txt download contains the parquet, its README and loader scripts, but **no question
generator**, and the README does not say how the questions or their wrong options were made. So the mechanism
below is inferred from the 15,960 training choice questions in `data/b1_slice/train.jsonl`, not read from code.
The pattern is consistent: **the correct answer follows the dataset's own label frequencies, while the wrong
options look drawn far more evenly, so an option's identity predicts whether it is correct.** Measured as
"times correct / times offered" in training:

- `mcq/count`: option "1" is correct 84% of the times it is offered (854/1,018); "2" 29%, "3" 14%, "4" 4%,
  "5" 2%.
- `mcq/country`: Finland 57%, Portugal 39%, Serbia 37%, Austria 25%, Ireland 25%, Lithuania 23%, Belgium 8%,
  Luxembourg 2%.
- `mcq/season`: Spring 45%, Summer 25%, Winter 21%, and **"Autumn" is never the correct option** (it is
  offered 840 times and never right) while "Fall" is right every time it appears (79 of 79): the answer key
  says "Fall" and the wrong options say "Autumn". This is a pure text leak. (The 21% of season questions that
  list both were already dropped by B1.)
- `mcq/climate zone`: "Cold, no dry season, warm summer" 65%, then 40% / 41% / 37% / 30% / 10%, and three
  zones at 0-1%.
- `mcq/area`: no cue (the correct range is the unique widest 24%, the unique narrowest 5%, the lowest 37%,
  against 25% chance). Its 33% text-only score is weak.
- Binary questions leak through their wording: for `binary/count`, "less than" is "no" 13% of the time,
  "fewer" 26%, "one" 27%, but "exactly" 68% and "more than" 62%; for `binary/area`, "between" is "no" 63%
  and "only one" 83%.

Some of this is real regularity in the data (most land-cover classes have one region per patch, so "exactly
two" is usually false), and some is an artefact of how wrong options were chosen. Either way a model can
collect it without looking at the image. **This explains why the text-only baseline (62.3% binary, 40.2%
multiple choice) matches the adapter.** It also means the plan's headline metric, accuracy on these
questions, will overstate image understanding for any model trained on them unless it is compared against a
text-only baseline.

**Not changed:** no training data, code or adapter. **Constraint on fixing it:** the local slice has only
1,995 training patches, and more imagery needs a further extraction from the raw archive.

### 2026-09-20 — Loss masking checked; a text-only model reproduces nearly all of the adapter's score

**Loss masking (step 1) is correct.** `collate()` was run on one training example of each type (448 px). In
each, the labelled tokens are exactly the answer plus `<|im_end|>` (binary `no<|im_end|>`, 2 tokens; multiple
choice `b<|im_end|>`, 2 tokens; caption 53 tokens), they are contiguous to the end, they start right after
`<|im_start|>assistant\n`, and none of the 256 image tokens carries a label. So the masking is not the reason
training loss did not fall. One consequence, not a bug: a choice example has only one informative label token
(the other, `<|im_end|>`, is trivial), so its loss is the answer token's loss divided by two, and the per-step
loss sits near the chance level for a mostly-choice mixture (my back-of-envelope figure is about 0.45-0.5 at
chance, against the observed 0.19-0.50; the caption share is small and its per-token loss was not measured).
A flat training loss is therefore consistent with the model having learned the format and text priors but
little more, though that reading is not proven.

**Answer balance (step 2), from `data/b1_slice/train.jsonl` (7,980 binary, 7,980 multiple choice):** letters
are balanced (each of a-d is 25-27% in every category). Binary is balanced (50-51%) except `adjacency`, which
is 61.3% "no". Guessing the training-set commonest answer per category scores only 55.8% binary and 24.5%
multiple choice on the bench sample, so the leak is not the letter or the yes/no split.

**Text-only models, fit on the training questions and scored on the same 800 bench choice examples, with no
image and no neural network:**

| | text-only model | tuned adapter, real image | tuned adapter, grey image | commonest |
|---|---|---|---|---|
| binary (n=400) | **62.3%** (logistic regression on question word n-grams) | 65.0% | 60.5% | 51.75% |
| multiple choice (n=400) | **40.2%** (smoothed frequency with which each option text was correct, per category) | 41.5% | 36.5% | 27.0% |

**So a model that never sees an image scores within about 3 points (binary) and 1 point (multiple choice) of
the adapter, which is inside the noise (about 3.4 points per score at n=400).** The adapter's lead over
always-commonest is therefore mostly, and possibly entirely, text priors: the questions themselves give away
much of the answer (for instance, the options offered for a coverage or count question tend to identify the
correct one). I have not inspected the question generator to confirm that mechanism. Text-only, per category:
binary adjacency 60.0%, area 68.7%, count 79.7%, presence 46.8%; multiple choice adjacency 42.7%, area 33.3%,
climate zone 52.0%, count 59.1%, country 38.1%, presence 16.3%, relative pos 32.0%, season 46.7%. The text
model beats the adapter on `binary/count` (79.7% against 73.9%) and `mcq/count` (59.1% against 52.3%). A
16.3% score on `mcq/presence` (below chance) means the option frequencies do not carry over there; the
per-category text figures are noisy at these sample sizes.

**What this means.** **No evidence in the current results that the adapter reads the imagery.** The grey-image
gap (+4.5 binary, +5 multiple choice) is the only sign of image use, it is borderline, and the caption
country result may be tile memorisation. The 3 h 38 min training run proved the pipeline (trains, saves,
reloads, no memory or stability problem) and taught the format and the text priors. It did not show visual
learning, and more steps on this data would mostly sharpen the priors. **Any future adapter must be judged by
its lead over the text-only model, not over chance or always-commonest.**

**Limits.** The two text-only models are quick baselines, not the best possible text-only model, so a stronger
one would score higher and shrink the adapter's lead further. Both ran inline and were not saved as a script,
so they are not yet reproducible from the repo. Nothing under `ml/`, `backend/` or `frontend/` changed in
this step; only this log.

### 2026-09-20 — Blind (no-image) baseline of the tuned adapter: most of the score is text priors

**What was run.** `ml/b5_eval.py run --adapter data/b5_run1/adapter_final --blank-image --out
data/b5_eval/tuned_blind.json`: the same adapter, the same 860 examples and scoring, but every image replaced by
a constant mid-grey one, so replies can only come from the question text. 853 s. New `--blank-image` option
(default off) added to `ml/b5_eval.py` and a `blank_image` parameter to `generate` in `ml/b5_common.py`; base
and tuned runs are unaffected. 0 unreadable replies.

| | tuned, real image | tuned, blind | always-commonest | chance |
|---|---|---|---|---|
| binary (n=400) | 65.0% | 60.5% | 51.75% | 50% |
| multiple choice (n=400) | 41.5% | 36.5% | 27.0% | 25% |

**Reading it.** With no image the adapter still scores 60.5% binary and 36.5% multiple choice, 9 points above
always-commonest on both. So **about two thirds or more of the tuned model's lead over always-commonest is
text priors** (the questions and the answer distribution carry information), and the image adds about +4.5
points on binary and +5 on multiple choice. Those two gaps are each borderline: they are unpaired
differences of two 400-example scores (about 3.4 points of noise per score), and per-example replies were
not stored, so a paired test was not possible. Read them as "some image use is plausible, not established".

Per category, real minus blind (n in brackets, most intervals 10-15 points wide, so only the large ones mean
anything): `binary/presence` +13.9 (79), `mcq/area` +15.6 (45), `mcq/country` +19.0 (21), `mcq/climate zone`
+10.0 (50), `mcq/adjacency` +8.3 (96). Near zero or negative, meaning no visible image use: `binary/area`,
`binary/count`, `mcq/count`, `mcq/presence`, `mcq/season`. Note `binary/area` (76.1% blind) and `binary/count`
(72.5% blind) are the categories that looked strongest before, and they are answered from the text.

Captions (n=60): country named 61.7% with the image against 31.7% blind, so the image (or memorised tiles)
supplies the country; season 35.0% with the image against 38.3% blind, so **there is no sign the model reads
the season from the image**.

**Limits.** A grey image is off-distribution for the model, so blind is a proxy for "text only", not an exact
measure of it. The tile-sharing caveat still holds for the real-image column. The held-out-tile check was not
run: only 12 of the 800 choice examples (9 binary, 3 multiple choice) sit on tiles absent from the training
slice (17 at scene level), too few to score. A real held-out test needs new bench examples built from the raw
BigEarthNet bench patches on unseen tiles (raw-archive extraction, not done, awaiting owner approval).

**Files (uncommitted).** `ml/b5_common.py`, `ml/b5_eval.py`, `docs/PROGRESS_LOG.md`. Results are in
`data/b5_eval/tuned_blind.json` (gitignored). No commit, pull or push.

### 2026-09-20 — First thin adapter trained locally and scored against the baseline

**Run.** `ml/b5_train_lora.py`, 300 optimiser steps (batch 1, grad-accum 16, so 4,800 examples, one pass over
about 27% of the 17,955), 448 px, LoRA rank 16, lr 2e-4, seed 20260920, bfloat16 on the RTX 3050. **Real wall
time 13,060 s = 3 h 38 min** (started 14:05:37; the 2.3 h estimate was extrapolated from a few steps and was
low; about 40 s per optimiser step). 0 skipped non-finite steps, peak allocated 2,913 MiB throughout, no
out-of-memory. Scoring the 860-example sample took 776 s (13 min). The session that started training ended
mid-run; the process survived it and was re-attached by monitoring `train_log.jsonl`. Checkpoints at steps
100/200/300 and `adapter_final` are in `data/b5_run1/` (adapter weights only, no optimiser state, so a run
could not be resumed exactly).

**Training signal.** Single-step training loss stayed in about 0.19-0.50 from step 196 to 300 with no visible
downward trend. Validation (100 examples per check): loss 0.633 / 0.518 / 0.500 at steps 100 / 200 / 300;
choice accuracy 51.2% / 50.0% / 51.2% (n=86 binary+multiple-choice mixed, so about 5 points of noise either
way; a mixed set has no single chance level, roughly 25-50%).

**Smoke check.** The saved adapter was reloaded and run on the first 24 bench examples: replies changed from
the base model's sentences to bare "no" / "c", and 0 of 23 choice replies were unreadable.

**Scored result (same 860-example sample, same scoring rules as `base.json`; `data/b5_eval/tuned.json`):**

| | base plain acc | base acc among readable | tuned acc (0 unreadable) | chance | always-commonest |
|---|---|---|---|---|---|
| binary (n=400) | 19.0% | 60.8% (n=125, self-selected) | **65.0%** (260/400) | 50% | 51.8% |
| multiple choice (n=400) | 13.3% | 29.6% (n=179, self-selected) | **41.5%** (166/400) | 25% | 27.0% |

Unreadable replies: base 275/400 binary and 221/400 mcq; tuned 0 and 0. **The jump from 19.0% to 65.0% and
13.3% to 41.5% is mostly the format fix and is not evidence of learning.** The like-for-like comparison is
against the base model's readable-only figures, which are themselves self-selected: binary 60.8% to 65.0%
(+4 points, base n=125, inside the noise), multiple choice 29.6% to 41.5% (+12 points). The cleaner claim is
tuned versus always-commonest: +13 points binary and +14.5 points multiple choice, each with a 95% interval
of about 5 points either side.

Per category, tuned (n in brackets): binary adjacency 61.6% (185), area 74.6% (67), count 73.9% (69),
presence 57.0% (79); mcq adjacency 42.7% (96), area 42.2% (45), climate zone 50.0% (50), count 52.3% (44),
country 52.4% (21), presence 30.6% (49), relative pos 36.0% (50), season 31.1% (45). Base was 0-36.7%
across these, mostly unreadable, so the per-category base numbers are not a fair comparison either.
`mcq/presence`, `mcq/season` and `binary/presence` are within noise of chance or the commonest baseline
(intervals of 11-14 points at n 45-79); the rest is above it but each sample is small.

Captions (n=60), scored only on naming the right country and season, not caption quality: country 61.7%
(base 0%), season 35.0% (base 13.3%; chance 25%, interval about 12 points). The model has learned the
training caption template.

**What these numbers can and cannot support.** They support: the recipe trains, saves and reloads without
instability on this GPU, and the adapter answers in the required format. They are also consistent with some
real signal above the commonest-answer baseline. They do NOT support any claim that the model reads imagery
well, for three reasons. (1) **Bench shares Sentinel tiles with the training pool** (B1 entry), so the level
is optimistic for unseen regions, and the country caption result in particular may be tile memorisation.
(2) **There is no blind baseline**: nobody has run the tuned model, or a text-only model, with the image
removed, so text priors in the question (for example count and area questions having skewed answers) cannot
be separated from image reading. (3) Training loss did not visibly fall, and validation choice accuracy
(about 51%, n=86, held-out patches) is not better than the bench choice accuracy blended over the same
question types (426/800 = 53%), so held-out validation does not show a gain on unseen patches over bench;
it also is not evidence against one. The parser is still strict and only spot-checked, though with 0
unreadable replies its effect is nil for the tuned model.

**Files (uncommitted).** `docs/PROGRESS_LOG.md` only; `data/` is gitignored, so `data/b5_run1/`,
`data/b5_eval/tuned.json` and `tuned_run.log` are not tracked. Nothing under `backend/` or `frontend/`
changed, so the pytest and Vitest counts stand. No commit, pull or push was run.

### 2026-09-20 — B1 thin slice and B5 written; decision to train the first adapter locally

**B1 (`ml/b1_slice.py`, counts in `ml/b1_slice_report.json`).** 1,995 train and 206 validation patches
from 2,100 and 210 candidates; 17,955 and 1,854 examples (per patch: 1 caption, 4 binary, 4 multiple choice,
spread across categories). Official split labels are kept; a 2-cell spatial buffer keeps training patches
away from validation-slice and bench patches (minimum measured distance 3, checked independently). Three
findings that shaped the rules: (1) **the official split is patch-level, not geographic**: 52 of 54 tiles sit
in more than one split and 97.8% of patches have an adjacent neighbour, and the buffer only excluded 340 of
229,114 train patches, so bench scores stay optimistic for unseen regions; (2) the plan's "drop the bottom
quartile" is degenerate here (75% of patches score exactly 0), so a 5% cloud-like cap replaced it, dropping
105 of 2,100; it is a brightness proxy that misses cloud shadow (visible in a sampled render); (3) 21% of
season questions list both "Fall" and "Autumn", so those are dropped from training and the bench sample.
Extraction streamed the S2 archive once and kept only B02/B03/B04 of the candidates. Bounding-box rows are
excluded (B6). Data is in `data/b1_slice/` (gitignored); `python ml/pack_for_kaggle.py` makes a 60.7 MiB zip.

**B5 (`ml/b5_common.py`, `b5_train_lora.py`, `b5_eval.py`, `b5_kaggle.ipynb`).** Qwen2-VL-2B (pinned
revision), 4-bit NF4, LoRA rank 16 on the language model's q/k/v/o only (4,358,144 trainable parameters),
loss on answer tokens only, S2 true-colour input. Evaluation samples 860 bench examples (400 binary, 400
multiple choice, 60 captions) and reports accuracy beside chance and an always-answer-the-commonest baseline;
captions are scored only on naming the right country and season, which is not a caption-quality metric.

**Measured training memory on the RTX 3050** (3-4 optimiser steps each, batch 1, gradient checkpointing):
2,787 MiB at 448 px on random examples; 3,072 MiB at 448 px and 3,880 MiB at 672 px on the longest captions;
about 1.7 s per example at 448 px. No out-of-memory error, no non-finite loss. This contradicts the D2
statement that QLoRA cannot fit; see the note under D2 in the Development Plan. Two-image inputs were not
tested.

**Baseline evaluation of the untuned model finished** (`data/b5_eval/base.json`, 860 bench examples, 448 px,
run from an unzipped copy of the pack, which also shows the package is portable). Plain accuracy is
**below chance, and that is mostly a format failure, not a vision result**: the model answers in sentences.

| | plain accuracy | unreadable replies | accuracy among readable replies | chance / always-commonest |
|---|---|---|---|---|
| binary (n=400) | 19.0% | 275 of 400 | 60.8% (76 of 125) | 50% / 51.75% |
| multiple choice (n=400) | 13.3% | 221 of 400 | 29.6% (53 of 179) | 25% / 27.0% |

(Corrected 2026-09-20: this table first said 30.0% for the multiple-choice always-commonest figure;
`base.json`, which the evaluation code computed, says 27.0% (0.27). The binary figure is exactly 207/400 =
51.75%, so 51.7% and 51.8% are both roundings of it.)

Captions (n=60): 0% name the correct country, 13.3% name the correct season. Per category, multiple choice was
0% on `area`, 2.0% on `relative pos`, 4.4% on `season`; the best were `mcq/country` 33.3% (n=21) and
`binary/presence` 36.7% (n=79), all small samples.

**How to read this.** (1) A tuned adapter will learn to output "yes" or "b" and so gain a great deal from format
alone; that gain is NOT evidence it learned anything about the images. Compare `acc_among_readable` and the
per-category figures, not plain accuracy. (2) The readable subset is self-selected (the model answers when
it can), so 60.8% is not a clean estimate of its binary skill, and multiple choice among readable replies is
at chance. (3) The parser is strict: "There is no instance of industrial..." means "no" but scores as
unreadable, so part of the below-chance figure is the parser, not the model. `ml/b5_eval.py` now records
`readable_n` and `acc_among_readable`; for this baseline they were derived from the recorded counts, which is
exact because unreadable replies are all scored wrong.

**Commands (repo root, Git Bash):**

```
export HF_HOME="D:/Projects/SatQuery/data/hf_cache"
# baseline, if it did not finish:
.venv-ml/Scripts/python.exe ml/b5_eval.py run --out data/b5_eval/base.json
# thin local training:
.venv-ml/Scripts/python.exe ml/b5_train_lora.py --data data/b1_slice --out data/b5_run1 --size 448 --max-steps 300 --grad-accum 16 --eval-every 100 --eval-n 100 --save-every 100
# score the adapter on the same sample:
.venv-ml/Scripts/python.exe ml/b5_eval.py run --adapter data/b5_run1/adapter_final --out data/b5_eval/tuned.json
```

**Owner decision (recorded as instructed in the request for this handover):** train locally first. Nothing
under `backend/` or `frontend/` changed in this work, so the pytest and Vitest counts stand.

### 2026-09-20 — Qwen2-VL-2B runs 4-bit on the RTX 3050 (smoke test), revision pinned

`tools/ml_smoke_test.py` loads `Qwen/Qwen2-VL-2B-Instruct` at commit
`895c3a49bc3fa70a340399125c650a463535e71c` (read from the Hub, then downloaded at that commit) in NF4 4-bit
with bfloat16 compute, and runs one BigEarthNet.txt bench patch through it: a Sentinel-2 RGB render, alone
and paired with a Sentinel-1 VV render, at 224, 448, 672 and 896 pixel square inputs, 96 new tokens,
greedy. Environment: torch 2.5.1+cu121, transformers 5.17.0, bitsandbytes 0.50.2, accelerate 1.15.0,
in a separate `.venv-ml` (`tools/requirements-ml.txt`); the backend's `requirements.txt` is untouched.

**Measured, all eight runs completed, none ran out of memory:**

| Images | Input size | Input tokens | Peak allocated | Time for 96 tokens |
|---|---|---|---|---|
| 1 | 224 | 103 | 1,484 MiB | 5.1 s |
| 1 | 448 | 295 | 1,534 MiB | 4.3 s |
| 1 | 672 | 615 | 1,578 MiB | 4.8 s |
| 1 | 896 | 1,063 | 1,728 MiB | 5.2 s |
| 2 | 224 | 169 | 1,506 MiB | 3.5 s (89 tokens) |
| 2 | 448 | 553 | 1,565 MiB | 4.3 s |
| 2 | 672 | 1,193 | 1,785 MiB | 5.2 s |
| 2 | 896 | 2,089 | 2,312 MiB | 6.9 s |

Weights took 1,454 MiB and 11.9 s to load. Free VRAM was 3,303 MiB before loading (not 4,096: the desktop
holds the rest), and 1,781 MiB after. The worst case, two images at 896, peaked at 2,312 MiB, leaving
roughly 1 GB of that free space. **That confirms the D1 reasoning that 4-bit inference fits with room to
raise the input resolution; it does not confirm anything about training** (see Verification gaps).

**Output quality, honestly:** the base model produces fluent, generic descriptions ("a rural area with a
mix of agricultural and residential features") and at 896 px it invents detail the 10 m data cannot
contain ("houses… with red roofs"). It did not state the country or season the reference caption gives, and
the two-image run treated the SAR render as a second view of the same scene. One sample, so this shows the
model runs and how it behaves untuned, and it says nothing about accuracy. It is the case for the LoRA step,
not a result. Note also that a bench patch is 120 px at 10 m, so upscaling adds tokens, not information; the
0.65 m demo scale has not been run.

**Files:** `tools/ml_smoke_test.py`, `tools/requirements-ml.txt`. Results and two sample renders are in
`data/ml_smoke/` (gitignored). Nothing under `backend/` or `frontend/` changed, so the pytest and Vitest
counts are as recorded in the entry below.

### 2026-09-20 — Scenario G: the temporal-ordering rejection is now a demo

Scenario G is scenario C's Bengaluru pair uploaded in reverse order. The validator reads the two
acquisition times from inside the GeoTIFFs and rejects with `temporal_ordering_invalid`, HTTP 200, full
three-step trace, tier Low. It needs no new imagery. Changes: a `scenario_g` entry in `mockScenarios.ts`
and `mockTraces.ts` (copied from the live response), and `DemoScenarioBar` / `ProcessingStatus` now style
a scenario as a rejection from `mockResponse.rejected` instead of hard-coding `scenario_f`.

**The parity test now sends what the UI sends.** `tests/test_demo_parity.py` used 19 placeholder bytes for
every file, which carry no timestamps, so it could never have seen this rejection. It now posts the bundled
GeoTIFF where one exists (`analyze_demo`) and placeholders only for B and F. Regenerating the snapshot
added only `scenario_g`; A-F are byte-identical to before, which confirms the real rasters do not change
any earlier outcome. The separate real-file parity test in `tests/test_demo_rasters.py` became redundant
and was removed.

**Verified:** 140 pytest, 58 Vitest (2 new for G), `npm run build` clean, two known lint warnings. Not
re-checked in a browser: the G mock was compared to the live response by the parity test, but nobody has
clicked scenario G in the UI.

### 2026-09-20 — Real GeoTIFF demo inputs, and the BigEarthNet bench subset extracted

**Log corrections first.** "Next step" and the "Current status" headline still said Track D was unbuilt
and Track B/C was blocked on D1/D2, contradicting Open item 4; `CLAUDE.md` still said the container
images had never been built locally. All three corrected.

**Demo rasters.** `tools/make_demo_rasters.py` is a Pillow port of the SVG scenes in `mockImagery.ts`
that writes seven 8-bit LZW GeoTIFFs to `frontend/public/demo/` with a real CRS (UTM 43N/44N/46N),
geotransform, GSD (0.65 m, 1 m, 10 m), platform tag and, where the mock had one, acquisition time. Pairs
share a ground extent, so the footprint overlap is 100% even where the pixel sizes differ. Filenames are
unchanged, so `demoParity.json` did not move. The upload path (`SatQueryContext.tsx`) now fetches the
scenario's `rasterUrl` and sends its real bytes; the SVG stays the on-screen picture, and the old
canvas-rasterize path remains the fallback. The mocks' band counts, dimensions and cloud shares were
corrected to what the files contain.

**Two corrections to the plan.** It said `crs_mismatch_unresolvable` could be shown with two different UTM
zones; it cannot, because the validator only fires on a CRS labelled unresolvable (a local engineering
CRS). And its "new pytest per rejection" was redundant, since `tests/test_metadata.py` already exercises
all three rejections through the API. Neither was built.

**The parity test had never seen a real file.** `tests/test_demo_parity.py` uploads 19 placeholder bytes,
which no raster library can open, so every metadata field was `None` there. The new
`tests/test_demo_rasters.py` (26 tests) checks each raster opens in both rasterio and Pillow, reports the
georeferencing it was written with, and that all six demos still reproduce the snapshot when fed the
real files. One frontend test proves the demo uploads the fetched GeoTIFF bytes; disabling the new path
fails it.

**Browser check** (headless Edge, uvicorn plus Vite, `playwright-core` kept in the scratchpad, not the
repo): all six demos ran live with the "Live Backend" badge, no console errors, and the intended tier
(A High, B Medium, C High, D High, E High, F rejected `modality_mismatch`). The backend's own storage
shows the GeoTIFFs arrived byte-for-byte and every overlay is 600x400, so Pillow decoded them and the
640x640 fallback did not fire. Swapping scenario C's two files made the backend answer
`temporal_ordering_invalid` (checked at the API, not through a UI control, since none exists).

**BigEarthNet bench subset.** `tools/extract_bigearthnet_bench.py` streamed both `.tar.zst` archives once
and kept only the 1,082 `bench` patches: 328 MB in `data/BigEarthNet/bench_subset/` (gitignored), instead of
unpacking the 117 GB of compressed archives. Verified against the files: every patch has all 12 S2 band files and both S1 files.
S2 is `uint16` in EPSG:32633 at three resolutions (120x120 at 10 m for B02/B03/B04/B08; 60x60 at 20 m for
six bands; 20x20 at 60 m for B01/B09); S1 is `float32` VV/VH at 120x120, 10 m. Sampled from the parquet,
the bench annotations are: captions of land cover, season, country and climate; binary and multiple-choice
questions on presence, area, count, adjacency and relative position; and 1,582 box rows whose targets
are LULC regions ("largest patch of coniferous forest") with normalised `[x0 y0, x1 y1]` outputs (the
coordinate convention is inferred from one sample, not confirmed). That covers caption, VQA and region
grounding on co-registered optical+SAR, but **not** the objects the demos show (vessels and tanks at
0.65 m) and not change detection, which still needs CDVQA or similar. Each 120-pixel patch spans 1.2 km.

**Verified:** 140 pytest, 56 Vitest, `npm run build` clean, lint shows only the two known warnings (now at
lines 69 and 308). The local `PROJ_LIB` clash was worked around by pointing `PROJ_DATA`/`PROJ_LIB` at
`rasterio/proj_data`. `graphify update .` rebuilt the code graph (866 nodes, 1,895 edges, 48 communities); the
markdown edits made today were **not** re-extracted, since that needs `/graphify . --update` (LLM).

### 2026-09-20 — D1 settled on the 2B, for resolution rather than parameter count

The first recommendation was `Qwen2.5-VL-3B-Instruct` with the 2B as a fallback. On review the order
reversed, and **`Qwen/Qwen2-VL-2B-Instruct` is the decision**.

The reasoning that flipped it: on a 4 GB card the binding constraint is not parameters but **how many
pixels reach the model**. At 4-bit the 2B's weights are roughly 1.2–1.5 GB against the 3B's 2.2–2.5 GB,
leaving about 2.5 GB rather than 1.5 GB for visual tokens and KV cache — and the two-image tasks
(change, fusion) double the token count, so they are where the 3B would force the hardest downsampling.
Remote-sensing grounding is pixel-hungry: a vessel or a storage tank at 0.65 m GSD is a small object.
A 2B model seeing the scene at adequate resolution should localise better than a 3B model squinting at
a shrunken one, and bounding boxes are this project's product.

**Accepted losses, stated for the record:** Qwen2.5-VL improved localisation over Qwen2-VL, so the base
model starts weaker at exactly the central capability; and there is less reasoning headroom on the
compound fusion-then-change path. Both are expected to narrow under LoRA fine-tuning on in-domain data
(RSVQA, VRSBench, CDVQA), since the system never relies on general capability.

**Why this was a cheap decision:** both models are Qwen-VL family with the same processor API and the
same LoRA target module names, so reversing it is a model ID change plus a re-train. If measurement
later shows the 2B is the limiting factor, step up to the 3B.

Unchanged by this: **training still does not fit on the 4 GB card.** The 2B is closer than the 3B but
is still expected to overrun once visual tokens and optimiser state are counted. Cloud training stands.

### 2026-09-20 — CI fully green; D2 answered, D1 recommended, A6 declined

**CI.** After the rasterio/numpy fix, all three jobs pass. `containers` is the one that matters: it
built both images for the first time, brought the stack up on Compose health gates, drove an analyze
cycle through the running API, and confirmed a session survived a `docker compose restart`. That closes
B17 and the "images never built" gap. What CI still does not cover is a human looking at the
nginx-served frontend — see Verification gaps.

**D2 — compute, answered.** An NVIDIA RTX 3050, 4 GB dedicated VRAM (8 GB "shared" is system RAM over
PCIe and does not count). Consequence, and it is the important one: **4 GB cannot fine-tune a 2–3B
vision-language model**, even with QLoRA, because visual tokens plus activations overrun the card.
Training must run on a free or cheap cloud GPU (Kaggle gives 2x T4 16 GB); 4-bit inference does fit
locally if image resolution is capped. Two-image tasks (change, fusion) are the tightest case.

**D1 — backbone, decided: `Qwen/Qwen2-VL-2B-Instruct`.** (First proposed as the 3B Qwen2.5-VL with the
2B as fallback; the 2B was chosen on review — see the separate entry below.) The first factor is
**multi-image input**: change detection and fusion are two of the four task families, and
Florence-2 and PaliGemma are single-image architectures, so they would force both images onto one
canvas and destroy the per-image 0–100 box coordinate space the whole codebase is built on. Qwen2.5-VL
also emits bounding boxes natively, and PEFT can hold several LoRA adapters resident and switch with
`set_adapter()`, which is what the SPDD 13.2 no-reload rule requires. Exact revision to be pinned at
download time — no SHA has been invented here.

**A6 — map layer, recommended against for now.** Every demo input is a synthetic SVG raster with no
CRS and no footprint, so a georeference flag would be false in all six scenarios and the map would be
empty in exactly the situations shown to a judge. The prerequisite is real GeoTIFF demo inputs (new
Open item 5), which would also make the A1 metadata work and three unreachable rejection codes visible
for the first time. A6 is worth doing after that, not before.

### 2026-09-20 — First CI run: `requirements.txt` was missing rasterio and numpy

The first push failed the `backend` job (and so skipped `containers`): `tests/test_metadata.py`
imports numpy, which a clean install did not have. The cause was wider than the test. The metadata
service reads CRS, bands, footprint and GSD from the file with `rasterio`, but `requirements.txt` listed
it as a commented-out option, so a clean install or a container built from it fell back to filename
hints and could not run the suite. `rasterio>=1.3` and `numpy>=1.26` are now real dependencies. Local
runs never saw this because both were already installed. Reproduced in a fresh venv with the latest
versions (rasterio 1.5.1, numpy 2.5.3, fastapi 0.141, starlette 1.6): all 114 tests pass once the local
`PROJ_LIB` clash (see Verification gaps) is bypassed. The `frontend` job passed; its two lint warnings
are the known ones. The workflow's actions target Node 20, which GitHub warns is deprecated;
harmless for now.

### 2026-09-20 — Track D: containers, health-gated startup, CI and the offline test

The plan's Track D assumes a gateway, model server, database and object store; only a FastAPI app, a
static frontend and SQLite exist (Appendix B), so it was built for that system.

**D1 containers.** `backend/Dockerfile` (python:3.12-slim, unprivileged user, `/data` volume, build
from the repo root because imports are absolute), `frontend/Dockerfile` (Node build, nginx runtime,
`VITE_API_BASE_URL` as a build arg) with an SPA-fallback `nginx.conf` so `/results/<id>` survives a
reload, `docker-compose.yml` (frontend on `:8080`, API on `:8000`, both loopback only, named data
volume), and `.dockerignore` files. `.gitignore` gained the new top-level paths.

**D2 config and audit.** Compose loads an optional `.env` into the backend, so every `SATQUERY_*`
tunable works unchanged and no threshold is repeated in Compose. **The audit found a real offline
violation:** the frontend loaded Inter, Outfit and JetBrains Mono from Google Fonts. They are now
bundled (`@fontsource`, latin subsets, `src/fonts.ts`) and the CDN links are gone.

**D3 startup.** `/v1/health` now opens the database and returns 503 if it cannot, reporting the schema
version otherwise. The app opens (and so migrates) the database at startup, so a database from a newer
build stops the process instead of failing each request. The backend `HEALTHCHECK` runs
`backend/docker_healthcheck.py`; Compose starts the frontend only when the backend is `service_healthy`.
There is no model-serving stage to gate on yet.

**D4 tests and CI.** `tests/test_deployment.py` (8 tests): health and startup migration; an offline
guard that refuses every non-loopback connection while all six demos, session lookup and JSON/HTML/PDF
reports run (a second test proves the guard blocks); a CDN scan of the frontend sources and any built
`dist`; and three concurrent analyses with distinct sessions and answers (Appendix A #23).
`.github/workflows/ci.yml` runs pytest, then lint, tests, build and a bundle CDN scan, then builds the
images and drives an analyze cycle plus a restart through the running stack.

**Verified:** 114 pytest, 55 Vitest, `tsc -b` and `npm run build` clean, two pre-existing lint warnings.
Mutation-checked: restoring a CDN link fails the CDN test; removing the startup hook fails the startup
test. Container path checked without Docker (see Verification gaps): healthcheck OK, analyze returned 3
boxes, three concurrent real-HTTP requests all succeeded in 0.16 s wall time, and a session survived a
restart on the same data directory. In Edge against the production build with every non-localhost
request blocked, a demo ran with zero blocked requests, no page errors, all three font families loaded,
and a reload of `/results/<id>` rendered. A YAML parse also caught an invalid escape in the first draft
of the workflow.

### 2026-09-20 — Demo imagery redrawn as port scenes, and the browser checks done

**SVG decision (done: redraw).** Every scenario shared one farmland-and-river picture, while the
answers and boxes describe a port, so the annotations sat on the wrong scene. One port image could not
serve all scenarios (the tanks in A overlap the water basin in B; the vessels in D overlap the quay in
E), so `frontend/src/data/mockImagery.ts` now draws a scene per scenario, sized to that scenario's
backend boxes: A tanks and container terminal, B harbour basin and retention pond, C waterfront with
T1 bare ground and T2 new pier and staging yard, D optical and SAR port pair (the moored vessel is
under cloud in optical and visible in SAR), E fused quay and new yard. F reuses D's pair. Nothing
tests the pictures; they were checked by eye.

**Browser checks (headless Edge against uvicorn and Vite, `playwright-core` kept out of the repo).**
- All six demos live: `/results/sq-...` URLs, "Live Backend", no console errors; every box sits on the
  feature it describes.
- Backend stopped: all six fall back with the amber "Demo Data" badge, six `ERR_CONNECTION_REFUSED`
  errors (one per attempt) and six fallback log lines, and the pages match the live ones except the
  badge, mock session IDs and the trace's `input_images` names.
- Two images, vague query: returns `ambiguous_intent` with the clarifying question.

**Defect found by that last check and fixed.** The rejection card offered "Switch to Optical-SAR Fusion
Query" for every reason code, and titled an unclear query a "Physical Input Precondition Rejection".
The fusion button now shows only for `modality_mismatch`; `ambiguous_intent` reads "Query Needs
Clarification" with a "Rephrase Query" button. Five new Vitest cases; mutation-checked (always showing
the button fails 3 of them).

**Verified:** 106 pytest, 55 Vitest, `tsc -b` and `npm run build` clean, lint shows only the two
pre-existing warnings.

### 2026-09-20 — Demo-scenario parity test, and the mocks reconciled with the backend

The offline fallback used to say something different from the live backend for every demo, not just
scenario A: answer text, box labels, coordinates, scores, region tags, rationale and the rejection
wording all differed. Now they match, and a test keeps them matching.

**How it works.** `tests/test_demo_parity.py` runs each of the six demo queries (with the demo file
names) through the live pipeline and compares the outcome to `frontend/src/data/demoParity.json`:
task type, tier, rationale, answer text, every box field, region tags and the rejection reason and
details. `mockScenarios.test.ts` then compares `DEMO_SCENARIOS` to the same file, including the demo
query and file names. Neither language parses the other. After an intentional change to a demo, run
`SATQUERY_UPDATE_PARITY=1 python -m pytest tests/test_demo_parity.py`, then edit the mocks to match. A
second set of tests pins the snapshot's task type and tier to the intended values, so regenerating it
cannot bless a wrong outcome.

**Mocks reconciled.** `mockScenarios.ts` now carries the backend's answer text, boxes, region tags,
rationale and rejection details for scenarios A-F (scenario E's mock gained its region tags; scenario
F's detected/required context now uses the live keys). Images, metadata and mock session IDs are
unchanged. The new Vitest cases failed on all six scenarios before the reconciliation.

**Not compared:** masks (live mask URLs are per-session storage paths), trace steps (already covered),
and the demo imagery. The bundled SVG previews still show farmland while the text describes a port;
see Open item 5.

**Verified:** 106 pytest (7 new), 50 Vitest (7 new), `tsc -b` and `npm run build` clean, lint shows only
the two pre-existing warnings. Mutation-checked: changing a tier in the snapshot fails the pytest.
Not checked in a browser.

**A8 bookkeeping.** A8 is committed (`1c0b334`); the stale "in progress" open item is removed and the
Development Plan F8 row is now DONE. The A8 entry below quotes 92 pytest, which was the count at that
moment.

### 2026-09-20 — Step A8 implemented: direct session reopen

`/results/:sessionId` now fetches the stored session on mount, so a shared link or a page
reload works. States: loading, **Session Not Found** (404) and **Could Not Load Session**
(backend unreachable) are distinct; neither falls back to the empty state. A fresh live
result redirects to its own `/results/<id>`; demo results are never persisted and keep
`/results`. Files: `services/api.ts` (`SessionNotFoundError`), `context/SatQueryContext.tsx`
(`openSession`), `pages/Results.tsx`, `App.tsx`.

**Verified:** 43 Vitest tests (5 new), 92 pytest, `npm run build` clean, lint shows only two
pre-existing fast-refresh warnings. Mutation-checked: treating 404 as a generic error, and
disabling the fetch, each failed tests. Driven for real with headless Edge against uvicorn
and Vite: a live session URL rendered "Live Backend" with its trace; an unknown id showed
Session Not Found; with the backend stopped, Could Not Load Session.
**Known gap:** reopened sessions show no source imagery, since the response omits inputs.
### 2026-09-20 — Graph and docs refreshed while A8 was in flight

Re-ran `/graphify . --update` and reconciled the docs. Found A8 (direct session reopen) partly
implemented in the working tree by another session; it is recorded under Open items as in progress
rather than done, because it was mid-edit and unverified in a browser. Baseline at the time:
99 pytest passing; 43 Vitest passing, including the 5 new A8 tests; `tsc` clean.

**Graph:** 758 nodes, 1,664 edges, 39 communities (was 766 / 1,581 / 40; 51 nodes from the
re-extracted files were replaced). The report's header says "8 files" and "0 tokens": both describe
only this incremental run (the 8 changed files, with usage not recorded), not the corpus. The 3
changed documents were extracted by one subagent, and the 5 changed frontend files by the AST pass.

### 2026-09-20 — Knowledge graph refreshed after the doc changes

Ran `/graphify . --update` so the graph reflects the code and doc edits made today, including
the five changed documents (which need LLM extraction, unlike code). Result: **766 nodes,
1,581 edges, 40 communities**, up from 627 nodes; 145 nodes added, 7 removed. Community labels
are derived from each community's member files. The report's file count (95) and its token cost
(0) are not reliable: the count includes more than the earlier 34-file corpus, and the
extraction subagents' token use was not recorded. Also added `docs/HANDOFF_PROMPT.md`, a
ready-to-paste prompt for starting the next session from this state.

### 2026-09-20 — Documentation freshness pass

Audited every markdown file against the code. Stale and now fixed: `CLAUDE.md` still said
responses persist to `response.json` (they persist to SQLite); the Development Plan still
described A3 as a SQLAlchemy/Alembic to-do with B4 marked TODO, listed A7 as outstanding, and
quoted 35 pytest and 26 Vitest tests (now 99 and 38). Also fixed in the Development Plan: the storage row and directory layout still said "JSON, no
database", Appendix B said the API base URL was hardcoded (it reads `VITE_API_BASE_URL`), and a
note still described the 42 ms trace floor as live. `SPDD` gets a short implementation note
pointing at Appendix B for its deviations (`weasyprint`, Postgres); it is a design baseline and
is not rewritten to track the build. `Final_Synthesized_Solution` and `Problem_Statement` are
source documents with no status content and were left untouched.

### 2026-09-20 — Demo traces aligned with the live backend (option 2 of the scenario-bank issue)

The offline demo fallback used to show a 7-step trace with snake_case component names, adapter
IDs like `adapter_vqa_caption:v1.2-lora` and 100-1200 ms timings, while a live session showed
CamelCase names, the real adapter IDs and tiny durations. The two views of the same scenario
did not look alike, which defeats the point of a fallback meant to be indistinguishable in a demo.

`frontend/src/data/mockTraces.ts` now holds the six traces, copied from what the live backend
returns for the same queries (component names, adapter IDs, parameters, summaries, statuses,
step sequence including the rejected `PreconditionGate` step in scenario F). Durations are fixed
small values, not measurements. `mockScenarios.ts` spreads them in and its hand-written step
arrays are gone (about 340 lines removed). Regenerate the file from a live `/v1/analyze` response
if the pipeline's steps change.

Two scenarios also disagreed with the backend on outcome, and a trace saying one thing while its
own response said another would have been worse than the old mismatch, so those were aligned too:
scenario A is now `single_caption` / High (was `single_vqa` / Medium) and scenario E is High
(was Medium), each with the backend's rationale text.

**Not aligned, deliberately:** answer text, boxes and coordinates. The scenario A mock still
describes different content from the backend. That is the parity-test work (option 1) and was not
part of this step.

**Verified:** `tsc -b`, lint (no errors) and `npm run build` are clean; Vitest is **38 tests**
(7 new in `mockScenarios.test.ts`: each demo's trace task type and tier match its response, step
indices are sequential, the last step's status matches the rejected flag, component names are
CamelCase). Not checked in a browser this step.

### 2026-09-20 — Log reconciliation, trace timings and the demo growth figure

Housekeeping pass before moving on.

**Log vs code.** The log had already caught up with A3 (SQLite), and `session_repository.py`
is wired into `StorageService` and covered by `tests/test_persistence.py`, so it is a finished
step and not a stray file. Two leftovers were corrected: the status table still said sessions
persist as "memory cache + JSON on disk", and the status paragraph still called real-model
integration "the track now in front of us" although it is blocked on decisions D1/D2.

**Trace timings.** `TraceEmitter` reported time since pipeline start, floored at 42 ms, as each
step's duration. It now reports the measured time since the previous step, with no floor, so a
fast step honestly shows a small number (0 ms is possible). Three new tests in
`tests/test_trace_emitter.py`. The durations are real but tiny, because the dummy specialists do
no work; they become meaningful once real inference lands.

**Demo growth figure.** `+14,200 sq m` was typed in the router and three times in the scenario
engine. It is now `DEMO_GROWTH_SQM` in `scenario_engine.py`, used by the scenario 3 and 5 text,
the scenario 5 box label and the router, with a test that they agree. It is still demo data, not
a computed value: deriving it from `pixel_count x GSD^2` gives 14,256 sq m, which would contradict
the box label in the same response.

**Two images, no change intent (decided: ask).** Two same-sensor images with a query that
mentions neither change nor fusion used to be classified as `change_vqa`. `QueryInterpreter`
now returns an `ambiguous` TaskSpec with a clarifying question, so the response is the existing
`ambiguous_intent` rejection (HTTP 200, full trace) telling the user to ask what changed or to
upload one image. No new rejection code. All six demo queries are unaffected (the change ones
contain "between"). Three new tests, mutation-checked: they fail with the branch disabled.

Backend suite: **99 tests**, all passing; Vitest 31.

### 2026-09-20 — Step A3 implemented: persistent datastore

Sessions now live in SQLite instead of an in-process dict plus JSON files.
`backend/app/services/session_repository.py` (stdlib `sqlite3`, not SQLAlchemy/Alembic —
three tables did not justify two dependencies; all SQL is in that one module) owns the
`sessions`, `evidence_ledgers` and `execution_traces` tables, with append-only migrations
tracked by `PRAGMA user_version` and a refusal to open a newer-schema database.
`StorageService` delegates to it, resolving the database path from
`SATQUERY_DATABASE_PATH` at call time. Pre-existing `response.json` sessions are imported
on first read. Images, overlays and reports stay on disk.

**Verified:** 92 pytest tests pass (11 new in `tests/test_persistence.py`); two mutation
checks (corrupting the stored answer, removing `ON DELETE CASCADE`) each made tests fail;
a live uvicorn run created a session, was killed, and after a restart with the JSON file
deleted `GET /v1/session/{id}` returned 200. Frontend untouched. Not exposed over HTTP:
session listing, because the API has no authentication.


### 2026-09-20 — Steps A7, A4 and A1 implemented

Three steps, each verified before the next began: frontend tests, externalized
configuration, and real raster metadata. Backend suite went from 40 to **81 tests**; the
frontend now has **31**, where it had none. Both builds are clean.

**A7 — frontend tests.** Vitest, React Testing Library and jsdom, with `npm test`. Brought
forward from "whenever there is slack" after browser verification found a render crash
that no Python test could see. Coverage: the evidence viewer, confidence badge, rejection
state and trace, the Results and Upload pages, and the API-base resolution. Fixtures use
`null` exactly where the API sends `null`, because a fixture using `undefined` would let
default parameters hide the very bug these tests exist to catch. **Mutation-checked:**
reintroducing the original `regionTags` crash fails 6 tests, including the page-level one.
While writing them I found two more defects: raw LaTeX (`$\ge 70\%$`) rendered verbatim on
the landing page and in the rejection card, now fixed.

**A4 — externalized configuration.** Every tunable is now an environment variable with a
documented default: storage root, host, port, CORS origins, the three validation
thresholds, the optical-cloud cutoff and the high-confidence intent threshold, plus
`VITE_API_BASE_URL` for the frontend. Malformed values fail at startup naming the
variable. The audit corrected the plan: its "quantity tolerance" and "0.55 ambiguity
threshold" do not exist in the code, so they were not invented. Two behaviour changes: the
dev server binds `127.0.0.1` instead of `0.0.0.0`, and the default CORS list drops the `*`
wildcard. Verified live — a backend configured only through the environment served on the
configured port, wrote to the configured storage, and honoured a CORS override.

**A1 — real raster metadata.** The old service fabricated rather than guessed: every `.tif`
got the CRS `EPSG:32643` whatever it contained, every optical image a cloud cover of
exactly 12%, and GSD was invented from the filename. That is why the CRS, footprint-overlap
and ordering preconditions could never fire on real input. The service now reads CRS, bands,
dimensions, GSD in metres, NoData share, footprint and acquisition time from the file, reads
modality from platform tags ahead of the filename, and never invents a value — an unknowable
field is `None`. Pair overlap is computed once both images are read. Cloud share is an
8-bit brightness approximation and explicitly **not** a cloud-detection model; an earlier
draft that scaled 16-bit data by its own peak would have flagged the brightest few percent
of any scene as cloud, so non-8-bit rasters now report it as unknown. Short filename hints
match whole tokens, so `farms.png` is no longer multispectral. Twenty-eight new tests use
synthetic GeoTIFFs; **23 fail against the old service.**

**Knowledge graph** refreshed after all three: 580 nodes, 1,344 edges. The new metadata
service, config layer, badge component and both new test suites are in it. Community
labels are now derived from each community's member files rather than hand-written, since
community IDs shift on every rebuild and a fixed table silently mislabels them.

**End-to-end check.** All six demo scenarios were driven through Chrome after A1: each ran
against the live backend with no page errors, the five analyses returned their intended
tiers, and the mismatch scenario rejected.

### 2026-09-20 — Browser verification, and a crash it uncovered

Drove the running application in Chrome (Playwright, backend on `:8000`, Vite on
`:5173`) to verify step A5, since its browser-side half could not be covered by the
Python test suite.

**It immediately found a crash.** The Results page threw
`Cannot read properties of null (reading 'length')` inside `EvidenceViewer` and
rendered nothing at all. The cause: the backend sends `regionTags: null` for every
non-fusion task, while the component declared `regionTags?: RegionTag[]` and relied
on a default parameter — and a TypeScript default fills `undefined`, never `null`.

**This was pre-existing, not introduced by A5, and it was severe:** the Results page
crashed on every live single-image and change analysis. It was invisible to the test
suite, which exercises the API rather than the UI, and the demo fallback did not mask
it — the fallback only fires when the HTTP call itself fails, and here the call
succeeded before the render blew up. This is the clearest argument yet for step A7
(frontend tests), which would have caught it.

Fixed by correcting the TypeScript contract to say what the wire format actually
sends (`RegionTag[] | null`, and `details` likewise nullable on a rejection response)
and normalizing with `?? []` at the two consumers, `EvidenceViewer` and
`ConfidenceBadge`.

**A5 then verified end to end, both paths:**

- *Backend running* — the page shows a green **LIVE BACKEND** badge; the browser
  uploaded a real 184 KB, 600x400 PNG rasterized from the scenario's own preview, and
  the backend drew its overlay on that image at 600x400 rather than on the 640x640
  synthetic fallback canvas. The rasterization path works.
- *Backend stopped* — the page shows an amber **DEMO DATA - BACKEND UNREACHABLE**
  badge, with `ERR_CONNECTION_REFUSED` in the console and the bundled scenario served.

The two screenshots also make the divergence between the two scenario banks concrete:
the live session renders an 8-step trace with CamelCase component names, the mock a
7-step trace with snake_case names and different timings. Already recorded under
Known limitations; not addressed here.

### 2026-09-20 — Step A5 implemented: live/mock honesty in the UI

The client fell back to a bundled demo scenario whenever the API call failed, and did
so silently — the Results page looked identical whether the backend was running or
not. That is a debugging hazard and a presentation hazard: a result could look fully
analysed while never having been computed.

**The fallback is kept**, because it protects a live demo, but it is now labelled.
The context tracks whether a result came from the API or the scenario bank, and a new
`ResultSourceBadge` renders "Live Backend" or "Demo Data — Backend Unreachable" on
both the success and rejection views, with a tooltip explaining what the second means.

**Demo scenarios now upload real rasters.** They previously posted a 19-byte
placeholder blob, so `overlay_service` could not open it and fell back to drawing a
synthetic 640×640 port scene — meaning every demo overlay was annotated on imagery
the user was not looking at. The client now rasterizes the scenario's own SVG preview
to a PNG through a canvas and uploads that, so the backend annotates exactly the image
on screen. Verified on the backend side: a decodable 600×400 upload produces a 600×400
overlay, placeholder bytes produce the 640×640 fallback.

Two corrections to the plan's own step A5, recorded in Development Plan §10.5:

- Its suggestion to "send no files" for demo scenarios would have broken them. Image
  count drives task validation, so a two-image scenario with no files would have been
  rejected for `insufficient_image_count`.
- Its claim that the synthetic fallback canvas "becomes dead code and should be
  removed" was wrong. It still fires whenever rasterization fails or an upload cannot
  be opened by Pillow. It is now covered by a test rather than deleted.

Test suite grew from 38 to 40, covering both overlay paths.

### 2026-09-20 — Step A2 implemented: real PDF export

`GET /v1/session/{id}/report?format=pdf` now returns a genuine PDF rather than
printable HTML. This closes module B14 and the last outstanding gap in Phase 7, so
Phases 0-8 are all complete.

**Renderer choice.** The plan specified WeasyPrint, which cannot be used here: it
depends on native GTK libraries and fails on this machine with
`cannot load library 'libgobject-2.0-0'`. Installing GTK on a demo machine is an
avoidable failure mode on presentation day. `xhtml2pdf` is pure Python, needs no
native dependencies, and renders the existing template correctly — it ignores
`border-collapse`, which is cosmetic only.

**Content parity had to be fixed first.** The plan assumed the HTML template already
carried full parity with the Results page and that the PDF step needed no template
work. That was wrong: the template showed only *counts* of boxes and region tags,
and embedded no imagery at all. A content-parity test against it would have passed
while the report showed no evidence whatsoever. The report now carries the annotated
overlay image and a table of every bounding box with its bounds and score. A
verified render is three pages: answer and confidence, evidence image plus box
table, then the full execution trace.

**Other changes.** The PDF is rendered once per session and cached at
`sessions/<id>/report.pdf`; session ids are unique per analysis, so a cached file
can never be stale. A rejected session now returns `409` for every report format,
per SPDD §9.3 — the frontend already early-returns to the rejection view and never
offers the download button, so nothing in the UI breaks. `?format=html` still
serves the printable HTML for anyone who wants it.

Test suite grew from 35 to 38: the PDF is a real PDF and is cached, the report
carries the evidence images and box labels, and a rejected session yields 409.

### 2026-09-20 — Remaining work broken into executable steps

Added §10.5 to the Development Plan: a sequenced execution plan covering everything
still marked PARTIAL or TODO. Sections 10.2–10.4 said what each module is; §10.5 says
what to do next and in what order.

The remaining work is organised into four tracks:

- **Track A — hardening, no model required.** Eight independent items that can start
  immediately: real raster metadata, real PDF export, persistent datastore,
  externalized config, live/mock honesty in the UI, the map layer, frontend tests and
  direct session reopen. Each carries numbered steps and a "done when" condition.
- **Track B — the ML programme.** M0–M11 in dependency order, gated on two blocking
  decisions that need a human, not a keyboard: pinning the backbone model with an
  exact revision, and confirming actual GPU hardware.
- **Track C — integration.** Wiring Track B into the running system. Starts with C0,
  removing the scenario-engine calls that `ConfidenceScorer` and both fusion modules
  still make directly — if those survive the swap, the scorer keeps overriding real
  model confidence with canned rationales and the swap looks successful while doing
  nothing.
- **Track D — deployment.** Containers, config wiring, health-gated startup, and the
  offline-NFR smoke test.

§10.5 also closes the granularity gap left by yesterday's merge. Compressing the old
Implementation Plan's per-step detail into one table row per module was the right call
for the modules already built, but it left the unbuilt ones without an executable
breakdown. That detail now exists again for exactly the work that still needs it, and
each step names the files it touches, the Appendix A ambiguity it must resolve first,
and the condition that closes it.

### 2026-09-19 — Plan documents merged

`SatQuery_AI_Implementation_Plan.md` (1,232 lines) and
`SatQuery_AI_Hackathon_Development_Plan.md` (1,646 lines) were merged into a single
`docs/SatQuery_AI_Development_Plan.md`, and the two originals removed.

The two were not in fact redundant — they described the same system at different
granularities. The Development Plan held the product goal, philosophy, UX
specification, dummy-model scenarios and the nine delivery phases; the
Implementation Plan held the module/step task breakdown across Frontend (F0–F9),
Backend (B0–B17) and AI/ML (M0–M11), with cross-domain dependencies and 24 flagged
ambiguities. Both layers are preserved in the merged document: sections 1–9 are the
product and roadmap, section 10 is the task breakdown.

What the merge resolved: the two plans contradicted each other, and both
contradicted the code. The Implementation Plan specified a `services/` microservice
monorepo, per-service requirements files, SQLAlchemy with Alembic migrations,
Docker Compose with health-gated startup, CI, and `VITE_API_BASE_URL` — none of
which exists. The Development Plan specified Tailwind, Leaflet, a `/processing`
route and `dummy_scenarios.py` — also none of which exists. Every such conflict is
now recorded in Appendix B with the adopted resolution, and every module and phase
carries a DONE / PARTIAL / TODO marker reflecting the actual build state.

Appendix A carries the 24 flagged ambiguities forward, updated: four are now
resolved by decisions the code has since made (Python version and dependency pins,
local-filesystem object store, overlay-rendering ownership, and the removal of an
unused component), the rest remain open, including the three standing risks —
compute budget, domain-shift proxy data availability, and complementarity-detector
readiness.

References in `CLAUDE.md` were updated to point at the merged document.

The graphify knowledge graph was rebuilt against the new document set: **435 nodes,
1,080 edges, 25 communities**, with the two deleted plans pruned and the merged
plan present. Note a limitation of the doc layer: `CLAUDE.md` and
`PROGRESS_LOG.md` contribute only one node each, because documents that describe
code have their extracted entities attributed to the code files they discuss, and
graphify drops those as out-of-scope. The code layer (385 AST nodes) is complete
and is what architecture queries actually traverse.

### 2026-09-19 — Codebase audit, clutter removal and bug fixes

Full read-through of the backend, frontend and the five design documents,
verifying the code against the SPDD and the two plan documents.

**Verification performed.** Frontend dependencies were not installed in this
checkout; after `npm install`, `npm run build` and `npm run lint` both pass
(2 non-blocking fast-refresh warnings in `SatQueryContext.tsx`). The backend
imports and serves all 6 routes. Of the four root-level test scripts, three
passed and `test_phase4_scenarios.py` failed on a real bug.

**Bugs found and fixed:**

1. **Every grounded demo answered "Low confidence".** `VerifierNode` pulled the
   first integer out of the concatenated answer text and compared it to the box
   count. Scenario 1's answer begins "1) Marine Port Basin", so the list marker
   was read as a claim of 1 target against 3 boxes. Scenarios 1, 4 and 5 all
   tripped it. The check now runs only for genuine counting questions, and treats
   a claim as consistent if any integer in the answer matches the feature count.
2. **Boxes were duplicated in fusion and compound responses.** `SpecialistRouter`
   handed the same scenario boxes to several evidence items and the verifier
   summed across items. The compound route returned literal duplicate box IDs, so
   the UI drew each box twice. Added `dedupe_boxes()`, applied on both the router
   and verifier paths.
3. **Captions were ungrounded.** The `single_vqa`/`single_caption` route only ran
   the grounding specialist for counting questions, so Scenario 1 narrated three
   fuel tanks while returning zero boxes. Grounding now runs for the whole
   VQA/caption family. This was the `test_phase4_scenarios.py` failure.
4. **Input preview URLs returned 404.** `routes_analyze.py` built
   `/storage/sessions/{id}/inputs/{filename}` while `StorageService` saved files
   as `image_{n}_{filename}`. Storage now returns the stored name and the route
   uses it.
5. **Report confidence badge was always green.** `report_service.py` hardcoded
   the `badge-high` CSS class, so a Low-confidence report rendered as High. The
   badge now follows the tier, and interpolated values are HTML-escaped — the
   user's query reaches the report through trace summaries.
6. **`change_and_grounding` discarded its change boxes** — grounding results
   replaced them instead of being merged.
7. **`Query(regex=...)`** in `routes_session.py` is removed in current FastAPI;
   changed to `pattern=`.
8. **Configured thresholds were ignored.** `CompatibilityValidator` hardcoded
   30.0 and 40.0 instead of `MAX_NODATA_PERCENT` and `CLOUD_MASK_WARN_PERCENT`.
9. **A demo answer contradicted its own evidence** — the vessel fallback claimed
   3 vessels while returning 2 boxes.
10. **A no-op expression** in `orchestrator_service.py`
    (`any(... for _ in [1])`) was simplified.

**Clutter removed:**

- `backend/app/specialists/scenarios.py` (168 lines) — superseded by
  `scenario_engine.py` and imported nowhere.
- `frontend/src/components/ValidationMessage.tsx` — never imported.
- Five unreferenced image assets (`hero.png`, `react.svg`, `vite.svg`,
  `favicon.svg`, `icons.svg`); `index.html` uses an inline data-URI favicon.
- Root `package-lock.json` — an empty stub with no accompanying `package.json`.
- `frontend/README.md` — the unmodified Vite starter template.
- `playwright-core` — an unused frontend dependency.
- `EVIDENCE_DIR` in `config.py` — created on import, never written to.
- 84 accumulated demo session folders in `backend/storage/sessions/`.
- Unused imports across `config.py`, `storage_service.py`, `metadata_service.py`,
  `query_interpreter.py`, `verifier_node.py` and `report_service.py`.

**Restructured:**

- The four root-level `test_*.py` scripts, which hand-rolled multipart bodies
  against a server the developer had to remember to start, were replaced by a
  `tests/` suite: **35 pytest tests** using FastAPI's `TestClient`, writing to a
  temporary storage root so runs never pollute `backend/storage/`. Coverage spans
  the validator, the API contract, all 8 task types, all 4 rejection paths, and a
  regression test for each bug above.
- Added `requirements.txt` and `pytest.ini`; dependencies previously had to be
  guessed and installed by hand.
- The frontend's API base URL was hardcoded in three places; it is now exported
  once from `services/api.ts`, alongside a `resolveAssetUrl()` helper. The
  backend's `/storage/...` overlay and preview paths were resolving against the
  Vite dev server and silently 404ing, so backend-rendered overlays never
  appeared in the UI; they now resolve against the API.
- `.gitignore` is whitelist-style (`/*` with explicit un-ignores), which meant
  `CLAUDE.md`, `tests/`, `pytest.ini`, `requirements.txt` and `.graphifyignore`
  were all invisible to git. Whitelisted them; `graphify-out/` stays ignored.
- Added `CLAUDE.md` at the repo root and a graphify knowledge graph in
  `graphify-out/` (466 nodes, 1130 edges, 32 communities).

**Result:** 35/35 tests pass, the frontend builds clean, and the demo scenarios
return their intended confidence tiers with unique boxes.

### Earlier (pre-log)

Reconstructed from git history; these commits predate this log.

- **`1aad09c`** — Restructured into `docs/`, added backend, frontend and tests.
- **`efb5b3b`** — Initial commit: problem statement, synthesized solution,
  implementation plan, SPDD and the SIH presentation.
- **`291961d`** — Light theme.
- **`09121d6`** — Working frontend, partially working backend.
