import hashlib
import numpy as np
from sqlalchemy.orm import Session

from app.models.models import Watermark
from app.services.watermark.dct_dwt.dct_dwt_extractor import extract_bits_robust
from .watermark_config import (
    HASH_BITS,
    MAX_CANDIDATES,
    confidence_to_status,
    interpret_verification_result,
)
from app.services.watermark.dct_dwt.correlation import correlate_watermark_signal

# =========================================================
# BIT GENERATION (PUBLIC, FIXED-LENGTH)
# =========================================================
def generate_bits(watermark_id: str) -> np.ndarray:
    digest = hashlib.sha256(watermark_id.encode()).digest()
    return np.unpackbits(
        np.frombuffer(digest, dtype=np.uint8)
    )[:HASH_BITS]


def similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(a == b))


# =========================================================
# 1️⃣ DB-SCAN VERIFIER (PLATFORM ATTRIBUTION)
# =========================================================
def verify_image_owner_robust(image_bytes: bytes, db: Session) -> dict:
    candidates = db.query(Watermark).filter(
        Watermark.status == "active"
    ).limit(MAX_CANDIDATES).all()

    best = None
    best_score = 0.0
    second_best = 0.0

    for wm in candidates:
        expected_bits = generate_bits(wm.id)

        extracted = extract_bits_robust(
            image_bytes=image_bytes,
            bit_length=len(expected_bits)
        )
        if extracted is None:
            continue

        score = similarity(extracted, expected_bits)

        if score > best_score:
            second_best = best_score
            best_score = score
            best = wm
        elif score > second_best:
            second_best = score

    if best and best_score >= 0.7:
        if second_best >= best_score - 0.03:
            return {
                "verified": False,
                "confidence": round(best_score, 3),
                "status": "not_verified",
                "reason": "ambiguous_match",
            }

        return {
            "verified": True,
            "confidence": round(best_score, 3),
            "status": confidence_to_status(best_score),
            "watermark_id": best.id,
            "owner_id": best.owner_id,
        }

    return {
        "verified": False,
        "confidence": round(best_score, 3),
        "status": "not_verified",
        "reason": "no_confident_match",
    }

# =========================================================
# 2️⃣ SELF VERIFIER (CLAIMED WATERMARK_ID)
# =========================================================
def verify_self_watermark(
    image_bytes: bytes,
    watermark_ids: list[str],
) -> dict:
    """
    Checks image against a LIST of watermark_ids (already owned by user).
    Returns RAW result.
    """

    extracted = extract_bits_robust(image_bytes, HASH_BITS)
    if extracted is None:
        return {
            "verified": False,
            "confidence": 0.0,
            "status": "not_verified",
            "reason": "extraction_failed",
        }

    best_id = None
    best_score = 0.0

    for wm_id in watermark_ids:
        expected = generate_bits(wm_id)
        score = similarity(extracted, expected)

        if score > best_score:
            best_score = score
            best_id = wm_id

    if best_id and best_score >= 0.75:
        return {
            "verified": True,
            "confidence": round(best_score, 3),
            "status": confidence_to_status(best_score),
            "watermark_id": best_id,
        }

    return {
        "verified": False,
        "confidence": round(best_score, 3),
        "status": "not_verified",
    }