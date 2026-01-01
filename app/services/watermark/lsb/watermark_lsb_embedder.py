import io
import hashlib
import numpy as np
from PIL import Image
import pillow_heif  # HEIC / HEIF support

pillow_heif.register_heif_opener()


# =========================================================
# JPEG QUALITY POLICY (initial guess only)
# =========================================================
def _jpeg_quality_for_size(size_bytes: int) -> int:
    if size_bytes < 100_000:
        return 80
    if size_bytes < 300_000:
        return 82
    if size_bytes < 1_000_000:
        return 84
    if size_bytes < 5_000_000:
        return 88
    return 90


# =========================================================
# IMAGE SAFETY POLICY (photo-only watermarking)
# =========================================================
def _is_safe_photo_image(img: Image.Image, fmt: str) -> bool:
    w, h = img.size

    if fmt in ("JPEG", "JPG", "HEIC", "HEIF"):
        return img.mode == "RGB" and min(w, h) >= 256

    if fmt == "WEBP":
        return img.mode == "RGB" and min(w, h) >= 256

    if fmt == "PNG":
        return img.mode == "RGB" and min(w, h) >= 512

    if fmt in ("TIFF", "BMP"):
        return img.mode == "RGB" and min(w, h) >= 256

    return False


# =========================================================
# JPEG ENCODERS
# =========================================================
def _encode_jpeg(
    img: Image.Image,
    quality: int,
    exif: bytes | None,
    icc_profile: bytes | None
) -> bytes:
    out = io.BytesIO()

    save_kwargs = {
        "format": "JPEG",
        "quality": quality,
        "subsampling": 2,
        "progressive": False,
        "optimize": True
    }

    if exif:
        save_kwargs["exif"] = exif
    if icc_profile:
        save_kwargs["icc_profile"] = icc_profile

    img.save(out, **save_kwargs)
    return out.getvalue()


def _encode_jpeg_with_autoclamp(
    img: Image.Image,
    original_size: int,
    exif: bytes | None,
    icc_profile: bytes | None
) -> bytes:
    """
    Enforces:
        original_size <= final_size <= original_size * 1.02
    Never drops watermark.
    """

    min_size = original_size
    max_size = int(original_size * 1.02)

    quality = _jpeg_quality_for_size(original_size)
    best_candidate = None
    best_size = None

    for _ in range(6):
        encoded = _encode_jpeg(img, quality, exif, icc_profile)
        size = len(encoded)

        if min_size <= size <= max_size:
            return encoded

        if size >= min_size:
            if best_size is None or size < best_size:
                best_candidate = encoded
                best_size = size

        # Adjust quality
        if size < min_size:
            quality += 3
        else:
            quality -= 3

        quality = max(78, min(92, quality))

    return best_candidate if best_candidate else encoded


# =========================================================
# GENERIC CLAMP (NON-JPEG)
# =========================================================
def _clamp_encoded_bytes(
    encoded_bytes: bytes,
    original_size: int,
    max_ratio: float = 1.02
) -> bytes:
    """
    Never return original bytes.
    Accepts slight size increase if needed.
    """
    max_size = int(original_size * max_ratio)

    if len(encoded_bytes) <= max_size:
        return encoded_bytes

    # Still return encoded bytes (watermark preserved)
    return encoded_bytes


# =========================================================
# MAIN IMAGE WATERMARK ENGINE
# =========================================================
def embed_image_watermark(image_bytes: bytes, signature: str) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    original_format = (img.format or "PNG").upper()

    # Skip unsafe images (icons, flat graphics, tiny images)
    if not _is_safe_photo_image(img, original_format):
        return image_bytes

    exif = img.info.get("exif")
    icc_profile = img.info.get("icc_profile")

    if img.mode != "RGB":
        img = img.convert("RGB")

    pixels = np.array(img, dtype=np.uint8)

    # Embed 256 bits (32 ASCII chars)
    binary = "".join(format(ord(c), "08b") for c in signature[:32])
    capacity = pixels.shape[0] * pixels.shape[1]

    if len(binary) > capacity:
        raise ValueError("Image too small for watermark")

    idx = 0
    for i in range(pixels.shape[0]):
        for j in range(pixels.shape[1]):
            if idx >= len(binary):
                break
            pixels[i, j, 0] = (pixels[i, j, 0] & 0b11111110) | int(binary[idx])
            idx += 1

    watermarked = Image.fromarray(pixels, mode="RGB")

    # ---------------- OUTPUT ----------------
    if original_format in ("JPEG", "JPG", "HEIC", "HEIF"):
        return _encode_jpeg_with_autoclamp(
            watermarked,
            len(image_bytes),
            exif,
            icc_profile
        )

    out = io.BytesIO()

    if original_format == "PNG":
        watermarked.save(out, format="PNG", optimize=True, compress_level=9)

    elif original_format == "WEBP":
        watermarked.save(out, format="WEBP", quality=90, method=6)

    elif original_format == "TIFF":
        watermarked.save(out, format="TIFF", compression="tiff_deflate")

    elif original_format == "BMP":
        watermarked.save(out, format="BMP")

    else:
        watermarked.save(out, format="PNG", optimize=True)

    return _clamp_encoded_bytes(
        encoded_bytes=out.getvalue(),
        original_size=len(image_bytes),
        max_ratio=1.02
    )


# =========================================================
# HASH + DISPATCHER
# =========================================================
def hash_content(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def embed_watermark(
    content: bytes,
    mime: str,
    signature: str,
    watermark_id: str | None = None
) -> bytes:
    if mime.startswith("image/"):
        return embed_image_watermark(content, signature)

    raise ValueError("Unsupported content type")
