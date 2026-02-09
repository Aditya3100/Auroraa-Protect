# image_crypto.py

import os
import hmac
import hashlib
import numpy as np

from app.services.watermark.image.image_config import SIGNAL_LENGTH

SECRET = os.environ.get("AURORAA_WATERMARK_SECRET")

if not SECRET:
    raise RuntimeError("AURORAA_WATERMARK_SECRET is not set")

SECRET = SECRET.encode()


def generate_signal(owner_id: str, epoch: str) -> np.ndarray:
    """
    Generate style continuous watermark signal.
    """

    # asset_id is IGNORED for owner-level uniqueness
    msg = f"AURORAA|{owner_id}|{epoch}".encode()

    digest = hmac.new(
        SECRET,
        msg,
        hashlib.sha256
    ).digest()

    bits = np.unpackbits(
        np.frombuffer(digest, dtype=np.uint8)
    )[:SIGNAL_LENGTH]

    # Convert {0,1} → {-1,+1}
    signal = np.where(bits == 1, 1.0, -1.0)

    return signal

def generate_shuffle_seed(owner_id, epoch):

    # asset_id is IGNORED
    msg = f"SHUFFLE|{owner_id}|{epoch}".encode()

    digest = hmac.new(
        SECRET,
        msg,
        hashlib.sha256
    ).digest()

    return int.from_bytes(digest[:8], "big")

def shuffled_blocks(h, w, owner_id, epoch):

    blocks = [
        (i, j)
        # for i in range(0, h - 8, 8)
        for i in range(0, h - 7, 8)
        for j in range(0, w - 8, 8)
    ]

    seed = generate_shuffle_seed(
        owner_id,
        epoch
    )

    rng = np.random.default_rng(seed)
    rng.shuffle(blocks)

    return blocks

