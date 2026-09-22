"""B4: the optical-vs-SAR pixel classifier and the one place it is consulted.

These tests do not depend on the fitted coefficients (`modality_model.json`, produced by `ml/b4_modality.py`
from the B1 pool). They check the feature function's invariants, the confidence threshold, and that the
classifier is asked only when the tags and the file name say nothing — the held-out accuracy is the fitting
script's job, and lives in the JSON and in `docs/PROGRESS_LOG.md`.
"""
import numpy as np
import pytest

from backend.app import config
from backend.app.services import modality_model
from backend.app.services.metadata_service import MetadataService, _modality_hint_from_filename
from tests.test_metadata import write_geotiff

FEATURE = {name: i for i, name in enumerate(modality_model.FEATURE_NAMES)}
service = MetadataService()


def feature(image, name):
    return modality_model.features(image)[FEATURE[name]]


def speckled(rng, shape=(1, 120, 120)):
    """A smooth scene multiplied by single-look-like speckle, as SAR looks."""
    smooth = np.linspace(0.2, 0.8, shape[-1])[None, None, :].repeat(shape[1], axis=1)
    return (smooth * rng.gamma(1.0, 1.0, size=shape)).astype(np.float32)


def smooth_scene(shape=(3, 120, 120)):
    y, x = np.mgrid[0:shape[1], 0:shape[2]]
    base = np.sin(x / 18.0) + np.cos(y / 22.0)
    return np.stack([base * (1 + 0.1 * b) for b in range(shape[0])]).astype(np.float32)


def test_features_report_band_count_dtype_and_sign():
    rng = np.random.default_rng(0)
    f = modality_model.features(rng.integers(0, 4096, (4, 60, 60), dtype=np.uint16))
    assert (f[FEATURE["bands_4plus"]], f[FEATURE["is_float"]], f[FEATURE["negative_share"]]) == (1.0, 0.0, 0.0)
    db = rng.normal(-14.0, 3.0, (2, 60, 60)).astype(np.float32)  # SAR backscatter in dB is negative
    f = modality_model.features(db)
    assert (f[FEATURE["bands_2"]], f[FEATURE["is_float"]], f[FEATURE["negative_share"]]) == (1.0, 1.0, 1.0)


def test_grey_replicated_to_three_bands_is_flagged():
    grey = np.random.default_rng(1).integers(0, 255, (1, 40, 40), dtype=np.uint8)
    assert feature(np.repeat(grey, 3, axis=0), "replicated_bands") == 1.0
    assert feature(grey, "replicated_bands") == 0.0


def test_texture_features_separate_speckle_from_a_smooth_scene():
    rng = np.random.default_rng(2)
    for name in ("local_cv", "high_frequency_share"):
        assert feature(speckled(rng), name) > feature(smooth_scene(), name)
    # neighbouring pixels of a smooth scene agree; speckle's do not
    assert feature(speckled(rng), "lag1_autocorrelation") < feature(smooth_scene(), "lag1_autocorrelation")


def test_features_survive_a_blank_band_and_nans():
    flat = np.zeros((3, 20, 20), dtype=np.float32)
    assert np.all(np.isfinite(modality_model.features(flat)))
    nan_band = np.full((2, 20, 20), np.nan, dtype=np.float32)
    nan_band[0, :10] = -12.0
    assert np.all(np.isfinite(modality_model.features(nan_band)))


def test_features_are_scale_and_offset_independent():
    """The same scene in different units must give the same texture features."""
    scene = smooth_scene()
    a = modality_model.features(scene)
    b = modality_model.features(scene * 1000.0 + 5000.0)
    for name in ("lag1_autocorrelation", "high_frequency_share", "local_cv", "band_correlation"):
        assert a[FEATURE[name]] == pytest.approx(b[FEATURE[name]], abs=0.02), name


def fake_model(monkeypatch, p_sar):
    monkeypatch.setattr(modality_model, "sar_probability", lambda image: p_sar)


def test_prediction_is_withheld_below_the_confidence_threshold(monkeypatch):
    image = smooth_scene()
    fake_model(monkeypatch, 0.97)
    assert modality_model.predict(image, 0.9) == ("sar", 0.97)
    fake_model(monkeypatch, 0.62)
    assert modality_model.predict(image, 0.9) == (None, 0.62)
    fake_model(monkeypatch, 0.02)
    assert modality_model.predict(image, 0.9) == ("optical", 0.98)


def test_no_fitted_model_means_no_answer(monkeypatch):
    monkeypatch.setattr(modality_model, "_model", lambda: None)
    assert modality_model.predict(smooth_scene(), 0.9) == (None, None)


# ---- the one call site ------------------------------------------------------------------------------------

def test_filename_hint_is_none_when_the_name_says_nothing():
    assert _modality_hint_from_filename("scene_042.tif") is None
    assert _modality_hint_from_filename("RISAT1_Hyderabad_DualPol.tif") == "sar"
    assert _modality_hint_from_filename("Sentinel2_RGBNIR_Assam.tif") == "multispectral"


def asked(monkeypatch, answer="sar"):
    """Replaces the classifier; returns the list of images it was asked about."""
    calls = []

    def predict(image, min_probability):
        calls.append(image)
        return answer, 0.99

    monkeypatch.setattr(modality_model, "predict", predict)
    return calls


def test_pixels_decide_only_when_tags_and_name_do_not(tmp_path, monkeypatch):
    calls = asked(monkeypatch)
    unnamed = write_geotiff(tmp_path / "scene_042.tif")
    assert service.inspect_file(unnamed, "scene_042.tif").detected_modality == "sar"
    assert len(calls) == 1

    # a SAR platform tag decides by itself
    tagged = write_geotiff(tmp_path / "scene_043.tif", tags={"PLATFORM": "RISAT-1"})
    assert service.inspect_file(tagged, "scene_043.tif").detected_modality == "sar"
    # a file name that states a modality is believed, and the classifier is not consulted
    named = write_geotiff(tmp_path / "Sentinel2_RGBNIR_Assam.tif")
    assert service.inspect_file(named, "Sentinel2_RGBNIR_Assam.tif").detected_modality == "multispectral"
    assert len(calls) == 1


def test_an_unconfident_classifier_leaves_the_old_default(tmp_path, monkeypatch):
    monkeypatch.setattr(modality_model, "predict", lambda image, min_probability: (None, 0.6))
    path = write_geotiff(tmp_path / "scene_044.tif")
    assert service.inspect_file(path, "scene_044.tif").detected_modality == "optical"


def test_a_broken_classifier_never_breaks_metadata_reading(tmp_path, monkeypatch):
    def explode(image, min_probability):
        raise RuntimeError("model file is corrupt")

    monkeypatch.setattr(modality_model, "predict", explode)
    path = write_geotiff(tmp_path / "scene_045.tif")
    metadata = service.inspect_file(path, "scene_045.tif")
    assert metadata.detected_modality == "optical"
    assert metadata.band_count == 3  # the rest of the metadata is still read


def test_threshold_is_configurable_and_sane():
    assert 0.5 <= config.MODALITY_MIN_PROBABILITY <= 1.0
