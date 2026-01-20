import cv2
import numpy as np
import pywt
from .watermark_config import *

# =========================================================
# OPTIONAL: GLOBAL BLOCK SHUFFLE (RECOMMENDED)
# =========================================================
def _shuffled_blocks(h, w):
    blocks = [
        (i, j)
        for i in range(0, h - 8, 8)
        for j in range(0, w - 8, 8)
    ]
    rng = np.random.default_rng(1337420)  # platform-wide constant
    rng.shuffle(blocks)
    return blocks

# =========================================================
# BIT EXTRACTOR
# =========================================================
def extract_bits_robust(
    image_bytes: bytes,
    bit_length: int
) -> np.ndarray | None:
    """
    Extract watermark bits using DWT + DCT + majority voting.
    Designed for DB-scan attribution.
    """

    img = cv2.imdecode(
        np.frombuffer(image_bytes, np.uint8),
        cv2.IMREAD_COLOR
    )
    if img is None:
        return None

    # Convert to Y channel
    y = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)[:, :, 0].astype(np.float32)

    h, w = y.shape
    y = y[:h - h % 2, :w - w % 2]

    # DWT
    LL, _ = pywt.dwt2(y, DWT_WAVE)

    # Choose ONE of these:
    # blocks = _fixed_blocks(*LL.shape)
    blocks = _shuffled_blocks(*LL.shape)

    votes = [[] for _ in range(bit_length)]
    bit_idx = rep = 0

    # DCT extraction
    for (i, j) in blocks:
        if bit_idx >= bit_length:
            break

        block = LL[i:i+8, j:j+8]
        dct = cv2.dct(block)

        bit = 1 if dct[DCT_POS_A] > dct[DCT_POS_B] else 0
        votes[bit_idx].append(bit)

        rep += 1
        if rep >= REPEAT:
            rep = 0
            bit_idx += 1

    if bit_idx < bit_length:
        # Image too small / damaged
        return None

    # Majority vote per bit
    return np.array(
        [1 if np.mean(v) > 0.5 else 0 for v in votes],
        dtype=np.uint8
    )
