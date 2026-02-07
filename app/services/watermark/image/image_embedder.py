# image_embedder.py

import cv2
import numpy as np
import pywt

from .image_config import *
from .image_crypto import generate_signal, shuffled_blocks


def embed_watermark(
    image_bytes: bytes,
    owner_id: str,
    asset_id: str,
    epoch: str
) -> bytes:

    # Decode image
    img = cv2.imdecode(
        np.frombuffer(image_bytes, np.uint8),
        cv2.IMREAD_COLOR
    )

    if img is None:
        raise ValueError("Invalid image")

    # Generate watermark signal
    signal = generate_signal(owner_id, asset_id, epoch)

    # Convert to Y channel
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    y = ycrcb[:, :, 0].astype(np.float32)

    h, w = y.shape
    y = y[:h - h % 2, :w - w % 2]

    # DWT
    LL, (LH, HL, HH) = pywt.dwt2(y, DWT_WAVE)

    # ✅ Keyed block shuffle
    blocks = shuffled_blocks(
        LL.shape[0],
        LL.shape[1],
        owner_id,
        asset_id,
        epoch
    )

    required = len(signal) * REPEAT

    if required > len(blocks):
        raise ValueError("Image too small for watermark")

    bit = 0
    rep = 0

    # Embed signal
    for (i, j) in blocks:

        if bit >= len(signal):
            break

        block = LL[i:i+8, j:j+8]
        dct = cv2.dct(block)

        s = signal[bit]

        dct[DCT_POS_A] += STRENGTH * s
        dct[DCT_POS_B] -= STRENGTH * s

        LL[i:i+8, j:j+8] = cv2.idct(dct)

        rep += 1

        if rep >= REPEAT:
            rep = 0
            bit += 1

    # Inverse DWT
    y_marked = pywt.idwt2((LL, (LH, HL, HH)), DWT_WAVE)

    h2 = min(y_marked.shape[0], ycrcb.shape[0])
    w2 = min(y_marked.shape[1], ycrcb.shape[1])

    ycrcb[:h2, :w2, 0] = np.clip(
        y_marked[:h2, :w2],
        0,
        255
    )

    out = cv2.cvtColor(
        ycrcb.astype(np.uint8),
        cv2.COLOR_YCrCb2BGR
    )

    # Encode JPEG
    ok, enc = cv2.imencode(
        ".jpg",
        out,
        [cv2.IMWRITE_JPEG_QUALITY, 90]
    )
    # ok, enc = cv2.imencode(".png", out)

    if not ok:
        raise RuntimeError("encoding failed")
    
    print("SIGNAL:", np.mean(signal), np.std(signal))

    return enc.tobytes()
