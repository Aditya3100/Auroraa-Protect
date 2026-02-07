# image_extractor.py

import cv2
import numpy as np
import pywt

from .image_config import (
    DWT_WAVE,
    DCT_POS_A,
    DCT_POS_B,
    SIGNAL_LENGTH,
    REPEAT,
    TARGET
)

from .image_crypto import shuffled_blocks


def detect_watermark_signal(
    image_bytes: bytes,
    owner_id: str,
    asset_id: str,
    epoch: str
) -> np.ndarray | None:

    # --------------------------------
    # Decode image
    # --------------------------------
    img = cv2.imdecode(
        np.frombuffer(image_bytes, np.uint8),
        cv2.IMREAD_COLOR
    )

    if img is None:
        return None

    # --------------------------------
    # Resize normalization (CRITICAL)
    # --------------------------------
    img = cv2.resize(
        img,
        (TARGET, TARGET),
        interpolation=cv2.INTER_AREA
    )

    # --------------------------------
    # Convert to Y channel
    # --------------------------------
    y = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2YCrCb
    )[:, :, 0].astype(np.float32)

    h, w = y.shape
    y = y[:h - h % 2, :w - w % 2]

    # --------------------------------
    # DWT
    # --------------------------------
    LL, (LH, HL, HH) = pywt.dwt2(y, DWT_WAVE)

    # --------------------------------
    # Multi-band extraction
    # --------------------------------
    bands = [LL, LH, HL]

    deltas = []

    # 3 bands × signal × repeat
    max_len = SIGNAL_LENGTH * REPEAT * 3

    for band in bands:

        blocks = shuffled_blocks(
            band.shape[0],
            band.shape[1],
            owner_id,
            asset_id,
            epoch
        )

        for idx, (i, j) in enumerate(blocks):

            if idx >= max_len:
                break

            block = band[i:i+8, j:j+8]

            if block.shape != (8, 8):
                continue

            dct = cv2.dct(block)

            delta = dct[DCT_POS_A] - dct[DCT_POS_B]

            deltas.append(delta)

    if not deltas:
        return None

    # Debug (remove later)
    print(
        "DELTAS:",
        round(np.mean(deltas), 4),
        round(np.std(deltas), 4)
    )

    return np.array(deltas, dtype=np.float32)
