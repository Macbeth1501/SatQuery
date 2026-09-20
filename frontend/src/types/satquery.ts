/**
 * SatQuery AI — Authoritative TypeScript Definitions (SPDD §8)
 * SIH26167: Vision-Language Assistant for Multimodal Remote Sensing
 */

export type TaskType =
  | 'single_vqa'
  | 'single_caption'
  | 'single_grounding'
  | 'change_vqa'
  | 'change_description'
  | 'change_and_grounding'
  | 'fusion'
  | 'fusion_then_change';

export type Modality = 'optical' | 'multispectral' | 'sar';

export type ImageFormat = 'geotiff' | 'tiff' | 'png' | 'jpeg';

export type ConfidenceTier = 'High' | 'Medium' | 'Low';

export type RejectionReasonCode =
  | 'unsupported_format'
  | 'modality_mismatch'
  | 'insufficient_image_count'
  | 'crs_mismatch_unresolvable'
  | 'insufficient_footprint_overlap'
  | 'temporal_ordering_invalid'
  | 'ambiguous_intent';

export interface BoundingBox {
  id?: string;
  label?: string;
  xLeft: number;    // 0-100 normalized percentage
  yTop: number;     // 0-100 normalized percentage
  xRight: number;   // 0-100 normalized percentage
  yBottom: number;  // 0-100 normalized percentage
  theta?: number;   // Oriented box angle in [-90, 90]
  score?: number;   // Confidence score
  isPrimary?: boolean;
}

export interface RegionTag {
  region: string;
  tag: 'agreement' | 'optical_only' | 'sar_only';
  score: number;
  description?: string;
}

export interface ImageMetadata {
  imageId: string;
  name: string;
  format: ImageFormat;
  crs: string | null;
  bandCount: number;
  detectedModality: Modality;
  gsdMeters: number | null;
  footprintPolygon?: string | null;
  acquisitionTimestamp?: string | null;
  nodataPercent: number;
  cloudMaskPercent?: number | null;
  dimensions?: { width: number; height: number };
  previewUrl: string;
  /**
   * Frontend-only, never sent by the API: a georeferenced raster under /demo/ that a demo scenario
   * uploads in place of its rasterized preview, so the backend reads real metadata from it.
   */
  rasterUrl?: string;
}

export interface TaskSpec {
  taskType: TaskType;
  status: 'resolved' | 'ambiguous';
  targetObject: string | null;
  questionText: string | null;
  requiredImageCount: number;
  requiredModalities: Modality[];
  requiresTemporalPairing: boolean;
  requestedParameters?: {
    iouThreshold?: number;
    topK?: number;
  };
  intentConfidence: number;
  clarifyingQuestion: string | null;
}

export interface EvidenceItem {
  sourceSpecialist: string;
  adapterId: string;
  answerText: string | null;
  boxes: BoundingBox[];
  maskRef: string | null;
  regionTags?: RegionTag[];
  deterministicPixelCount: number | null;
  quantityFlag: boolean;
  geometryValid: boolean;
  quantityDiscrepancy: boolean;
}

export interface ExecutionStep {
  stepIndex: number;
  component: string;
  adapterIdOrVersion: string | null;
  parametersUsed: Record<string, unknown>;
  wallClockMs: number;
  outputSummary: string;
  status?: 'completed' | 'running' | 'failed' | 'rejected';
}

export interface RejectionInfo {
  reasonCode: RejectionReasonCode;
  humanReadableReason: string;
  suggestedAction?: string;
  detectedContext?: Record<string, string>;
  requiredContext?: Record<string, string>;
}

export interface ExecutionTrace {
  sessionId: string;
  selectedTaskType: string;
  steps: ExecutionStep[];
  confidenceTier: ConfidenceTier;
  confidenceRationale: string;
  rejection?: RejectionInfo | null;
}

export interface AnalyzeResponse {
  sessionId: string;
  answerText: string | null;
  evidence: {
    boxes: BoundingBox[];
    masks: string[];
    /** null (not undefined) for non-fusion tasks -- the backend omits nothing. */
    regionTags?: RegionTag[] | null;
    overlayImageUrls: string[];
  };
  confidence: {
    tier: ConfidenceTier;
    rationale: string;
    /** null on a rejection response, where no checks were run. */
    details?: {
      geometryCheck: boolean;
      crossToolAgreement: boolean;
      quantityDiscrepancy: boolean;
    } | null;
  };
  executionTrace: ExecutionTrace;
  reportUrl: string | null;
  rejected: boolean;
  rejectionReason: string | null;
  rejectionDetails?: RejectionInfo | null;
  taskSpec?: TaskSpec;
}

export interface DemoScenario {
  id: string;
  name: string;
  tag: string;
  description: string;
  query: string;
  images: Array<{
    slot: 1 | 2;
    role: string;
    metadata: ImageMetadata;
  }>;
  expectedTaskType: TaskType;
  mockResponse: AnalyzeResponse;
}
