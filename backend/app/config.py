"""Application configuration.

Every tunable value is read from an environment variable with a documented default,
so the same code runs unchanged on a laptop, in CI and in a container. Nothing else in
the backend should hard-code a threshold, origin, path or port -- import it from here.

A malformed value fails at startup with a message naming the variable, rather than
surfacing later as a confusing comparison error deep inside the pipeline.
"""
import os
from pathlib import Path
from typing import List, Optional

PREFIX = "SATQUERY_"


class ConfigError(ValueError):
    """An environment variable is set but cannot be used."""


def _raw(name: str) -> Optional[str]:
    value = os.environ.get(PREFIX + name)
    return value.strip() if value is not None and value.strip() != "" else None


def _env_str(name: str, default: str) -> str:
    return _raw(name) or default


def _env_float(name: str, default: float, minimum: float, maximum: float) -> float:
    raw = _raw(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(f"{PREFIX}{name}={raw!r} is not a number.") from exc
    if not (minimum <= value <= maximum):
        raise ConfigError(
            f"{PREFIX}{name}={value} is outside the allowed range {minimum}-{maximum}."
        )
    return value


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = _raw(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{PREFIX}{name}={raw!r} is not an integer.") from exc
    if not (minimum <= value <= maximum):
        raise ConfigError(
            f"{PREFIX}{name}={value} is outside the allowed range {minimum}-{maximum}."
        )
    return value


def _env_list(name: str, default: List[str]) -> List[str]:
    raw = _raw(name)
    if raw is None:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# --- Paths -------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = Path(_env_str("STORAGE_DIR", str(BASE_DIR / "storage"))).expanduser()
SESSIONS_DIR = STORAGE_DIR / "sessions"
# SQLite file holding session records. Uploads, overlays and reports stay on disk in
# SESSIONS_DIR; only the structured records live in the database.
DATABASE_PATH = Path(_env_str("DATABASE_PATH", str(STORAGE_DIR / "satquery.db"))).expanduser()

STORAGE_DIR.mkdir(parents=True, exist_ok=True)
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

# --- Application -------------------------------------------------------------
APP_TITLE = "SatQuery AI API"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Agentic Vision-Language Assistant for Multimodal Remote Sensing (ISRO SIH26167)"

# --- Server ------------------------------------------------------------------
HOST = _env_str("HOST", "127.0.0.1")
PORT = _env_int("PORT", 8000, 1, 65535)

# --- Validation thresholds (SPDD §4.2) ---------------------------------------
# Minimum geographic footprint overlap between the two images of a pair.
MIN_FOOTPRINT_OVERLAP_PERCENT = _env_float("MIN_FOOTPRINT_OVERLAP_PERCENT", 70.0, 0.0, 100.0)
# A NoData share above this attaches a warning; it does not reject.
MAX_NODATA_PERCENT = _env_float("MAX_NODATA_PERCENT", 40.0, 0.0, 100.0)
# A cloud-mask share above this attaches a warning; it does not reject.
CLOUD_MASK_WARN_PERCENT = _env_float("CLOUD_MASK_WARN_PERCENT", 40.0, 0.0, 100.0)

# --- Confidence scoring ------------------------------------------------------
# Average cloud cover above this, with no radar to see through it, forces Low.
OPTICAL_CLOUD_DEGRADED_PERCENT = _env_float("OPTICAL_CLOUD_DEGRADED_PERCENT", 40.0, 0.0, 100.0)
# Interpreter confidence at or above this is required for the baseline High tier.
HIGH_INTENT_CONFIDENCE = _env_float("HIGH_INTENT_CONFIDENCE", 0.85, 0.0, 1.0)

# --- Real model (single-image VQA only) --------------------------------------
# Base URL of the model server started by `ml/serve_vqa.py` (e.g. http://127.0.0.1:8001).
# Unset (the default) keeps the deterministic demo specialists; set, single-image questions
# are answered by the trained adapter and every other task stays on the demo engine.
# Read as `config.VQA_MODEL_URL` at call time, so tests can switch it on and off.
VQA_MODEL_URL = _raw("VQA_MODEL_URL")
VQA_MODEL_TIMEOUT_SECONDS = _env_float("VQA_MODEL_TIMEOUT_SECONDS", 60.0, 1.0, 600.0)
# Which resident adapter the model server answers with (its GET /adapters lists them). run2 is
# the live demo's adapter by owner decision (2026-09-22); run3 is the scored model of record.
VQA_MODEL_ADAPTER = _env_str("VQA_MODEL_ADAPTER", "run2")
# The model's own answer probability at or above this gives Medium; below it, Low. A real
# model answer is never High: run 2 scores ~33% on held-out multiple choice (chance 25%).
MODEL_MEDIUM_PROBABILITY = _env_float("MODEL_MEDIUM_PROBABILITY", 0.75, 0.0, 1.0)

# --- Modality heuristic (B4) -------------------------------------------------
# Probability the pixel classifier must reach before it may name a modality for a file whose
# tags and name say nothing (backend/app/services/modality_model.py). Below it, the old
# default stands, so an uncertain guess never overrides what the file itself says.
MODALITY_MIN_PROBABILITY = _env_float("MODALITY_MIN_PROBABILITY", 0.9, 0.5, 1.0)

# --- CORS --------------------------------------------------------------------
# Comma-separated list. The default is the Vite dev server only: a wildcard combined
# with credentialed requests is unsafe, so it is no longer part of the default.
CORS_ORIGINS = _env_list(
    "CORS_ORIGINS",
    [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
)
