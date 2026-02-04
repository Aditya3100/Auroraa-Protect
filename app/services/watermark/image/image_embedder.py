import cv2
import numpy as np
import pywt
import hashlib
from .image_config import *
from .image_crypto import generate_bits

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
# EMBEDDER
# =========================================================
def embed_watermark_robust(image_bytes, watermark_id, owner_id) -> bytes:
    """
    Embed a robust DB-scan watermark into an image.
    """

    img = cv2.imdecode(
        np.frombuffer(image_bytes, np.uint8),
        cv2.IMREAD_COLOR
    )
    if img is None:
        raise ValueError("Invalid image")

    bits = generate_bits(owner_id, watermark_id)

    # Convert to Y channel
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    y = ycrcb[:, :, 0].astype(np.float32)

    h, w = y.shape
    y = y[:h - h % 2, :w - w % 2]

    # ---------------- DWT ----------------
    LL, (LH, HL, HH) = pywt.dwt2(y, DWT_WAVE)

    blocks = _shuffled_blocks(*LL.shape)

    blocks_required = len(bits) * REPEAT
    if blocks_required > len(blocks):
        raise ValueError("Image too small for watermark")

    bit_idx = rep = 0

    # ---------------- DCT EMBEDDING ----------------
    for (i, j) in blocks:
        if bit_idx >= len(bits):
            break

        block = LL[i:i+8, j:j+8]
        dct = cv2.dct(block)

        if bits[bit_idx]:
            dct[DCT_POS_A] += STRENGTH
            dct[DCT_POS_B] -= STRENGTH
        else:
            dct[DCT_POS_A] -= STRENGTH
            dct[DCT_POS_B] += STRENGTH

        LL[i:i+8, j:j+8] = cv2.idct(dct)

        rep += 1
        if rep >= REPEAT:
            rep = 0
            bit_idx += 1

    # ---------------- INVERSE DWT ----------------
    y_marked = pywt.idwt2((LL, (LH, HL, HH)), DWT_WAVE)

    h_min = min(y_marked.shape[0], ycrcb.shape[0])
    w_min = min(y_marked.shape[1], ycrcb.shape[1])

    ycrcb[:h_min, :w_min, 0] = np.clip(
        y_marked[:h_min, :w_min],
        0,
        255
    )

    out = cv2.cvtColor(ycrcb.astype(np.uint8), cv2.COLOR_YCrCb2BGR)

    success, encoded = cv2.imencode(
        ".jpg",
        out,
        [cv2.IMWRITE_JPEG_QUALITY, 90]
    )

    if not success:
        raise ValueError("JPEG encoding failed")

    return encoded.tobytes()
