import { describe, expect, it } from 'vitest';
import { DEMO_SCENARIOS } from './mockScenarios';
import parity from './demoParity.json';

// demoParity.json is the live backend's output for each demo, pinned by
// tests/test_demo_parity.py. The offline fallback must say the same thing.
describe('demo scenarios match the live backend', () => {
  it('covers exactly the scenarios in the snapshot', () => {
    expect(DEMO_SCENARIOS.map((s) => s.id).sort()).toEqual(Object.keys(parity).sort());
  });

  it.each(DEMO_SCENARIOS.map((s) => [s.id, s] as const))(
    '%s reproduces the backend outcome',
    (id, scenario) => {
      const live = parity[id as keyof typeof parity];
      const { mockResponse: mock } = scenario;

      expect(scenario.query).toBe(live.query);
      expect(scenario.images.map((i) => i.metadata.name)).toEqual(live.files);
      expect(scenario.expectedTaskType).toBe(live.taskType);
      expect(mock.confidence.tier).toBe(live.tier);
      expect(mock.confidence.rationale).toBe(live.rationale);
      expect(mock.rejected).toBe(live.rejected);
      expect(mock.answerText).toBe(live.answerText);
      expect(mock.evidence.boxes).toEqual(live.boxes);
      expect(mock.evidence.regionTags ?? null).toEqual(live.regionTags);
      expect(mock.rejectionReason).toBe(live.rejectionReason);
      const details = mock.rejectionDetails;
      expect(
        details
          ? {
              reasonCode: details.reasonCode,
              humanReadableReason: details.humanReadableReason,
              suggestedAction: details.suggestedAction,
              detectedContext: details.detectedContext,
              requiredContext: details.requiredContext,
            }
          : null,
      ).toEqual(live.rejectionDetails);
    },
  );
});

describe('demo scenario traces', () => {
  it.each(DEMO_SCENARIOS.map((s) => [s.id, s] as const))(
    '%s trace agrees with its own response',
    (_id, scenario) => {
      const { executionTrace, confidence, rejected } = scenario.mockResponse;
      expect(executionTrace.selectedTaskType).toBe(scenario.expectedTaskType);
      expect(executionTrace.confidenceTier).toBe(confidence.tier);
      expect(executionTrace.steps.map((s) => s.stepIndex)).toEqual(
        executionTrace.steps.map((_, i) => i + 1),
      );
      expect(executionTrace.steps.at(-1)?.status).toBe(rejected ? 'rejected' : 'completed');
    },
  );

  it('uses the same CamelCase component names as the live backend', () => {
    for (const scenario of DEMO_SCENARIOS) {
      for (const step of scenario.mockResponse.executionTrace.steps) {
        expect(step.component).toMatch(/^[A-Z][A-Za-z]+$/);
      }
    }
  });
});
