# image_extractor.py

import cv2
import numpy as np
import pywt

from .image_config import *
from .image_crypto import shuffled_blocks


def detect_watermark_signal(
    image_bytes: bytes,
    owner_id: str,
    asset_id: str,
    epoch: str
) -> np.ndarray | None:

    # Decode image
    img = cv2.imdecode(
        np.frombuffer(image_bytes, np.uint8),
        cv2.IMREAD_COLOR
    )

    if img is None:
        return None

    # Convert to Y channel
    y = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2YCrCb
    )[:, :, 0].astype(np.float32)

    h, w = y.shape
    y = y[:h - h % 2, :w - w % 2]

    # DWT
    LL, _ = pywt.dwt2(y, DWT_WAVE)

    # ✅ Same keyed shuffle as embedder
    blocks = shuffled_blocks(
        LL.shape[0],
        LL.shape[1],
        owner_id,
        asset_id,
        epoch
    )

    deltas = []

    # Extract signal
    for (i, j) in blocks:

        block = LL[i:i+8, j:j+8]

        if block.shape != (8, 8):
            continue

        dct = cv2.dct(block)

        delta = (
            dct[DCT_POS_A]
            - dct[DCT_POS_B]
        )

        deltas.append(delta)

    if not deltas:
        return None
    
    print("DELTAS:", np.mean(deltas), np.std(deltas))

    return np.array(deltas, dtype=np.float32)
