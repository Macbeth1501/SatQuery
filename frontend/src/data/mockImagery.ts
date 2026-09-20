/**
 * Synthetic port-scene imagery for the offline demo scenarios (inline SVG data URIs, so the
 * demo works with no network).
 *
 * Each scene is drawn to fit the bounding boxes the live backend returns for that scenario
 * (see demoParity.json), so the annotated features sit on something that looks like what
 * the answer text describes. The boxes are 0-100 percentages; the canvas is 600x400, so a
 * box maps to pixels with X() and Y().
 */

const W = 600;
const H = 400;
const X = (pct: number) => (pct * W) / 100;
const Y = (pct: number) => (pct * H) / 100;

const toUri = (body: string, defs = ''): string => {
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">` +
    `<defs>${defs}</defs>${body}</svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
};

const rect = (x: number, y: number, w: number, h: number, fill: string, extra = '') =>
  `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}" ${extra}/>`;

const ellipse = (cx: number, cy: number, rx: number, ry: number, fill: string, extra = '') =>
  `<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" fill="${fill}" ${extra}/>`;

const poly = (points: string, fill: string, extra = '') =>
  `<polygon points="${points}" fill="${fill}" ${extra}/>`;

const label = (text: string, fill = '#ffffff') =>
  `<text x="20" y="30" fill="${fill}" font-family="monospace" font-size="12" opacity="0.9">${text}</text>`;

/** A grid of small building/container blocks filling a rectangle. */
const blocks = (
  x: number,
  y: number,
  w: number,
  h: number,
  cols: number,
  rows: number,
  fills: string[],
): string => {
  const cw = w / cols;
  const ch = h / rows;
  let out = '';
  for (let r = 0; r < rows; r += 1) {
    for (let c = 0; c < cols; c += 1) {
      const fill = fills[(r * 3 + c * 2) % fills.length];
      out += rect(x + c * cw + 1.5, y + r * ch + 1.5, cw - 3, ch - 3, fill);
    }
  }
  return out;
};

/** An elongated hull, rotated about its centre. */
const vessel = (cx: number, cy: number, len: number, wid: number, angle: number, fill: string) =>
  rect(cx - len / 2, cy - wid / 2, len, wid, fill, `rx="${wid / 2.5}" transform="rotate(${angle} ${cx} ${cy})"`);

const WATER_GRADIENT =
  '<linearGradient id="water" x1="0%" y1="0%" x2="100%" y2="100%">' +
  '<stop offset="0%" stop-color="#0f3854"/><stop offset="100%" stop-color="#1e5c82"/></linearGradient>';

const CONTAINER_COLORS = ['#b5482f', '#2f5f8f', '#c9a227', '#4f7a4a', '#8a8a8a', '#a33b3b'];

// ---------------------------------------------------------------------------
// Scenario A: land-cover of a port, with three storage tanks (backend boxes s1_tank_01..03)
// ---------------------------------------------------------------------------

const tank = (l: number, t: number, r: number, b: number, roof: string) => {
  const cx = X((l + r) / 2);
  const cy = Y((t + b) / 2);
  const rx = X(r - l) / 2 - 4;
  const ry = Y(b - t) / 2 - 3;
  return (
    ellipse(cx, cy + 5, rx, ry, '#3a3a3a', 'opacity="0.55"') +
    ellipse(cx, cy, rx, ry, '#d8d8d2') +
    ellipse(cx, cy, rx * 0.78, ry * 0.78, roof) +
    ellipse(cx, cy, rx * 0.2, ry * 0.2, '#6b6b66')
  );
};

export const SCENE_A_OPTICAL = toUri(
  rect(0, 0, W, H, '#8b8674') +
    // marine port basin: the lower-left of the frame
    poly('0,255 240,255 320,285 390,335 400,400 0,400', 'url(#water)') +
    // quay edge
    `<polyline points="0,255 240,255 320,285 390,335 400,400" fill="none" stroke="#c8c4b4" stroke-width="5"/>` +
    // container terminal
    rect(405, 300, 195, 100, '#7a7a74') +
    blocks(410, 305, 185, 90, 9, 4, CONTAINER_COLORS) +
    // two gantry cranes along the southern quay
    `<line x1="330" y1="292" x2="392" y2="338" stroke="#e6b422" stroke-width="4"/>` +
    `<line x1="352" y1="305" x2="398" y2="342" stroke="#e6b422" stroke-width="4"/>` +
    // hydrocarbon depot pad and pipe runs
    rect(80, 70, 480, 190, '#9a9684', 'opacity="0.55"') +
    `<path d="M160 131 L301 149 L438 243" stroke="#5b5b56" stroke-width="3" fill="none"/>` +
    tank(18.4, 24.1, 34.8, 41.5, '#e9e9e4') +
    tank(42.1, 28.5, 58.2, 45.9, '#b9b9b0') +
    tank(65.0, 52.0, 81.2, 69.4, '#cfcfc6') +
    // transport corridor
    `<path d="M0 60 L600 90" stroke="#d6d2c4" stroke-width="7"/>` +
    `<path d="M0 60 L600 90" stroke="#4c4c48" stroke-width="1.5" stroke-dasharray="8,6"/>` +
    label('OPTICAL [Cartosat-2S] 0.65m GSD | BANDS: RGB-NIR'),
  WATER_GRADIENT,
);

// ---------------------------------------------------------------------------
// Scenario B: water-body grounding, two candidates (boxes s2_water_primary / secondary)
// ---------------------------------------------------------------------------

export const SCENE_B_OPTICAL = toUri(
  rect(0, 0, W, H, '#6d7a52') +
    rect(330, 200, 270, 200, '#8a8674') +
    blocks(345, 215, 240, 170, 8, 6, ['#a8a496', '#76736a', '#8a4d3b']) +
    // primary navigational channel / harbour basin
    `<path d="M60 70 Q 150 46 250 62 Q 318 80 312 190 Q 306 300 250 344 Q 150 362 74 336 Q 44 220 60 70 Z" fill="url(#water)"/>` +
    // secondary inland retention pond
    ellipse(X(73), Y(26.5), X(11) - 3, Y(11.5) - 3, 'url(#water)') +
    `<path d="M0 30 L330 0" stroke="#d6d2c4" stroke-width="4"/>` +
    label('OPTICAL [Sentinel-2] 10m GSD | BANDS: RGB-NIR'),
  WATER_GRADIENT,
);

// ---------------------------------------------------------------------------
// Scenario C: bi-temporal change (boxes s3_change_pier / s3_change_staging, on T2)
// ---------------------------------------------------------------------------

const temporalBase = (developed: boolean) =>
  rect(0, 0, W, H, '#7c7560') +
  // waterfront on the left
  `<path d="M0 0 L205 0 Q 222 120 210 220 Q 200 320 215 400 L0 400 Z" fill="url(#water)"/>` +
  // existing quay and terminal, present in both dates
  rect(215, 250, 190, 120, '#8f8b7c') +
  blocks(225, 258, 170, 100, 6, 3, ['#a8a496', '#76736a']) +
  // the eastern area that changes: gravel and scrub at T1, built at T2
  (developed
    ? // new pier foundation and rail extension
      rect(X(35), Y(22), X(27), Y(32), '#9a9a94') +
      `<line x1="${X(37)}" y1="${Y(30)}" x2="${X(60)}" y2="${Y(30)}" stroke="#3a3a3a" stroke-width="3"/>` +
      `<line x1="${X(37)}" y1="${Y(42)}" x2="${X(60)}" y2="${Y(42)}" stroke="#3a3a3a" stroke-width="3"/>` +
      // newly paved logistics staging yard
      rect(X(68), Y(45), X(20.5), Y(27), '#c9c9c2') +
      blocks(X(69), Y(47), X(18.5), Y(23), 6, 4, CONTAINER_COLORS)
    : rect(X(35), Y(22), X(27), Y(32), '#6f6a55') +
      rect(X(68), Y(45), X(20.5), Y(27), '#8a8462') +
      ellipse(X(78), Y(58), 40, 24, '#5f7a3d', 'opacity="0.7"'));

export const TEMPORAL_T1 = toUri(
  temporalBase(false) + label('OBSERVATION T1 (2023-03-15) — BASELINE'),
  WATER_GRADIENT,
);
export const TEMPORAL_T2 = toUri(
  temporalBase(true) + label('OBSERVATION T2 (2025-01-20) — CURRENT', '#38bdf8'),
  WATER_GRADIENT,
);

// ---------------------------------------------------------------------------
// Scenarios D and F: optical + SAR port pair (boxes s4_vessel_berth4 / berth7 / cloud_penetrated)
// ---------------------------------------------------------------------------

// Vessel hulls sit inside the s4 boxes: berth 4 (22.5-44.1, 14.2-32.8), berth 7 (51-73.6, 38.4-57.2),
// and the moored vessel (12.2-26.4, 64.8-78.5) that optical cloud hides but SAR resolves.
const V1 = { cx: X(33.3), cy: Y(23.5), len: 105, wid: 28, angle: 25 };
const V2 = { cx: X(62.3), cy: Y(47.8), len: 115, wid: 30, angle: 25 };
const V3 = { cx: X(19.3), cy: Y(71.6), len: 70, wid: 22, angle: 20 };
const CHANNEL = '0,-89 600,253 600,393 0,51';

export const PORT_OPTICAL = toUri(
  rect(0, 0, W, H, '#8b8674') +
    poly(CHANNEL, 'url(#water)') +
    // separate basin holding the moored vessel
    ellipse(V3.cx, V3.cy, 62, 36, 'url(#water)') +
    // central concrete quay and berths along the channel
    poly('60,-40 600,270 600,290 60,-20', '#b9b5a5', 'opacity="0.8"') +
    blocks(380, 280, 200, 100, 8, 4, ['#a8a496', '#76736a', '#8a4d3b']) +
    // inland container staging yard
    rect(410, 300, 160, 80, '#7a7a74') +
    blocks(414, 304, 152, 72, 8, 3, CONTAINER_COLORS) +
    vessel(V1.cx, V1.cy, V1.len, V1.wid, V1.angle, '#2f3a48') +
    vessel(V2.cx, V2.cy, V2.len, V2.wid, V2.angle, '#5b3a2a') +
    vessel(V3.cx, V3.cy, V3.len, V3.wid, V3.angle, '#3a4a3a') +
    // cumulus deck over the moored vessel
    ellipse(V3.cx, V3.cy, 78, 44, '#f4f6f8', 'opacity="0.93"') +
    ellipse(V3.cx + 34, V3.cy - 14, 46, 28, '#ffffff', 'opacity="0.9"') +
    ellipse(V3.cx - 40, V3.cy + 12, 40, 24, '#eef1f4', 'opacity="0.9"') +
    label('OPTICAL [Sentinel-2 / Cartosat-2S] | BANDS: RGB-NIR | CLOUD 42%'),
  WATER_GRADIENT,
);

export const PORT_SAR = toUri(
  rect(0, 0, W, H, '#2a2a2a') +
    rect(0, 0, W, H, '#444444', 'opacity="0.25"') +
    poly(CHANNEL, '#050505') +
    ellipse(V3.cx, V3.cy, 62, 36, '#030303', 'stroke="#38bdf8" stroke-width="1.5" stroke-dasharray="4,2"') +
    // double-bounce returns from the quay and built-up terminal
    poly('60,-40 600,270 600,290 60,-20', '#e2e2e2', 'opacity="0.85"') +
    blocks(380, 280, 200, 100, 8, 4, ['#d6d6d6', '#e8e8e8', '#bdbdbd']) +
    rect(410, 300, 160, 80, '#9a9a9a', 'opacity="0.6"') +
    vessel(V1.cx, V1.cy, V1.len, V1.wid, V1.angle, '#f2f2f2') +
    vessel(V2.cx, V2.cy, V2.len, V2.wid, V2.angle, '#f2f2f2') +
    vessel(V3.cx, V3.cy, V3.len, V3.wid, V3.angle, '#f2f2f2') +
    label('SAR [RISAT-1A / Sentinel-1] C-Band VV/VH | BACKSCATTER dB', '#38bdf8') +
    `<text x="${V3.cx + 70}" y="${V3.cy + 4}" fill="#38bdf8" font-family="sans-serif" font-size="11" font-weight="bold">SAR WATER DETECT (CLOUD PIERCED)</text>`,
);

// ---------------------------------------------------------------------------
// Scenario E: fused quay plus new staging yard (boxes s5_fused_quay / s5_expanded_staging)
// ---------------------------------------------------------------------------

export const COMPOUND_OPTICAL = toUri(
  rect(0, 0, W, H, '#8b8674') +
    // harbour to the west and south
    `<path d="M0 0 L100 0 Q 110 200 90 330 Q 300 350 380 320 L600 330 L600 400 L0 400 Z" fill="url(#water)"/>` +
    // baseline fused built-up harbour quay
    rect(X(20), Y(15), X(38), Y(33), '#9a9686') +
    blocks(X(20) + 4, Y(15) + 4, X(38) - 8, Y(33) - 8, 9, 5, ['#a8a496', '#76736a', '#8a4d3b', '#b9b5a5']) +
    // newly paved eastern staging yard
    rect(X(68), Y(45), X(20.5), Y(27), '#d4d4cc') +
    blocks(X(69), Y(47), X(18.5), Y(23), 6, 4, CONTAINER_COLORS) +
    `<path d="M${X(58)} ${Y(40)} L${X(68)} ${Y(55)}" stroke="#4c4c48" stroke-width="5"/>` +
    label('OPTICAL [Cartosat-2S] 0.65m GSD | BANDS: RGB-NIR'),
  WATER_GRADIENT,
);

export const COMPOUND_SAR = toUri(
  rect(0, 0, W, H, '#2a2a2a') +
    rect(0, 0, W, H, '#444444', 'opacity="0.25"') +
    `<path d="M0 0 L100 0 Q 110 200 90 330 Q 300 350 380 320 L600 330 L600 400 L0 400 Z" fill="#050505"/>` +
    rect(X(20), Y(15), X(38), Y(33), '#8a8a8a', 'opacity="0.8"') +
    blocks(X(20) + 4, Y(15) + 4, X(38) - 8, Y(33) - 8, 9, 5, ['#e2e2e2', '#d6d6d6', '#f0f0f0']) +
    rect(X(68), Y(45), X(20.5), Y(27), '#6a6a6a', 'opacity="0.7"') +
    label('SAR [RISAT-1A] C-Band Dual-Pol | BACKSCATTER dB', '#38bdf8'),
);
