import os
import hmac
import hashlib
import numpy as np
import uuid

from app.services.watermark.dct_dwt.watermark_config import HASH_BITS


# Load secret from .env
SECRET = os.environ.get("AURORAA_WATERMARK_SECRET")

if not SECRET:
    raise RuntimeError("AURORAA_WATERMARK_SECRET is not set")

SECRET = SECRET.encode()

def generate_bits(owner_id: str, asset_id: str) -> np.ndarray:
    """
    Generate watermark bits with embedded UUID asset_id.
    """

    # Convert UUID string → 16 bytes
    asset_uuid = uuid.UUID(asset_id)
    asset_bytes = asset_uuid.bytes  # 16 bytes = 128 bits

    asset_bits = np.unpackbits(
        np.frombuffer(asset_bytes, dtype=np.uint8)
    )

    # HMAC part
    msg = f"AURORAA|{owner_id}|{asset_id}".encode()

    digest = hmac.new(
        SECRET, msg, hashlib.sha256
    ).digest()

    hmac_bits = np.unpackbits(
        np.frombuffer(digest, dtype=np.uint8)
    )

    # Combine
    final = np.concatenate([asset_bits, hmac_bits])

    return final[:HASH_BITS]
