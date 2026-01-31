import cv2
import numpy as np
import pywt

from .watermark_config import (
    DWT_WAVE,
    DCT_POS_A,
    DCT_POS_B,
    REPEAT,
)
from .dct_dwt_embedder import _shuffled_blocks


def correlate_watermark_signal(
    image_bytes: bytes,
    expected_bits: np.ndarray,
) -> float:
    """
    Measures statistical correlation between image and expected watermark signal.
    Compatible with fixed global block shuffle embedder.

    Returns score in roughly [-1, 1].
    """

    img = cv2.imdecode(
        np.frombuffer(image_bytes, np.uint8),
        cv2.IMREAD_COLOR
    )
    if img is None:
        return 0.0

    # Y channel
    y = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)[:, :, 0].astype(np.float32)
    h, w = y.shape
    y = y[:h - h % 2, :w - w % 2]

    # DWT
    LL, _ = pywt.dwt2(y, DWT_WAVE)

    # IMPORTANT: same block order as embedder
    blocks = _shuffled_blocks(*LL.shape)

    signal = []
    expected = []

    bit_idx = 0
    rep = 0

    for (i, j) in blocks:
        if bit_idx >= len(expected_bits):
            break

        block = LL[i:i+8, j:j+8]
        dct = cv2.dct(block)

        # Embedded bias
        delta = dct[DCT_POS_A] - dct[DCT_POS_B]
        signal.append(delta)

        expected.append(1 if expected_bits[bit_idx] else -1)

        rep += 1
        if rep >= REPEAT:
            rep = 0
            bit_idx += 1

    if len(signal) < len(expected_bits) * REPEAT * 0.6:
        return 0.0

    signal = np.array(signal, dtype=np.float32)
    expected = np.array(expected, dtype=np.float32)

    # Normalize signal
    signal = (signal - signal.mean()) / (signal.std() + 1e-6)

    # Correlation score
    return float(np.mean(signal * expected))
