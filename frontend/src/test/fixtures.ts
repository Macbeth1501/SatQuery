/**
 * Response fixtures shaped exactly as the backend serialises them.
 *
 * These deliberately use `null` where the API sends null — notably
 * `evidence.regionTags` on any non-fusion task and `confidence.details` on a
 * rejection. A fixture that used `undefined` instead would let optional-parameter
 * defaults paper over the very mismatch these tests exist to catch.
 */
import type { AnalyzeResponse, ExecutionTrace, RejectionInfo } from '../types/satquery';

export const successTrace: ExecutionTrace = {
  sessionId: 'sq-test0001',
  selectedTaskType: 'single_vqa',
  steps: [
    {
      stepIndex: 1,
      component: 'QueryInterpreter',
      adapterIdOrVersion: 'intent_classifier_v1.0',
      parametersUsed: { query: 'how many fuel storage tanks are visible?' },
      wallClockMs: 42,
      outputSummary: 'Parsed natural language query',
      status: 'completed',
    },
    {
      stepIndex: 2,
      component: 'GroundingSpecialist',
      adapterIdOrVersion: 'grounding_adapter_v1.0',
      parametersUsed: {},
      wallClockMs: 51,
      outputSummary: 'Localised 3 target features',
      status: 'completed',
    },
  ],
  confidenceTier: 'High',
  confidenceRationale: 'All verification checks passed.',
  rejection: null,
};

export const modalityMismatch: RejectionInfo = {
  reasonCode: 'modality_mismatch',
  humanReadableReason:
    'Cross-sensor modality conflict: Bitemporal change detection requires matching sensor physics.',
  suggestedAction: 'For Optical-SAR pairs, run a multimodal Fusion query instead.',
  detectedContext: { image_1_modality: 'optical', image_2_modality: 'sar' },
  requiredContext: { allowed_pairs: 'optical+optical, sar+sar' },
};

/** A single-image analysis: the backend sends regionTags: null here. */
export const successResponse: AnalyzeResponse = {
  sessionId: 'sq-test0001',
  answerText: 'Three fuel storage tanks are visible along the southern quay.',
  evidence: {
    boxes: [
      { id: 'b1', label: 'Fuel Storage Tank A', xLeft: 18.4, yTop: 24.1, xRight: 34.8, yBottom: 41.5, score: 0.96, isPrimary: true },
      { id: 'b2', label: 'Fuel Storage Tank B', xLeft: 42.1, yTop: 28.5, xRight: 58.2, yBottom: 45.9, score: 0.72, isPrimary: false },
      { id: 'b3', label: 'Secondary Tank', xLeft: 65.0, yTop: 52.0, xRight: 81.2, yBottom: 69.4, score: 0.41, isPrimary: false },
    ],
    masks: [],
    regionTags: null,
    overlayImageUrls: ['/storage/sessions/sq-test0001/evidence/evidence_boxes_overlay.png'],
  },
  confidence: {
    tier: 'High',
    rationale: 'All verification checks passed.',
    details: { geometryCheck: true, crossToolAgreement: true, quantityDiscrepancy: false },
  },
  executionTrace: successTrace,
  reportUrl: '/v1/session/sq-test0001/report',
  rejected: false,
  rejectionReason: null,
  rejectionDetails: null,
};

/** A rejection: HTTP 200, no answer, no evidence, confidence.details null. */
export const rejectedResponse: AnalyzeResponse = {
  sessionId: 'sq-test0002',
  answerText: null,
  evidence: { boxes: [], masks: [], regionTags: null, overlayImageUrls: [] },
  confidence: {
    tier: 'Low',
    rationale: `Physical precondition check failed: ${modalityMismatch.humanReadableReason}`,
    details: null,
  },
  executionTrace: {
    sessionId: 'sq-test0002',
    selectedTaskType: 'change_vqa',
    steps: [
      {
        stepIndex: 1,
        component: 'QueryInterpreter',
        adapterIdOrVersion: 'intent_classifier_v1.0',
        parametersUsed: {},
        wallClockMs: 42,
        outputSummary: 'Parsed natural language query',
        status: 'completed',
      },
    ],
    confidenceTier: 'Low',
    confidenceRationale: 'Execution halted by physical precondition validator.',
    rejection: modalityMismatch,
  },
  reportUrl: '/v1/session/sq-test0002/report',
  rejected: true,
  rejectionReason: modalityMismatch.humanReadableReason,
  rejectionDetails: modalityMismatch,
};

/** A fusion analysis, the one task type that does populate regionTags. */
export const fusionResponse: AnalyzeResponse = {
  ...successResponse,
  sessionId: 'sq-test0003',
  evidence: {
    ...successResponse.evidence,
    regionTags: [
      { region: 'Primary Target', tag: 'agreement', score: 0.95, description: 'Verified in both sensors.' },
      { region: 'Cloud-Occluded Perimeter', tag: 'sar_only', score: 0.91, description: 'SAR penetrates cloud.' },
      { region: 'Texture Area', tag: 'optical_only', score: 0.88, description: 'Resolved in optical bands.' },
    ],
  },
};
