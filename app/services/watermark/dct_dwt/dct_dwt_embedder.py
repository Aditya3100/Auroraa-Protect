import cv2
import numpy as np
import pywt
import hashlib


# =========================================================
# BIT GENERATION (FROM OWNERS ID)
# =========================================================
def generate_bits(owner_id: str, length: int = 32):
    digest = hashlib.sha256(owner_id.encode()).digest()
    return np.unpackbits(np.frombuffer(digest, dtype=np.uint8))[:length]


# =========================================================
# ROBUST DWT + DCT WATERMARK EMBEDDER
# =========================================================
def embed_robust_watermark(
    image_bytes: bytes,
    owner_id: str,
    strength: float = 8.0,
    repeat: int = 20
) -> bytes:

    # Decode image
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image")

    bits = generate_bits(owner_id)

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
