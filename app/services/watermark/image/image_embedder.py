# image_embedder.py

import cv2
import numpy as np
import pywt

from .image_config import (
    DWT_WAVE,
    DCT_POS_A,
    DCT_POS_B,
    REPEAT,
    STRENGTH,
    TARGET
)

from .image_crypto import generate_signal, shuffled_blocks


def embed_watermark(
    image_bytes: bytes,
    owner_id: str,
    epoch: str
) -> bytes:

    # --------------------------------
    # Decode image
    # --------------------------------
    img = cv2.imdecode(
        np.frombuffer(image_bytes, np.uint8),
        cv2.IMREAD_COLOR
    )

    if img is None:
        raise ValueError("Invalid image")

    # --------------------------------
    # Resize normalization (CRITICAL)
    # --------------------------------
    img = cv2.resize(
        img,
        (TARGET, TARGET),
        interpolation=cv2.INTER_AREA
    )

    # --------------------------------
    # Generate watermark signal
    # --------------------------------
    signal = generate_signal(owner_id, epoch)

    # --------------------------------
    # Convert to Y channel
    # --------------------------------
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    y = ycrcb[:, :, 0].astype(np.float32)

    h, w = y.shape

    # Make even for DWT
    y = y[:h - h % 2, :w - w % 2]

    # --------------------------------
    # Fixed strength (normalized size)
    # --------------------------------
    strength = STRENGTH

    # --------------------------------
    # DWT
    # --------------------------------
    LL, (LH, HL, HH) = pywt.dwt2(y, DWT_WAVE)

    # --------------------------------
    # Capacity check (3 bands)
    # --------------------------------
    total_blocks = 0

    for band in (LL, LH, HL):

        blocks = shuffled_blocks(
            band.shape[0],
            band.shape[1],
            owner_id,
            epoch
        )

        total_blocks += len(blocks)

    if len(signal) * REPEAT > total_blocks:
        raise ValueError("Image too small for watermark")

    # --------------------------------
    # Multi-band embedding
    # --------------------------------
    bands = [LL, LH, HL]

    bit = 0
    rep = 0

    for band in bands:

        # Reduce power on high-frequency bands
        if band is LL:
            band_strength = strength
        else:
            band_strength = strength * 0.7

        blocks = shuffled_blocks(
            band.shape[0],
            band.shape[1],
            owner_id,
            epoch
        )

        for (i, j) in blocks:

            if bit >= len(signal):
                break

            block = band[i:i+8, j:j+8]

            if block.shape != (8, 8):
                continue

            dct = cv2.dct(block)

            s = signal[bit]

            # Embed watermark
            dct[DCT_POS_A] += band_strength * s
            dct[DCT_POS_B] -= band_strength * s

            band[i:i+8, j:j+8] = cv2.idct(dct)

            rep += 1

            if rep >= REPEAT:
                rep = 0
                bit += 1

        if bit >= len(signal):
            break

    # --------------------------------
    # Inverse DWT
    # --------------------------------
    y_marked = pywt.idwt2((LL, (LH, HL, HH)), DWT_WAVE)

    h2 = min(y_marked.shape[0], ycrcb.shape[0])
    w2 = min(y_marked.shape[1], ycrcb.shape[1])

    ycrcb[:h2, :w2, 0] = np.clip(
        y_marked[:h2, :w2],
        0,
        255
    )

    # --------------------------------
    # Convert back to BGR
    # --------------------------------
    out = cv2.cvtColor(
        ycrcb.astype(np.uint8),
        cv2.COLOR_YCrCb2BGR
    )

    # --------------------------------
    # Encode JPEG
    # --------------------------------
    ok, enc = cv2.imencode(
        ".jpg",
        out,
        [cv2.IMWRITE_JPEG_QUALITY, 92]
    )

    if not ok:
        raise RuntimeError("Encoding failed")

    # Debug (remove later)
    print(
        "SIGNAL:",
        round(np.mean(signal), 4),
        round(np.std(signal), 4)
    )

    return enc.tobytes()
