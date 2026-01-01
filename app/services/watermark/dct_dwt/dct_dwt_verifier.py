import hashlib
import numpy as np
from app.services.watermark.dct_dwt.dct_dwt_embedder import generate_bits
from app.services.watermark.dct_dwt.dct_dwt_extractor import extract_confidence


def verify_robust_watermark(
    image_bytes: bytes,
    asset_id: str
) -> dict:

    bits = generate_bits(asset_id)
    confidence = extract_confidence(image_bytes, bits)

    if confidence >= 0.75:
        status = "verified"
    elif confidence >= 0.6:
        status = "most"
    elif confidence >= 0.55:
        status = "likely"    
    else:
        status = "not_verified"

    return {
        "verified": status != "not_verified",
        "confidence": round(confidence, 3),
        "status": status
    }
