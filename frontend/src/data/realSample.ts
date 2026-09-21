import type { ImageMetadata } from '../types/satquery';
import data from './realSamples.json';

/**
 * The real inputs the live-model presets offer: Sentinel-2 patches from BigEarthNet, written by
 * tools/make_real_sample.py. Nothing here is drawn -- unlike the DEMO_SCENARIOS, these images and their
 * reference answers are the dataset's own, and the answer comes from the trained adapter behind
 * ml/serve_vqa.py (the backend returns 503 rather than a demo answer when that server is down).
 */
export interface RealSampleQuestion {
  question: string;
  /** BigEarthNet's reference answer: 'yes' / 'no', or an option letter 'a'-'d'. */
  answer: string;
  type: 'binary' | 'mcq';
  category: string;
}

export interface RealSample {
  /** Short id, '<tile>_<row>_<col>'. */
  id: string;
  patchId: string;
  tile: string;
  platform: string;
  acquired: string;
  country: string;
  season: string;
  widthPx: number;
  heightPx: number;
  gsdMeters: number;
  crs: string;
  rasterFile: string;
  previewFile: string;
  questions: RealSampleQuestion[];
}

export const REAL_SAMPLES = (data as { samples: RealSample[] }).samples;

const REAL_DIR = '/real/';

/** Month and year of acquisition, e.g. 'Nov 2017'. */
export function sampleDate(sample: RealSample): string {
  const [year, month] = sample.acquired.split('-');
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${months[Number(month) - 1]} ${year}`;
}

export function findSample(id: string | null | undefined): RealSample | null {
  return REAL_SAMPLES.find((s) => s.id === id) ?? null;
}

/** The sample a file belongs to, by its file name (the GeoTIFF or its PNG), or null. */
export function findSampleByFile(name: string | null | undefined): RealSample | null {
  return REAL_SAMPLES.find((s) => s.rasterFile === name || s.previewFile === name) ?? null;
}

/** The sample image as the rest of the UI sees it. The GeoTIFF is what the preset uploads, so the
 *  backend reads CRS, GSD and the acquisition time from the file itself. For the PNG (same pixels, no
 *  georeference) those facts are unknown and are left null rather than borrowed from the GeoTIFF.
 *  Either way the on-screen picture is the PNG, because browsers cannot display a TIFF. */
export function realSampleImage(sample: RealSample, fileName: string = sample.rasterFile): ImageMetadata {
  const common = {
    imageId: `img_bigearthnet_${sample.id}`,
    bandCount: 3,
    detectedModality: 'optical' as const,
    nodataPercent: 0,
    cloudMaskPercent: null,
    dimensions: { width: sample.widthPx, height: sample.heightPx },
    previewUrl: REAL_DIR + sample.previewFile,
  };
  if (fileName === sample.previewFile) {
    return { ...common, name: sample.previewFile, format: 'png', crs: null, gsdMeters: null, acquisitionTimestamp: null };
  }
  return {
    ...common,
    name: sample.rasterFile,
    format: 'geotiff',
    crs: sample.crs,
    gsdMeters: sample.gsdMeters,
    acquisitionTimestamp: sample.acquired,
    rasterUrl: REAL_DIR + sample.rasterFile,
  };
}

export interface GradedAnswer {
  reference: string;
  /** The reference as a reader sees it: 'No', or 'b) 30 to 60%'. */
  referenceText: string;
  /** The model's answer read from the start of the answer text; null when it cannot be read. */
  modelAnswer: string | null;
  correct: boolean;
}

function optionText(question: string, letter: string): string | null {
  const match = new RegExp(`(?:^|[\\s,;])${letter}\\)\\s*(.*?)(?=,\\s*[a-d]\\)\\s|$)`).exec(question);
  return match ? match[1].trim() : null;
}

/**
 * Grades an answer against BigEarthNet's reference when the query is one of the sample's questions;
 * null for any other query, which has no reference to compare against.
 */
export function gradeAnswer(sample: RealSample, query: string, answerText: string): GradedAnswer | null {
  const q = sample.questions.find((item) => item.question.trim() === query.trim());
  if (!q) return null;

  const head = answerText.trim().toLowerCase();
  let modelAnswer: string | null = null;
  if (q.type === 'binary') {
    modelAnswer = /^yes\b/.test(head) ? 'yes' : /^no\b/.test(head) ? 'no' : null;
  } else {
    const letter = /^\(?([a-d])\)/.exec(head);
    modelAnswer = letter ? letter[1] : null;
  }

  const text = q.type === 'binary' ? null : optionText(q.question, q.answer);
  const referenceText =
    q.type === 'binary'
      ? q.answer.charAt(0).toUpperCase() + q.answer.slice(1)
      : text
        ? `${q.answer}) ${text}`
        : q.answer;

  return { reference: q.answer, referenceText, modelAnswer, correct: modelAnswer === q.answer };
}
