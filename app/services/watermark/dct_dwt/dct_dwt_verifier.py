import zlib
import numpy as np
import hashlib

from .watermark_config import *
from .dct_dwt_extractor import extract_bits

def verify_robust_watermark(image_bytes: bytes, owner_id: str) -> dict:
    print("[VERIFY] received bytes:", len(image_bytes))
    print("[VERIFY] sha256:", hashlib.sha256(image_bytes).hexdigest())

    recovered_bits, _ = extract_bits(image_bytes, owner_id)

    decoded = ecc_decode(recovered_bits)
    if decoded is None:
        print("[WM] ECC decode failed")
        return {"verified": False, "confidence": 0.0, "status": "not_verified"}

    crc_ok = zlib.crc32(decoded[:-4]).to_bytes(4, "big") == decoded[-4:]

    expected_bits = ecc_encode(generate_payload_bits(owner_id))
    n = min(len(recovered_bits), len(expected_bits))

    confidence = float(np.mean(
        recovered_bits[:n] == expected_bits[:n]
    ))

    print("[WM] CRC OK:", crc_ok)
    print("[WM] Confidence:", confidence)

    status = (
        "verified" if crc_ok and confidence >= 0.75
        else "likely" if confidence >= 0.6
        else "not_verified"
    )

    return {
        "verified": crc_ok and confidence >= 0.75,
        "confidence": round(confidence, 3),
        "status": status
    }
