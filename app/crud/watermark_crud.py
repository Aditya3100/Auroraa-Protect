from sqlalchemy.orm import Session
from app.models.models import Watermark
from app.schemas.watermark_schemas import WatermarkCreate

import hashlib
from sqlalchemy.orm import Session

from app.models.models import Watermark
from app.services.watermark.lsb.watermark_lsb_extractor import extract_image_watermark
from app.services.watermark.lsb.watermark_lsb_embedder import hash_content

# ---------- CONTENT TYPE MAPPER ----------
def map_content_type(mime: str) -> str:
    mime = mime.split(";")[0].lower()

    if mime.startswith("image/"):
        return "image"
    if mime.startswith("video/"):
        return "video"
    if mime.startswith("audio/"):
        return "audio"
    return "document"