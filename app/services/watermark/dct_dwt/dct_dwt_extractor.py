import cv2
import numpy as np
import pywt

from .watermark_config import *

# ---------------------------------------------------------
def _shuffled_blocks(h, w, seed):
    blocks = [(i, j) for i in range(0, h - 8, 8)
                      for j in range(0, w - 8, 8)]
    rng = np.random.default_rng(seed)
    rng.shuffle(blocks)
    return blocks

# ---------------------------------------------------------
def extract_bits(image_bytes: bytes, owner_id: str) -> tuple[np.ndarray, float]:
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image")

    # Convert to Y channel
    y = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)[:, :, 0].astype(np.float32)

    # -----------------------------------------------------
    # 🔴 CRITICAL FIX: force even dimensions before DWT
    # -----------------------------------------------------
    h, w = y.shape
    h -= h % 2
    w -= w % 2
    y = y[:h, :w]

    # -----------------------------------------------------
    # DWT
    # -----------------------------------------------------
    LL, _ = pywt.dwt2(y, DWT_WAVE)

    # Payload size (must match embedder)
    payload_len_bits = (2 + 1 + 16 + 4) * 8
    total_bits = payload_len_bits + RS_PARITY * 8

    blocks = _shuffled_blocks(*LL.shape, seeded_rng(owner_id))

    votes = [[] for _ in range(total_bits)]
    idx = rep = 0

    # -----------------------------------------------------
    # Extract bits
    # -----------------------------------------------------
    for (i, j) in blocks:
        if idx >= total_bits:
            break

        dct = cv2.dct(LL[i:i+8, j:j+8])
        bit = 1 if dct[DCT_POS_A] > dct[DCT_POS_B] else 0
        votes[idx].append(bit)

        rep += 1
        if rep >= REPEAT:
            rep = 0
            idx += 1

    recovered = np.array(
        [1 if np.mean(v) > 0.5 else 0 for v in votes],
        dtype=np.uint8
    )

    return recovered, float(np.mean(recovered))
