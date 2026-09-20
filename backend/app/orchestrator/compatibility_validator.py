from typing import List, Union
from backend.app.config import (
    CLOUD_MASK_WARN_PERCENT,
    MAX_NODATA_PERCENT,
    MIN_FOOTPRINT_OVERLAP_PERCENT,
)
from backend.app.schemas.image_metadata import ImageMetadata
from backend.app.schemas.task_spec import TaskSpec, TaskType
from backend.app.schemas.validation import (
    RejectionReasonCode,
    ValidationPass,
    ValidationRejection,
)


class CompatibilityValidator:
    """Evaluates GeoGraphRAG physical precondition rules against query & remote sensing rasters."""

    def validate(
        self, task_spec: TaskSpec, images: List[ImageMetadata]
    ) -> Union[ValidationPass, ValidationRejection]:
        # 1. Ambiguous query check
        if task_spec.status == "ambiguous":
            return ValidationRejection(
                reason_code=RejectionReasonCode.AMBIGUOUS_INTENT,
                human_readable_reason="The query intent is ambiguous or insufficiently specified for remote sensing analysis.",
                missing_requirement="Target object, spatial scope, or specific remote sensing question.",
                suggested_action=task_spec.clarifying_question or "Please formulate a specific question such as 'Count the storage tanks' or 'Identify newly built roads'.",
                detected_context={"query": task_spec.question_text or ""},
                required_context={"expected_task": "Unambiguous task specification"},
            )

        # 2. Image count check
        if len(images) < task_spec.required_image_count:
            return ValidationRejection(
                reason_code=RejectionReasonCode.INSUFFICIENT_IMAGE_COUNT,
                human_readable_reason=(
                    f"Task '{task_spec.task_type.value}' strictly requires {task_spec.required_image_count} "
                    f"input images, but only {len(images)} was uploaded."
                ),
                missing_requirement=f"Requires {task_spec.required_image_count} input rasters (e.g. bitemporal baseline T1 & T2 pair).",
                suggested_action="Upload a secondary image representing the comparative temporal acquisition or complementary sensor modality.",
                detected_context={"image_count": str(len(images))},
                required_context={"required_image_count": str(task_spec.required_image_count)},
            )

        # 3. Format check
        supported_formats = ["geotiff", "tiff", "png", "jpeg"]
        for img in images:
            fmt = (img.format or "").lower()
            if fmt not in supported_formats:
                return ValidationRejection(
                    reason_code=RejectionReasonCode.UNSUPPORTED_FORMAT,
                    human_readable_reason=f"Raster format '{img.format}' is not supported by SatQuery AI.",
                    missing_requirement="Valid remote sensing image format: GeoTIFF, TIFF, PNG, or JPEG.",
                    suggested_action="Convert raster to standard GeoTIFF or PNG format prior to analysis.",
                    detected_context={"file_format": str(img.format), "filename": img.name},
                    required_context={"supported_formats": "geotiff, tiff, png, jpeg"},
                )

        # Extract normalized modalities
        modalities = [
            img.detected_modality.value if hasattr(img.detected_modality, "value") else str(img.detected_modality)
            for img in images
        ]

        # 4. Modality mismatch check
        # Case A: Bitemporal change detection requires homogeneous sensor physics
        if task_spec.requires_temporal_pairing and task_spec.task_type in [
            TaskType.CHANGE_VQA,
            TaskType.CHANGE_DESCRIPTION,
            TaskType.CHANGE_AND_GROUNDING,
        ]:
            if len(images) >= 2 and ("sar" in modalities and "optical" in modalities):
                return ValidationRejection(
                    reason_code=RejectionReasonCode.MODALITY_MISMATCH,
                    human_readable_reason=(
                        "Cross-sensor modality conflict: Bitemporal change detection requires matching sensor "
                        "physics (Optical-Optical or SAR-SAR). An Optical-SAR pair cannot be validated for physical change."
                    ),
                    missing_requirement="Homogeneous sensor modality pair for differential radiometric analysis.",
                    suggested_action="For Optical-SAR pairs, run a multimodal 'Fusion' query instead (e.g. 'Detect ships under clouds'). For change detection, provide two Optical or two SAR images.",
                    detected_context={"image_1_modality": modalities[0], "image_2_modality": modalities[1]},
                    required_context={"allowed_pairs": "optical+optical, sar+sar"},
                )

        # 5. Temporal ordering check (if metadata provides timestamps)
        if task_spec.requires_temporal_pairing and len(images) >= 2:
            t1 = images[0].acquisition_timestamp
            t2 = images[1].acquisition_timestamp
            if t1 and t2 and t1 > t2:
                return ValidationRejection(
                    reason_code=RejectionReasonCode.TEMPORAL_ORDERING_INVALID,
                    human_readable_reason=(
                        f"Temporal ordering violation: Slot 1 acquisition timestamp ({t1}) is after "
                        f"Slot 2 acquisition timestamp ({t2})."
                    ),
                    missing_requirement="Chronological ordering where Slot 1 is baseline (T1) and Slot 2 is current (T2).",
                    suggested_action="Swap the order of the uploaded images so that earlier image is in Slot 1.",
                    detected_context={"slot_1_time": str(t1), "slot_2_time": str(t2)},
                    required_context={"chronological": "slot_1_time <= slot_2_time"},
                )

        # 6. Spatial compatibility / Footprint overlap check
        if len(images) >= 2:
            # Check footprint overlap if present in metadata or dimensions
            # Look for explicit metadata overlap percent or footprint mismatch
            overlap_pct = getattr(images[0], "footprint_overlap_percent", None)
            if overlap_pct is not None and overlap_pct < MIN_FOOTPRINT_OVERLAP_PERCENT:
                return ValidationRejection(
                    reason_code=RejectionReasonCode.INSUFFICIENT_FOOTPRINT_OVERLAP,
                    human_readable_reason=(
                        f"Insufficient geographic footprint overlap: Images share only {overlap_pct:.1f}% "
                        f"spatial intersection (minimum required: {MIN_FOOTPRINT_OVERLAP_PERCENT:.0f}%)."
                    ),
                    missing_requirement=f"At least {MIN_FOOTPRINT_OVERLAP_PERCENT:.0f}% geographic footprint overlap between comparative rasters.",
                    suggested_action="Upload imagery covering the same geographic scene or coordinates.",
                    detected_context={"footprint_overlap": f"{overlap_pct:.1f}%"},
                    required_context={"min_required_overlap": f"{MIN_FOOTPRINT_OVERLAP_PERCENT:.0f}%"},
                )

        # 7. Coordinate Reference System (CRS) compatibility check
        if len(images) >= 2:
            crs_1 = images[0].crs
            crs_2 = images[1].crs
            # If both have CRS specified but they are completely incompatible / unresolvable
            if crs_1 and crs_2 and crs_1 != crs_2:
                # If neither is standard UTM / WGS84 or explicitly flagged unresolvable
                if "unresolvable" in crs_1.lower() or "unresolvable" in crs_2.lower():
                    return ValidationRejection(
                        reason_code=RejectionReasonCode.CRS_MISMATCH_UNRESOLVABLE,
                        human_readable_reason=(
                            f"Incompatible Coordinate Reference Systems: Image 1 is '{crs_1}' and Image 2 is '{crs_2}'. "
                            "On-the-fly reprojection could not establish geometric congruence."
                        ),
                        missing_requirement="Transformable or identical Coordinate Reference System.",
                        suggested_action="Reproject both rasters to EPSG:4326 (WGS84) or the appropriate local UTM zone before analysis.",
                        detected_context={"image_1_crs": crs_1, "image_2_crs": crs_2},
                        required_context={"compatible_crs": "Uniform or transformable CRS"},
                    )

        # Passed all preconditions
        warnings = []
        for img in images:
            if img.nodata_percent > MAX_NODATA_PERCENT:
                warnings.append(f"Image {img.name} contains {img.nodata_percent:.1f}% NoData pixels.")
            if (img.cloud_mask_percent or 0.0) > CLOUD_MASK_WARN_PERCENT:
                warnings.append(f"Image {img.name} has {img.cloud_mask_percent:.1f}% cloud obscuration.")

        return ValidationPass(
            task_spec=task_spec,
            normalized_inputs=images,
            warnings=warnings,
        )
