from PIL import Image
import numpy as np
import io

def embed_image_watermark(image_bytes: bytes, signature: str) -> bytes:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    pixels = np.array(img)

    binary = ''.join(format(ord(c), '08b') for c in signature[:32])
    idx = 0

    for i in range(pixels.shape[0]):
        for j in range(pixels.shape[1]):
            if idx >= len(binary):
                break
            pixels[i, j, 0] = (pixels[i, j, 0] & ~1) | int(binary[idx])
            idx += 1

    watermarked = Image.fromarray(pixels)
    out = io.BytesIO()
    watermarked.save(out, format="PNG")
    return out.getvalue()



from PyPDF2 import PdfReader, PdfWriter
import io

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


from docx import Document

def embed_docx_watermark(path, asset_id, signature):
    doc = Document(path)
    doc.core_properties.comments = f"Auroraa:{asset_id}:{signature}"
    doc.save(path)
