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
# SynthID Verifier
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
    # Decode repetitions
    # -----------------------------

    decoded = []

    for i in range(0, len(observed), REPEAT):

        chunk = observed[i:i + REPEAT]

        if len(chunk) < REPEAT:
            break

        decoded.append(np.mean(chunk))

    decoded = np.array(decoded, dtype=np.float32)

    if len(decoded) == 0:
        return {
            "verified": False,
            "confidence": 0.0,
            "status": "not_verified",
            "reason": "decode_failed"
        }

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
    # Normalize (zero mean / unit var)
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
