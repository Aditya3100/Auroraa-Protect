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
def embed_robust_watermark(image_bytes: bytes, owner_id: str) -> bytes:
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image")

    # Convert to Y channel
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    y = ycrcb[:, :, 0].astype(np.float32)

    # -----------------------------------------------------
    # 🔴 CRITICAL FIX: force even dimensions before DWT
    # -----------------------------------------------------
    h, w = y.shape
    h -= h % 2
    w -= w % 2
    y = y[:h, :w]

    # -----------------------------------------------------
    # Payload + ECC
    # -----------------------------------------------------
    payload_bits = generate_payload_bits(owner_id)
    encoded_bits = ecc_encode(payload_bits)

    # -----------------------------------------------------
    # DWT
    # -----------------------------------------------------
    LL, (LH, HL, HH) = pywt.dwt2(y, DWT_WAVE)

    blocks = _shuffled_blocks(*LL.shape, seeded_rng(owner_id))
    required = len(encoded_bits) * REPEAT
    if required > len(blocks):
        raise ValueError("Image too small for watermark")

    # -----------------------------------------------------
    # Embed bits
    # -----------------------------------------------------
    idx = rep = 0
    for (i, j) in blocks:
        if idx >= len(encoded_bits):
            break

        block = LL[i:i+8, j:j+8]
        dct = cv2.dct(block)

        if encoded_bits[idx]:
            dct[DCT_POS_A] += STRENGTH
            dct[DCT_POS_B] -= STRENGTH
        else:
            dct[DCT_POS_A] -= STRENGTH
            dct[DCT_POS_B] += STRENGTH

        LL[i:i+8, j:j+8] = cv2.idct(dct)

        rep += 1
        if rep >= REPEAT:
            rep = 0
            idx += 1

    # -----------------------------------------------------
    # Inverse DWT
    # -----------------------------------------------------
    y_marked = pywt.idwt2((LL, (LH, HL, HH)), DWT_WAVE)
    ycrcb[:y_marked.shape[0], :y_marked.shape[1], 0] = np.clip(y_marked, 0, 255)

    out = cv2.cvtColor(ycrcb.astype(np.uint8), cv2.COLOR_YCrCb2BGR)
    _, encoded = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 95])

    return encoded.tobytes()
