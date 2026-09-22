"""B4 / M9: optical-vs-SAR from pixel statistics, for files whose tags and name do not say (ML_PLAN phase 0).

Deliberately not a neural network: a logistic regression over a handful of dtype-independent statistics, fitted
in `.venv-ml` by `ml/b4_modality.py` and exported to `modality_model.json` beside this file (coefficients plus the
feature standardisation), so the backend needs numpy only. `features` is shared with the fitting script, so the
features it was fitted on and the features it is served are one function.

It is consulted only when `metadata_service` cannot decide (no SAR platform tag, no filename hint) and answers
None when its probability is below `config.MODALITY_MIN_PROBABILITY`; the caller then keeps its old default. It
was fitted on Sentinel-1/2 (BigEarthNet) in several renderings, so Cartosat/RISAT textures are outside what it has
seen; the held-out scores are in the JSON's `evaluation` block.
"""
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

MODEL_PATH = Path(__file__).with_name("modality_model.json")
MAX_SIDE = 256  # statistics come from a decimated read; this keeps a call well under 100 ms
FEATURE_NAMES = (
    "bands_1", "bands_2", "bands_3", "bands_4plus", "is_float", "negative_share", "replicated_bands",
    "lag1_autocorrelation", "high_frequency_share", "local_cv", "skewness", "band_correlation",
)


def _normalise(band: np.ndarray) -> np.ndarray:
    """A band clipped to its 1st-99th percentiles and scaled to [0, 1], so the dtype and units stop mattering."""
    lo, hi = np.percentile(band, [1, 99])
    if hi - lo < 1e-12:
        return np.zeros_like(band, dtype=np.float64)
    return np.clip((band.astype(np.float64) - lo) / (hi - lo), 0.0, 1.0)


def _box3(x: np.ndarray) -> np.ndarray:
    """3x3 mean with edge padding."""
    p = np.pad(x, 1, mode="edge")
    h, w = x.shape
    return sum(p[i:i + h, j:j + w] for i in range(3) for j in range(3)) / 9.0


def features(image: np.ndarray) -> np.ndarray:
    """(bands, h, w) array of any dtype -> the FEATURE_NAMES vector. Uses at most the first 4 bands."""
    image = np.asarray(image)
    if image.ndim == 2:
        image = image[None]
    count = image.shape[0]
    step = max(1, int(np.ceil(max(image.shape[1:]) / MAX_SIDE)))
    data = image[:4, ::step, ::step]
    is_float = float(np.issubdtype(data.dtype, np.floating))
    values = data.astype(np.float64)
    values = np.where(np.isfinite(values), values, np.nan)
    fill = np.nanmedian(values) if np.isfinite(np.nanmedian(values)) else 0.0
    values = np.nan_to_num(values, nan=fill)
    negative = float((values < 0).mean())
    replicated = float(count >= 2 and all(np.array_equal(values[0], values[b]) for b in range(1, values.shape[0])))

    lag1, high, cv, skew = [], [], [], []
    normed = [_normalise(b) for b in values]
    for x in normed:
        a, b = x[:, :-1].ravel(), x[:, 1:].ravel()
        lag1.append(float(np.corrcoef(a, b)[0, 1]) if a.std() > 0 and b.std() > 0 else 1.0)
        smooth = _box3(x)
        std = x.std()
        high.append(float(np.abs(x - smooth).mean() / std) if std > 0 else 0.0)
        local_sd = np.sqrt(np.maximum(_box3(x * x) - smooth * smooth, 0.0))
        cv.append(float(np.median(local_sd / (smooth + 0.05))))
        skew.append(float(((x - x.mean()) ** 3).mean() / std ** 3) if std > 0 else 0.0)
    # A flat band has no correlation to report; treating it as perfectly correlated keeps a blank image from
    # looking like a two-sensor composite, and avoids a divide-by-zero inside corrcoef.
    usable = [x.ravel() for x in normed if x.std() > 0]
    if len(usable) >= 2 and not replicated:
        pairs = [(i, j) for i in range(len(usable)) for j in range(i + 1, len(usable))]
        band_corr = float(np.mean([np.corrcoef(usable[i], usable[j])[0, 1] for i, j in pairs]))
    else:
        band_corr = 1.0
    return np.array([
        float(count == 1), float(count == 2), float(count == 3), float(count >= 4), is_float, negative, replicated,
        float(np.mean(lag1)), float(np.mean(high)), float(np.mean(cv)), float(np.mean(skew)), band_corr,
    ])


@lru_cache(maxsize=1)
def _model() -> Optional[dict]:
    if not MODEL_PATH.is_file():
        return None
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    if tuple(model["feature_names"]) != FEATURE_NAMES:
        raise ValueError(f"{MODEL_PATH.name} was fitted on different features; refit with ml/b4_modality.py")
    return model


def sar_probability(image: np.ndarray) -> Optional[float]:
    """P(SAR) for the image, or None when no fitted model is on disk."""
    model = _model()
    if model is None:
        return None
    z = (features(image) - np.array(model["mean"])) / np.array(model["scale"])
    logit = float(z @ np.array(model["coef"]) + model["intercept"])
    return 1.0 / (1.0 + np.exp(-logit))


def predict(image: np.ndarray, min_probability: float) -> Tuple[Optional[str], Optional[float]]:
    """('sar' | 'optical', probability of that answer), or (None, probability) when it is below
    `min_probability`, or (None, None) without a model."""
    p_sar = sar_probability(image)
    if p_sar is None:
        return None, None
    label, p = ("sar", p_sar) if p_sar >= 0.5 else ("optical", 1.0 - p_sar)
    return (label if p >= min_probability else None), p
