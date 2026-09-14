# SatQuery AI — 12-Minute Speech (Bullet Point / Cue Card Version)

*Use this as your speaking cue card. Each bullet is a beat to hit in your own words — don't read it verbatim, use it to jog your memory live.*

---

## OPENING (0:00 – 1:15)

- Satellites already see everything — floods, deforestation, new construction
- Problem isn't "seeing" — it's that answering a simple question about imagery needs a GIS expert + right model + hours of manual work
- A disaster officer can't just *ask* "has water level risen since yesterday" — too much expertise stands in the way
- We built **SatQuery AI**: type a question in plain English, upload 1–2 images (optical/SAR, same-day/months apart) → system figures out what to do, does it, checks itself, returns a trustworthy answer
- Promise 3 things in this talk:
  1. We understood this problem statement deeply
  2. Our architecture is genuinely buildable, not just clever
  3. We found the one risk most teams will walk past

---

## SLIDE 1 — TITLE (1:15 – 1:35)

- SatQuery AI — Vision-Language Assistant for Multimodal Remote Sensing via Text Queries
- SIH26167, ISRO, Space Technology theme, Software category
- Team Technocrats
- Move fast — don't linger here

---

## SLIDE 2 — PROPOSED SOLUTION / INNOVATION & USP (1:35 – 4:00)

**Innovation 1 — Validate before executing**
- Naive system: runs change detection even on non-overlapping images → confident wrong answer
- Our system: checks modality, format, CRS, spatial/temporal overlap **before** running anything
- If invalid → rejects query with a specific reason, doesn't guess
- Hard structural constraint, not a "please be careful" prompt

**Innovation 2 — Honest optical-SAR fusion**
- Obvious (wrong) approach: feed both into one model, hope fusion emerges
- BigEarthNet's own findings: SAR + multispectral channels fed into RGB-pretrained model → performance gets *worse*, not better
- Our approach: analyze optical and SAR **independently**, then compare
- Tag every finding: "both agree" / "optical-only" / "SAR-only"
- Final answer cites exactly which modality supported which claim

**Innovation 3 — Every answer is auditable**
- Visual evidence (shown, not just claimed)
- Confidence score (honest about known weak points, e.g. counting)
- Full execution trace (which model ran, what parameters, what it returned)
- Not a black box — matters a lot for a space-agency customer

---

## SLIDE 3 — TECHNICAL APPROACH (4:00 – 6:30)

- One shared frozen vision-language backbone
- Small task-specific **LoRA adapters** on top (<1% of parameters each)
- Separate adapters for: VQA/captioning, grounding, change-VQA
- Why separate adapters, not one joint model?
  - Joint multi-task training on narrow RS data → documented collapse (one case: F1 dropped below 50%)
  - Separate adapters avoid collapse; shared backbone avoids loading N full models

**Full pipeline flow:**
1. User uploads image(s) + text query via web UI
2. Metadata extracted (CRS, resolution, bands, acquisition date)
3. Query interpreted → converted into structured task (VQA / grounding / change / fusion)
4. Compatibility validation (the "reject before running" step)
5. Routed to correct specialist adapter or fusion pipeline
6. Output verified — sanity checks (boxes inside image, overlap checks, cross-tool agreement)
7. Confidence scored
8. Final answer composed: text + visual evidence + confidence + trace

- Point to the diagram — every box = a real component being built, not a placeholder

---

## SLIDE 4 — FEASIBILITY AND VIABILITY (6:30 – 9:15) ⭐ MOST IMPORTANT SLIDE

**Feasibility basics (move fast):**
- LoRA = cheap compute, realistic for hackathon timeframe
- All datasets open-source: BigEarthNet, VRSBench, RSVQA, CDVQA
- Self-hostable via Docker, no third-party API dependency

**⭐ THE KEY DIFFERENTIATOR — slow down here:**
- Mandatory training data (BigEarthNet) = Sentinel-1/2 imagery → 10–60m resolution
- Actual evaluation data (per problem statement) = Cartosat-2S + RISAT → 0.65–2m resolution
- **Gap = 5x to 30x resolution difference between training and evaluation data**
- This is barely spelled out in the problem statement — most teams will miss it or ignore it
- Most teams: train on BigEarthNet, hope it generalizes, hope for the best
- Us: built it as a first-class design concern from day one
  - GSD-normalization tiling (rescale incoming imagery to match trained resolution regime)
  - Radiometric-jitter augmentation during training (expose model to wider brightness/contrast/noise range)
- Not claiming this fully solves the gap — no team can without real evaluation data
- Claiming: we identified it as the central engineering problem and designed for it honestly

**Other risks + mitigations (quick mention):**
- Multimodal fusion complexity → structured fusion pipeline (not naive concatenation)
- Model reliability (counting, small changes) → verifier layer + confidence discount
- Compute/integration → modular components, Docker deployment

---

## SLIDE 5 — IMPACT AND BENEFITS (9:15 – 10:45)

- Disaster management: instant evidence-backed flood/damage assessment, no manual GIS wait
- Agriculture: crop/land tracking without needing to pick the right model
- Forest/water monitoring: natural-language question instead of manual image-by-image review
- Environmental angle: turns monitoring from *retrospective audit* → *real-time early warning*
- Governance angle (important — customer is ISRO):
  - Sensitive imagery (Cartosat/RISAT class)
  - Third-party API dependency = non-starter for a space agency
  - Our system: fully self-hostable, no default external dependency
- Auditability: every answer has evidence + confidence + trace
  - Matters if output ever feeds real decisions (e.g., flagging illegal construction, deforestation enforcement)

---

## SLIDE 6 — RESEARCH AND REFERENCES (10:45 – 11:30)

- Not speculative — every decision tied to verifiable research
- BigEarthNet paper → defines training data + its own documented limitations
- MM-OVSeg → informs our fusion comparison/alignment approach
- Calibration research → separating "confidence in what I saw" vs "confidence in how I reasoned" gives much better-calibrated scores than asking a model to just state a percentage
- Two independent 2026 surveys on agentic RS systems → name fragile tool orchestration (wrong tool, malformed calls) as the field's current unsolved problem
- Our validate-before-execute design = direct structural answer to that named, published gap

---

## CLOSING (11:30 – 12:00)

- SatQuery AI ≠ a language model with a satellite image bolted on
- Validates before acting → never guesses on unanswerable questions
- Never fakes fusion → compares optical/SAR honestly, cites sources
- Confronts the Sentinel→Cartosat/RISAT resolution gap head-on — most teams will miss this
- Every answer shows its work, end to end
- Technically grounded + honestly scoped + genuinely buildable
- = not just a working prototype, but something ISRO could realistically trust with real data
- Thank you — happy to take questions

---

## PACING CHECKPOINTS

| Checkpoint | Target time elapsed |
|---|---|
| Finish opening | 1:15 |
| Finish Slide 1 | 1:35 |
| Finish Slide 2 | 4:00 |
| Finish Slide 3 | 6:30 |
| Finish Slide 4 (domain-gap slide) | 9:15 |
| Finish Slide 5 | 10:45 |
| Finish Slide 6 | 11:30 |
| Finish closing | 12:00 |

**Delivery notes:**
- Slide 4 domain-gap point is your strongest differentiator — slow down, let the "5x to 30x" number land
- Rehearse out loud with a timer at least twice — spoken pace ≠ reading pace
- If short on time, cut Slide 6 down to 2 sentences first
