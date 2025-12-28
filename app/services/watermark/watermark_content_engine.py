import hashlib
import io
from PIL import Image
import numpy as np
from PyPDF2 import PdfReader, PdfWriter
from docx import Document


# ---------- IMAGE ----------
def embed_image_watermark(image_bytes: bytes, signature: str) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    original_format = img.format  # JPEG, PNG, WEBP, etc.

    img = img.convert("RGB")
    pixels = np.array(img, dtype=np.uint8)

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

    # ✅ SAVE USING ORIGINAL FORMAT
    Image.fromarray(pixels, mode="RGB").save(
        out,
        format=original_format,
        quality=95 if original_format == "JPEG" else None,
        optimize=True
    )

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
