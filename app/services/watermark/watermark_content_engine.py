import hashlib
import io
from PIL import Image
import numpy as np
from PyPDF2 import PdfReader, PdfWriter
from docx import Document


# ---------- IMAGE ----------
def _jpeg_quality_for_size(size_bytes: int) -> int:
    if size_bytes < 80_000:
        return 85
    if size_bytes < 200_000:
        return 90
    return 93


def embed_image_watermark(image_bytes: bytes, signature: str) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    original_format = (img.format or "PNG").upper()

    # Strip metadata (important for size stability)
    img.info.pop("exif", None)

    # Convert to RGB safely
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")

    pixels = np.array(img, dtype=np.uint8)

    # Prepare watermark bits (256 bits max)
    binary = ''.join(format(ord(c), '08b') for c in signature[:32])
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

    out = io.BytesIO()
    watermarked = Image.fromarray(pixels, mode="RGB")

    # ---------- FORMAT-SPECIFIC SAVING ----------
    if original_format in ("JPEG", "JPG"):
        quality = _jpeg_quality_for_size(len(image_bytes))
        watermarked.save(
            out,
            format="JPEG",
            quality=quality,
            subsampling=2,     # preserve 4:2:0
            optimize=True
        )

    elif original_format == "PNG":
        watermarked.save(
            out,
            format="PNG",
            optimize=True,
            compress_level=9
        )

    elif original_format == "WEBP":
        watermarked.save(
            out,
            format="WEBP",
            quality=90,
            method=6
        )

    elif original_format == "TIFF":
        watermarked.save(
            out,
            format="TIFF",
            compression="tiff_deflate"
        )

    elif original_format == "BMP":
        watermarked.save(out, format="BMP")

    elif original_format == "GIF":
        # GIF must be palette-based
        watermarked.convert("P", palette=Image.ADAPTIVE).save(
            out,
            format="GIF",
            optimize=True
        )

    else:
        # Safe fallback
        watermarked.save(out, format="PNG", optimize=True)

    return out.getvalue()

# ---------- PDF ----------
def embed_pdf_watermark(pdf_bytes: bytes, asset_id: str, signature: str) -> bytes:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    writer.add_metadata({
        "/AuroraaAssetID": asset_id,
        "/AuroraaSignature": signature
    })

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


# ---------- DOCX ----------
def embed_docx_watermark(docx_bytes: bytes, asset_id: str, signature: str) -> bytes:
    doc = Document(io.BytesIO(docx_bytes))
    doc.core_properties.comments = f"Auroraa:{asset_id}:{signature}"

    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


# ---------- DISPATCHER ----------
def embed_watermark(content: bytes, mime: str, asset_id: str, signature: str) -> bytes:
    if mime.startswith("image/"):
        return embed_image_watermark(content, signature)

    if mime == "application/pdf":
        return embed_pdf_watermark(content, asset_id, signature)

    if mime.endswith("wordprocessingml.document"):
        return embed_docx_watermark(content, asset_id, signature)

    raise ValueError("Unsupported content type")


def hash_content(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
