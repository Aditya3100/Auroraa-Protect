# image_verifier.py

import numpy as np

from .image_extractor import detect_watermark_signal
from .image_crypto import generate_signal
from .image_config import (
    confidence_to_status,
    SIGNAL_LENGTH,
    REPEAT,
)


# --------------------------------
# Correlation
# --------------------------------

def correlate(a: np.ndarray, b: np.ndarray) -> float:

    L = min(len(a), len(b))

    if L == 0:
        return 0.0

    a = a[:L]
    b = b[:L]

    num = np.dot(a, b)
    den = np.linalg.norm(a) * np.linalg.norm(b)

    if den == 0:
        return 0.0

    return float(num / den)


# --------------------------------
# Watermark Verifier
# --------------------------------

def verify_watermark(
    image_bytes: bytes,
    owner_id: str,
    asset_id: str,
    epoch: str
) -> dict:

    # -----------------------------
    # Extract raw deltas
    # -----------------------------

    observed = detect_watermark_signal(
        image_bytes,
        owner_id,
        asset_id,
        epoch
    )

    if observed is None:
        return {
            "verified": False,
            "confidence": 0.0,
            "status": "not_verified",
            "reason": "extraction_failed"
        }

    # -----------------------------
    # Decode repetitions (3-band aware)
    # -----------------------------

    band_size = SIGNAL_LENGTH * REPEAT

    decoded_bands = []

    for b in range(3):

        start = b * band_size
        end = start + band_size

        band_obs = observed[start:end]

        if len(band_obs) < band_size:
            continue

        band_decoded = []

        for i in range(0, len(band_obs), REPEAT):

            chunk = band_obs[i:i + REPEAT]

            if len(chunk) < REPEAT:
                break

            band_decoded.append(np.mean(chunk))

        if band_decoded:
            decoded_bands.append(
                np.array(band_decoded, dtype=np.float32)
            )

    # Fuse bands
    if not decoded_bands:
        return {
            "verified": False,
            "confidence": 0.0,
            "status": "not_verified",
            "reason": "decode_failed"
        }

    min_len = min(len(b) for b in decoded_bands)

    decoded = np.mean(
        [b[:min_len] for b in decoded_bands],
        axis=0
    )

    # -----------------------------
    # Generate expected signal
    # -----------------------------

    expected = generate_signal(
        owner_id,
        asset_id,
        epoch
    )

    # -----------------------------
    # Align length
    # -----------------------------

    L = min(len(decoded), len(expected))

    decoded = decoded[:L]
    expected = expected[:L]

    if L == 0:
        return {
            "verified": False,
            "confidence": 0.0,
            "status": "not_verified",
            "reason": "length_mismatch"
        }

    # -----------------------------
    # Normalize
    # -----------------------------

    decoded = (decoded - decoded.mean()) / (decoded.std() + 1e-6)
    expected = (expected - expected.mean()) / (expected.std() + 1e-6)

    # -----------------------------
    # Correlate
    # -----------------------------

    score = correlate(decoded, expected)

    status = confidence_to_status(score)

    # -----------------------------
    # Return
    # -----------------------------

    return {
        "verified": status != "not_verified",
        "confidence": round(float(score), 3),
        "status": status,
        "owner_id": owner_id,
        "asset_id": asset_id,
        "epoch": epoch,
    }
