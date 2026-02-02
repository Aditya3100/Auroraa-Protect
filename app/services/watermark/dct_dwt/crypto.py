import os
import hmac
import hashlib
import numpy as np

from app.services.watermark.dct_dwt.watermark_config import HASH_BITS


# Load secret from .env
SECRET = os.environ.get("AURORAA_WATERMARK_SECRET")

if not SECRET:
    raise RuntimeError("AURORAA_WATERMARK_SECRET is not set")

SECRET = SECRET.encode()


def generate_bits(owner_id: str, asset_id: str) -> np.ndarray:
    """
    Generate cryptographically bound watermark bits.
    """

    # msg = f"{owner_id}:{asset_id}".encode()
    msg = f"AURORAA|{owner_id}|{asset_id}".encode()

    digest = hmac.new(
        SECRET,
        msg,
        hashlib.sha256
    ).digest()

    return np.unpackbits(
        np.frombuffer(digest, dtype=np.uint8)
    )[:HASH_BITS]
