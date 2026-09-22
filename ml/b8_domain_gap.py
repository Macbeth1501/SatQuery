"""B8 / M6, part 1: the domain-gap functions (ML_PLAN phase 0). numpy and Pillow only, so `backend/` can import it.

The adapters trained on Sentinel-2 (optical, 10 m) and Sentinel-1 (SAR, 10 m pixel spacing). The deployment target
is Cartosat-2S (optical, 2 m multispectral) and RISAT (SAR, metre-scale, single look). Two uses, kept apart:

  1. Always on, at inference: `normalise_gsd` and `tiles` bring an input to the 10 m scale the adapters trained
     at, so a 2 m Cartosat scene is not read as a 5x zoom of a Sentinel patch. On a 10 m input both are the
     identity, so the live demo is unchanged. (Appendix A #13, resolved by the approved ML_PLAN: applied to every
     specialist call, at C2's shared entry point, once C2 exists; not wired yet.)
  2. Stress test only (ML_PLAN phase 7): `simulate_scale_gap`, `inject_speckle`, `match_histogram` make held-out
     Sentinel patches look more like the target sensors. Used only in before/after ablation tables, never in
     training data or headline numbers.

Every sensor number is from a published specification, cited beside it in SPECS. A value no specification gave
is None and marked `flagged`; a function that needs it refuses to run rather than guess. What this does NOT do, by
design: it cannot add detail Sentinel never recorded (a simulated 2 m view is a 10 m view enlarged), and it does
not model RISAT's finer resolution, only its speckle.
"""
import numpy as np
from PIL import Image

SPECS = {
    "sentinel2_msi": {
        "gsd_m": 10.0,  # B02, B03, B04, B08; ESA Sentinel-2 MSI user guide, spatial resolution
        "source": "ESA Sentinel-2 MSI user guide (10 m bands B02, B03, B04, B08)",
    },
    "sentinel1_iw_grdh": {
        "pixel_spacing_m": 10.0,
        "resolution_m": (20.4, 22.5),  # range x azimuth, beam IW1
        "enl": 4.4,  # IW1; IW2 and IW3 are 4.3
        "source": "Copernicus SentiWiki, S1 Products, IW GRD High resolution table (read 2026-09-22)",
    },
    "cartosat2s_mx": {
        "gsd_m": 2.0,
        "bands_um": [(0.43, 0.52), (0.52, 0.61), (0.61, 0.69), (0.76, 0.90)],  # blue, green, red, NIR
        "swath_km": 10.0,
        "bit_depth": None,  # flagged: no specification read gives the quantisation
        "reference_histogram": None,  # flagged: needs a real Cartosat-2S scene; none is on disk
        "flagged": ["bit_depth", "reference_histogram"],
        "source": "eoPortal, CartoSat-2D (Cartosat-2 series) HRMX sensor table (read 2026-09-22)",
    },
    "cartosat2s_pan": {
        "gsd_m": 0.65,
        "band_um": (0.50, 0.85),
        "source": "eoPortal, CartoSat-2D PAN sensor table (read 2026-09-22)",
    },
    "risat1_frs1": {
        "resolution_m": (3.0, 2.0),  # azimuth x range
        "enl": 1.0,  # single look: "other modes provide single-look data" (only CRS offers 2 range looks)
        "centre_frequency_ghz": 5.35,
        "source": "eoPortal, RISAT-1 imaging modes (read 2026-09-22)",
    },
}
TRAINING_GSD_M = SPECS["sentinel2_msi"]["gsd_m"]
TRAINING_TILE_PX = 120  # a BigEarthNet patch: 1.2 km at 10 m


class MissingSpecification(ValueError):
    """A function needs a sensor value that no cited specification provides."""


def _resize(band, size, shrinking):
    """One 2-D float band to (height, width) `size`; BOX averages when shrinking, bicubic when enlarging."""
    img = Image.fromarray(np.ascontiguousarray(band, dtype=np.float32))  # float32 -> Pillow mode "F"
    return np.asarray(img.resize((size[1], size[0]), Image.BOX if shrinking else Image.BICUBIC), dtype=np.float32)


def resample(image, factor):
    """(bands, h, w) scaled by `factor` in each spatial axis (0.2 = five times smaller)."""
    image = np.asarray(image)
    h, w = image.shape[-2:]
    size = (max(1, round(h * factor)), max(1, round(w * factor)))
    return np.stack([_resize(b, size, factor < 1) for b in image])


def normalise_gsd(image, gsd_m, target_gsd_m=TRAINING_GSD_M):
    """Resamples (bands, h, w) from `gsd_m` to `target_gsd_m` metres per pixel. Identity when they match, so a
    Sentinel input comes back unchanged (same object). A finer input is area-averaged, never sharpened."""
    if gsd_m is None or gsd_m <= 0:
        raise ValueError(f"gsd_m must be a positive number of metres, got {gsd_m!r}")
    if abs(gsd_m - target_gsd_m) < 1e-6:
        return image
    return resample(image, gsd_m / target_gsd_m)


def tiles(image, tile_px=TRAINING_TILE_PX):
    """Non-overlapping (bands, tile_px, tile_px) tiles with their (row, col) offsets, covering the whole image; the
    last row and column are shifted inward to stay full size. An image smaller than a tile is one tile, as is."""
    h, w = image.shape[-2:]
    if h <= tile_px and w <= tile_px:
        return [((0, 0), image)]

    def starts(n):
        if n <= tile_px:
            return [0]
        s = list(range(0, n - tile_px + 1, tile_px))
        return s if s[-1] == n - tile_px else s + [n - tile_px]

    return [((r, c), image[..., r:r + min(tile_px, h), c:c + min(tile_px, w)]) for r in starts(h) for c in starts(w)]


def simulate_scale_gap(image, source_gsd_m=TRAINING_GSD_M, target_gsd_m=SPECS["cartosat2s_mx"]["gsd_m"]):
    """Stress test: what the model sees when a target-sensor tile of the same pixel size is NOT normalised. The
    central (source/target)-th of the patch (24 of 120 px for 10 m -> 2 m, i.e. 240 m) is enlarged back to full
    size. Field of view and object scale match the target sensor; detail does not (it is enlarged 10 m data)."""
    image = np.asarray(image)
    h, w = image.shape[-2:]
    keep = target_gsd_m / source_gsd_m
    ch, cw = max(1, round(h * keep)), max(1, round(w * keep))
    top, left = (h - ch) // 2, (w - cw) // 2
    crop = image[..., top:top + ch, left:left + cw]
    return np.stack([_resize(b, (h, w), False) for b in crop])


def added_looks(source_enl, target_enl):
    """ENL of the unit-mean gamma speckle that, multiplied onto an image with `source_enl`, leaves `target_enl`.
    Independent unit-mean speckles multiply their (1 + 1/L) factors; None when the target is not noisier."""
    if target_enl >= source_enl:
        return None
    inverse = (1.0 + 1.0 / target_enl) / (1.0 + 1.0 / source_enl) - 1.0
    return 1.0 / inverse


def inject_speckle(sar_db, rng, source_enl=SPECS["sentinel1_iw_grdh"]["enl"], target_enl=SPECS["risat1_frs1"]["enl"]):
    """Stress test: multiplicative gamma speckle that takes Sentinel-1 GRDH (ENL 4.4) to single-look RISAT
    statistics (ENL 1). Input and output are backscatter in dB, as BigEarthNet S1 stores it; NaN stays NaN. When
    the target is no noisier than the source, the input is returned unchanged: speckle cannot be removed here."""
    looks = added_looks(source_enl, target_enl)
    sar_db = np.asarray(sar_db, dtype=np.float32)
    if looks is None:
        return sar_db
    linear = np.power(10.0, sar_db / 10.0)
    noise = rng.gamma(shape=looks, scale=1.0 / looks, size=linear.shape).astype(np.float32)
    return (10.0 * np.log10(np.maximum(linear * noise, 1e-12))).astype(np.float32)


def match_histogram(image, reference=None):
    """Stress test: maps each band's values onto the reference band's distribution by quantile. `reference` must be
    a real target-sensor image (bands, h, w) with the same band order; there is no default, because no published
    specification gives Cartosat-2S's radiometric distribution (SPECS flags it)."""
    if reference is None:
        raise MissingSpecification(
            "match_histogram needs a real Cartosat-2S reference image: SPECS['cartosat2s_mx']['reference_histogram'] "
            "is unset because no cited specification provides one")
    image, reference = np.asarray(image), np.asarray(reference)
    if image.shape[0] != reference.shape[0]:
        raise ValueError(f"band count differs: {image.shape[0]} vs reference {reference.shape[0]}")
    out = np.empty(image.shape, dtype=np.float32)
    for b in range(image.shape[0]):
        src = image[b].ravel()
        ranks = np.argsort(np.argsort(src, kind="stable"), kind="stable")
        quantiles = (ranks + 0.5) / src.size
        ref_sorted = np.sort(reference[b].ravel())
        ref_q = (np.arange(ref_sorted.size) + 0.5) / ref_sorted.size
        out[b] = np.interp(quantiles, ref_q, ref_sorted).reshape(image.shape[1:])
    return out
