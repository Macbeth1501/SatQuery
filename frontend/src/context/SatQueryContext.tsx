import React, { createContext, useContext, useState } from 'react';
import type { ImageMetadata, AnalyzeResponse, DemoScenario } from '../types/satquery';
import { DEMO_SCENARIOS } from '../data/mockScenarios';
import { findSample, realSampleImage, type RealSample } from '../data/realSample';
import { analyzeRaster } from '../services/api';

/** Where the displayed result actually came from. */
export type ResultSource = 'live' | 'demo';

/**
 * Renders an image URL (including the demo scenarios' SVG data URIs) into a real
 * PNG File so the backend receives a decodable raster it can draw overlays on.
 * Returns null if the browser cannot rasterize it, so callers can fall back.
 */
async function rasterizeToPngFile(src: string, filename: string): Promise<File | null> {
  try {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    const loaded = new Promise<void>((resolve, reject) => {
      img.onload = () => resolve();
      img.onerror = () => reject(new Error('demo image failed to load'));
    });
    img.src = src;
    await loaded;

    const canvas = document.createElement('canvas');
    canvas.width = img.naturalWidth || 600;
    canvas.height = img.naturalHeight || 400;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, 'image/png')
    );
    if (!blob) return null;

    const pngName = filename.replace(/\.[^.]+$/, '') + '.png';
    return new File([blob], pngName, { type: 'image/png' });
  } catch {
    return null;
  }
}

/**
 * Fetches a bundled demo raster (a GeoTIFF under /demo/) as a File carrying its real bytes.
 * Returns null when the scenario has no raster asset or it cannot be fetched, so callers fall
 * back to rasterizing the preview.
 */
async function fetchRasterFile(url: string | undefined, filename: string): Promise<File | null> {
  if (!url) return null;
  try {
    const response = await fetch(url);
    if (!response.ok) return null;
    const blob = await response.blob();
    if (blob.size === 0) return null;
    return new File([blob], filename, { type: 'image/tiff' });
  } catch {
    return null;
  }
}

/** A readable reason for a failed analyze call: the backend's own `detail` when it sent one. */
function describeFailure(err: unknown): string {
  const message = err instanceof Error ? err.message : String(err);
  const api = /^API error \((\d+)\): ([\s\S]*)$/.exec(message);
  if (api) {
    let detail = api[2];
    try {
      const body = JSON.parse(api[2]);
      if (typeof body?.detail === 'string') detail = body.detail;
    } catch {
      // not JSON; keep the raw text
    }
    return api[1] === '503'
      ? `The model server is not running. ${detail}`
      : `The backend returned HTTP ${api[1]}: ${detail}`;
  }
  return `The backend could not be reached (${message}). Start it with: uvicorn backend.app.main:app --port 8000`;
}

export interface ProcessingStepInfo {
  index: number;
  label: string;
  component: string;
  description: string;
}

export const PIPELINE_STEPS: ProcessingStepInfo[] = [
  { index: 1, label: 'Query Interpretation', component: 'query_interpreter', description: 'Parsing natural language query into structured TaskSpec & taxonomy' },
  { index: 2, label: 'Compatibility Validation', component: 'compatibility_validator', description: 'Evaluating physical preconditions: modality, CRS, overlap, temporal delta' },
  { index: 3, label: 'Specialist Dispatch', component: 'specialist_router', description: 'Selecting specialist models from registry via deterministic routing table' },
  { index: 4, label: 'Specialist Execution', component: 'specialists / LoRA adapters', description: 'Running remote-sensing vision-language inference with hot-swapped LoRA weights' },
  { index: 5, label: 'Evidence Verification', component: 'verifier_node', description: 'Cross-checking geometric bounds, cross-tool agreement, and deterministic counts' },
  { index: 6, label: 'Confidence Scoring', component: 'confidence_scorer', description: 'Calibrating High/Medium/Low confidence tier and logging rationale' },
  { index: 7, label: 'Trace Emission', component: 'trace_emitter', description: 'Serializing auditable execution trace with step timings and parameters' },
  { index: 8, label: 'Response Composition', component: 'response_composer', description: 'Assembling grounded natural language answer with visual evidence overlays' },
];

interface SatQueryContextType {
  image1: ImageMetadata | null;
  image2: ImageMetadata | null;
  query: string;
  activeScenario: DemoScenario | null;
  isAnalyzing: boolean;
  activeStep: number;
  results: AnalyzeResponse | null;
  resultSource: ResultSource | null;
  activeLayers: {
    boxes: boolean;
    masks: boolean;
    regions: boolean;
  };
  supportedCapabilities: {
    singleVqa: boolean;
    captioning: boolean;
    grounding: boolean;
    changeAnalysis: boolean;
    opticalSarFusion: boolean;
    compoundPipeline: boolean;
  };
  setFile1: (file: File | null) => void;
  setFile2: (file: File | null) => void;
  setImage1: (img: ImageMetadata | null) => void;
  setImage2: (img: ImageMetadata | null) => void;
  setQuery: (q: string) => void;
  loadScenario: (scenarioId: string) => void;
  /** The real BigEarthNet sample loaded as image 1, or null: its answers come from the trained
   *  adapter, and a failed call shows an error instead of falling back to demo data. */
  activeRealSample: RealSample | null;
  /** Loads a real BigEarthNet sample by id, optionally with one of its questions. `file` is the sample
   *  uploaded by hand; its own bytes are then sent instead of fetching the bundled copy. */
  loadRealSample: (sampleId: string, question?: string, file?: File) => void;
  /** Why the last analysis produced no result; set only on the real-sample path. */
  analysisError: string | null;
  startAnalysis: (onComplete?: () => void) => void;
  resetSession: () => void;
  toggleLayer: (layer: 'boxes' | 'masks' | 'regions') => void;
  setResults: (res: AnalyzeResponse | null) => void;
  /** Shows a stored session fetched from the backend (direct URL / reload). */
  openSession: (res: AnalyzeResponse) => void;
}

const SatQueryContext = createContext<SatQueryContextType | undefined>(undefined);

export const SatQueryProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [file1, setFile1] = useState<File | null>(null);
  const [file2, setFile2] = useState<File | null>(null);
  const [image1, setImage1] = useState<ImageMetadata | null>(DEMO_SCENARIOS[0].images[0].metadata);
  const [image2, setImage2] = useState<ImageMetadata | null>(null);
  const [query, setQuery] = useState<string>(DEMO_SCENARIOS[0].query);
  const [activeScenario, setActiveScenario] = useState<DemoScenario | null>(DEMO_SCENARIOS[0]);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [activeStep, setActiveStep] = useState<number>(0);
  const [results, setResults] = useState<AnalyzeResponse | null>(null);
  const [resultSource, setResultSource] = useState<ResultSource | null>(null);
  const [realSampleId, setRealSampleId] = useState<string | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [activeLayers, setActiveLayers] = useState({
    boxes: true,
    masks: true,
    regions: true,
  });

  // Calculate dynamic capability readiness based on loaded imagery
  const imageCount = (image1 ? 1 : 0) + (image2 ? 1 : 0);
  const modalities = [image1?.detectedModality, image2?.detectedModality].filter(Boolean);
  const isOpticalPresent = modalities.includes('optical') || modalities.includes('multispectral');
  const isSarPresent = modalities.includes('sar');
  const isOpticalSarPair = imageCount === 2 && isOpticalPresent && isSarPresent;
  const isSameModalityPair = imageCount === 2 && !isOpticalSarPair;

  const supportedCapabilities = {
    singleVqa: imageCount >= 1,
    captioning: imageCount >= 1,
    grounding: imageCount >= 1 && isOpticalPresent,
    changeAnalysis: isSameModalityPair,
    opticalSarFusion: isOpticalSarPair,
    compoundPipeline: isOpticalSarPair || imageCount >= 2,
  };

  const loadScenario = (scenarioId: string) => {
    const scenario = DEMO_SCENARIOS.find((s) => s.id === scenarioId);
    if (!scenario) return;

    setActiveScenario(scenario);
    setRealSampleId(null);
    setAnalysisError(null);
    setQuery(scenario.query);

    const img1 = scenario.images.find((i) => i.slot === 1)?.metadata || null;
    const img2 = scenario.images.find((i) => i.slot === 2)?.metadata || null;

    setFile1(null);
    setFile2(null);
    setImage1(img1);
    setImage2(img2);
    setResults(null);
    setResultSource(null);
  };

  const loadRealSample = (sampleId: string, question?: string, file?: File) => {
    const sample = findSample(sampleId);
    if (!sample) return;
    setActiveScenario(null);
    setRealSampleId(sample.id);
    setAnalysisError(null);
    setFile1(file ?? null);
    setImage1(realSampleImage(sample, file?.name));
    // A hand upload fills slot 1 only; the preset starts a clean single-image session.
    if (!file) {
      setFile2(null);
      setImage2(null);
    }
    // A hand upload keeps whatever the user already typed; the preset seeds its first question.
    if (question !== undefined || !file) setQuery(question ?? sample.questions[0].question);
    setResults(null);
    setResultSource(null);
  };

  // The sample stays active only while its image is the one loaded; replacing the image
  // (an upload or a scenario) ends it.
  const loadedSample = findSample(realSampleId);
  const activeRealSample =
    loadedSample && (image1?.name === loadedSample.rasterFile || image1?.name === loadedSample.previewFile)
      ? loadedSample
      : null;

  const toggleLayer = (layer: 'boxes' | 'masks' | 'regions') => {
    setActiveLayers((prev) => ({ ...prev, [layer]: !prev[layer] }));
  };

  const resetSession = () => {
    setFile1(null);
    setFile2(null);
    setImage1(null);
    setImage2(null);
    setQuery('');
    setActiveScenario(null);
    setRealSampleId(null);
    setAnalysisError(null);
    setResults(null);
    setResultSource(null);
    setActiveStep(0);
    setIsAnalyzing(false);
  };

  // A reopened session carries no input imagery (the response does not include it), so
  // clear the images rather than leave whatever scenario was loaded beside a stranger's result.
  const openSession = (res: AnalyzeResponse) => {
    setFile1(null);
    setFile2(null);
    setImage1(null);
    setImage2(null);
    setActiveScenario(null);
    setRealSampleId(null);
    setAnalysisError(null);
    setQuery(res.taskSpec?.questionText ?? '');
    setResults(res);
    setResultSource('live');
  };

  const startAnalysis = async (onComplete?: () => void) => {
    setIsAnalyzing(true);
    setActiveStep(1);
    setAnalysisError(null);

    // Animate pipeline progress
    let currentStep = 1;
    const interval = setInterval(() => {
      currentStep++;
      if (currentStep <= 7) {
        setActiveStep(currentStep);
      }
    }, 280);

    let targetResponse: AnalyzeResponse;
    let source: ResultSource = 'live';

    try {
      // A demo scenario has no uploaded file, only a rendered preview. Rasterize it
      // so the backend receives a decodable image rather than placeholder bytes --
      // that is what lets it draw overlays on the imagery the user is looking at.
      const resolveFile = async (
        file: File | null,
        meta: ImageMetadata | null
      ): Promise<File | null> => {
        // An empty slot sends nothing, even if a stale File survived in state.
        if (!meta) return null;
        if (file) return file;
        // Prefer the scenario's georeferenced GeoTIFF: the backend then reads real CRS, GSD,
        // footprint and timestamps from it. The SVG preview stays the on-screen picture.
        const georeferenced = await fetchRasterFile(meta.rasterUrl, meta.name);
        if (georeferenced) return georeferenced;
        const rasterized = await rasterizeToPngFile(meta.previewUrl, meta.name);
        if (rasterized) return rasterized;
        // Preserve the image count so task validation still behaves correctly.
        return new File([new Blob(['satquery_placeholder_bytes'])], meta.name, {
          type: 'image/png',
        });
      };

      const files: File[] = [];
      const resolved1 = await resolveFile(file1, image1);
      if (resolved1) files.push(resolved1);
      const resolved2 = await resolveFile(file2, image2);
      if (resolved2) files.push(resolved2);

      targetResponse = await analyzeRaster(query, files);
    } catch (err) {
      // The real sample exists to show the trained model answering. A canned answer here would
      // look identical to a real one, so show why there is no answer instead.
      if (activeRealSample) {
        clearInterval(interval);
        console.error('Live model call failed:', err);
        setAnalysisError(describeFailure(err));
        setIsAnalyzing(false);
        setActiveStep(0);
        return;
      }
      console.warn('Live backend call unfulfilled, falling back to client-side scenario:', err);
      source = 'demo';
      if (activeScenario) {
        targetResponse = activeScenario.mockResponse;
      } else {
        targetResponse = {
          ...DEMO_SCENARIOS[0].mockResponse,
          sessionId: `sat-usr-${Math.floor(1000 + Math.random() * 9000)}`,
          answerText: `Analyzed ${imageCount} uploaded image(s) for query: "${query}". Visual feature extraction identified key geographic characteristics matching prompt specifications.`,
          evidence: {
            boxes: [
              { id: 'usr_b1', label: 'Identified Target Feature', xLeft: 30, yTop: 30, xRight: 75, yBottom: 70, score: 0.91, isPrimary: true }
            ],
            masks: [],
            overlayImageUrls: [image1?.previewUrl || '']
          }
        };
      }
    }

    // Finish pipeline animation
    clearInterval(interval);
    setActiveStep(targetResponse.rejected ? 2 : 8);
    setTimeout(() => {
      setIsAnalyzing(false);
      setResults(targetResponse);
      setResultSource(source);
      if (onComplete) onComplete();
    }, 300);
  };

  return (
    <SatQueryContext.Provider
      value={{
        setFile1,
        setFile2,
        image1,
        image2,
        query,
        activeScenario,
        isAnalyzing,
        activeStep,
        results,
        resultSource,
        activeLayers,
        supportedCapabilities,
        setImage1,
        setImage2,
        setQuery,
        loadScenario,
        activeRealSample,
        loadRealSample,
        analysisError,
        startAnalysis,
        resetSession,
        toggleLayer,
        setResults,
        openSession,
      }}
    >
      {children}
    </SatQueryContext.Provider>
  );
};

export const useSatQuery = () => {
  const context = useContext(SatQueryContext);
  if (!context) {
    throw new Error('useSatQuery must be used within a SatQueryProvider');
  }
  return context;
};
