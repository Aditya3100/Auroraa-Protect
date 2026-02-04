import hashlib
import numpy as np
from sqlalchemy.orm import Session

from app.models.models import Watermark
from app.services.watermark.image.image_extractor import extract_bits_robust
from .image_config import (
    HASH_BITS,
    MAX_CANDIDATES,
    confidence_to_status,
    interpret_verification_result,
)
from .image_crypto import generate_bits
import uuid

# =========================================================
# Helper
# =========================================================
def similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(a == b))


# =========================================================
# SELF VERIFIER (OWNER-BOUND + SECURE)
# =========================================================

def verify_self_watermark(
    image_bytes: bytes,
    owner_id: str,
):

    extracted = extract_bits_robust(image_bytes, HASH_BITS)

    if extracted is None:
        return {
            "verified": False,
            "confidence": 0.0,
            "status": "not_verified",
            "reason": "extraction_failed",
        }

    # -------------------------
    # Decode asset_id (first 128 bits = UUID)
    # -------------------------
    asset_bits = extracted[:128]

    asset_bytes = np.packbits(asset_bits).tobytes()

    try:
        asset_id = str(uuid.UUID(bytes=asset_bytes))
    except Exception:
        return {
            "verified": False,
            "confidence": 0.0,
            "status": "not_verified",
            "reason": "invalid_asset_id",
        }

    # -------------------------
    # Recompute expected bits
    # -------------------------
    expected = generate_bits(owner_id, asset_id)

    score = similarity(extracted, expected)

    # -------------------------
    # Verify
    # -------------------------
    if score < 0.90:
        return {
            "verified": False,
            "confidence": round(score, 3),
            "status": "not_verified",
            "reason": "owner_mismatch",
        }

    return {
        "verified": True,
        "confidence": round(score, 3),
        "status": confidence_to_status(score),
        "asset_id": asset_id,
    }


# =========================================================
# 1️⃣ DB-SCAN VERIFIER (PLATFORM ATTRIBUTION)
# =========================================================
# def verify_image_owner_robust(image_bytes: bytes, db: Session) -> dict:
#     candidates = db.query(Watermark).filter(
#         Watermark.status == "active"
#     ).limit(MAX_CANDIDATES).all()

#     best = None
#     best_score = 0.0
#     second_best = 0.0

#     for wm in candidates:
#         expected_bits = generate_bits(wm.id)

#         extracted = extract_bits_robust(
#             image_bytes=image_bytes,
#             bit_length=len(expected_bits)
#         )
#         if extracted is None:
#             continue

#         score = similarity(extracted, expected_bits)

#         if score > best_score:
#             second_best = best_score
#             best_score = score
#             best = wm
#         elif score > second_best:
#             second_best = score

#     if best and best_score >= 0.7:
#         if second_best >= best_score - 0.03:
#             return {
#                 "verified": False,
#                 "confidence": round(best_score, 3),
#                 "status": "not_verified",
#                 "reason": "ambiguous_match",
#             }

#         return {
#             "verified": True,
#             "confidence": round(best_score, 3),
#             "status": confidence_to_status(best_score),
#             "watermark_id": best.id,
#             "owner_id": best.owner_id,
#         }

#     return {
#         "verified": False,
#         "confidence": round(best_score, 3),
#         "status": "not_verified",
#         "reason": "no_confident_match",
#     }