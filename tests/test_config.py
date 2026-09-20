"""Configuration loading: defaults, overrides, and fail-fast on bad values."""
import importlib

import pytest

from backend.app import config


@pytest.fixture
def reload_config(monkeypatch, tmp_path):
    """Reloads the config module under a patched environment, then restores it.

    Storage is pointed at a temp directory so importing never creates folders in the
    real backend/storage, and the original module state is restored afterwards so
    other tests keep the redirected storage root from conftest.
    """
    saved = {k: getattr(config, k) for k in dir(config) if k.isupper()}
    monkeypatch.setenv("SATQUERY_STORAGE_DIR", str(tmp_path / "store"))

    def _reload(**env):
        for key, value in env.items():
            monkeypatch.setenv(f"SATQUERY_{key}", value)
        return importlib.reload(config)

    yield _reload

    monkeypatch.undo()
    importlib.reload(config)
    for key, value in saved.items():
        setattr(config, key, value)


def test_defaults_match_the_documented_values(reload_config):
    cfg = reload_config()
    assert cfg.MIN_FOOTPRINT_OVERLAP_PERCENT == 70.0
    assert cfg.MAX_NODATA_PERCENT == 40.0
    assert cfg.CLOUD_MASK_WARN_PERCENT == 40.0
    assert cfg.HIGH_INTENT_CONFIDENCE == 0.85
    assert cfg.PORT == 8000


def test_server_binds_to_loopback_by_default(reload_config):
    """It used to bind 0.0.0.0, exposing the API to the whole network."""
    assert reload_config().HOST == "127.0.0.1"


def test_thresholds_can_be_overridden(reload_config):
    cfg = reload_config(MIN_FOOTPRINT_OVERLAP_PERCENT="55", HIGH_INTENT_CONFIDENCE="0.9")
    assert cfg.MIN_FOOTPRINT_OVERLAP_PERCENT == 55.0
    assert cfg.HIGH_INTENT_CONFIDENCE == 0.9


def test_storage_dir_is_created_where_configured(reload_config, tmp_path):
    cfg = reload_config()
    assert cfg.STORAGE_DIR == tmp_path / "store"
    assert cfg.SESSIONS_DIR.is_dir()


def test_cors_defaults_exclude_the_wildcard(reload_config):
    """A wildcard origin combined with credentials is unsafe."""
    assert "*" not in reload_config().CORS_ORIGINS


def test_cors_origins_parse_from_a_comma_separated_list(reload_config):
    cfg = reload_config(CORS_ORIGINS=" https://a.example , https://b.example,, ")
    assert cfg.CORS_ORIGINS == ["https://a.example", "https://b.example"]


@pytest.mark.parametrize(
    "name, value, fragment",
    [
        ("MIN_FOOTPRINT_OVERLAP_PERCENT", "seventy", "not a number"),
        ("MIN_FOOTPRINT_OVERLAP_PERCENT", "150", "outside the allowed range"),
        ("HIGH_INTENT_CONFIDENCE", "1.5", "outside the allowed range"),
        ("PORT", "eighty", "not an integer"),
        ("PORT", "70000", "outside the allowed range"),
    ],
)
def test_bad_values_fail_at_startup_naming_the_variable(reload_config, name, value, fragment):
    # Reloading redefines ConfigError, so match on its stable ValueError base and name
    # rather than on a class object captured before the reload.
    with pytest.raises(ValueError) as excinfo:
        reload_config(**{name: value})
    assert type(excinfo.value).__name__ == "ConfigError"
    assert f"SATQUERY_{name}" in str(excinfo.value)
    assert fragment in str(excinfo.value)


def test_blank_values_fall_back_to_the_default(reload_config):
    assert reload_config(MAX_NODATA_PERCENT="  ").MAX_NODATA_PERCENT == 40.0


def test_validator_uses_the_configured_thresholds():
    """The thresholds must actually reach the code that enforces them."""
    from backend.app.orchestrator import compatibility_validator, confidence_scorer

    assert compatibility_validator.MIN_FOOTPRINT_OVERLAP_PERCENT == config.MIN_FOOTPRINT_OVERLAP_PERCENT
    assert confidence_scorer.HIGH_INTENT_CONFIDENCE == config.HIGH_INTENT_CONFIDENCE
