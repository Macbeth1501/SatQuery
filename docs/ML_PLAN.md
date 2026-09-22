# Plan: the 10 remaining ML capabilities (B1-B4, B6-B10, B12)

**Status: approved by the owner 2026-09-22. Phase 0 is done: B2 (G-B2 passed), C0, B8 functions, and now B4 fitted (beats the always-optical baseline on every rendering, 92.9% overall, 10.2 ms/call). Phase 1 (B1 full ingestion) is done: 549,488 patches per modality, the official split plus buffer index, the 5%-cloud cap, and the box-row extraction with the `[x0 y0, x1 y1]` convention confirmed before B6 trains. Next: phase 2's B9 go/no-go. Progress lives in `docs/PROGRESS_LOG.md`.** Sequencing detail
for Track B of `docs/SatQuery_AI_Development_Plan.md` §10.5; where the two disagree, this file carries the owner's
later decisions (B9 moved early, full B1 ingestion, Kaggle and laptop in parallel).

## Context

The application shell is complete, but only one ML path is real: single-image VQA through `ml/serve_vqa.py` (run 2 live, run 3 is the model of record). `docs/HANDOFF_PROMPT.md` §3 asks for a plan the owner can review before any training starts. The plan must say what order to build the 10 remaining items in, what each needs, and where the go/no-go gates are. Constraints: a 4 GB RTX 3050; cloud GPUs on **free tiers only, run so they never hit a quota**; full BigEarthNet S1/S2 already on disk as `.tar.zst` (117 GB, 224 GB free); no CDVQA, SOMA-1M or CMU-Data yet.

Owner decisions taken for this plan (2026-09-22): B9 gets an **early, time-boxed go/no-go test**; B1 is a **full ingestion**; B3 replaces the keyword interpreter **only if it beats it by a significant paired margin** on held-out queries; cloud means free Kaggle, with runs sized to stay under its limits.

**One standard for every trained piece** (unchanged from run 2 and run 3): the result is written down before the run, scored on held-out tiles, paired against a baseline that does not use the image, and reported honestly even when it fails. Nothing is wired into `backend/` until it passes. The demo cards are never evidence.

## Where each item runs: both, in parallel (owner decision 2026-09-22)

The owner has a phone-verified Kaggle account, fast unmetered upload, a laptop that can run overnight, and wants the fastest finish. So **Kaggle trains (B6, B7, B9) while the laptop works at the same time**: B1 ingestion, B4, B8, scoring returned adapters, serving the demo, and training overnight as a backup whenever the Kaggle week's quota is short. Example: while B6 trains on Kaggle, B1 ingests locally; while B7 trains on Kaggle, B9 can fall back to the laptop overnight.

The rule: **any GPU training run goes to Kaggle (free tier) if a measured speed test shows it is faster there**, and it is budgeted so it never hits a limit. Data preparation, serving, evaluation and CPU work stay on this machine, and so does the demo (the live model runs locally). This machine is the fallback whenever Kaggle quota is short.

| Item | Where | Why |
|---|---|---|
| B1 data | Local (CPU + disk) | The 117 GB archives are here; uploading all of them is impractical. Kaggle only gets small packed subsets. |
| B2 serving | Local | Inference for the demo; no training. |
| B3 interpreter | Local | Prompting the base model; no training. |
| B4 modality | Local (CPU) | A tiny model that takes seconds on CPU. |
| B6 grounding | **Kaggle** (local fallback) | QLoRA, like run 3; a T4 has 16 GB versus 4 GB here, so bigger batches and higher resolution. |
| B7 change | **Kaggle** | Two images per example; 4 GB here is unlikely to fit. |
| B8 domain gap | Local | A function plus inference-only ablations. |
| B9 detector | **Kaggle** (local fallback) | Contrastive training benefits from large batches, which 4 GB caps. |
| B10 fusion | Local (Kaggle if it needs two-image training) | A linear probe plus templates. |
| B12 confidence | Local | Calibration only. |

**Rules for staying under the free limits (for every Kaggle run):**
1. **Read the real limits from the account first** (weekly GPU hours, maximum session length, dataset size). This plan assumes no numbers.
2. **Measure before committing:** a 20-step timing run on Kaggle and the same 20 steps locally. Kaggle is used only if it is actually faster; that number goes in the log.
3. **Budget each run** from the measured time per step: it must finish within one session with at least 25% spare time, and use at most about 60% of the week's remaining hours. If it doesn't fit, the run is shortened or split, never paid for.
4. **Checkpoint every N steps and resume** (`b5_train_lora.py --resume`, already built), so a session cutoff costs minutes, not the run. Download checkpoints at the end of each session.
5. **One Kaggle run at a time**, and a quota ledger in `docs/PROGRESS_LOG.md` (hours used and left per week) updated after every session.
6. **Upload only packed subsets** through `ml/pack_for_kaggle.py` (reused, extended per item), never the full B1 pool.
7. Trained adapters come back to this machine for evaluation and serving, so every score is produced by the same local harness as run 2/run 3.

## Order and rationale

| Phase | Items | Compute | Why here |
|---|---|---|---|
| 0 | B2 serving, B4 modality, B8 domain-gap function, C0 cleanup | Local, inference only / CPU | Cheap, and everything else plugs into them. Nothing here needs new data or training. |
| 1 | B1 full ingestion (runs in the background alongside phase 0) | CPU + disk, a long unattended run | B6, B9 and B10 all train from it. |
| 2 | **B9 go/no-go test** (time-boxed) | Kaggle (local fallback) | Highest risk. Deciding it early makes B10's path a deliberate choice. |
| 3 | B3 interpreter | Local, inference only | Reuses the backbone already loaded in B2; no training. |
| 4 | B6 grounding | Kaggle QLoRA (local fallback) | Single image; the recipe is proven by run 3. |
| 5 | B7 change | Kaggle | Two-image input; needs new data (CDVQA). |
| 6 | B10 fusion | Local | Depends on the B9 result and the Appendix A #12 decision. |
| 7 | B8 ablation tables (one per adapter) | Local inference | Run as each adapter lands; collected here. |
| 8 | B12 decoupled confidence (stretch) | Local | Only after everything else is demo-ready. |

Differences from the Development Plan's order (§10.5 "Suggested order"): B9 moves from last to phase 2, as the owner chose. B2 comes before B1 finishes, because serving only needs the adapters that already exist. B8's *function* comes early and its *ablations* come late.

## Per item

### Phase 0

**B2 — multi-adapter serving (M1).** Extend `ml/serve_vqa.py`; do not rewrite it. Keep its measured decoding choices (the answer distribution from the first `generate` step, logits recomputed in float32, no forward pass after `generate`). Load run 2 and run 3 together on the one 4-bit backbone through PEFT (`load_adapter` with a name, `set_adapter` per request, `disable_adapter` for base). Add `/health`, `/adapters` and one parameterised `/infer` taking `adapter` and a task token (`[vqa] [caption] [ground] [change] [fusion]`), with the task-token helper shared in `ml/b5_common.py`. The live demo keeps sending `adapter=run2`, so nothing visible changes. **Done when:** a synthetic back-to-back run2→run3 call shows no latency spike on the second call (the §10.5 criterion), with both deltas resident, and measured VRAM fits beside the desktop. Backend side: `backend/app/services/model_client.py` sends the adapter name. `serve_vqa.py` needs a small pytest for the task-token helper in `tests/test_ml.py`.

**B4 — modality heuristic (M9).** CPU only, not a neural network. Features: band count, dtype, wavelength/platform tags, value-range and distribution statistics (SAR float dB vs optical uint16 reflectance). Train logistic regression / a shallow tree (scikit-learn, already in `.venv-ml`; the backend needs it too, or the tree is exported as plain rules/coefficients so `backend/` gets no new dependency; **recommend exporting coefficients to JSON**). Training data: BigEarthNet S1 and S2 patches from B1 or the bench subset, plus the demo rasters. The baseline is today's tag/filename logic. Called only when `metadata_service.py` cannot decide, and it returns `None` below a confidence threshold that lives in `config.py`. **Done when:** held-out accuracy is reported, it runs in under 100 ms, and it is wired into the ambiguous-modality fallback with tests.

**B8 — domain-gap function (M6), part 1.** A pure function in `ml/` that normalises GSD by tiling and resampling, and applies radiometric jitter: histogram matching toward Cartosat-2S, and speckle injection matching RISAT. Parameters come only from published sensor specifications, cited in the code. Where a specification value cannot be found it stays a named, flagged parameter; no number is invented. Decide Appendix A #13 here: **recommend applying it to every specialist call** (matching the SPDD), at C2's shared entry point. It is used only for the ablation (phase 7), never in headline numbers.

**C0 — remove scenario-engine calls** from `confidence_scorer.py`, `complementarity_detector.py` and `verbalizer.py` on any path a real model will use. Required before B9/B10 can be wired in.

### Phase 1

**B1 — full ingestion (M0).** A new `ml/b1_full.py` streams both `.tar.zst` archives (`zstandard` + `tarfile`, never unpacking to disk) into LMDB: S2 as RGB+NIR `uint16` and S1 as VV/VH `float16`, 120×120, keyed by patch ID. S2 and S1 are joined by the reBEN metadata, whose parquet ships with the archives (to check). Keep the **official split** as `b1_slice.py` does, with the 2-cell spatial buffer, and write a committed split log. Keep the 5%-cloud cap that replaced the degenerate quartile filter, and log `pairs_in/pairs_kept` to `ml/b1_full_report.json`. Pull the box rows from `BigEarthNet.txt.parquet`; **the `[x0 y0, x1 y1]` box convention must be confirmed by drawing boxes on patches before B6 trains.** Fusion-bridging data (SOMA-1M, CMU-Data) goes in a separate `data/fusion_bridge/` and only if B10 turns out to need it. Estimated disk: about 55 GB S2 plus 27 GB S1 before LMDB overhead (an estimate to be measured on the first 10k patches before the full run). The run is resumable by patch ID and runs in the background with sleep disabled. **Done when:** the pool rebuilds from the committed script and the report is auditable.

### Phase 2 — B9 go/no-go (M7)

A time-boxed test, fixed before it starts (proposed: about 3 working sessions). A pair of small ViT-S/16 DINO encoders (optical and SAR), trained with InfoNCE on a packed subset of B1's co-registered S1/S2 pairs, on Kaggle (large contrastive batches), with a local 4 GB fallback at a smaller batch size. A frozen DINO initialisation for the optical side; the SAR side starts from the same weights with a new patch embedding for 2 channels.

**Pre-registered test (written down before training):**
1. Alignment: cross-modal retrieval R@1/R@10 on held-out tiles, well above chance and above a baseline without training (a random-init encoder or raw band statistics).
2. Complementarity, which is the actual job: on held-out pairs, detecting regions where the optical image is uninformative (real cloud-flagged patches, plus synthetic cloud overlays as a secondary check), measured as the AUROC of feature disagreement, paired against today's rule-based detector on the same pairs.

**Go** = both pass on held-out tiles. **No-go** = the rule-based fallback is kept, verified end-to-end, and labelled "rule-based" in the demo and write-up. Either outcome is recorded in `docs/PROGRESS_LOG.md` and closes the gate; the choice is not reopened silently later.

### Phase 3 — B3 interpreter (M2)

No new model: the base Qwen2-VL-2B already loaded in B2 is run with the adapters switched off, text only, and a `/interpret` endpoint does few-shot prompting constrained to the `TaskSpec` JSON Schema (grammar-constrained decoding, e.g. `lm-format-enforcer`/`outlines`; pick the one that works with the pinned `transformers`). Then an out-of-enum `taskType` is structurally impossible. Exemplars come from the Problem Statement's queries plus hand-written ambiguous cases. A **held-out labelled query set** (about 300, written before prompting is tuned, never used for exemplars) scores it against the keyword `query_interpreter.py`. `intentConfidence` comes from the constrained token's probability and is calibrated on a separate validation slice. **Replace only if** the paired McNemar lead is significant and no demo query regresses (owner rule). Then C1 wiring follows: one repair retry, `interpretation_failed` added as a rejection code (Appendix A #5), and the keyword interpreter kept as the fallback when the server is unreachable.

### Phase 4 — B6 grounding (M4)

A **separate LoRA, trained from the base model**, not from run 3 (never trained jointly with VQA). Reuse `b5_train_lora.py`/`b5_common.py` with a grounding collate that emits Qwen2-VL box tokens, converting BigEarthNet's convention to Qwen's 0-1000 grid and then to the app's 0-100 at serve time. Multiple candidates through top-k sampling or beams, returning ≥2 boxes. Baseline without the image: a prior box per question type (the mean box from train). Metrics: Acc@0.5 and mean IoU on held-out tiles, paired against the prior-box baseline. Trained on Kaggle under the quota rules (local fallback), about the scale of run 3; the 20-step timing test decides. Only passing boxes are wired into the router, always with a confidence badge.

### Phase 5 — B7 change (M5)

1. **Data:** CDVQA ingestion (check its licence and source before downloading), keeping `test2` as the reporting split.
2. **Trained on free Kaggle (T4)**, reusing `ml/b5_kaggle.ipynb` + `ml/pack_for_kaggle.py`, under the quota rules above. A local two-image fit test is done only to know whether this machine can serve and evaluate it.
3. **Two-stage model:** first plain Qwen2-VL multi-image + LoRA (the baseline); then the difference-attention module as a small trainable block between the two visual encodings, kept only if it beats stage 1 on the pre-registered test.
4. The deterministic count comes from the attention/difference map, independent of the text answer.
Baselines: text only and the same image twice. Accuracy reported per question category on `test2`.

### Phase 6 — B10 fusion (M8)

First decide Appendix A #12. **Recommendation: a structured LULC side-channel** made of per-class yes/no probabilities from run 3 over the 19 BigEarthNet classes (it can already do this through `/infer`) for the optical side, plus a linear probe on the B9 SAR encoder (or on SAR band statistics if B9 was no-go) for the SAR side. The verbalizer takes only these structured fields, never pixels, and every claim names the modality it came from (templates in `verbalizer.py`). Evaluation: a small hand-built set, labelled **non-standard**, paired against optical-only. C3 adds the `trained`/`rule_based` switch at one call site.

### Phase 7 — B8 ablation

For each adapter that passed (run 3, B6, B7, B10): score on the held-out slice as-is and after the B8 transform, in a before/after table. Never mixed into headline numbers.

### Phase 8 — B12 (stretch)

Separate perception/reasoning confidence, calibrated on validation only. Not started until phases 0-7 are demo-ready.

## Gates

- **G-B2:** the two-adapter latency criterion passes; otherwise B6/B7 serving is redesigned before training.
- **G-B9:** the go/no-go above; it sets B10's path.
- **G-each-adapter (B3, B4, B6, B7, B10):** a significant paired lead over the baseline without the image/model, on held-out data, or it is not wired in and the failure is logged.
- **G-B12:** everything else demo-ready.

## Practical rules for every step

- Disable sleep (`powercfg /change standby-timeout-ac 0`, `-dc 0`) before any GPU run or the B1 ingestion.
- The B2 server and training share the GPU, so it is one or the other.
- After each step: update `docs/PROGRESS_LOG.md` (Current status, Next step, History), update the matching row of Development Plan §10.5, run `graphify update .`, and run the backend and frontend tests if `backend/` or `frontend/` changed.
- No git writes; list the uncommitted paths at the end.
- Standing owner rule: GPU training goes to free-tier Kaggle when it is measurably faster, budgeted so it never hits a quota limit; no paid plans.
- The first Kaggle step (before B6/B9): read the account's limits, then the 20-step speed comparison on the run-3 recipe, logged.

## Verification

- B2: a script timing run2→run3→base back-to-back calls; `/adapters` lists both; the live demo's 23 answers are unchanged (a Playwright check in a scratchpad venv).
- B1: the report's counts; spot-check 20 random patches (S1/S2 alignment, split membership); a rebuild from scratch on a 1k-patch subset gives the same keys.
- Each trained piece: a committed result file under `data/*_eval/` plus a paired comparison in the style of `ml/b5_compare.py` (McNemar p, Wilson CI); every number in the log traces to a file.
- Wiring: `python -m pytest`, `npm test`, `npm run build`, and one browser check per new path.

## First concrete step

B2 (extend `ml/serve_vqa.py` to hold both adapters, with `/health`, `/adapters`, `/infer`, and the latency test), with B1's 10k-patch disk measurement running in parallel on the CPU.
