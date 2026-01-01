import io
import numpy as np
from PIL import Image


def extract_image_watermark(image_bytes: bytes) -> str | None:
    """
    Extracts 32 ASCII characters (256 bits) from
    the LSB of the RED channel.
    """

    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception:
        return None

    if img.mode != "RGB":
        img = img.convert("RGB")

    pixels = np.array(img, dtype=np.uint8)

    bits = []
    needed_bits = 32 * 8  # 256 bits

    for i in range(pixels.shape[0]):
        for j in range(pixels.shape[1]):
            bits.append(str(pixels[i, j, 0] & 1))
            if len(bits) >= needed_bits:
                break
        if len(bits) >= needed_bits:
            break

    if len(bits) < needed_bits:
        return None

    chars = []
    for i in range(0, needed_bits, 8):
        byte = bits[i:i + 8]
        chars.append(chr(int("".join(byte), 2)))

    extracted = "".join(chars)

    # ✅ Minimal sanity check: printable ASCII
    if not all(32 <= ord(c) <= 126 for c in extracted):
        return None

    return extracted
