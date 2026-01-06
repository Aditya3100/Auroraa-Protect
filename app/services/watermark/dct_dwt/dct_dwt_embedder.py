import cv2
import numpy as np
import pywt
import hashlib

import os

AURORAA_SECRET = os.getenv("AURORAA_WATERMARK_SECRET", "auroraa-dev-secret")

# =========================================================
# ECC: Hamming (7,4)
# =========================================================
def hamming_encode(bits: np.ndarray) -> np.ndarray:
    encoded = []

    for i in range(0, len(bits), 4):
        d = bits[i:i+4]
        if len(d) < 4:
            d = np.pad(d, (0, 4 - len(d)))

        d1, d2, d3, d4 = d

        p1 = d1 ^ d2 ^ d4
        p2 = d1 ^ d3 ^ d4
        p3 = d2 ^ d3 ^ d4

        encoded.extend([p1, p2, d1, p3, d2, d3, d4])

    return np.array(encoded, dtype=np.uint8)

# =========================================================
# BIT GENERATION (FROM OWNERS ID)
# =========================================================
# def generate_bits(owner_id: str, length: int = 32):
#     digest = hashlib.sha256(owner_id.encode()).digest()
#     return np.unpackbits(np.frombuffer(digest, dtype=np.uint8))[:length]

def generate_bits(owner_id: str, length: int = 32):
    payload = f"{owner_id}:{AURORAA_SECRET}".encode()
    digest = hashlib.sha256(payload).digest()
    return np.unpackbits(np.frombuffer(digest, dtype=np.uint8))[:length]

# =========================================================
# ROBUST DWT + DCT WATERMARK EMBEDDER
# =========================================================
def embed_robust_watermark(
    image_bytes: bytes,
    owner_id: str,
    strength: float = 6.0,  # STRENGTH = how hard you push each watermark mark
    repeat: int = 20        # REPEAT = how many times you repeat the same bit
) -> bytes:

    # Decode image
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image")

    # bits = generate_bits(owner_id)
    bits = generate_bits(owner_id)
    bits = hamming_encode(bits)


    # Convert to YCrCb
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    y = ycrcb[:, :, 0].astype(np.float32)

    orig_h, orig_w = y.shape  # 🔑 save original shape

    # Ensure even dimensions for DWT
    y_even = y[:orig_h - orig_h % 2, :orig_w - orig_w % 2]

    # ---------------- DWT ----------------
    LL, (LH, HL, HH) = pywt.dwt2(y_even, "haar")

    h, w = LL.shape
    blocks_available = (h // 8) * (w // 8)
    blocks_required = len(bits) * repeat

    if blocks_required > blocks_available:
        raise ValueError("Image too small for robust watermark")

    bit_idx = 0
    rep = 0

    # ---------------- DCT EMBEDDING ----------------
    for i in range(0, h - 8, 8):
        for j in range(0, w - 8, 8):

            if bit_idx >= len(bits):
                break

            block = LL[i:i + 8, j:j + 8]
            dct = cv2.dct(block)

            # Mid-frequency embedding (robust zone)
            if bits[bit_idx]:
                dct[3, 3] += strength
                dct[2, 4] -= strength
            else:
                dct[3, 3] -= strength
                dct[2, 4] += strength

            LL[i:i + 8, j:j + 8] = cv2.idct(dct)

            rep += 1
            if rep >= repeat:
                rep = 0
                bit_idx += 1

        if bit_idx >= len(bits):
            break

    # ---------------- INVERSE DWT ----------------
    # y_marked = pywt.idwt2((LL, (LH, HL, HH)), "haar")

    # # 🔧 CRITICAL FIX: crop back to original Y size
    # y_marked = y_marked[:orig_h, :orig_w]

    # # Replace Y channel safely
    # ycrcb[:orig_h, :orig_w, 0] = np.clip(y_marked, 0, 255)

    # # Convert back to BGR
    # out = cv2.cvtColor(ycrcb.astype(np.uint8), cv2.COLOR_YCrCb2BGR)

    y_marked = pywt.idwt2((LL, (LH, HL, HH)), "haar")

    # 🔒 SAFE SHAPE CLAMP (THIS FIXES YOUR ERROR)
    h_min = min(orig_h, y_marked.shape[0])
    w_min = min(orig_w, y_marked.shape[1])

    ycrcb[:h_min, :w_min, 0] = np.clip(
        y_marked[:h_min, :w_min],
        0,
        255
    )

    # Convert back to BGR
    out = cv2.cvtColor(ycrcb.astype(np.uint8), cv2.COLOR_YCrCb2BGR)


    # ---------------- JPEG ENCODE (SOCIAL SAFE) ----------------
    success, encoded = cv2.imencode(
        ".jpg",
        out,
        [
            cv2.IMWRITE_JPEG_QUALITY, 95,
            cv2.IMWRITE_JPEG_OPTIMIZE, 1
        ]
    )

    if not success:
        raise ValueError("JPEG encoding failed")

    return encoded.tobytes()
