import type { DemoScenario } from '../types/satquery';
import { MOCK_TRACES } from './mockTraces';

import {
  COMPOUND_OPTICAL,
  COMPOUND_SAR,
  PORT_OPTICAL,
  PORT_SAR,
  SCENE_A_OPTICAL,
  SCENE_B_OPTICAL,
  TEMPORAL_T1,
  TEMPORAL_T2,
} from './mockImagery';

export const DEMO_SCENARIOS: DemoScenario[] = [
  // Scenario A: Single-Image VQA
  {
    id: 'scenario_a',
    name: 'Scenario A: Single Scene Understanding',
    tag: 'Single-Image VQA',
    description: 'Analyze visual land-cover and dominant structures from a single high-resolution optical image.',
    query: 'Describe the land-cover and major objects visible in this image.',
    expectedTaskType: 'single_caption',
    images: [
      {
        slot: 1,
        role: 'Primary Optical Scene',
        metadata: {
          imageId: 'img_opt_001',
          name: 'Cartosat2S_Scene_Bhopal.tif',
          format: 'geotiff',
          crs: 'EPSG:32643 (UTM Zone 43N)',
          bandCount: 3,
          detectedModality: 'optical',
          gsdMeters: 0.65,
          acquisitionTimestamp: '2024-11-04T05:32:10Z',
          nodataPercent: 0.0,
          cloudMaskPercent: 6.07,
          dimensions: { width: 600, height: 400 },
          previewUrl: SCENE_A_OPTICAL,
          rasterUrl: '/demo/Cartosat2S_Scene_Bhopal.tif'
        }
      }
    ],
    mockResponse: {
      sessionId: 'sat-vqa-9014',
      answerText: 'Land-cover analysis of the remote sensing scene classifies four dominant geographic zones: 1) Marine Port Basin (Water, 38.4% surface area), 2) Impervious Built-Up Terminal & Container Berth (41.2% area), 3) Industrial Hydrocarbon Depot containing 3 circular storage reservoirs, and 4) Intermodal Transportation Corridor. Major localized objects include 3 fuel storage tanks and 2 heavy gantry crane installations along the southern quay.',
      evidence: {
        boxes: [
          { id: 's1_tank_01', label: 'Fuel Storage Tank (Floating Roof, Dia: 45m)', xLeft: 18.4, yTop: 24.1, xRight: 34.8, yBottom: 41.5, score: 0.96, isPrimary: true },
          { id: 's1_tank_02', label: 'Fuel Storage Tank (Fixed Cone Roof, Dia: 40m)', xLeft: 42.1, yTop: 28.5, xRight: 58.2, yBottom: 45.9, score: 0.94, isPrimary: true },
          { id: 's1_tank_03', label: 'Secondary Industrial Tank (Cooling / Reserve)', xLeft: 65.0, yTop: 52.0, xRight: 81.2, yBottom: 69.4, score: 0.88, isPrimary: true }
        ],
        masks: [],
        overlayImageUrls: [SCENE_A_OPTICAL]
      },
      confidence: {
        tier: 'High',
        rationale: 'High confidence: Multispectral spectral signature clearly discriminates deep water, concrete terminal, and metallic storage tanks with zero cloud contamination.',
        details: {
          geometryCheck: true,
          crossToolAgreement: true,
          quantityDiscrepancy: false
        }
      },
      executionTrace: {
        sessionId: 'sat-vqa-9014',
        ...MOCK_TRACES.scenario_a,
      },
      reportUrl: '/v1/session/sat-vqa-9014/report?format=pdf',
      rejected: false,
      rejectionReason: null
    }
  },

  // Scenario B: Grounding with Ambiguity
  {
    id: 'scenario_b',
    name: 'Scenario B: Ambiguous Region Grounding',
    tag: 'Grounding Ambiguity',
    description: 'Test text-guided localization of geographic features with multi-candidate ambiguity handling.',
    query: 'Highlight the water body referred to in the query.',
    expectedTaskType: 'single_grounding',
    images: [
      {
        slot: 1,
        role: 'Primary Optical Scene',
        metadata: {
          imageId: 'img_opt_002',
          name: 'Sentinel2_Wetlands_Kerala.png',
          format: 'png',
          crs: 'EPSG:4326',
          bandCount: 3,
          detectedModality: 'optical',
          gsdMeters: 10.0,
          acquisitionTimestamp: '2024-09-18T04:45:00Z',
          nodataPercent: 0.0,
          dimensions: { width: 600, height: 400 },
          previewUrl: SCENE_B_OPTICAL
        }
      }
    ],
    mockResponse: {
      sessionId: 'sat-grd-4421',
      answerText: 'Visual grounding localized 2 candidate water body regions within the scene to account for spatial ambiguity: Candidate 1 (Primary, Score: 0.95) represents the Deepwater Navigational Channel / Basin (x:8.0%, y:12.0% to x:52.0%, y:88.0%). Candidate 2 (Secondary, Score: 0.81) represents an Inland Stormwater Retention Reservoir (x:62.0%, y:15.0% to x:84.0%, y:38.0%). Both regions exhibit characteristic low NIR reflectance indicative of open standing water.',
      evidence: {
        boxes: [
          { id: 's2_water_primary', label: 'Primary Navigational Channel / Harbor Basin (Deep Water)', xLeft: 8.0, yTop: 12.0, xRight: 52.0, yBottom: 88.0, score: 0.95, isPrimary: true },
          { id: 's2_water_secondary', label: 'Secondary Inland Retention Pond (Candidate 2)', xLeft: 62.0, yTop: 15.0, xRight: 84.0, yBottom: 38.0, score: 0.81, isPrimary: false }
        ],
        masks: [],
        overlayImageUrls: [SCENE_B_OPTICAL]
      },
      confidence: {
        tier: 'Medium',
        rationale: 'Moderate confidence: Multiple spatial candidates identified for generic \'water body\' query. Displaying multi-candidate boxes for transparent human review.',
        details: {
          geometryCheck: true,
          crossToolAgreement: true,
          quantityDiscrepancy: false
        }
      },
      executionTrace: {
        sessionId: 'sat-grd-4421',
        ...MOCK_TRACES.scenario_b,
      },
      reportUrl: '/v1/session/sat-grd-4421/report?format=pdf',
      rejected: false,
      rejectionReason: null
    }
  },

  // Scenario C: Bi-Temporal Change Analysis
  {
    id: 'scenario_c',
    name: 'Scenario C: Bi-Temporal Urban Expansion',
    tag: 'Change Detection',
    description: 'Compare co-registered observations across two dates to identify spatial changes and verify quantities.',
    query: 'What changed between these two dates, and where did the change occur?',
    expectedTaskType: 'change_vqa',
    images: [
      {
        slot: 1,
        role: 'Observation T1 (Before)',
        metadata: {
          imageId: 'img_t1_2023',
          name: 'Sentinel2_Bengaluru_2023.tif',
          format: 'geotiff',
          crs: 'EPSG:32643',
          bandCount: 3,
          detectedModality: 'optical',
          gsdMeters: 10.0,
          acquisitionTimestamp: '2023-03-15T05:10:00Z',
          nodataPercent: 0.0,
          previewUrl: TEMPORAL_T1,
          rasterUrl: '/demo/Sentinel2_Bengaluru_2023.tif'
        }
      },
      {
        slot: 2,
        role: 'Observation T2 (After)',
        metadata: {
          imageId: 'img_t2_2025',
          name: 'Sentinel2_Bengaluru_2025.tif',
          format: 'geotiff',
          crs: 'EPSG:32643',
          bandCount: 3,
          detectedModality: 'optical',
          gsdMeters: 10.0,
          acquisitionTimestamp: '2025-01-20T05:12:00Z',
          nodataPercent: 0.0,
          previewUrl: TEMPORAL_T2,
          rasterUrl: '/demo/Sentinel2_Bengaluru_2025.tif'
        }
      }
    ],
    mockResponse: {
      sessionId: 'sat-chg-7782',
      answerText: 'Bitemporal change analysis between baseline (T1) and current (T2) acquisitions identifies a major infrastructure expansion along the eastern waterfront. A net gain of +14,200 sq m (158,400 pixels at 0.3m GSD) of newly paved container staging area was constructed, alongside reinforced concrete foundation piers for a secondary gantry crane rail. No structural demolitions or shoreline erosion were observed.',
      evidence: {
        boxes: [
          { id: 's3_change_pier', label: 'New Pier Foundation & Rail Extension (+6,400 sq m)', xLeft: 35.0, yTop: 22.0, xRight: 62.0, yBottom: 54.0, score: 0.95, isPrimary: true },
          { id: 's3_change_staging', label: 'Newly Paved Logistics Staging Yard (+7,800 sq m)', xLeft: 68.0, yTop: 45.0, xRight: 88.5, yBottom: 72.0, score: 0.92, isPrimary: true }
        ],
        masks: ['/evidence/mask_change_heatmap.png'],
        overlayImageUrls: [TEMPORAL_T2]
      },
      confidence: {
        tier: 'High',
        rationale: 'High confidence: Bitemporal co-registration RMSE < 0.3 pixels; radiometric normalization verified between baseline and current acquisitions.',
        details: {
          geometryCheck: true,
          crossToolAgreement: true,
          quantityDiscrepancy: false
        }
      },
      executionTrace: {
        sessionId: 'sat-chg-7782',
        ...MOCK_TRACES.scenario_c,
      },
      reportUrl: '/v1/session/sat-chg-7782/report?format=pdf',
      rejected: false,
      rejectionReason: null
    }
  },

  // Scenario D: Optical-SAR Cross-Modal Fusion
  {
    id: 'scenario_d',
    name: 'Scenario D: Optical-SAR Complementary Fusion',
    tag: 'Optical-SAR Fusion',
    description: 'Extract complementary structural insights from co-registered Optical + Radar observations.',
    query: 'Use the optical and SAR images together to identify built-up and water-covered regions.',
    expectedTaskType: 'fusion',
    images: [
      {
        slot: 1,
        role: 'Optical Observation',
        metadata: {
          imageId: 'img_opt_s2',
          name: 'Sentinel2_RGBNIR_Assam.tif',
          format: 'geotiff',
          crs: 'EPSG:32646',
          bandCount: 3,
          detectedModality: 'optical',
          gsdMeters: 10.0,
          acquisitionTimestamp: '2024-07-12T04:20:00Z',
          nodataPercent: 0.0,
          cloudMaskPercent: 5.06,
          previewUrl: PORT_OPTICAL,
          rasterUrl: '/demo/Sentinel2_RGBNIR_Assam.tif'
        }
      },
      {
        slot: 2,
        role: 'SAR Observation',
        metadata: {
          imageId: 'img_sar_s1',
          name: 'Sentinel1_SAR_Assam_C_Band.tif',
          format: 'geotiff',
          crs: 'EPSG:32646',
          bandCount: 1,
          detectedModality: 'sar',
          gsdMeters: 10.0,
          acquisitionTimestamp: '2024-07-12T12:45:00Z',
          nodataPercent: 0.0,
          previewUrl: PORT_SAR,
          rasterUrl: '/demo/Sentinel1_SAR_Assam_C_Band.tif'
        }
      }
    ],
    mockResponse: {
      sessionId: 'sat-fus-5519',
      answerText: 'Multimodal Optical-SAR synthesis leverages complementary physical sensor mechanisms to resolve built-up and water boundaries: [Agreement]: Central concrete quay and 2 large cargo berths confirmed concurrently by Optical multispectral reflectance and high SAR double-bounce radar returns. [SAR Penetration]: Eastern water fairway and 1 moored vessel occluded by 42% optical cumulus clouds are unequivocally resolved by SAR C-band microwave backscatter. [Optical Detail]: Color-coded TEU shipping container blocks and painted road lanes resolved exclusively via high-resolution optical bands.',
      evidence: {
        boxes: [
          { id: 's4_vessel_berth4', label: 'Cargo Vessel (Berth 4) — Confirmed Optical & SAR', xLeft: 22.5, yTop: 14.2, xRight: 44.1, yBottom: 32.8, score: 0.97, isPrimary: true },
          { id: 's4_vessel_berth7', label: 'Bulk Carrier (Berth 7) — Confirmed Optical & SAR', xLeft: 51.0, yTop: 38.4, xRight: 73.6, yBottom: 57.2, score: 0.94, isPrimary: true },
          { id: 's4_vessel_cloud_penetrated', label: 'Moored Vessel — Detected under Cloud via SAR C-Band', xLeft: 12.2, yTop: 64.8, xRight: 26.4, yBottom: 78.5, score: 0.91, isPrimary: true }
        ],
        masks: [],
        regionTags: [
          { region: 'Central Commercial Quay & Berths', tag: 'agreement', score: 0.96, description: 'Optical spectral reflectance and SAR double-bounce radar returns mutually verify high-density built-up terminal structures.' },
          { region: 'Cloud-Occluded Eastern Fairway', tag: 'sar_only', score: 0.92, description: 'C-band microwave radar backscatter penetrates 42% cloud deck, confirming water fairway and resolving 1 maritime target.' },
          { region: 'Inland Container Staging Yard', tag: 'optical_only', score: 0.89, description: 'Multispectral color variations distinguish individual container stacks and lane markings undetectable in single-polarization radar.' }
        ],
        overlayImageUrls: [PORT_OPTICAL, PORT_SAR]
      },
      confidence: {
        tier: 'High',
        rationale: 'High confidence: Multi-sensor synergy eliminates cloud obscuration false negatives while maintaining high geometric fidelity.',
        details: {
          geometryCheck: true,
          crossToolAgreement: true,
          quantityDiscrepancy: false
        }
      },
      executionTrace: {
        sessionId: 'sat-fus-5519',
        ...MOCK_TRACES.scenario_d,
      },
      reportUrl: '/v1/session/sat-fus-5519/report?format=pdf',
      rejected: false,
      rejectionReason: null
    }
  },

  // Scenario E: Compound Workflow (Fusion -> Change)
  {
    id: 'scenario_e',
    name: 'Scenario E: Compound Workflow (Fusion → Change)',
    tag: 'Compound Sequential Plan',
    description: 'Execute multi-step sequential reasoning: First identify infrastructure via fusion, then evaluate expansion.',
    query: 'Use the optical and SAR images together to identify built-up areas, then determine whether the built-up area increased.',
    expectedTaskType: 'fusion_then_change',
    images: [
      {
        slot: 1,
        role: 'Optical Scene',
        metadata: {
          imageId: 'img_comp_opt',
          name: 'Cartosat2S_Hyderabad.tif',
          format: 'geotiff',
          crs: 'EPSG:32644',
          bandCount: 3,
          detectedModality: 'optical',
          gsdMeters: 0.65,
          nodataPercent: 0.0,
          previewUrl: COMPOUND_OPTICAL,
          rasterUrl: '/demo/Cartosat2S_Hyderabad.tif'
        }
      },
      {
        slot: 2,
        role: 'SAR Scene',
        metadata: {
          imageId: 'img_comp_sar',
          name: 'RISAT1_Hyderabad_DualPol.tif',
          format: 'geotiff',
          crs: 'EPSG:32644',
          bandCount: 1,
          detectedModality: 'sar',
          gsdMeters: 1.0,
          nodataPercent: 0.0,
          previewUrl: COMPOUND_SAR,
          rasterUrl: '/demo/RISAT1_Hyderabad_DualPol.tif'
        }
      }
    ],
    mockResponse: {
      sessionId: 'sat-cmp-8812',
      answerText: 'Fused Optical-SAR analysis confirms 2 primary features across the region of interest. [Agreement]: 1 feature(s) verified concurrently across both high-resolution Optical RGB and SAR radar backscatter peaks. [SAR Penetration]: 0 feature(s) detected exclusively via SAR C-band microwave penetration beneath optical cloud deck. [Optical Context]: 1 area(s) resolved in multispectral optical bands. Cross-modal synthesis confirms all targets with zero false-alarm artifacts. In addition, temporal analysis demonstrates verified infrastructure growth of +14,200 sq m across the monitored perimeter.',
      evidence: {
        boxes: [
          { id: 's5_fused_quay', label: 'Baseline Fused Built-Up Harbor Quay', xLeft: 20.0, yTop: 15.0, xRight: 58.0, yBottom: 48.0, score: 0.96, isPrimary: true },
          { id: 's5_expanded_staging', label: 'Verified Built-Up Expansion (+14,200 sq m Paved Yard)', xLeft: 68.0, yTop: 45.0, xRight: 88.5, yBottom: 72.0, score: 0.93, isPrimary: true }
        ],
        masks: [],
        regionTags: [
          { region: 'Baseline Commercial Terminal', tag: 'agreement', score: 0.95, description: 'Verified across Optical and SAR baseline acquisitions.' },
          { region: 'Eastern Embankment Extension', tag: 'optical_only', score: 0.91, description: 'Fresh asphalt and concrete foundation radiometric signature resolved via multispectral bands.' }
        ],
        overlayImageUrls: [COMPOUND_OPTICAL]
      },
      confidence: {
        tier: 'High',
        rationale: 'High confidence: Two-stage verification confirms physical built-up expansion with cross-sensor agreement on baseline footprint.',
        details: {
          geometryCheck: true,
          crossToolAgreement: true,
          quantityDiscrepancy: false
        }
      },
      executionTrace: {
        sessionId: 'sat-cmp-8812',
        ...MOCK_TRACES.scenario_e,
      },
      reportUrl: '/v1/session/sat-cmp-8812/report?format=pdf',
      rejected: false,
      rejectionReason: null
    }
  },

  // Scenario F: Input Compatibility Rejection (First-Class Rejection Demo)
  {
    id: 'scenario_f',
    name: 'Scenario F: Physical Input Mismatch (Rejection Demo)',
    tag: 'Input Validation Rejection',
    description: 'Demonstrate first-class precondition checking: Requesting temporal change on an Optical-SAR pair.',
    query: 'What changed between these two dates and did built-up area increase?',
    expectedTaskType: 'change_vqa',
    images: [
      {
        slot: 1,
        role: 'Optical Image',
        metadata: {
          imageId: 'img_rej_opt',
          name: 'Optical_Sensor_Scene.png',
          format: 'png',
          crs: 'EPSG:4326',
          bandCount: 3,
          detectedModality: 'optical',
          gsdMeters: 5.0,
          nodataPercent: 0.0,
          previewUrl: PORT_OPTICAL
        }
      },
      {
        slot: 2,
        role: 'SAR Image',
        metadata: {
          imageId: 'img_rej_sar',
          name: 'SAR_Radar_Scene.png',
          format: 'png',
          crs: 'EPSG:4326',
          bandCount: 1,
          detectedModality: 'sar',
          gsdMeters: 5.0,
          nodataPercent: 0.0,
          previewUrl: PORT_SAR
        }
      }
    ],
    mockResponse: {
      sessionId: 'sat-rej-1029',
      answerText: null,
      evidence: {
        boxes: [],
        masks: [],
        overlayImageUrls: []
      },
      confidence: {
        tier: 'Low',
        rationale: 'Physical precondition check failed: Cross-sensor modality conflict: Bitemporal change detection requires matching sensor physics (Optical-Optical or SAR-SAR). An Optical-SAR pair cannot be validated for physical change.'
      },
      executionTrace: {
        sessionId: 'sat-rej-1029',
        ...MOCK_TRACES.scenario_f,
        rejection: {
          reasonCode: 'modality_mismatch',
          humanReadableReason: 'Cross-sensor modality conflict: Bitemporal change detection requires matching sensor physics (Optical-Optical or SAR-SAR). An Optical-SAR pair cannot be validated for physical change.',
          suggestedAction: 'For Optical-SAR pairs, run a multimodal \'Fusion\' query instead (e.g. \'Detect ships under clouds\'). For change detection, provide two Optical or two SAR images.',
          detectedContext: {
            'image_1_modality': 'optical',
            'image_2_modality': 'sar'
          },
          requiredContext: {
            'allowed_pairs': 'optical+optical, sar+sar'
          }
        },
      },
      reportUrl: null,
      rejected: true,
      rejectionReason: 'Cross-sensor modality conflict: Bitemporal change detection requires matching sensor physics (Optical-Optical or SAR-SAR). An Optical-SAR pair cannot be validated for physical change.',
      rejectionDetails: {
        reasonCode: 'modality_mismatch',
        humanReadableReason: 'Cross-sensor modality conflict: Bitemporal change detection requires matching sensor physics (Optical-Optical or SAR-SAR). An Optical-SAR pair cannot be validated for physical change.',
        suggestedAction: 'For Optical-SAR pairs, run a multimodal \'Fusion\' query instead (e.g. \'Detect ships under clouds\'). For change detection, provide two Optical or two SAR images.',
        detectedContext: {
          'image_1_modality': 'optical',
          'image_2_modality': 'sar'
        },
        requiredContext: {
          'allowed_pairs': 'optical+optical, sar+sar'
        }
      }
    }
  },

  // Scenario G: Reversed Acquisition Order (Rejection Demo)
  {
    id: 'scenario_g',
    name: 'Scenario G: Reversed Acquisition Order (Rejection Demo)',
    tag: 'Input Validation Rejection',
    description: 'Scenario C\'s Bengaluru pair uploaded in the wrong order: the validator reads the acquisition times from the files and refuses a change analysis whose baseline is newer than its current image.',
    query: 'What changed between these two dates, and where did the change occur?',
    expectedTaskType: 'change_vqa',
    images: [
      {
        slot: 1,
        role: 'Slot 1 (Later Observation, 2025)',
        metadata: {
          imageId: 'img_rev_2025',
          name: 'Sentinel2_Bengaluru_2025.tif',
          format: 'geotiff',
          crs: 'EPSG:32643',
          bandCount: 3,
          detectedModality: 'optical',
          gsdMeters: 10.0,
          acquisitionTimestamp: '2025-01-20T05:12:00Z',
          nodataPercent: 0.0,
          previewUrl: TEMPORAL_T2,
          rasterUrl: '/demo/Sentinel2_Bengaluru_2025.tif'
        }
      },
      {
        slot: 2,
        role: 'Slot 2 (Earlier Observation, 2023)',
        metadata: {
          imageId: 'img_rev_2023',
          name: 'Sentinel2_Bengaluru_2023.tif',
          format: 'geotiff',
          crs: 'EPSG:32643',
          bandCount: 3,
          detectedModality: 'optical',
          gsdMeters: 10.0,
          acquisitionTimestamp: '2023-03-15T05:10:00Z',
          nodataPercent: 0.0,
          previewUrl: TEMPORAL_T1,
          rasterUrl: '/demo/Sentinel2_Bengaluru_2023.tif'
        }
      }
    ],
    mockResponse: {
      sessionId: 'sat-rej-2048',
      answerText: null,
      evidence: {
        boxes: [],
        masks: [],
        overlayImageUrls: []
      },
      confidence: {
        tier: 'Low',
        rationale: 'Physical precondition check failed: Temporal ordering violation: Slot 1 acquisition timestamp (2025-01-20T05:12:00) is after Slot 2 acquisition timestamp (2023-03-15T05:10:00).'
      },
      executionTrace: {
        sessionId: 'sat-rej-2048',
        ...MOCK_TRACES.scenario_g,
        rejection: {
          reasonCode: 'temporal_ordering_invalid',
          humanReadableReason: 'Temporal ordering violation: Slot 1 acquisition timestamp (2025-01-20T05:12:00) is after Slot 2 acquisition timestamp (2023-03-15T05:10:00).',
          suggestedAction: 'Swap the order of the uploaded images so that earlier image is in Slot 1.',
          detectedContext: {
            'slot_1_time': '2025-01-20T05:12:00',
            'slot_2_time': '2023-03-15T05:10:00'
          },
          requiredContext: {
            'chronological': 'slot_1_time <= slot_2_time'
          }
        },
      },
      reportUrl: null,
      rejected: true,
      rejectionReason: 'Temporal ordering violation: Slot 1 acquisition timestamp (2025-01-20T05:12:00) is after Slot 2 acquisition timestamp (2023-03-15T05:10:00).',
      rejectionDetails: {
        reasonCode: 'temporal_ordering_invalid',
        humanReadableReason: 'Temporal ordering violation: Slot 1 acquisition timestamp (2025-01-20T05:12:00) is after Slot 2 acquisition timestamp (2023-03-15T05:10:00).',
        suggestedAction: 'Swap the order of the uploaded images so that earlier image is in Slot 1.',
        detectedContext: {
          'slot_1_time': '2025-01-20T05:12:00',
          'slot_2_time': '2023-03-15T05:10:00'
        },
        requiredContext: {
          'chronological': 'slot_1_time <= slot_2_time'
        }
      }
    }
  }
];